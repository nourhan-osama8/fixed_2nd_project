import streamlit as st
from services import api_client
from components.navbar import render_navbar
from components.cards import metric_card
from components.alerts import show_api_error


def show() -> None:
    render_navbar("📊 Admin Dashboard")

    # Fetch summary
    summary = api_client.get("/reports/summary")
    cases_by_status = api_client.get("/reports/cases-by-status")
    cases_by_category = api_client.get("/reports/cases-by-category")

    if "error" in (summary or {}):
        show_api_error(summary)
        return

    # ── Metric Cards ─────────────────────────────────────────────
    st.markdown("### 📈 Platform Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Customers", summary.get("total_customers", 0), icon="👥", color="#4F8EF7")
    with c2:
        metric_card("Open Cases", summary.get("open_cases", 0), icon="📋", color="#f59e0b")
    with c3:
        metric_card("Resolved Cases", summary.get("resolved_cases", 0), icon="✅", color="#22c55e")
    with c4:
        metric_card("Pending Follow-ups", summary.get("pending_followups", 0), icon="🔔", color="#a855f7")

    st.markdown("---")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        metric_card("Total Cases", summary.get("total_cases", 0), icon="📁", color="#4F8EF7")
    with c6:
        metric_card("In Progress", summary.get("in_progress_cases", 0), icon="🔄", color="#3b82f6")
    with c7:
        metric_card("Needs Human", summary.get("needs_human", 0), icon="🔴", color="#ef4444")
    with c8:
        metric_card("Active Agents", summary.get("total_agents", 0), icon="🧑‍💼", color="#06b6d4")

    st.markdown("---")

    # ── Charts ───────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Cases by Status")
        if isinstance(cases_by_status, dict) and "error" not in cases_by_status:
            import pandas as pd
            df_status = pd.DataFrame(
                [{"Status": k.replace("_", " "), "Count": v} for k, v in cases_by_status.items()]
            )
            st.bar_chart(df_status.set_index("Status"))
        else:
            st.info("No case status data.")

    with col_right:
        st.markdown("#### Cases by Category")
        if isinstance(cases_by_category, dict) and "error" not in cases_by_category:
            import pandas as pd
            df_cat = pd.DataFrame(
                [{"Category": k.replace("_", " "), "Count": v} for k, v in cases_by_category.items()]
            )
            st.bar_chart(df_cat.set_index("Category"))
        else:
            st.info("No category data.")

    st.markdown("---")
    st.markdown("#### 🚀 Quick Actions")
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        if st.button("➕ New Customer", use_container_width=True):
            st.session_state.current_page = "customers"
            st.rerun()
    with qc2:
        if st.button("📋 View All Cases", use_container_width=True):
            st.session_state.current_page = "cases"
            st.rerun()
    with qc3:
        if st.button("📚 Knowledge Base", use_container_width=True):
            st.session_state.current_page = "documents"
            st.rerun()
    with qc4:
        if st.button("🏆 Success Metrics", use_container_width=True):
            st.session_state.current_page = "success_metrics"
            st.rerun()
