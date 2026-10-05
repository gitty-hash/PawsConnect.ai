"""Instrumentation for PawStay's business KPIs.

The four KPIs the shelter cares about:
  1. 30-day post-adoption return rate
  2. average time from a concerning check-in to human intervention
  3. share of flagged placements stabilised without a return
  4. share of urgent cases correctly escalated for human review
KPI 4 comes from the evaluation harness (pawstay_eval.py). KPIs 1-3 need *outcome and
timing data*, so the app logs staff actions to an append-only JSONL file; the KPI board
reads from it. ``data/pawstay_events_seed.jsonl`` holds SYNTHETIC seed events so the
board is not empty on first launch - the UI always says how many events are seed data.

Event shapes
    {"type": "flag",    "case_id", "day", "status", "ts"}          check-in flagged by PawStay
    {"type": "contact", "case_id", "day", "ts"}                    staff contacted the adopter
    {"type": "outcome", "case_id", "outcome": "stabilised"|"returned"|"active", "ts"}
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .common import DATA

LIVE_LOG = DATA / "pawstay_events.jsonl"
SEED_LOG = DATA / "pawstay_events_seed.jsonl"


def _read(path: Path, seed: bool) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            e["_seed"] = seed
            out.append(e)
    return out


def all_events() -> list[dict]:
    return _read(SEED_LOG, True) + _read(LIVE_LOG, False)


def log_event(event: dict) -> None:
    event = {**event, "ts": event.get("ts", time.time())}
    LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with LIVE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def kpi_summary(events: list[dict] | None = None) -> dict:
    events = events if events is not None else all_events()
    flags = {(e["case_id"], e["day"]): e for e in events if e["type"] == "flag"}
    contacts = {(e["case_id"], e["day"]): e for e in events if e["type"] == "contact"}
    outcomes: dict[str, str] = {}
    for e in events:                                   # last outcome wins
        if e["type"] == "outcome":
            outcomes[e["case_id"]] = e["outcome"]

    hours = [(contacts[k]["ts"] - flags[k]["ts"]) / 3600 for k in flags if k in contacts and contacts[k]["ts"] >= flags[k]["ts"]]
    flagged_cases = {k[0] for k in flags}
    decided = [c for c in outcomes if outcomes[c] in ("stabilised", "returned")]
    returned = [c for c in decided if outcomes[c] == "returned"]
    flagged_decided = [c for c in flagged_cases if outcomes.get(c) in ("stabilised", "returned")]
    flagged_stable = [c for c in flagged_decided if outcomes[c] == "stabilised"]
    return {
        "n_events": len(events),
        "n_seed_events": sum(e["_seed"] for e in events),
        "n_flags": len(flags),
        "n_contacts": len(hours),
        "avg_hours_to_contact": (sum(hours) / len(hours)) if hours else None,
        "n_decided": len(decided),
        "return_rate": (len(returned) / len(decided)) if decided else None,
        "n_flagged_decided": len(flagged_decided),
        "flagged_stabilised_rate": (len(flagged_stable) / len(flagged_decided)) if flagged_decided else None,
    }
