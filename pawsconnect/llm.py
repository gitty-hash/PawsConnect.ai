"""One gateway for every model call in PawsConnect.

Course reference
----------------
* Chapter 2 lab (02a/02b multi-modal notebooks): the single ``ask_llm()`` helper,
  ``encode_image_base64()`` and the multimodal message format (a *list* of text +
  image parts), ``detail="low"`` for product/pet photos.
* Chapter 3 lab (03_prompt_engineering.ipynb): the ``chat()`` gateway with
  ``temperature`` and ``json_mode`` - "one place for mock mode, model choice and
  options".  Mock mode there returns canned answers per ``tag``; here the same
  idea becomes **cached demo mode**: every response recorded from a real
  gpt-4o-mini run is replayed, so the app runs with no API key (assignment
  Section 5).

Two modes
---------
``cached`` - replay recorded responses from ``cache/cached_responses.json``.
``live``   - call the OpenAI API; the key is read from ``OPENAI_API_KEY`` (never
             hard-coded).  ``record=True`` additionally stores each response in
             the cache file (used by ``scripts/record_cache.py``).

The cache key is a hash of everything that influences the answer (tag, sample
slot, temperature, json_mode, model and the full message text), so editing a
prompt automatically invalidates its cached answers instead of silently serving
stale ones.  Images are hashed by their *original file bytes* so a cache
recorded on one computer still matches on another.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "cache" / "cached_responses.json"

MODEL = "gpt-4o-mini"  # cheap, fast, and it can see images (Chapter 2/3 labs)

# Approximate public price for gpt-4o-mini, USD per 1M tokens (for the cost meter only).
PRICE_IN, PRICE_OUT = 0.15, 0.60


class CacheMiss(Exception):
    """Raised in cached mode when an input was never recorded."""


class LiveUnavailable(Exception):
    """Raised in live mode when no API key / client is available."""


# --------------------------------------------------------------------------- images
def image_part(raw_bytes: bytes, detail: str = "low", max_side: int = 1024) -> dict:
    """Build the image part of a multimodal message (Chapter 2: base64 data URL).

    The photo is downscaled before sending - cheaper and plenty for a pet photo.
    ``_orig_sha`` carries the hash of the *original* bytes for the cache key and is
    stripped before the request is sent.
    """
    from PIL import Image  # local import keeps module import light

    img = Image.open(io.BytesIO(raw_bytes))
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": detail},
        "_orig_sha": hashlib.sha256(raw_bytes).hexdigest()[:20],
    }


def _strip_private(messages: list[dict]) -> list[dict]:
    """Remove ``_``-prefixed helper keys before the request goes to the API."""
    clean = copy.deepcopy(messages)
    for m in clean:
        if isinstance(m.get("content"), list):
            for part in m["content"]:
                for k in [k for k in part if k.startswith("_")]:
                    part.pop(k)
    return clean


def _key_view(messages: list[dict]) -> list[dict]:
    """Messages as they enter the cache key: image data URLs -> original-file hash."""
    view = copy.deepcopy(messages)
    for m in view:
        if isinstance(m.get("content"), list):
            for part in m["content"]:
                if part.get("type") == "image_url":
                    part["image_url"] = {"detail": part["image_url"].get("detail"),
                                         "sha": part.get("_orig_sha", "")}
                    part.pop("_orig_sha", None)
    return view


def make_key(model, tag, slot, temperature, json_mode, messages) -> str:
    payload = json.dumps(
        {"model": model, "tag": tag, "slot": slot, "temperature": temperature,
         "json_mode": json_mode, "messages": _key_view(messages)},
        sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- cache
_cache_store: dict | None = None


def _load_cache() -> dict:
    global _cache_store
    if _cache_store is None:
        if CACHE_PATH.exists():
            _cache_store = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        else:
            _cache_store = {"meta": {}, "entries": {}}
    return _cache_store


def save_cache() -> None:
    store = _load_cache()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(store, indent=1, ensure_ascii=False), encoding="utf-8")


def cache_size() -> int:
    return len(_load_cache()["entries"])


# --------------------------------------------------------------------------- gateway
def new_usage() -> dict:
    return {"calls": 0, "replays": 0, "prompt_tokens": 0, "completion_tokens": 0}


def estimate_cost(usage: dict) -> float:
    return usage["prompt_tokens"] / 1e6 * PRICE_IN + usage["completion_tokens"] / 1e6 * PRICE_OUT


class LLMGateway:
    """``chat(messages, tag, ...)`` -> reply string, in cached or live mode."""

    def __init__(self, mode: str = "cached", model: str = MODEL,
                 record: bool = False, usage: dict | None = None, reuse_recorded: bool = False):
        assert mode in ("cached", "live")
        self.mode, self.model, self.record = mode, model, record
        self.reuse_recorded = reuse_recorded   # recording only: skip calls whose answer is already cached
        self.usage = usage if usage is not None else new_usage()
        self._client = None

    # -- live client -------------------------------------------------------
    def _get_client(self):
        if self._client is not None:
            return self._client
        api_key = os.environ.get("OPENAI_API_KEY", "")   # best practice: never hard-code keys
        if not api_key:
            raise LiveUnavailable(
                "Live mode needs the OPENAI_API_KEY environment variable. "
                "Switch to Cached demo mode, or set the key and restart the app.")
        from openai import OpenAI
        try:
            # Same idea as the PATCH in the course notebooks: ask for uncompressed
            # responses (avoids a Brotli decoder problem on some setups). The notebooks
            # use httpx2; plain httpx (installed with openai) does the same job and works
            # on every machine.
            import httpx
            self._client = OpenAI(api_key=api_key,
                                  http_client=httpx.Client(headers={"Accept-Encoding": "identity"}))
        except Exception:
            self._client = OpenAI(api_key=api_key)
        return self._client

    # -- the one function every feature calls -------------------------------
    def chat(self, messages: list[dict], tag: str, slot: int = 0,
             temperature: float = 0.0, json_mode: bool = False) -> str:
        """Send a chat request (or replay it from the cache).

        messages    : list of {"role": "system"|"user"|"assistant", "content": ...}
        tag         : readable label for this call site (also part of the cache key)
        slot        : sample index for repeated identical calls (self-consistency)
        temperature : 0 = deterministic (classification, judging); >0 = diverse
        json_mode   : ask the API to guarantee a syntactically valid JSON object
        """
        key = make_key(self.model, tag, slot, temperature, json_mode, messages)

        if self.mode == "cached":
            entry = _load_cache()["entries"].get(key)
            if entry is None:
                raise CacheMiss(
                    "This input was not recorded in the cached demo. "
                    "Pick one of the bundled samples, or switch to Live mode "
                    "(needs OPENAI_API_KEY) to try your own input.")
            self.usage["replays"] = self.usage.get("replays", 0) + 1     # replayed, not a live API call
            return entry["response"]

        if self.record and self.reuse_recorded:
            entry = _load_cache()["entries"].get(key)
            if entry is not None:
                return entry["response"]

        client = self._get_client()
        kwargs = {"model": self.model, "messages": _strip_private(messages),
                  "temperature": temperature}
        if json_mode:
            # response_format makes the API return syntactically valid JSON -
            # essential when code (not a human) reads the output (Ch.2 / Ch.3 labs).
            kwargs["response_format"] = {"type": "json_object"}

        last_err = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(**kwargs)
                break
            except Exception as err:  # transient network / rate-limit errors
                last_err = err
                name = type(err).__name__
                if name in ("APIConnectionError", "RateLimitError", "InternalServerError", "APITimeoutError"):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        else:
            raise last_err  # type: ignore[misc]

        text = resp.choices[0].message.content or ""
        self.usage["calls"] += 1
        if resp.usage:
            self.usage["prompt_tokens"] += resp.usage.prompt_tokens
            self.usage["completion_tokens"] += resp.usage.completion_tokens

        if self.record:
            store = _load_cache()
            store["meta"] = {"model": self.model, "recorded": time.strftime("%Y-%m-%d")}
            store["entries"][key] = {"tag": tag, "slot": slot, "response": text}
        return text


def parse_json(raw: str) -> dict:
    """Parse a model reply that should be JSON (tolerates ```json fences)."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)
