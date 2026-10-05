"""Part C2 - Adoption counselor persona with an LLM-as-judge guardrail.

Chapter 3 (03_prompt_engineering.ipynb)
* Step 4 "Meet Skye": a ``role: "system"`` message defines persona + policy; the
  persona is the product.
* Step 6 "LLM-as-judge": ``draft -> judge -> (send | retry with feedback | escalate)``.
  The judge sees the rubric, the user message and the draft - NOT the persona
  prompt (fresh eyes); it runs at temperature 0 and returns JSON so code can act.
Chapter 2 lab Part 1 (CampusMart assistant): the LISTING block pasted into the
prompt is *grounding* - the model answers from our data, not from memory.

Difference from the lab: the assignment asks for ``pass`` / ``revise`` and for the
app to react visibly - we regenerate ONCE with the judge's feedback, and if the
second draft still fails we show an escalate-to-human message instead.
"""
from __future__ import annotations

import re

from ..llm import LLMGateway, parse_json
from ..prompts import (COUNSELOR_ESCALATION_MESSAGE, COUNSELOR_JUDGE_SYSTEM,
                       COUNSELOR_SYSTEM, COUNSELOR_WEAK_SYSTEM)
from .common import as_list, evidence_gate, pick

CHECKS = ["in_scope", "listing_consistent", "tone", "no_medical_advice", "honesty_rules"]

# Two-key guardrail: for these rules a judge fail also needs the quoted phrase to match a
# policy lexicon (the course judge flagged "would be a great fit" as a promise - see prompts.md).
CONFIRMERS = {
    "honesty_rules": re.compile(
        r"\b(is|are|still|currently|definitely|totally)\b.{0,20}\bavailable\b|waiting for you|reserved for you|"
        r"(will|'ll|going to) be (approved|yours)|guarantee\w*|promise\w*|he'?s yours|she'?s yours", re.I),
    "no_medical_advice": re.compile(
        r"\b(medicat\w*|medicine|dose|dosage|mg|ibuprofen|tylenol|aspirin|antibiotic\w*|pepto|home remedy|"
        r"diagnos\w*|you should give|try giving|give (him|her|them) (some|a))\b", re.I),
}


def format_listing(pet: dict) -> str:
    """Render the shelter's record of one pet as the LISTING block (grounding)."""
    return "\n".join([
        f"Name: {pet['name']}",
        f"Species / breed: {pet['species']} - {pet['breed_note']}",
        f"Age: {pet['age_text']}; sex: {pet['sex']}; weight: {pet['weight_lb']} lb",
        f"Energy: {pet['energy']}",
        f"Good with kids: {pet['good_with_kids']}",
        f"Good with dogs: {pet['good_with_dogs']}",
        f"Good with cats: {pet['good_with_cats']}",
        f"Alone time: {pet['alone_time']}",
        f"Special needs / notes: {pet['special_needs']}",
        f"Vet status: {pet['vet_status']}",
        f"Story: {pet['story']}",
    ])


def _draft(gw, system, history, listing_text, user_msg, feedback, tag):
    messages = [{"role": "system", "content": system}]
    messages += history      # earlier turns: final replies only
    user = f"LISTING:\n{listing_text}\n\nADOPTER MESSAGE: {user_msg}"
    if feedback:
        user += ("\n\n[INTERNAL reviewer feedback - fix these issues, do not mention them]: " + feedback)
    messages.append({"role": "user", "content": user})
    return gw.chat(messages, tag=tag, temperature=0.7).strip()   # lab: drafts at 0.7


def judge_reply(gw: LLMGateway, user_msg: str, listing_text: str, draft: str) -> dict:
    messages = [
        {"role": "system", "content": COUNSELOR_JUDGE_SYSTEM},
        {"role": "user", "content": f"LISTING:\n{listing_text}\n\nADOPTER MESSAGE:\n{user_msg}\n\nDRAFT REPLY:\n{draft}"},
    ]
    d = parse_json(gw.chat(messages, tag="counselor_judge", temperature=0, json_mode=True))
    raw_checks = {c: pick((d.get("checks") or {}).get(c), ["pass", "fail"], "pass") for c in CHECKS}
    # Evidence gate (common.py): a fail counts only with a verbatim, un-hedged quote from the draft.
    checks, violations, discarded = evidence_gate(raw_checks, as_list(d.get("violations")), draft,
                                                  hedge_checks=("honesty_rules",), confirmers=CONFIRMERS)
    verdict = "pass" if all(v == "pass" for v in checks.values()) else "revise"
    return {"verdict": verdict, "checks": checks, "violations": violations, "discarded_fails": discarded,
            "feedback": str(d.get("feedback") or "") if verdict == "revise" else ""}


def guarded_reply(gw: LLMGateway, pet: dict, user_msg: str, history: list[dict] | None = None,
                  weak: bool = False) -> dict:
    """draft -> judge -> (send | regenerate once with feedback | escalate to a human)."""
    history = history or []
    listing_text = format_listing(pet)
    system = COUNSELOR_WEAK_SYSTEM if weak else COUNSELOR_SYSTEM

    draft1 = _draft(gw, system, history, listing_text, user_msg, "", "counselor_draft")
    judge1 = judge_reply(gw, user_msg, listing_text, draft1)
    turn = {"user": user_msg, "weak_persona": weak, "draft1": draft1, "judge1": judge1,
            "draft2": None, "judge2": None}

    if judge1["verdict"] == "pass":
        turn.update(outcome="passed", final=draft1)
        return turn

    # Verdict "revise": visibly react - regenerate ONCE using the judge's feedback.
    draft2 = _draft(gw, system, history, listing_text, user_msg, judge1["feedback"], "counselor_redraft")
    judge2 = judge_reply(gw, user_msg, listing_text, draft2)
    turn.update(draft2=draft2, judge2=judge2)
    if judge2["verdict"] == "pass":
        turn.update(outcome="revised", final=draft2)
    else:
        turn.update(outcome="escalated", final=COUNSELOR_ESCALATION_MESSAGE)
    return turn
