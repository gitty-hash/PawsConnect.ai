"""Tab - Part D: PawStay, AI post-adoption stability monitor (innovation feature).

Chapter 3 few-shot JSON + LLM-as-judge guardrail; Chapter 1 evaluation set + regression gate.
Audience: post-adoption coordinators. Four sub-views:
  Staff queue  - the coordinator's home screen: every placement, worst first
  Case timeline - one placement's check-ins, assessed longitudinally
  Evaluation   - labelled test set + regression gate (Chapter 1 mindset)
  KPIs         - the four business KPIs and how each is measured
"""
from __future__ import annotations

import copy
import time

import pandas as pd
import streamlit as st

from ..features import events
from ..features.pawstay import STATUS_RANK, STRESS_ASSESSMENT, assess_checkin, judge_stress_test, run_case
from ..features.pawstay_eval import GATE, evaluate, load_cases
from ..prompts import PAWSTAY_CONCERNS
from ..theme import badge, esc, human, kind_for
from .common import gateway, guard, live_only_note

STATUS_ICON = {"Stable": "🟢", "Needs Attention": "🟡", "Urgent Human Follow-up": "🔴"}


def _cases() -> list[dict]:
    if "pawstay_cases" not in st.session_state:
        st.session_state["pawstay_cases"] = copy.deepcopy(load_cases())
    return st.session_state["pawstay_cases"]


def _memo_key(case: dict, upto: int | None) -> tuple:
    n = len(case["checkins"]) if upto is None else upto + 1
    return (case["case_id"], n, tuple(c["text"] for c in case["checkins"][:n]))


def _peek(case: dict, upto: int | None = None) -> list[dict] | None:
    """Already-computed results for a case, or None (never calls the model)."""
    return st.session_state.setdefault("pawstay_results", {}).get(_memo_key(case, upto))


def _results(case: dict, upto: int | None = None) -> list[dict] | None:
    """Longitudinal results for a case, memoised per (case, number of check-ins)."""
    n = len(case["checkins"]) if upto is None else upto + 1
    store = st.session_state.setdefault("pawstay_results", {})
    key = _memo_key(case, upto)
    if key not in store:
        res = guard(run_case, gateway(), case, n - 1)
        if res is None:
            return None
        store[key] = res
    return store[key]


