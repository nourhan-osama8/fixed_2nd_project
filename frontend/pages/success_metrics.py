"""
Success Metrics page - Admin-only section showing contact-centre KPIs.

Metrics shown:
  * Avg Time-to-Answer (seconds from case creation to first call)
  * Avg Agent Response Latency (avg call duration proxy for resolution speed)
  * Agent Satisfaction Survey (YES/NO/NO_ANSWER distribution from AI follow-ups)
  * AI Usage Rate pct (share of AI-handled vs human calls)
  * Knowledge Base Coverage pct (share of READY documents)
  * Resolution Rate pct
"""

import streamlit as st
from services import api_client
from components.navbar import render_navbar
from components.alerts import show_api_error


# ---- helpers ----------------------------------------------------------------

def _fmt_sec(seconds) -> str:
    """Format a seconds value as a human-readable string."""
    if seconds is None:
        return "N/A"
    s = float(seconds)
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{s/60:.1f} min"
    return f"{s/3600:.1f} hrs"


def _pct(value) -> str:
    return f"{value:.1f}%" if value is not None else "N/A"


def _raw_pct(value) -> float:
    return float(value) if value is not None else 0.0


def _health_color(pct: float) -> str:
    """Return a hex color based on percentage health tier."""
    if pct >= 75:
        return "#22c55e"
    if pct >= 45:
        return "#f59e0b"
    return "#ef4444"


def _health_label(pct: float) -> str:
    if pct >= 75:
        return "Excellent"
    if pct >= 45:
        return "Needs Attention"
    return "Critical"


# ---- SVG circular progress ring ---------------------------------------------

