"""Part D - PawStay: AI post-adoption stability monitor (innovation feature).

Stakeholder : post-adoption coordinators at the shelter (not adopters, not the public).
Task        : decide, for every Day 1/3/7/14/30 check-in, who needs a human call and how
              soon - by comparing each message with the placement's *earlier* check-ins.
Techniques  : Chapter 3 few-shot classification + structured JSON output (Step 2 of the
              StayScape lab), Chapter 3 LLM-as-judge guardrail (Step 6) that keeps the
              assistant in scope, and Chapter 1's evaluation mindset (see pawstay_eval.py:
              a labelled test set and a regression gate).

Pipeline per check-in (same draft -> judge -> retry/escalate shape as Step 6):
    1. DRAFT   - few-shot prompt + history -> JSON assessment
    2. RULES   - code-side checks: enum validation, quote verification, safety net
    3. JUDGE   - second LLM call checks scope (no diagnosis, no return advice, ...)
    4. ROUTE   - pass -> use it | revise -> regenerate ONCE with feedback | still failing
                 -> keep the case but force human review and mark guardrail_failed
"""
from __future__ import annotations

import re

from ..llm import LLMGateway, parse_json
from ..prompts import (PAWSTAY_CONCERNS, PAWSTAY_FEW_SHOT, PAWSTAY_JUDGE_SYSTEM, PAWSTAY_ROUTES,
                       PAWSTAY_STATUSES, PAWSTAY_SYSTEM, PAWSTAY_TRENDS)
from .common import as_bool, as_list, evidence_gate, pick

STATUS_RANK = {s: i for i, s in enumerate(PAWSTAY_STATUSES)}
# Three scope checks are made by the LLM judge; the last two are enforced in plain code
# (v1/v2 testing showed an LLM judge is unreliable at route and quote checking).
LLM_CHECKS = ["no_diagnosis", "no_return_recommendation", "no_advice_to_adopter"]
JUDGE_CHECKS = LLM_CHECKS + ["evidence_grounded", "escalation_correct"]

NO_ACTION = "No action - continue scheduled check-ins"
BEHAVIOUR_ROUTE = "Behavior & Support Coordinator"
# Concerns whose owner is fixed by policy; behaviour concerns keep the model's choice.
ROUTE_BY_CONCERN = {
    "possible_health_symptom": "Medical Team (vet staff)",
    "appetite_or_eating": "Medical Team (vet staff)",
    "aggression_or_safety": "Welfare & Safety Lead",
    "adopter_overwhelmed_or_return_intent": "Post-Adoption Coordinator",
}

