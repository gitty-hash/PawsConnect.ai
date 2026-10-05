"""Build prompts.md from the prompts in the code, so the documentation cannot drift.

    python scripts/export_prompts.py

prompts.md = header + the FINAL text of every prompt (pulled live from
pawsconnect/prompts.py) + the hand-written iteration log in docs/iteration_log.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pawsconnect import prompts as P  # noqa: E402

SECTIONS = [
    ("Part B - Photo-to-Profile (Chapter 2: vision + structured output + fallback)", "profile", [("Vision prompt", P.PROFILE_PROMPT)]),
    ("Part C1 - Inquiry triage (Chapter 3: few-shot, defined labels, JSON)", "triage",
     [("System prompt", P.TRIAGE_SYSTEM), ("Few-shot examples (appended to each user turn)", P.TRIAGE_FEW_SHOT)]),
    ("Part C2 - Counselor persona (Chapter 3: role-playing system prompt)", "counselor",
     [("System prompt (full persona)", P.COUNSELOR_SYSTEM),
      ("Deliberately weakened persona (red-team toggle only)", P.COUNSELOR_WEAK_SYSTEM),
      ("Escalation message shown when the judge fails twice", P.COUNSELOR_ESCALATION_MESSAGE)]),
    ("Part C2 - LLM-as-judge guardrail (Chapter 3)", "counselor_judge", [("Judge system prompt / review rubric", P.COUNSELOR_JUDGE_SYSTEM)]),
    ("Part C3 - Match explainer (Chapter 3: chain-of-thought + self-consistency)", "match", [("Chain-of-thought prompt template", P.MATCH_PROMPT_TEMPLATE)]),
    ("Part D - PawStay assessment (Chapter 3: few-shot JSON, longitudinal)", "pawstay",
     [("System prompt", P.PAWSTAY_SYSTEM), ("Few-shot examples (appended to each user turn)", P.PAWSTAY_FEW_SHOT)]),
    ("Part D - PawStay guardrail judge (Chapter 3: LLM-as-judge)", "pawstay_judge", [("Judge system prompt / scope rubric", P.PAWSTAY_JUDGE_SYSTEM)]),
]


def main() -> None:
    out = ["# prompts.md - PawsConnect prompt log\n",
           "Final prompt for every feature (generated from `pawsconnect/prompts.py` by `scripts/export_prompts.py`), "
           "followed by the iteration log. Model for all features: `gpt-4o-mini`.\n",
           "## 1. Final prompts\n"]
    for title, key, blocks in SECTIONS:
        out.append(f"### {title}  _(version {P.PROMPT_VERSION[key]})_\n")
        for name, text in blocks:
            out.append(f"**{name}**\n\n```text\n{text}\n```\n")
    import json
    meta_path = ROOT / "data" / "banners" / "banner_meta.json"
    if meta_path.exists():
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        out.append("### Part B bonus - promotional banner (Chapter 2: Shopify Magic, image generation)\n")
        out.append(f"Tool: {m['tool']}; input: {m['source_photo']}; size {m['size']}, quality {m['quality']}; generated {m['generated']}.\n")
        out.append(f"```text\n{m['prompt']}\n```\n")
    log = ROOT / "docs" / "iteration_log.md"
    out.append("## 2. Iteration log\n")
    out.append(log.read_text(encoding="utf-8") if log.exists() else "_(not written yet)_\n")
    (ROOT / "prompts.md").write_text("\n".join(out), encoding="utf-8")
    print("wrote prompts.md")


if __name__ == "__main__":
    main()
