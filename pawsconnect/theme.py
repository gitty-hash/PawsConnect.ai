"""Visual helpers: one stylesheet and small HTML badge/card builders.

Interpretability rules from the assignment (Section 5): outputs render as cards, tables
and badges - never raw JSON walls; every classification shows its label AND the model's
stated reason; uncertain outputs are visibly flagged for human review.
"""
from __future__ import annotations

import html

CSS = """
<style>
:root { --paw-ink:#2b2a33; --paw-muted:#6b6a75; --paw-line:#e6e1d8; --paw-card:#fffdf8; --paw-accent:#c2602d; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }
.pc-badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.78rem; font-weight:600;
            margin:0 6px 4px 0; border:1px solid transparent; white-space:nowrap; }
.pc-green  { background:#e3f4e8; color:#1d6b3a; border-color:#bfe3cb; }
.pc-amber  { background:#fff1d6; color:#8a5a00; border-color:#f3d9a0; }
.pc-orange { background:#ffe3d2; color:#a14412; border-color:#f5c3a3; }
.pc-red    { background:#fde0e0; color:#a11f1f; border-color:#f3b4b4; }
.pc-blue   { background:#e1ecfb; color:#1f4f99; border-color:#b9d1f1; }
.pc-grey   { background:#eeedf0; color:#4a4955; border-color:#d9d7de; }
.pc-purple { background:#ece4fa; color:#55349a; border-color:#d3c4f1; }
.pc-card { background:var(--paw-card); border:1px solid var(--paw-line); border-radius:14px; padding:16px 18px; margin-bottom:12px; }
.pc-card h4 { margin:0 0 6px 0; font-size:1.05rem; }
.pc-muted { color:var(--paw-muted); font-size:0.88rem; }
.pc-flag { background:#fff4e5; border:1px solid #f3c98b; color:#7a4a00; border-radius:10px; padding:8px 12px; margin:8px 0; font-size:0.9rem; }
.pc-ok   { background:#eaf7ee; border:1px solid #bfe3cb; color:#1d6b3a; border-radius:10px; padding:8px 12px; margin:8px 0; font-size:0.9rem; }
.pc-bad  { background:#fdeaea; border:1px solid #f3b4b4; color:#8c1d1d; border-radius:10px; padding:8px 12px; margin:8px 0; font-size:0.9rem; }
.pc-table { width:100%; border-collapse:collapse; font-size:0.9rem; }
.pc-table th { text-align:left; padding:8px 10px; border-bottom:2px solid var(--paw-line); color:var(--paw-muted); font-weight:600; }
.pc-table td { padding:10px; border-bottom:1px solid var(--paw-line); vertical-align:top; }
.pc-vote { display:inline-block; min-width:92px; text-align:center; padding:6px 10px; border-radius:10px; margin:0 6px 6px 0; font-weight:600; font-size:0.85rem; }
.pc-quote { border-left:3px solid #d8c7a8; padding:2px 10px; margin:4px 0; color:#4a4630; font-style:italic; }
.pc-step { display:inline-block; padding:4px 12px; border-radius:8px; margin:0 6px 6px 0; font-size:0.82rem; background:#f1ede4; }
</style>
"""

KIND = {
    # urgency
    "critical": "red", "high": "orange", "medium": "amber", "low": "green",
    # pawstay status
    "Stable": "green", "Needs Attention": "amber", "Urgent Human Follow-up": "red",
    # trend
    "Improving": "green", "Worsening": "red", "New concern": "orange", "First check-in": "blue",
    # confidence
    "high_conf": "green", "medium_conf": "amber", "low_conf": "red",
    # fit scale
    "Strong Fit": "green", "Good Fit": "blue", "Possible Fit": "amber", "Poor Fit": "red",
    # verdicts
    "pass": "green", "revise": "orange", "fail": "red",
}


def badge(text: str, kind: str = "grey") -> str:
    return f'<span class="pc-badge pc-{kind}">{html.escape(str(text))}</span>'


def kind_for(label: str, default: str = "grey") -> str:
    return KIND.get(label, default)


def conf_badge(field: str, conf: str) -> str:
    kind = {"high": "green", "medium": "amber", "low": "red"}.get(conf, "grey")
    return badge(f"{field}: {conf} confidence", kind)


def review_flag(reasons: list[str], needed: bool = True) -> str:
    if not needed:
        return '<div class="pc-ok">No human review flag - all fields were reported with adequate confidence.</div>'
    items = "".join(f"<li>{html.escape(r)}</li>" for r in reasons) or "<li>Flagged for review.</li>"
    return f'<div class="pc-flag"><b>Needs human review</b> before publishing / acting.<ul style="margin:6px 0 0 18px">{items}</ul></div>'


def esc(text) -> str:
    return html.escape(str(text))


def human(label: str) -> str:
    """snake_case -> Sentence case for display."""
    return label.replace("_", " ").capitalize()
