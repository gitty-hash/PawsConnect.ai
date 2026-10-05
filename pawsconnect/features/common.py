"""Small shared helpers: data loading and enum validation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def pick(value, allowed, default):
    """Return ``value`` if it is one of ``allowed`` (case-insensitive), else ``default``.

    The model is told to use a fixed label set (Chapter 3: "pin the label set so the
    model cannot invent categories") - this is the code-side check that it did.
    """
    if isinstance(value, str):
        for a in allowed:
            if value.strip().lower() == a.lower():
                return a
    return default


def as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return bool(value)


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _norm_text(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", s.lower())).strip()


HEDGES = ("can't", "cant", "cannot", "can not", "not ", "no guarantee", "confirm", "check with", "may ", "might",
          "unable", "unsure", "don't know", "do not know", "isn't", "never ")


def evidence_gate(raw_checks: dict, violations: list, text: str, hedge_checks: tuple = (),
                  confirmers: dict | None = None) -> tuple[dict, list, list]:
    """Keep a judge's "fail" only if it copied offending words that really occur in ``text``.

    v2/v3 testing showed gpt-4o-mini as judge inventing violations (and flagging replies that
    *refuse* to promise availability). A fail without verbatim evidence is discarded; for the
    checks in ``hedge_checks`` a quoted sentence that is hedged or negated ("I can't promise...")
    is discarded too. ``confirmers`` maps a check name to a compiled regex that the quoted phrase
    must ALSO match (a two-key guardrail: the LLM finds the phrase, a policy lexicon confirms it).
    Returns (final_checks, supported_violations, discarded_check_names).
    """
    import re
    norm = _norm_text(text)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    final, supported, discarded = {}, [], []
    for check, verdict in raw_checks.items():
        if verdict != "fail":
            final[check] = "pass"
            continue
        proof = None
        for v in violations:
            if not isinstance(v, dict) or str(v.get("check", "")).strip() != check:
                continue
            phrase = _norm_text(str(v.get("phrase", "")))
            if not phrase or phrase not in norm:
                continue
            if confirmers and check in confirmers and not confirmers[check].search(str(v.get("phrase", ""))):
                continue
            if check in hedge_checks:
                sent = next((x for x in sentences if phrase in _norm_text(x)), "")
                if any(h in sent.lower() for h in HEDGES):
                    continue
            proof = v
            break
        if proof:
            final[check] = "fail"
            supported.append({"check": check, "phrase": str(proof["phrase"])})
        else:
            final[check] = "pass"
            discarded.append(check)
    return final, supported, discarded