# --- rule-based safety net -------------------------------------------------------
# Plain-Python phrases that should NEVER end a check-in as "Stable" without a human
# looking. Deliberately conservative: a match raises "Stable" to "Needs Attention" and
# sets human_review; the LLM still decides whether it is "Urgent". (Over-flagging costs a
# phone call; under-flagging can cost an animal's welfare.)
SAFETY_PATTERNS = {
    "bite or injury": r"\b(bit (my|his|her|the|our|a)\b|bitten|biting|bites|broke the skin|bleeding|blood)\b",
    "vomiting or not eating": r"\b(throw(s|ing)? up|threw up|vomit\w*|hasn'?t eaten|not eaten|refus\w+ (to )?(eat|food)|won'?t eat)\b",
    "lethargy or collapse": r"\b(lethargic|barely lifted|collaps\w+|seizure|unresponsive)\b",
    "bloated or tight belly": r"\b(bloated|swollen belly|belly looks? .{0,20}(big|tight|swollen))\b",
    "return or give-up language": r"\b(bring (him|her|them) back|return(ing)? (him|her|them|the)|give (him|her|them) back|rehome|re-home|can'?t keep|cannot keep|(don'?t|do not) know if (i|we) can keep)\b",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", s.lower())).strip()


_NEGATION = re.compile(r"\b(no|not|never|without|nothing|stopped|isn'?t|aren'?t|wasn'?t|didn'?t|hasn'?t|haven'?t)\b|n't", re.I)


def safety_flags(text: str) -> list[str]:
    """Names of risk phrases found in the text, ignoring negated mentions ("no more biting")."""
    flags = []
    for name, pat in SAFETY_PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            before = text[max(0, m.start() - 18): m.start()]
            # "hasn't eaten" / "won't eat" carry their own negation as part of the risk phrase.
            if name == "vomiting or not eating" and re.search(r"hasn'?t|not eaten|won'?t|refus", m.group(0), re.I):
                flags.append(name)
                break
            if not _NEGATION.search(before):
                flags.append(name)
                break
    return flags


# --- prompt construction ----------------------------------------------------------
def build_user_prompt(case: dict, idx: int, priors: list[dict]) -> str:
    """Placement + earlier check-ins (with the recorded assessments) + the current one.

    ``priors`` are the results already produced for check-ins 0..idx-1 - this is what
    makes PawStay *longitudinal*: the model compares, it does not judge messages alone.
    """
    lines = [f"PLACEMENT: {case['placement']}"]
    if idx == 0:
        lines.append("PRIOR CHECK-INS: none")
    else:
        lines.append("PRIOR CHECK-INS:")
        for ci, pr in zip(case["checkins"][:idx], priors[:idx]):
            a = pr["assessment"]
            lines.append(f'- Day {ci["day"]} | adopter said: "{ci["text"]}" | recorded assessment: '
                         f'{a["status"]}, concern={a["concern_category"]}')
    cur = case["checkins"][idx]
    lines.append(f'CURRENT CHECK-IN (Day {cur["day"]}): "{cur["text"]}"')
    return "\n".join(lines)


def _messages(case, idx, priors, feedback=""):
    user = f"{PAWSTAY_FEW_SHOT}\n\n{build_user_prompt(case, idx, priors)}\nOutput:"
    if feedback:
        user += ("\n\n[INTERNAL reviewer feedback - fix these issues in a new JSON object, "
                 "do not mention the reviewer]: " + feedback)
    return [{"role": "system", "content": PAWSTAY_SYSTEM}, {"role": "user", "content": user}]


# --- normalisation + code-side rules ------------------------------------------------
def normalise_assessment(d: dict) -> dict:
    evidence = []
    for e in as_list(d.get("evidence")):
        if isinstance(e, dict) and e.get("quote"):
            evidence.append({"day": e.get("day"), "quote": str(e["quote"])})
    return {
        "status": pick(d.get("status"), PAWSTAY_STATUSES, "Needs Attention"),
        "concern_category": pick(d.get("concern_category"), list(PAWSTAY_CONCERNS), "none"),
        "trend": pick(d.get("trend"), PAWSTAY_TRENDS, "Stable"),
        "positive_signals": [str(x) for x in as_list(d.get("positive_signals"))],
        "evidence": evidence,
        "explanation": str(d.get("explanation") or ""),
        "recommended_route": pick(d.get("recommended_route"), PAWSTAY_ROUTES, "Post-Adoption Coordinator"),
        "suggested_staff_action": str(d.get("suggested_staff_action") or ""),
        "human_review": as_bool(d.get("human_review")),
        "uncertainty_note": str(d.get("uncertainty_note") or ""),
    }


def verify_quotes(assessment: dict, case: dict, idx: int) -> list[str]:
    """Return evidence quotes that do NOT appear in the adopter's words (hallucinated)."""
    corpus = _norm(" ".join(c["text"] for c in case["checkins"][: idx + 1]))
    return [e["quote"] for e in assessment["evidence"] if _norm(e["quote"]) not in corpus]


def apply_safety_net(assessment: dict, text: str) -> tuple[dict, list[str]]:
    flags = safety_flags(text)
    notes = []
    if flags:
        if STATUS_RANK[assessment["status"]] == 0:     # "Stable" despite a risk phrase
            assessment["status"] = "Needs Attention"
            notes.append("Safety net raised 'Stable' to 'Needs Attention' (matched: " + ", ".join(flags) + ").")
        if not assessment["human_review"]:
            assessment["human_review"] = True
            notes.append("Safety net set human review (matched: " + ", ".join(flags) + ").")
    # Rule: Needs Attention / Urgent about health, safety or return intent always has a human.
    if assessment["status"] != "Stable" and not assessment["human_review"]:
        assessment["human_review"] = True
        notes.append("Any non-stable status needs human review.")
    return assessment, notes


def enforce_routing(a: dict) -> tuple[dict, list[str]]:
    """Make the route consistent with the status and concern (code, not LLM)."""
    notes = []
    if a["status"] == "Stable":
        if a["recommended_route"] != NO_ACTION:
            a["recommended_route"] = NO_ACTION
            notes.append("Route set to 'no action' because the status is Stable.")
    else:
        forced = ROUTE_BY_CONCERN.get(a["concern_category"])
        if forced and a["recommended_route"] != forced:
            a["recommended_route"] = forced
            notes.append(f"Route set to '{forced}' by policy for this concern.")
        elif not forced and a["recommended_route"] == NO_ACTION:
            a["recommended_route"] = BEHAVIOUR_ROUTE
            notes.append("A non-stable status cannot route to 'no action'.")
    return a, notes


# --- policy lexicons used to CONFIRM a judge violation (two-key guardrail) ------------------
# v4 testing: gpt-4o-mini quoted real phrases but misjudged them ("discuss ... management
# strategies" is not advice). A judge fail therefore counts only if the quoted phrase also
# matches the policy lexicon for that rule.
CONFIRMERS = {
    "no_diagnosis": re.compile(
        r"\b(bloat|gdv|volvulus|parvo\w*|distemper|kennel cough|infection|infected|disease|disorder|syndrome|"
        r"separation anxiety|anxiety|depress\w*|resource guarding|aggressive|ptsd|ocd|arthritis|diabet\w*|"
        r"pancreatitis|poison\w*|worms?|parasite\w*|allerg\w*)\b", re.I),
    "no_return_recommendation": re.compile(
        # "consider" only as an imperative: "are considering returning" describes the ADOPTER and must not match.
        r"\b(should|must|best to|better to|recommend\w*|suggest\w*|consider|advis\w*|encourag\w*|time to)\b.{0,40}"
        r"\b(return\w*|rehom\w*|re-hom\w*|surrender\w*|give (him|her|them) up|give up)\b", re.I),
    "no_advice_to_adopter": re.compile(
        r"\b(should|must|need to|needs to|tell|advise|instruct|recommend\w*|suggest\w*)\b.{0,40}"
        r"\b(feed\w*|give|crate\w*|train\w*|walk\w*|separate|avoid|try|use|medicat\w*|dose|supplement\w*|ignore)\b"
        r"|\b(dose|dosage|medication|medicine|supplement|melatonin|crate-train)\b", re.I),
}


# --- judge ------------------------------------------------------------------------------
def _reviewed_text(a: dict) -> str:
    return (f"explanation: {a['explanation']}\n"
            f"suggested_staff_action: {a['suggested_staff_action']}\n"
            f"uncertainty_note: {a['uncertainty_note']}")


def judge_assessment(gw: LLMGateway, assessment: dict) -> dict:
    """LLM-as-judge on the assistant's OWN text only, with an evidence gate.

    A failed check counts only if the judge copies the offending words and those words
    really occur in the reviewed text; otherwise the fail is discarded as unsupported.
    (Chapter 3 judge pattern + a code-side check, after v2 testing showed the judge
    inventing violations.)
    """
    text = _reviewed_text(assessment)
    d = parse_json(gw.chat([{"role": "system", "content": PAWSTAY_JUDGE_SYSTEM},
                            {"role": "user", "content": "TEXT TO REVIEW:\n" + text}],
                           tag="pawstay_judge", temperature=0, json_mode=True))
    raw_checks = {c: pick((d.get("checks") or {}).get(c), ["pass", "fail"], "pass") for c in LLM_CHECKS}
    checks, supported, discarded = evidence_gate(raw_checks, as_list(d.get("violations")), text,
                                                 confirmers=CONFIRMERS)
    verdict = "pass" if all(v == "pass" for v in checks.values()) else "revise"
    return {"verdict": verdict, "checks": checks, "violations": supported, "discarded_fails": discarded,
            "feedback": str(d.get("feedback") or "") if verdict == "revise" else ""}


# --- the pipeline -----------------------------------------------------------------------
def assess_checkin(gw: LLMGateway, case: dict, idx: int, priors: list[dict]) -> dict:
    """Run draft -> rules -> judge -> (accept | regenerate once | force human review)."""
    text = case["checkins"][idx]["text"]
    attempts = []
    feedback = ""
    result = None
    for attempt in range(2):                                   # draft, then ONE regeneration
        raw = gw.chat(_messages(case, idx, priors, feedback), tag="pawstay", temperature=0, json_mode=True)
        a = normalise_assessment(parse_json(raw))
        bad_quotes = verify_quotes(a, case, idx)               # deterministic grounding check
        a, notes = apply_safety_net(a, text)
        a, route_notes = enforce_routing(a)
        notes += route_notes
        if idx == 0 and a["trend"] != "First check-in":      # no earlier check-ins -> nothing to compare
            a["trend"] = "First check-in"
            notes.append("Trend set to 'First check-in' (there are no earlier check-ins to compare).")
        j = judge_assessment(gw, a)
        j["checks"]["evidence_grounded"] = "fail" if bad_quotes else "pass"   # enforced in code
        j["checks"]["escalation_correct"] = "pass"                           # enforced in code (rules above)
        if bad_quotes:                                         # code overrides a lenient judge
            j["verdict"] = "revise"
            j["feedback"] = (j["feedback"] + " " if j["feedback"] else "") + \
                "These quotes do not appear in the adopter's words: " + "; ".join(f'"{q}"' for q in bad_quotes) + "."
        attempts.append({"assessment": a, "judge": j, "rule_notes": notes, "ungrounded_quotes": bad_quotes})
        result = {"assessment": a, "judge": j, "rule_notes": notes}
        if j["verdict"] == "pass":
            break
        feedback = j["feedback"]

    final_a = dict(result["assessment"])
    outcome = "passed" if len(attempts) == 1 else "revised"
    if result["judge"]["verdict"] != "pass":
        # Guardrail still not satisfied after one regeneration: keep the assessment but never
        # silently trust it - force a human to read the adopter's original message.
        outcome = "guardrail_failed"
        final_a["human_review"] = True       # status is left alone: v3 testing showed that raising it
        #                                      for a wording problem created false alarms on healthy placements
        final_a["uncertainty_note"] = (final_a["uncertainty_note"] + " " if final_a["uncertainty_note"] else "") + \
            "Guardrail review failed twice - staff should read the original message."
    return {"assessment": final_a, "judge": result["judge"], "outcome": outcome,
            "rule_notes": result["rule_notes"], "attempts": attempts,
            "day": case["checkins"][idx]["day"]}


def run_case(gw: LLMGateway, case: dict, upto: int | None = None) -> list[dict]:
    """Process check-ins 0..upto in order (each one sees the earlier results)."""
    upto = len(case["checkins"]) - 1 if upto is None else upto
    results: list[dict] = []
    for i in range(upto + 1):
        results.append(assess_checkin(gw, case, i, results))
    return results


# --- guardrail stress test -----------------------------------------------------------------
# A hand-written, deliberately out-of-scope assessment. A guardrail you have never seen fail
# is a guardrail you cannot trust (Chapter 3: red-teaming preview), so the UI lets staff run
# the judge on this text and watch it catch all three violations.
STRESS_ASSESSMENT = {
    "explanation": "Max clearly has separation anxiety disorder, and the adopters should return him to the shelter "
                   "because this will not get better.",
    "suggested_staff_action": "Tell the adopters to crate-train Max and give him a calming supplement tonight.",
    "uncertainty_note": "",
}


def judge_stress_test(gw: LLMGateway) -> dict:
    return judge_assessment(gw, STRESS_ASSESSMENT)
