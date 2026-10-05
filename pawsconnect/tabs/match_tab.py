"""Tab - Part C3: Adopter-pet match explainer (Chapter 3 CoT + self-consistency)."""
from __future__ import annotations

import streamlit as st

from ..features.common import load_json
from ..features.counselor import format_listing
from ..features.match import N_SAMPLES, RATINGS, TEMPERATURE, explain_match
from ..prompts import FIT_SCALE
from ..theme import badge, esc, kind_for, review_flag
from .common import gateway, guard, live_only_note, rel


def render() -> None:
    st.subheader("Adopter-pet match explainer")
    st.caption("Chapter 3 - chain-of-thought reasoning + self-consistency voting. The model reasons step by step "
               f"{N_SAMPLES} times (temperature {TEMPERATURE}); the majority rating wins and any disagreement is shown. "
               "It supports the counselor; it never decides.")
    live_only_note()

    pets = {p["id"]: p for p in load_json("pet_listings.json")}
    profiles = {p["id"]: p for p in load_json("adopter_profiles.json")}

    c1, c2 = st.columns([6, 5], gap="large")
    with c1:
        pid = st.selectbox("Household profile", list(profiles), format_func=lambda i: profiles[i]["name"])
        profile_text = st.text_area("Household profile (free text - editable in Live mode)", value=profiles[pid]["profile"],
                                    height=170, key=f"prof_{pid}")
    with c2:
        petid = st.selectbox("Pet listing", list(pets), format_func=lambda i: f"{pets[i]['name']} - {pets[i]['breed_note']}")
        pet = pets[petid]
        a, b = st.columns([1, 2])
        if pet["photo"] and rel(pet["photo"]).exists():
            a.image(str(rel(pet["photo"])), width=130)
        b.caption(f"{pet['age_text']}, {pet['weight_lb']} lb, energy {pet['energy']}. Kids: {pet['good_with_kids']}")
        with st.expander("Full listing"):
            st.text(format_listing(pet))

    key = f"match::{pid}::{petid}::{hash(profile_text)}"
    if st.button("Explain the match", type="primary"):
        with st.spinner(f"Running {N_SAMPLES} step-by-step analyses..."):
            res = guard(explain_match, gateway(), profile_text, pets[petid])
        if res:
            st.session_state[key] = res
    res = st.session_state.get(key)
    if not res:
        st.info("Choose a household and a pet, then press **Explain the match**.")
        with st.expander("Fit scale used"):
            for k, v in FIT_SCALE.items():
                st.markdown(f"- **{k}** - {v}")
        return

    st.markdown(f"### {badge(res['final'], kind_for(res['final']))}", unsafe_allow_html=True)
    st.markdown(f"**{res['agreement']}**")
    votes_html = "".join(
        f"<span class='pc-vote pc-{kind_for(r['rating'])}'>Run {i + 1}<br>{esc(r['rating'])}</span>"
        for i, r in enumerate(res["runs"]))
    st.markdown(votes_html, unsafe_allow_html=True)
    if res["split"]:
        st.markdown(f"<div class='pc-flag'><b>The runs disagreed.</b> A split vote is a signal that this match is a close call. "
                    f"{'No clear majority, so a counselor must decide.' if res['human_review'] else 'The majority view is used below; a counselor can still weigh the dissent.'}</div>",
                    unsafe_allow_html=True)
    if res["human_review"]:
        st.markdown(review_flag([res["review_reason"] or "Close call."], True), unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("**Top three reasons for the rating**")
        for i, r in enumerate(res["reasons"], 1):
            st.markdown(f"{i}. {r}")
    with right:
        st.markdown("**Top concern**")
        st.markdown(f"<div class='pc-flag'>{esc(res['concern'])}</div>", unsafe_allow_html=True)

    with st.expander("Show step-by-step reasoning (chain of thought)"):
        tabs = st.tabs([f"Run {i + 1}: {r['rating']}" for i, r in enumerate(res["runs"])])
        for t, r in zip(tabs, res["runs"]):
            with t:
                st.markdown(r["reasoning"] or "_no reasoning captured_")
