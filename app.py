"""PawsConnect - AI suite for a pet-adoption platform (MIS 552, Homework 1).

Run:  python -m streamlit run app.py
Cached demo mode (default) needs no API key; Live mode reads OPENAI_API_KEY from the environment.
"""
import os

import streamlit as st

from pawsconnect.llm import MODEL, cache_size, estimate_cost, new_usage
from pawsconnect.prompts import PROMPT_VERSION
from pawsconnect.tabs import counselor_tab, match_tab, overview, pawstay_tab, profile_tab, triage_tab
from pawsconnect.theme import CSS

st.set_page_config(page_title="PawsConnect AI", page_icon="🐾", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ---- session state -----------------------------------------------------------------
st.session_state.setdefault("mode", "cached")
st.session_state.setdefault("usage", new_usage())

# ---- sidebar: demo-mode toggle (assignment Section 5) ------------------------------
with st.sidebar:
    st.markdown("## 🐾 PawsConnect")
    st.caption("AI suite for animal shelters and adopters")
    choice = st.radio("Mode", ["Cached demo (no API key)", "Live (OpenAI API)"],
                      index=0 if st.session_state["mode"] == "cached" else 1)
    st.session_state["mode"] = "cached" if choice.startswith("Cached") else "live"
    # Results computed in one mode must never be shown in the other (a cached replay on a "Live"
    # screen would be misleading), so switching modes clears every stored result.
    if st.session_state.get("_last_mode") not in (None, st.session_state["mode"]):
        for k in list(st.session_state.keys()):
            if k in ("profiles", "profile_batch", "triage", "chat_turns", "chat_note", "pawstay_results",
                     "pawstay_eval", "pawstay_cases", "flag_seen", "contacted") or str(k).startswith("match::"):
                del st.session_state[k]
    st.session_state["_last_mode"] = st.session_state["mode"]
    if st.session_state["mode"] == "cached":
        st.success(f"Replaying {cache_size()} recorded {MODEL} responses.")
    elif os.environ.get("OPENAI_API_KEY"):
        st.success("API key found in the environment.")
    else:
        st.error("No OPENAI_API_KEY in the environment. Set it and restart the app, or use Cached demo.")
    usage_slot = st.empty()      # filled at the end of the script so it includes this run's calls
    st.divider()
    st.caption("**Safety stance.** AI drafts and flags; people decide. No diagnosis, no medical or training advice, "
               "no return recommendations. Sample data is synthetic or CC0.")
    with st.expander("Prompt versions"):
        for k, v in PROMPT_VERSION.items():
            st.caption(f"{k}: {v}")
    if st.button("Reset demo state"):
        for k in list(st.session_state.keys()):
            if k not in ("mode",):
                del st.session_state[k]
        st.rerun()

st.title("PawsConnect")
st.caption("Helping shelters list faster, answer sooner and keep adoptions from failing.")

tabs = st.tabs(["Overview", "B. Photo to Profile", "C1. Inquiry Triage", "C2. Counselor Hazel",
                "C3. Match Explainer", "D. PawStay"])
with tabs[0]:
    overview.render()
with tabs[1]:
    profile_tab.render()
with tabs[2]:
    triage_tab.render()
with tabs[3]:
    counselor_tab.render()
with tabs[4]:
    match_tab.render()
with tabs[5]:
    pawstay_tab.render()

u = st.session_state["usage"]
if st.session_state["mode"] == "live":
    usage_slot.caption(f"Model: `{MODEL}` | live API calls this session: {u['calls']} | est. cost: ${estimate_cost(u):.4f}")
else:
    usage_slot.caption(f"Model: `{MODEL}` | cached responses replayed this session: {u.get('replays', 0)}")
