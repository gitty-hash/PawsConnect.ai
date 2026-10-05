"""Part C3 - Adopter-pet match explainer.

Chapter 3 (03_prompt_engineering.ipynb, Step 5 "Decide a refund case")
* chain-of-thought: "Think step by step" - facts, compare, weigh, THEN conclude;
* the last lines are machine-readable (``DECISION:`` in the lab, ``RATING:`` here)
  so code can read them;
* self-consistency: sample the SAME prompt several times at high temperature (diverse
  reasoning paths) and take a majority vote with ``collections.Counter``.
A split vote is information: it routes the match to a human counselor (lab summary:
"a split vote routes to a human").
"""
from __future__ import annotations

import re
from collections import Counter

from ..llm import LLMGateway
from ..prompts import FIT_SCALE, MATCH_PROMPT_TEMPLATE
from .counselor import format_listing

RATINGS = list(FIT_SCALE)                       # best -> worst
N_SAMPLES = 5                                   # assignment: at least 3
TEMPERATURE = 1.0                               # > 0 so runs can genuinely disagree


def _parse_run(text: str) -> dict:
    """Pull the machine-readable tail off one chain-of-thought run."""
    rating = None
    m = re.search(r"RATING:\s*\**\s*(Strong Fit|Good Fit|Possible Fit|Poor Fit)", text, re.I)
    if m:
        rating = next(r for r in RATINGS if r.lower() == m.group(1).lower())
    reasons = [x.strip() for x in re.findall(r"REASON\s*[123]:\s*(.+)", text)]
    concern = re.search(r"TOP CONCERN:\s*(.+)", text)
    reasoning = text.split("RATING:")[0].strip() if "RATING:" in text else text.strip()
    return {"rating": rating or "unparseable", "reasons": reasons[:3],
            "concern": concern.group(1).strip() if concern else "", "reasoning": reasoning}


def explain_match(gw: LLMGateway, profile_text: str, pet: dict,
                  n: int = N_SAMPLES, temperature: float = TEMPERATURE) -> dict:
    prompt = MATCH_PROMPT_TEMPLATE.format(profile=profile_text.strip(), listing=format_listing(pet))
    runs = []
    for i in range(n):
        # slot=i: same prompt, independent samples (also separates the cache entries).
        text = gw.chat([{"role": "user", "content": prompt}], tag="match", slot=i, temperature=temperature)
        runs.append(_parse_run(text))

    votes = Counter(r["rating"] for r in runs if r["rating"] != "unparseable")
    unparseable = sum(1 for r in runs if r["rating"] == "unparseable")
    if not votes:
        return {"runs": runs, "votes": {}, "final": "Unparseable", "agreement": "No run produced a rating.",
                "split": True, "human_review": True, "review_reason": "No valid ratings.",
                "reasons": [], "concern": "", "n": n, "unparseable": unparseable}

    top = max(votes.values())
    leaders = [r for r in RATINGS if votes.get(r) == top]
    majority = top > len([r for r in runs if r["rating"] != "unparseable"]) / 2
    # Tie between leaders -> choose the MORE CAUTIOUS (worse) rating and flag for a human.
    final = leaders[-1]
    split = len(votes) > 1
    human_review = (not majority) or unparseable > 0

    # Explain with the first run that agrees with the final rating.
    rep = next(r for r in runs if r["rating"] == final)
    ordered = ", ".join(f"{c} of {n} rated {r}" for r, c in sorted(votes.items(), key=lambda x: (-x[1], RATINGS.index(x[0]))))
    if not split:
        agreement = f"All {n} runs rated this {final}."
    elif majority:
        agreement = f"Majority vote: {ordered}."
    else:
        agreement = f"No majority - {ordered}. Showing the more cautious rating."
    return {
        "runs": runs, "votes": dict(votes), "final": final, "agreement": agreement,
        "split": split, "human_review": human_review,
        "review_reason": ("No clear majority among the runs." if not majority else
                          "Some runs could not be parsed." if unparseable else ""),
        "reasons": rep["reasons"], "concern": rep["concern"], "n": n, "unparseable": unparseable,
    }
