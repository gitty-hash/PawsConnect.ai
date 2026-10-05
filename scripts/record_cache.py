"""Record the cached-demo responses by running every bundled sample through the REAL model.

    python scripts/record_cache.py                 # record everything
    python scripts/record_cache.py --only triage   # re-record one feature
    python scripts/record_cache.py --fresh         # ignore what is already recorded

Needs OPENAI_API_KEY in the environment. Responses are written to
cache/cached_responses.json, keyed by a hash of the full prompt - so after editing a
prompt, re-run this script (the app will say "not recorded" until you do).
The script saves after every feature and skips calls that are already recorded, so an
interrupted run can simply be started again. Independent samples run in parallel.
Typical cost with gpt-4o-mini: well under $0.50 for everything.
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pawsconnect import llm  # noqa: E402
from pawsconnect.features import counselor, match, pawstay, profile, triage  # noqa: E402
from pawsconnect.features.common import load_json  # noqa: E402
from pawsconnect.features.pawstay_eval import load_cases  # noqa: E402
from pawsconnect.tabs.counselor_tab import SCENARIOS  # noqa: E402

FEATURES = ["profile", "triage", "counselor", "match", "pawstay"]
WORKERS = 6


def pmap(fn, items):
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        return list(ex.map(fn, items))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated subset of: " + ",".join(FEATURES))
    ap.add_argument("--fresh", action="store_true", help="re-call the model even if a response is already recorded")
    args = ap.parse_args()
    wanted = args.only.split(",") if args.only else FEATURES

    gw = llm.LLMGateway("live", record=True, reuse_recorded=not args.fresh)
    t0 = time.time()
    llm.cache_size()          # load the cache file once, before worker threads start

    if "profile" in wanted:
        files = sorted((ROOT / "Testing_Images").glob("*.jpg"))
        for f, p in zip(files, pmap(lambda f: profile.generate_profile(gw, f.read_bytes()), files)):
            print(f"[profile] {f.name:22} species={p['species']:5} breed={p['breed_confidence']:6} "
                  f"age={p['age_confidence']:6} pers={p['personality_confidence']:6} review={p['human_review']}", flush=True)
        llm.save_cache()
    if "triage" in wanted:
        qs = load_json("inquiries.json")
        for q, r in zip(qs, pmap(lambda q: triage.triage_message(gw, q["text"]), qs)):
            print(f"[triage ] {q['id']} {r['urgency']:8} {r['category']:24} {r['suggested_routing']:30} review={r['human_review']}", flush=True)
        llm.save_cache()
    if "counselor" in wanted:
        pets = {p["id"]: p for p in load_json("pet_listings.json")}
        items = list(SCENARIOS.items())
        for (key, sc), t in zip(items, pmap(lambda kv: counselor.guarded_reply(gw, pets[kv[1]["pet"]], kv[1]["msg"], [], kv[1]["weak"]), items)):
            print(f"[counsel] {key:12} outcome={t['outcome']}", flush=True)
        llm.save_cache()
    if "match" in wanted:
        pets = load_json("pet_listings.json")
        combos = [(prof, pet) for prof in load_json("adopter_profiles.json") for pet in pets]
        for (prof, pet), m in zip(combos, pmap(lambda pp: match.explain_match(gw, pp[0]["profile"], pp[1]), combos)):
            print(f"[match  ] {prof['id']:10} x {pet['id']:8} -> {m['final']:13} votes={m['votes']}", flush=True)
        llm.save_cache()
    if "pawstay" in wanted:
        cases = load_cases()
        for case, res in zip(cases, pmap(lambda c: pawstay.run_case(gw, c), cases)):
            print(f"[pawstay] {case['case_id']:8} " + " | ".join(
                f"D{r['day']}:{r['assessment']['status'][:6]}/{r['outcome'][:4]}" for r in res), flush=True)
        r = pawstay.judge_stress_test(gw)
        print(f"[pawstay] guardrail stress test -> {r['verdict']} {r['checks']}", flush=True)
        llm.save_cache()

    u = gw.usage
    print(f"\nSaved {llm.cache_size()} cache entries. {u['calls']} model calls this run, "
          f"{u['prompt_tokens']} in / {u['completion_tokens']} out tokens, "
          f"approx ${llm.estimate_cost(u):.3f}, {time.time() - t0:.0f}s.", flush=True)


if __name__ == "__main__":
    main()
