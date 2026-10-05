"""Tab - Part C1: Adoption inquiry triage queue (Chapter 3 few-shot classification)."""
from __future__ import annotations

import streamlit as st

from ..features.common import load_json
from ..features.triage import URGENCY_ORDER, triage_message
from ..prompts import TRIAGE_CATEGORIES, URGENCY_LEVELS
from ..theme import badge, esc, human, kind_for
from .common import gateway, guard, live_only_note


def _triage(msg_id: str, text: str):
    cache = st.session_state.setdefault("triage", {})
    if msg_id not in cache:
        result = guard(triage_message, gateway(), text)
        if result is not None:
            cache[msg_id] = result
    return cache.get(msg_id)


def render() -> None:
    st.subheader("Adoption inquiry triage")
    st.caption("Chapter 3 - few-shot prompting with a defined label set and structured JSON. "
               "Each message becomes an operational record; the queue is sorted by urgency.")
    live_only_note()

    inquiries = load_json("inquiries.json")
    with st.expander("Label sets the model must use (defined inside the prompt)"):
        c1, c2 = st.columns(2)
        c1.markdown("**Categories**")
        for k, v in TRIAGE_CATEGORIES.items():
            c1.markdown(f"- `{k}` - {v}")
        c2.markdown("**Urgency levels**")
        for k, v in URGENCY_LEVELS.items():
            c2.markdown(f"- `{k}` - {v}")

    if st.button("Triage all 12 sample messages", type="primary"):
        bar = st.progress(0.0)
        for i, q in enumerate(inquiries):
            if _triage(q["id"], q["text"]) is None:
                break
            bar.progress((i + 1) / len(inquiries))

    done = [(q, st.session_state.get("triage", {}).get(q["id"])) for q in inquiries]
    done = [(q, r) for q, r in done if r is not None]
    if done:
        done.sort(key=lambda qr: (URGENCY_ORDER[qr[1]["urgency"]], not qr[1]["human_review"]))
        n_review = sum(r["human_review"] for _, r in done)
        st.markdown(f"**Triage queue** - {len(done)} messages, **{n_review} flagged for human review**, "
                    f"{sum(r['urgency'] in ('critical', 'high') for _, r in done)} critical/high.")
        body = ""
        for q, r in done:
            amb = badge("ambiguous test", "purple") if q["ambiguous"] else ""
            review = (badge("Human review", "orange") + f"<div class='pc-muted'>{esc(' '.join(r['review_reasons']))}</div>"
                      if r["human_review"] else badge("Auto-routable", "green"))
            body += (
                f"<tr><td>{badge(r['urgency'].upper(), kind_for(r['urgency']))}</td>"
                f"<td>{badge(human(r['category']), 'blue')}<div class='pc-muted'>confidence: {esc(r['confidence'])}</div></td>"
                f"<td><b>{esc(r['summary'])}</b><div class='pc-muted'>{esc(q['sender'])} via {esc(q['channel'])} {amb}</div>"
                f"<div class='pc-muted' style='margin-top:4px'><i>Why:</i> {esc(r['reason'])}</div></td>"
                f"<td>{esc(r['suggested_routing'])}</td><td>{review}</td></tr>")
        st.markdown('<table class="pc-table"><tr><th>Urgency</th><th>Category</th><th>Summary and reason</th>'
                    f'<th>Route to</th><th>Review</th></tr>{body}</table>', unsafe_allow_html=True)
        with st.expander("Original messages"):
            for q in inquiries:
                st.markdown(f"**{q['sender']}** ({q['channel']}): {q['text']}")
    else:
        st.info("Press **Triage all 12 sample messages** to build the queue.")

    st.divider()
    st.markdown("#### Try your own message")
    own = st.text_area("Message", placeholder="Type an adopter or community message...", height=90)
    if st.button("Triage this message"):
        if st.session_state.get("mode") == "cached":
            st.info("Custom messages need Live mode - the cached demo only knows the 12 bundled samples.")
        elif own.strip():
            r = guard(triage_message, gateway(), own.strip())
            if r:
                st.markdown(badge(r["urgency"].upper(), kind_for(r["urgency"])) + badge(human(r["category"]), "blue")
                            + badge(r["suggested_routing"], "grey")
                            + (badge("Human review", "orange") if r["human_review"] else ""), unsafe_allow_html=True)
                st.write(r["summary"])
                st.caption("Why: " + r["reason"])