def _assessment_card(case: dict, idx: int, res: dict, show_staff_actions: bool = True) -> None:
    a, j = res["assessment"], res["judge"]
    ci = case["checkins"][idx]
    st.markdown(
        f"<div class='pc-card'><div class='pc-muted'>Day {ci['day']} - adopter's words</div>"
        f"<div class='pc-quote'>{esc(ci['text'])}</div></div>", unsafe_allow_html=True)

    outcome_badge = {"passed": badge("Guardrail: PASS", "green"),
                     "revised": badge("Guardrail: revised once, then PASS", "orange"),
                     "guardrail_failed": badge("Guardrail: FAILED twice - human must read", "red")}[res["outcome"]]
    st.markdown(
        badge(a["status"], kind_for(a["status"])) + badge("Trend: " + a["trend"], kind_for(a["trend"], "grey"))
        + badge("Concern: " + human(a["concern_category"]), "blue") + outcome_badge
        + (badge("Human review", "orange") if a["human_review"] else badge("No review flag", "green")),
        unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("**Why (explanation for staff)**")
        st.write(a["explanation"])
        if a["evidence"]:
            st.markdown("**Evidence from the adopter's words**")
            for e in a["evidence"]:
                st.markdown(f"<div class='pc-quote'>Day {esc(e['day'])}: &ldquo;{esc(e['quote'])}&rdquo;</div>", unsafe_allow_html=True)
        if a["positive_signals"]:
            st.markdown("**Positive signals** " + "".join(badge(s, "green") for s in a["positive_signals"]),
                        unsafe_allow_html=True)
    with c2:
        st.markdown("**Route to**")
        st.markdown(f"<div class='pc-flag'><b>{esc(a['recommended_route'])}</b><br>{esc(a['suggested_staff_action'])}</div>",
                    unsafe_allow_html=True)
        if a["uncertainty_note"]:
            st.caption("Uncertainty: " + a["uncertainty_note"])

    for note in res["rule_notes"]:
        st.markdown(f"<div class='pc-flag'>Rule-based safety net: {esc(note)}</div>", unsafe_allow_html=True)
    with st.expander("Guardrail review details (3 scope checks by the LLM judge; quote and routing checks enforced in code)"):
        for att_i, att in enumerate(res["attempts"], 1):
            jj = att["judge"]
            st.markdown(f"**Attempt {att_i}** " + badge(jj["verdict"].upper(), "green" if jj["verdict"] == "pass" else "orange"),
                        unsafe_allow_html=True)
            st.markdown("".join(badge(f"{human(k)}: {v}", "green" if v == "pass" else "red") for k, v in jj["checks"].items()),
                        unsafe_allow_html=True)
            for v in jj.get("violations", []):
                st.caption(f"Violation evidence ({human(v['check'])}): \"{v['phrase']}\"")
            if jj.get("discarded_fails"):
                st.caption("Judge fails discarded for lack of evidence (the quoted phrase was not in the text): "
                           + ", ".join(human(c) for c in jj["discarded_fails"]))
            if jj["feedback"]:
                st.caption("Feedback: " + jj["feedback"])
            if att["ungrounded_quotes"]:
                st.caption("Quotes not found in the adopter's words: " + "; ".join(att["ungrounded_quotes"]))

    if show_staff_actions and a["status"] != "Stable":
        _staff_actions(case, ci["day"])


def _staff_actions(case: dict, day: int) -> None:
    """Instrumentation: logging a contact is what makes KPI 2 (time to intervention) measurable."""
    seen = st.session_state.setdefault("flag_seen", {})
    k = (case["case_id"], day)
    seen.setdefault(k, time.time())
    done = st.session_state.setdefault("contacted", set())
    if k in done:
        st.success("Intervention logged for this check-in.")
        return
    if st.button("I contacted the adopter (log intervention)", key=f"contact_{case['case_id']}_{day}"):
        events.log_event({"type": "flag", "case_id": case["case_id"], "day": day, "ts": seen[k]})
        events.log_event({"type": "contact", "case_id": case["case_id"], "day": day})
        done.add(k)
        st.rerun()


def _queue() -> None:
    st.markdown("#### Staff queue - every active placement, most urgent first")
    st.caption("Each row is the **latest** check-in of a placement, assessed against its full history.")
    cases = _cases()
    if st.button("Load staff queue (processes all journeys)", type="primary"):
        bar = st.progress(0.0)
        for i, c in enumerate(cases):
            if _results(c) is None:
                break
            bar.progress((i + 1) / len(cases))
    rows = []
    for c in cases:
        n = len(c["checkins"])
        store = st.session_state.get("pawstay_results", {})
        key = (c["case_id"], n, tuple(x["text"] for x in c["checkins"]))
        if key in store:
            rows.append((c, store[key]))
    if not rows:
        st.info("Press **Load staff queue** to assess every placement.")
        return
    rows.sort(key=lambda cr: (-STATUS_RANK[cr[1][-1]["assessment"]["status"]], not cr[1][-1]["assessment"]["human_review"]))
    body = ""
    for c, res in rows:
        a = res[-1]["assessment"]
        journey = " &rarr; ".join(STATUS_ICON[r["assessment"]["status"]] for r in res)
        body += (f"<tr><td>{badge(a['status'], kind_for(a['status']))}</td>"
                 f"<td><b>{esc(c['pet_name'])}</b><div class='pc-muted'>{esc(c['adopter'])}, Day {c['checkins'][-1]['day']}</div>"
                 f"<div style='margin-top:4px'>{journey}</div></td>"
                 f"<td>{badge(human(a['concern_category']), 'blue')}{badge(a['trend'], kind_for(a['trend']))}</td>"
                 f"<td>{esc(a['explanation'])}</td><td>{esc(a['recommended_route'])}"
                 f"<div class='pc-muted'>{esc(a['suggested_staff_action'])}</div></td>"
                 f"<td>{badge('Human review', 'orange') if a['human_review'] else badge('Routine', 'green')}</td></tr>")
    st.markdown('<table class="pc-table"><tr><th>Status</th><th>Placement and journey</th><th>Concern and trend</th>'
                f'<th>Explanation</th><th>Route and action</th><th>Review</th></tr>{body}</table>', unsafe_allow_html=True)
    st.caption("Journey icons run Day 1 &rarr; latest check-in: 🟢 stable, 🟡 needs attention, 🔴 urgent. "
               "PawStay does not diagnose, give care advice, or recommend returning a pet.")


def _timeline() -> None:
    cases = _cases()
    st.markdown("#### Case timeline - how a placement changes over time")
    by_id = {c["case_id"]: c for c in cases}
    cid = st.selectbox("Placement", list(by_id), format_func=lambda i: f"{by_id[i]['pet_name']} - {by_id[i]['placement']}")
    case = by_id[cid]
    days = [c["day"] for c in case["checkins"]]
    upto = st.select_slider("Show check-ins up to day", options=days, value=days[-1]) if len(days) > 1 else days[0]
    idx = days.index(upto)
    # Cached mode replays instantly, so show it automatically; Live mode spends API calls, so wait for a click.
    res = _peek(case, idx)
    if res is None and (st.session_state.get("mode") == "cached"
                        or st.button("Analyse this placement (calls the model)", key=f"analyse_{cid}_{idx}")):
        res = _results(case, idx)
    if res is None:
        st.info("Press **Analyse this placement** to assess the check-ins up to this day.")
        return
    st.markdown("".join(
        f"<span class='pc-step'>Day {case['checkins'][i]['day']}: {STATUS_ICON[r['assessment']['status']]} {esc(r['assessment']['status'])} "
        f"({esc(r['assessment']['trend'])})</span>" for i, r in enumerate(res)), unsafe_allow_html=True)
    _assessment_card(case, idx, res[idx])
    if idx > 0:
        with st.expander("Earlier check-ins in this placement"):
            for i in range(idx):
                st.markdown(f"**Day {case['checkins'][i]['day']}** - {STATUS_ICON[res[i]['assessment']['status']]} "
                            f"{res[i]['assessment']['status']}, {res[i]['assessment']['trend']}")
                st.markdown(f"<div class='pc-quote'>{esc(case['checkins'][i]['text'])}</div>", unsafe_allow_html=True)

    with st.expander("Simulate a new check-in for this placement (Live mode)"):
        d = st.number_input("Day", min_value=1, max_value=60, value=days[-1] + 7)
        txt = st.text_area("Adopter's message", key=f"newci_{cid}")
        if st.button("Assess new check-in", key=f"assess_{cid}"):
            if st.session_state.get("mode") == "cached":
                st.info("New check-ins need Live mode.")
            elif txt.strip():
                case["checkins"].append({"day": int(d), "text": txt.strip(), "gold": {"status": [], "trend": []}})
                st.rerun()

    st.markdown("**Placement outcome (feeds KPIs 1 and 3)**")
    choice = st.radio("Outcome", ["active", "stabilised", "returned"], horizontal=True, key=f"out_{cid}",
                      label_visibility="collapsed")
    if st.button("Log outcome", key=f"logout_{cid}"):
        events.log_event({"type": "outcome", "case_id": cid, "outcome": choice})
        st.success(f"Logged: {case['pet_name']} - {choice}")


def _fmt(x, pct=True, none="n/a"):
    return none if x is None else (f"{x:.0%}" if pct else f"{x:.1f}")


def _evaluation() -> None:
    st.markdown("#### Evaluation: does PawStay catch what a coordinator would catch?")
    st.caption("Chapter 1 mindset: questions + answer key + scoring rule, then a regression gate before release. "
               "The answer key is a small **synthetic** set of check-ins labelled by us (`data/pawstay_cases.json`).")
    if st.button("Run evaluation on all labelled check-ins", type="primary"):
        bar = st.progress(0.0, text="Evaluating...")
        res = guard(evaluate, gateway(), None, lambda f, t: bar.progress(f, text=t))
        if res:
            st.session_state["pawstay_eval"] = res
    m = st.session_state.get("pawstay_eval")
    if not m:
        st.info("Press the button to score PawStay on every labelled check-in.")
        return
    gate = m["gate"]
    st.markdown(("<div class='pc-ok'><b>Regression gate: PASS</b> - safe to ship this prompt version.</div>" if gate["passed"]
                 else "<div class='pc-bad'><b>Regression gate: FAIL</b> - do not ship this prompt version.</div>"),
                unsafe_allow_html=True)
    for name, ok in gate["checks"].items():
        st.markdown(f"{'✅' if ok else '❌'} {name}")
    k = st.columns(4)
    k[0].metric("Urgent cases escalated to a human", _fmt(m["urgent_escalation_recall"]), f"n = {m['n_urgent']}")
    k[1].metric("Status accuracy", _fmt(m["status_accuracy"]), f"n = {m['n_checkins']} check-ins")
    k[2].metric("Trend accuracy", _fmt(m["trend_accuracy"]), f"{m['n_cases']} placements")
    k[3].metric("False alarms on clearly stable cases", _fmt(m["false_alarm_rate"]), f"n = {m['n_stable_only']}")
    k = st.columns(4)
    k[0].metric("Urgent label recall (strict)", _fmt(m["urgent_label_recall"]))
    k[1].metric("Ambiguous cases flagged for review", _fmt(m["ambiguous_flagged_rate"]), f"n = {m['n_ambiguous']}")
    k[2].metric("Judge passed on first try", _fmt(m["judge_first_pass_rate"]))
    k[3].metric("Revised / guardrail failures", f"{m['revised_count']} / {m['guardrail_failures']}")
    st.caption("Small test set: treat rates as indicative, not precise (Chapter 1: a score means nothing without its sample size).")
    st.markdown("**Guardrail stress test** - does the judge catch an assessment that breaks PawStay's rules?")
    st.markdown("<div class='pc-bad'>" + "<br>".join(f"<b>{esc(k)}:</b> {esc(v)}" for k, v in STRESS_ASSESSMENT.items() if v)
                + "</div>", unsafe_allow_html=True)
    if st.button("Run the judge on this deliberately bad assessment"):
        r = guard(judge_stress_test, gateway())
        if r:
            st.markdown(badge("Verdict: " + r["verdict"].upper(), "green" if r["verdict"] == "pass" else "orange")
                        + "".join(badge(f"{human(k)}: {v}", "green" if v == "pass" else "red") for k, v in r["checks"].items()),
                        unsafe_allow_html=True)
            for v in r["violations"]:
                st.caption(f"Caught ({human(v['check'])}): \"{v['phrase']}\"")
            if r["feedback"]:
                st.caption("Judge feedback: " + r["feedback"])
    df = pd.DataFrame(m["rows"])[["case", "day", "gold_status", "pred_status", "status_ok", "pred_trend", "trend_ok",
                                  "pred_concern", "human_review", "outcome"]]
    df.columns = ["Placement", "Day", "Expected status", "PawStay status", "Status OK", "PawStay trend", "Trend OK",
                  "Concern", "Human review", "Guardrail"]
    st.dataframe(df, hide_index=True)


def _kpis() -> None:
    st.markdown("#### KPIs: how PawStay is measured against real outcomes")
    ev = events.kpi_summary()
    m = st.session_state.get("pawstay_eval")
    st.caption(f"Event log: {ev['n_events']} events, of which **{ev['n_seed_events']} are SYNTHETIC seed events** shipped so this board "
               "is not empty. Actions you take in the Case timeline (contact / outcome buttons) append real events.")
    rows = [
        ("1. 30-day post-adoption return rate", _fmt(ev["return_rate"]), f"{ev['n_decided']} decided placements",
         "Placements whose outcome is logged as returned / (stabilised + returned). Compare PawStay cohort vs. pre-launch baseline."),
        ("2. Avg. time from concerning check-in to human intervention", ("n/a" if ev["avg_hours_to_contact"] is None else f"{ev['avg_hours_to_contact']:.1f} h"),
         f"{ev['n_contacts']} contacts", "Timestamp when PawStay flags a check-in vs. when staff log the contact."),
        ("3. Flagged placements stabilised without return", _fmt(ev["flagged_stabilised_rate"]), f"{ev['n_flagged_decided']} flagged and decided",
         "Of placements PawStay flagged at least once, the share whose outcome ends as stabilised."),
        ("4. Urgent cases correctly escalated for human review", _fmt(m["urgent_escalation_recall"]) if m else "run evaluation",
         f"n = {m['n_urgent']} urgent check-ins" if m else "", "From the Evaluation tab: gold-urgent check-ins that PawStay flagged for a human."),
    ]
    body = "".join(f"<tr><td><b>{esc(a)}</b></td><td style='font-size:1.3rem'>{esc(b)}</td><td class='pc-muted'>{esc(c)}</td><td class='pc-muted'>{esc(d)}</td></tr>"
                   for a, b, c, d in rows)
    st.markdown(f'<table class="pc-table"><tr><th>KPI</th><th>Current value</th><th>Sample</th><th>How it is measured</th></tr>{body}</table>',
                unsafe_allow_html=True)
    st.warning("Values for KPIs 1-3 come from seed/demo events and illustrate the dashboard only. Real impact claims need a pilot: "
               "log every flag, contact and outcome, then compare against the shelter's pre-PawStay return rate.")


def render() -> None:
    st.subheader("PawStay: post-adoption stability monitor")
    st.caption("Innovation feature for post-adoption coordinators. PawsConnect checks in on Day 1, 3, 7, 14 and 30; PawStay reads each reply "
               "together with the earlier ones, flags placements that are improving or deteriorating, and routes concerns to staff. "
               "It never diagnoses, never gives care advice and never recommends returning a pet.")
    live_only_note()
    q, t, e, k = st.tabs(["Staff queue", "Case timeline", "Evaluation", "KPIs"])
    with q:
        _queue()
    with t:
        _timeline()
    with e:
        _evaluation()
    with k:
        _kpis()