def _ring_card(label: str, value_str: str, pct: float,
               icon: str, subtitle: str = "", key_color: str = "") -> None:
    """Render a KPI card with an SVG progress ring."""
    if not key_color:
        key_color = _health_color(pct)
    radius = 44
    circ = 2 * 3.14159 * radius
    dash = (pct / 100) * circ
    gap = circ - dash
    health_col = _health_color(pct)
    health_lbl = _health_label(pct)
    st.markdown(
        f"""
        <div class="metric-ring-card" style="border-color:{key_color}33;box-shadow:0 4px 24px {key_color}18;">
            <div class="ring-icon">{icon}</div>
            <svg class="ring-svg" viewBox="0 0 110 110" width="110" height="110">
                <circle cx="55" cy="55" r="{radius}" fill="none" stroke="#1e293b" stroke-width="9"/>
                <circle cx="55" cy="55" r="{radius}" fill="none" stroke="{key_color}" stroke-width="9"
                    stroke-linecap="round"
                    stroke-dasharray="{dash:.2f} {gap:.2f}"
                    transform="rotate(-90 55 55)" class="ring-fill"/>
                <text x="55" y="60" text-anchor="middle" fill="{key_color}"
                    font-size="14" font-weight="700" font-family="Inter,sans-serif">{value_str}</text>
            </svg>
            <p class="ring-label">{label}</p>
            <p class="ring-sub">{subtitle}</p>
            <span class="health-badge" style="color:{health_col};">&#9679; {health_lbl}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _speed_card(label: str, value_str: str, icon: str,
                color: str, subtitle: str = "") -> None:
    """Simple value card for non-percentage time/speed metrics."""
    st.markdown(
        f"""
        <div class="metric-speed-card" style="border-color:{color}44;box-shadow:0 4px 20px {color}16;">
            <div style="font-size:2.2rem;margin-bottom:6px;">{icon}</div>
            <p class="speed-label">{label}</p>
            <p class="speed-value" style="color:{color};">{value_str}</p>
            <p class="speed-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _volume_badge(label: str, count: int, color: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="vol-badge" style="border-color:{color}55;background:linear-gradient(135deg,{color}18,#0f172a);">
            <div style="font-size:1.8rem;">{icon}</div>
            <p class="vol-count" style="color:{color};">{count:,}</p>
            <p class="vol-label">{label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- CSS injection ----------------------------------------------------------

def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        .stApp { font-family: 'Inter', sans-serif; }

        .metrics-header { text-align:center; padding:1.8rem 0 0.6rem 0; }
        .metrics-header h1 {
            font-size:2rem; font-weight:800;
            background:linear-gradient(135deg,#4F8EF7,#a855f7,#22c55e);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text; margin:0;
        }
        .metrics-header p { color:#64748b; font-size:0.9rem; margin:0.3rem 0 0 0; }

        .section-heading {
            display:flex; align-items:center; gap:10px;
            font-size:1rem; font-weight:700; color:#94a3b8;
            letter-spacing:0.08em; text-transform:uppercase;
            margin:1.6rem 0 0.8rem 0;
        }
        .section-heading::after {
            content:""; flex:1; height:1px;
            background:linear-gradient(90deg,#334155 0%,transparent 100%);
        }

        .metric-ring-card {
            background:linear-gradient(145deg,#0f172a,#1e293b);
            border:1px solid; border-radius:18px;
            padding:1.4rem 0.8rem; text-align:center;
            transition:transform 0.25s ease,box-shadow 0.25s ease;
            height:100%; min-height:220px;
        }
        .metric-ring-card:hover { transform:translateY(-4px); }
        .ring-icon { font-size:1.4rem; margin-bottom:6px; }
        .ring-svg { display:block; margin:0 auto; }
        .ring-fill { transition:stroke-dasharray 1.2s cubic-bezier(0.4,0,0.2,1); }
        .ring-label { color:#cbd5e1; font-size:0.82rem; font-weight:600; margin:8px 0 2px 0; letter-spacing:0.02em; }
        .ring-sub { color:#475569; font-size:0.72rem; margin:0 0 6px 0; }
        .health-badge { font-size:0.68rem; font-weight:600; letter-spacing:0.04em; }

        .metric-speed-card {
            background:linear-gradient(145deg,#0f172a,#1e293b);
            border:1px solid; border-radius:18px;
            padding:1.4rem 0.8rem; text-align:center;
            transition:transform 0.25s ease; min-height:160px;
        }
        .metric-speed-card:hover { transform:translateY(-4px); }
        .speed-label { color:#94a3b8; font-size:0.78rem; font-weight:600; margin:4px 0 2px 0; letter-spacing:0.04em; }
        .speed-value { font-size:2rem; font-weight:800; margin:4px 0 2px 0; line-height:1.1; }
        .speed-sub { color:#475569; font-size:0.7rem; margin:0; }

        .vol-badge {
            border:1px solid; border-radius:14px;
            padding:1.2rem 0.8rem; text-align:center;
            transition:transform 0.2s ease;
        }
        .vol-badge:hover { transform:translateY(-3px); }
        .vol-count { font-size:2.2rem; font-weight:800; margin:6px 0 2px 0; }
        .vol-label { color:#64748b; font-size:0.75rem; margin:0; font-weight:600; }

        .survey-row {
            border:1px solid #1e293b; border-radius:12px;
            padding:1rem 1.2rem; margin-bottom:10px; transition:background 0.2s;
        }
        .survey-row:hover { background:#1e293b !important; }
        .survey-row-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
        .survey-outcome-label { color:#e2e8f0; font-size:0.88rem; font-weight:600; }
        .survey-count-badge { font-size:0.78rem; font-weight:700; padding:2px 10px; border-radius:20px; }
        .survey-track { background:#1e293b; border-radius:6px; height:10px; overflow:hidden; }
        .survey-fill { height:100%; border-radius:6px; }

        .sat-banner {
            border-radius:20px; padding:2rem; text-align:center;
            margin-bottom:1.4rem; border:2px solid;
        }
        .sat-score { font-size:4rem; font-weight:900; line-height:1; margin:0.4rem 0; }
        .sat-title { font-size:0.85rem; color:#94a3b8; margin:0; letter-spacing:0.06em; text-transform:uppercase; }
        .sat-sub { font-size:0.78rem; color:#475569; margin:0.3rem 0 0 0; }

        .split-bar-container {
            background:#1e293b; border-radius:10px;
            height:28px; overflow:hidden; display:flex; margin-bottom:10px;
        }
        .split-bar-ai {
            background:linear-gradient(90deg,#a855f7,#7c3aed);
            border-radius:10px 0 0 10px;
            display:flex; align-items:center; justify-content:center;
            font-size:0.75rem; font-weight:700; color:#fff;
        }
        .split-bar-human {
            background:linear-gradient(90deg,#0ea5e9,#0284c7);
            border-radius:0 10px 10px 0;
            display:flex; align-items:center; justify-content:center;
            font-size:0.75rem; font-weight:700; color:#fff;
        }

        .live-dot {
            display:inline-block; width:7px; height:7px;
            background:#22c55e; border-radius:50%; margin-right:5px;
            animation:pulse-dot 1.8s infinite;
        }
        @keyframes pulse-dot {
            0%,100% { opacity:1; transform:scale(1); }
            50%      { opacity:0.4; transform:scale(1.5); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---- main page --------------------------------------------------------------

def show() -> None:
    render_navbar("Success Metrics")
    _inject_css()

    st.markdown(
        """
        <div class="metrics-header">
            <h1>&#128202; Contact-Centre Success Matrix</h1>
            <p><span class="live-dot"></span>Real-time KPIs from live database &nbsp;&#183;&nbsp; Refreshed on every page load</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Loading metrics..."):
        data = api_client.get("/metrics/all")

    if isinstance(data, dict) and "error" in data:
        show_api_error(data)
        return

    resolution_pct   = _raw_pct(data.get("resolution_rate_pct"))
    ai_usage_pct     = _raw_pct(data.get("ai_usage_rate_pct"))
    kb_coverage_pct  = _raw_pct(data.get("knowledge_coverage_score"))
    avg_tta          = data.get("avg_time_to_answer_sec")
    avg_lat          = data.get("avg_response_latency_sec")
    ai_calls         = data.get("total_ai_calls", 0)
    human_calls      = data.get("total_human_calls", 0)
    total_calls      = ai_calls + human_calls
    survey           = data.get("satisfaction_survey", {})
    dist             = survey.get("distribution", {})
    total_surveys    = survey.get("total_surveys", 0)
    satisfaction_pct = _raw_pct(survey.get("satisfaction_score_pct"))

    # -- Section 1: Core Rate KPIs (ring cards) --------------------------------
    st.markdown(
        '<div class="section-heading">&#11041; &nbsp; Core Performance Rates</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _ring_card("Resolution Rate",    _pct(resolution_pct),   resolution_pct,
                   "&#9989;", "resolved / total cases",  "#22c55e")
    with c2:
        _ring_card("AI Usage Rate",      _pct(ai_usage_pct),     ai_usage_pct,
                   "&#129302;", "AI calls / total calls",  "#a855f7")
    with c3:
        _ring_card("KB Coverage",        _pct(kb_coverage_pct),  kb_coverage_pct,
                   "&#128218;", "READY docs / total docs", "#f59e0b")
    with c4:
        _ring_card("Satisfaction Score", _pct(satisfaction_pct), satisfaction_pct,
                   "&#128522;", "survey YES rate",          "#4F8EF7")

    # -- Section 2: Speed KPIs ------------------------------------------------
    st.markdown(
        '<div class="section-heading">&#9889; &nbsp; Speed &amp; Responsiveness</div>',
        unsafe_allow_html=True,
    )
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        _speed_card("Avg Time-to-Answer",   _fmt_sec(avg_tta),
                    "&#9201;", "#4F8EF7", "case creation to first call")
    with s2:
        _speed_card("Avg Response Latency", _fmt_sec(avg_lat),
                    "&#128222;", "#06b6d4", "avg call duration proxy")
    with s3:
        _speed_card("Total AI Calls",       f"{ai_calls:,}",
                    "&#129302;", "#a855f7", "outbound AI handled")
    with s4:
        _speed_card("Total Human Calls",    f"{human_calls:,}",
                    "&#128100;", "#06b6d4", "agent-handled calls")

    # -- Section 3: AI vs Human split -----------------------------------------
    st.markdown(
        '<div class="section-heading">&#128260; &nbsp; AI vs Human Call Split</div>',
        unsafe_allow_html=True,
    )
    if total_calls == 0:
        st.info("No call data yet.")
    else:
        ai_w    = int(ai_calls    / total_calls * 100)
        human_w = 100 - ai_w
        ai_lbl    = f"AI {ai_w}%"       if ai_w    > 12 else ""
        human_lbl = f"Human {human_w}%" if human_w > 12 else ""
        st.markdown(
            f"""
            <div style="margin-bottom:10px;">
                <div class="split-bar-container">
                    <div class="split-bar-ai"    style="width:{ai_w}%;">{ai_lbl}</div>
                    <div class="split-bar-human" style="width:{human_w}%;">{human_lbl}</div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#475569;margin-top:4px;">
                    <span style="color:#a855f7;">AI Outbound &nbsp;&#183;&nbsp; {ai_calls:,} calls ({ai_w}%)</span>
                    <span style="color:#0ea5e9;">Human &nbsp;&#183;&nbsp; {human_calls:,} calls ({human_w}%)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        v1, v2, v3 = st.columns(3)
        with v1:
            _volume_badge("AI Calls",    ai_calls,    "#a855f7", "&#129302;")
        with v2:
            _volume_badge("Human Calls", human_calls, "#0ea5e9", "&#128100;")
        with v3:
            _volume_badge("Total Calls", total_calls, "#4F8EF7", "&#128222;")

    # -- Section 4: Satisfaction Survey ----------------------------------------
    st.markdown(
        '<div class="section-heading">&#128522; &nbsp; Satisfaction Survey - AI Follow-up Results</div>',
        unsafe_allow_html=True,
    )
    if total_surveys == 0:
        st.info("No AI follow-up survey data yet. Run AI outbound calls to populate this section.")
    else:
        sat_color = _health_color(satisfaction_pct)
        tier_text = _health_label(satisfaction_pct)
        st.markdown(
            f"""
            <div class="sat-banner" style="border-color:{sat_color};background:linear-gradient(145deg,{sat_color}14,#0f172a);">
                <p class="sat-title">Overall Satisfaction Score</p>
                <p class="sat-score" style="color:{sat_color};">{_pct(satisfaction_pct)}</p>
                <p class="sat-sub">Based on {total_surveys:,} completed follow-up surveys
                    &nbsp;&#183;&nbsp; <span style="color:{sat_color};">{tier_text}</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        color_map = {
            "YES":       ("#22c55e", "&#9989; Resolved",   "#22c55e1a"),
            "NO":        ("#ef4444", "&#10060; Still Open", "#ef44441a"),
            "NO_ANSWER": ("#f59e0b", "&#128245; No Answer", "#f59e0b1a"),
            "UNKNOWN":   ("#64748b", "&#10067; Unknown",    "#64748b1a"),
        }
        for outcome, count in dist.items():
            pct_val = (count / total_surveys * 100) if total_surveys > 0 else 0
            col, label, bg = color_map.get(outcome, ("#4F8EF7", outcome, "#4F8EF71a"))
            st.markdown(
                f"""
                <div class="survey-row" style="background:{bg};">
                    <div class="survey-row-header">
                        <span class="survey-outcome-label">{label}</span>
                        <span class="survey-count-badge" style="background:{col}22;color:{col};">
                            {count:,} &nbsp; {pct_val:.1f}%
                        </span>
                    </div>
                    <div class="survey-track">
                        <div class="survey-fill" style="width:{pct_val:.1f}%;background:{col};"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    col_ref, _ = st.columns([1, 5])
    with col_ref:
        if st.button("&#128260; Refresh Metrics", type="secondary", use_container_width=True):
            st.rerun()
