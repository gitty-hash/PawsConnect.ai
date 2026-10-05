"""Tab - Overview: stakeholder map and feature-to-technique matrix (Part A at a glance)."""
from __future__ import annotations

import streamlit as st

from ..llm import MODEL


def render() -> None:
    st.subheader("PawsConnect AI suite")
    st.markdown(
        "PawsConnect connects animal shelters with adopters. Shelter staff are short on time, adopters ask the same questions "
        "over and over, and promising matches fail quietly after the animal goes home. This demo shows five AI features, "
        "each built for a specific person on the platform and each with a human in the loop.")

    st.markdown("#### Who each feature is for")
    st.markdown("""
| Stakeholder | Goal on the platform | Pain point AI can relieve | Feature |
|---|---|---|---|
| **Shelter volunteers and staff** | Get animals listed and adopted fast | Photographing pets is quick; writing an honest profile for every animal is not, so listings sit half-empty | **Photo-to-Profile** (Part B) |
| **Intake and front-desk teams** | Answer every message that matters first | Thousands of messages a week mix emergencies, applications and spam | **Inquiry Triage** (Part C1) |
| **Adopters** | Find the right pet, get honest answers | Slow replies; nobody explains why a pet fits their household | **Counselor Hazel** (C2) and **Match Explainer** (C3) |
| **Post-adoption coordinators** | Keep placements from failing in the first 30 days | Problems show up only when the adopter calls, often after the point of no return | **PawStay** (Part D) |
| **Platform operations and trust** | Safe, trustworthy, auditable AI | Wrong or overconfident AI output reaching adopters | Review flags, judge guardrails, evaluation gate |
""")

    st.markdown("#### Which technique, and why not the alternatives")
    st.markdown("""
| Feature | Course technique | Why this fits (Chapter 1 roadmap) |
|---|---|---|
| Photo-to-Profile | **Ch. 2** multimodal vision model, structured JSON, fallback instruction | The model must *act* on an image it has never seen, so prompting a vision model is enough. No fine-tune: breed and age calls should stay uncertain, not be trained to sound sure. |
| Inquiry Triage | **Ch. 3** few-shot classification, defined label set, JSON | Needs to be *instructed well*, not to know anything new. Four worked examples teach the format; fine-tuning would cost far more than it adds. |
| Counselor Hazel | **Ch. 3** role-playing system prompt + LLM-as-judge | Persona and policy live in the prompt; the listing is pasted in (grounding), so no retrieval index is needed yet. The judge adds a check no prompt can promise. |
| Match Explainer | **Ch. 3** chain-of-thought + self-consistency vote | A judgment call over several factors: step-by-step reasoning plus voting beats one lucky sample, and a split vote tells us to involve a human. |
| PawStay | **Ch. 3** few-shot JSON + judge, **Ch. 1** evaluation set and regression gate | Prior check-ins go straight into the prompt (no RAG needed at this scale); a labelled test set and a release gate make the safety claim measurable. |
""")
    st.markdown("#### Model selection")
    st.markdown(f"All features use **`{MODEL}`**: it supports vision (needed for Part B), is fast and cheap enough to run five-way "
                "self-consistency, and keeps the whole demo well under the assignment's two-dollar budget. "
                "In **Cached demo** mode no API key is needed: the app replays answers recorded from real runs of this model.")

    st.markdown("#### Design principles you will see in every tab")
    st.markdown("""
- **Cards, tables and badges**, never raw JSON walls; every label comes with the model's stated reason.
- **Uncertainty is visible**: anything low-confidence, ambiguous or safety-related carries an orange *Human review* flag.
- **No diagnosis, no medical advice, no return recommendations** from any AI feature; welfare concerns go to a person.
- **Decisions stay human**: the match explainer and PawStay support coordinators; they never approve or reject an adopter.
""")
