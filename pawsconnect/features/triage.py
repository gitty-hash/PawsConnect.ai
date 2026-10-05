"""Part C1 - Adoption inquiry triage.

Chapter 3 (03_prompt_engineering.ipynb, Step 2 "Triage support tickets into JSON"):
few-shot prompting - worked examples inside the prompt teach both the task and the
exact JSON format; the label set is pinned in the instruction (Step 1 lesson).
``json_mode=True`` + ``temperature=0`` as in the lab; ``json.loads`` so downstream code
gets a dict, not a string.
"""
from __future__ import annotations

from ..llm import LLMGateway, parse_json
from ..prompts import ROUTING_TEAMS, TRIAGE_CATEGORIES, TRIAGE_FEW_SHOT, TRIAGE_SYSTEM, URGENCY_LEVELS
from .common import as_bool, pick

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CONF = ["high", "medium", "low"]


def triage_message(gw: LLMGateway, text: str) -> dict:
    messages = [
        {"role": "system", "content": TRIAGE_SYSTEM},
        # Examples + the new input in the user turn - the few-shot pattern from the lab.
        {"role": "user", "content": f'{TRIAGE_FEW_SHOT}\n\nMessage: "{text}"\nOutput:'},
    ]
    raw = gw.chat(messages, tag="triage", temperature=0, json_mode=True)
    return normalise_triage(parse_json(raw))


def normalise_triage(d: dict) -> dict:
    reasons: list[str] = []
    category = pick(d.get("category"), list(TRIAGE_CATEGORIES), None)
    urgency = pick(d.get("urgency"), list(URGENCY_LEVELS), None)
    routing = pick(d.get("suggested_routing"), ROUTING_TEAMS, None)
    if category is None or urgency is None or routing is None:
        reasons.append("Model returned a label outside the allowed set.")
        category = category or "other_or_spam"
        urgency = urgency or "high"            # unknown -> treat cautiously
        routing = routing or "Front Desk / Auto-reply"
    confidence = pick(d.get("confidence"), CONF, "low")
    human_review = as_bool(d.get("human_review"))

    # Rules the platform enforces on top of the model (Chapter 7 preview: guardrails).
    if confidence == "low":
        reasons.append("Low model confidence.")
    if category == "medical_question" and urgency in ("critical", "high"):
        reasons.append("Possible animal emergency - a human must confirm.")
    if category == "found_stray_report" and urgency in ("critical", "high"):
        reasons.append("Injured or distressed stray reported.")
    if human_review and not reasons:
        reasons.append("Model asked for human review.")

    return {
        "category": category,
        "urgency": urgency,
        "suggested_routing": routing,
        "summary": str(d.get("summary") or ""),
        "reason": str(d.get("reason") or ""),
        "confidence": confidence,
        "human_review": human_review or bool(reasons),
        "review_reasons": reasons,
    }
