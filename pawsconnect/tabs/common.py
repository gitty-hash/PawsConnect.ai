"""Shared Streamlit helpers for the tabs."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..features.common import ROOT
from ..llm import CacheMiss, LiveUnavailable, LLMGateway


def gateway() -> LLMGateway:
    """The gateway for this session's chosen mode (usage counter is shared in session_state)."""
    return LLMGateway(mode=st.session_state.get("mode", "cached"), usage=st.session_state["usage"])


def guard(fn, *args, **kwargs):
    """Run a model-backed function; show friendly messages instead of tracebacks."""
    try:
        return fn(*args, **kwargs)
    except CacheMiss as e:
        st.warning(str(e))
    except LiveUnavailable as e:
        st.error(str(e))
    except Exception as e:  # network errors, malformed model output, etc.
        st.error(f"The model call failed: {type(e).__name__}: {e}")
    return None


def rel(path: str) -> Path:
    """Resolve a project-relative path (so the folder can be zipped and moved)."""
    return ROOT / path


def live_only_note():
    if st.session_state.get("mode") == "cached":
        st.caption("Cached demo mode replays recorded gpt-4o-mini answers for the bundled samples. "
                   "Switch to **Live** in the sidebar (needs `OPENAI_API_KEY`) to try your own input.")
