"""Quick self-check: does the app run on THIS computer? (No API key needed.)

    python scripts/smoke_test.py

It loads the Streamlit app headlessly in Cached demo mode, presses every feature button
(photo profiles, triage, the four counselor scenarios, match explainer, PawStay queue,
evaluation, guardrail stress test) and checks that nothing crashes and every answer was found in
the recorded cache. Prints PASS or FAIL for each step; exits with a non-zero code on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

STEPS = [
    "Generate adoption profile",
    "Run all sample photos",
    "Triage all 12 sample messages",
    "1. In-scope question",
    "2. Off-topic request",
    "3. Adversarial: promise availability",
    "4. Red team: weakened persona",
    "Explain the match",
    "Load staff queue (processes all journeys)",
    "Run evaluation on all labelled check-ins",
    "Run the judge on this deliberately bad assessment",
]


def main() -> int:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    failures = 0
    if at.exception:
        print("FAIL  app failed to load:", at.exception[0].value[:200])
        return 1
    print("PASS  app loads in Cached demo mode")
    for label in STEPS:
        buttons = [b for b in at.button if b.label == label]
        if not buttons:
            print(f"FAIL  button not found: {label}")
            failures += 1
            continue
        buttons[0].click()
        at.run()
        missing = [w.value for w in at.warning if "not recorded" in w.value]
        if at.exception or missing:
            failures += 1
            detail = at.exception[0].value[:150] if at.exception else missing[0][:150]
            print(f"FAIL  {label}: {detail}")
        else:
            print(f"PASS  {label}")
    print(f"\n{len(STEPS) - failures} of {len(STEPS)} steps passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
