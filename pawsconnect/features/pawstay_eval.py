"""Evaluation harness + regression gate for PawStay.

Chapter 1 (00_llm_benchmarks_deepeval.ipynb + mis552_eval.py)
* "A benchmark is questions + an answer key + a scoring rule" -> our labelled set of
  check-ins (``data/pawstay_cases.json``, ``gold``) and the metrics below.
* "A score means nothing without the sample size and the distance from chance" -> the
  report prints the number of cases next to every rate.
* Section 7b "the regression gate": ``deployment_gate`` blocks a release when a
  threshold is missed. Ours puts safety first: every urgent case must be escalated.

All gold labels are SYNTHETIC (written for this course project) - see the data file.
"""
from __future__ import annotations

from ..llm import LLMGateway
from .common import load_json
from .pawstay import run_case

URGENT = "Urgent Human Follow-up"

# Gate thresholds (derive them from your own baseline - Chapter 1 notebook, section 7c).
GATE = {"urgent_escalation_recall": 1.00, "status_accuracy": 0.80, "guardrail_failures": 0}


def load_cases() -> list[dict]:
    return load_json("pawstay_cases.json")["cases"]


def evaluate(gw: LLMGateway, cases: list[dict] | None = None, progress=None) -> dict:
    cases = cases or load_cases()
    rows = []
    for ci, case in enumerate(cases):
        results = run_case(gw, case)
        for chk, res in zip(case["checkins"], results):
            a, g = res["assessment"], chk["gold"]
            rows.append({
                "case": case["pet_name"], "day": chk["day"],
                "gold_status": " / ".join(g["status"]), "pred_status": a["status"],
                "status_ok": a["status"] in g["status"],
                "gold_trend": " / ".join(g["trend"]), "pred_trend": a["trend"],
                "trend_ok": a["trend"] in g["trend"],
                "gold_concern": g.get("concern", ""), "pred_concern": a["concern_category"],
                "human_review": a["human_review"], "route": a["recommended_route"],
                "gold_urgent": g["status"] == [URGENT],
                "gold_stable_only": g["status"] == ["Stable"],
                "ambiguous": bool(g.get("ambiguous")),
                "outcome": res["outcome"],
                "judge_first_try": res["attempts"][0]["judge"]["verdict"] == "pass",
            })
        if progress:
            progress((ci + 1) / len(cases), f"Evaluated {case['pet_name']}")
    return summarize(rows)


def _rate(num: int, den: int):
    return (num / den) if den else None


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    urgent = [r for r in rows if r["gold_urgent"]]
    stable_only = [r for r in rows if r["gold_stable_only"]]
    ambiguous = [r for r in rows if r["ambiguous"]]
    m = {
        "n_checkins": n,
        "n_cases": len({r["case"] for r in rows}),
        "status_accuracy": _rate(sum(r["status_ok"] for r in rows), n),
        "trend_accuracy": _rate(sum(r["trend_ok"] for r in rows), n),
        "n_urgent": len(urgent),
        "urgent_label_recall": _rate(sum(r["pred_status"] == URGENT for r in urgent), len(urgent)),
        "urgent_escalation_recall": _rate(sum(r["human_review"] and r["pred_status"] != "Stable" for r in urgent), len(urgent)),
        "n_stable_only": len(stable_only),
        "false_alarm_rate": _rate(sum(r["pred_status"] != "Stable" for r in stable_only), len(stable_only)),
        "n_ambiguous": len(ambiguous),
        "ambiguous_flagged_rate": _rate(sum(r["human_review"] for r in ambiguous), len(ambiguous)),
        "judge_first_pass_rate": _rate(sum(r["judge_first_try"] for r in rows), n),
        "revised_count": sum(r["outcome"] == "revised" for r in rows),
        "guardrail_failures": sum(r["outcome"] == "guardrail_failed" for r in rows),
        "rows": rows,
    }
    m["gate"] = deployment_gate(m)
    return m


def deployment_gate(m: dict) -> dict:
    """Pass/fail per threshold - the Chapter 1 'regression gate' idea."""
    checks = {
        "Every urgent case escalated to a human": (m["urgent_escalation_recall"] is not None
                                                  and m["urgent_escalation_recall"] >= GATE["urgent_escalation_recall"]),
        f"Status accuracy >= {GATE['status_accuracy']:.0%}": (m["status_accuracy"] or 0) >= GATE["status_accuracy"],
        "No guardrail failures (judge satisfied after one retry)": m["guardrail_failures"] <= GATE["guardrail_failures"],
    }
    return {"checks": checks, "passed": all(checks.values())}
