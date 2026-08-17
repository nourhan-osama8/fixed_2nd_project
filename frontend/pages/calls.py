import streamlit as st
from datetime import datetime, timezone
from services import call_service, customer_service, case_service
from components.navbar import render_navbar
from components.alerts import show_success, show_error, show_api_error
from components.forms import section_header
from utils.formatters import format_datetime, format_duration, status_badge

CALL_TYPES = ["INBOUND_HUMAN", "OUTBOUND_HUMAN", "OUTBOUND_AI"]
OUTCOMES = ["PENDING", "RESOLVED", "FOLLOW_UP_REQUIRED", "NO_ANSWER", "ESCALATED"]


def show() -> None:
    render_navbar("📞 Calls")

    tab1, tab2 = st.tabs(["📋 Call History", "➕ Record Call"])

    # ── Tab 1: History ────────────────────────────────────────────
    with tab1:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_customer = st.session_state.get("filter_customer_id")
        with col_f2:
            filter_case = st.session_state.get("filter_case_id")

        if filter_case:
            st.info(f"🔍 Filtered by Case ID: `{filter_case[:8]}...`")
            if st.button("Clear Filter"):
                st.session_state.pop("filter_case_id", None)
                st.rerun()

        params = {}
        if filter_customer:
            params["customer_id"] = filter_customer
        if filter_case:
            params["case_id"] = filter_case

        calls = call_service.get_calls(limit=100, **params)

        if isinstance(calls, dict) and "error" in calls:
            show_api_error(calls)
        elif not calls:
            st.info("📭 No calls recorded yet.")
        else:
            for call in calls:
                icon = {"INBOUND_HUMAN": "📥", "OUTBOUND_HUMAN": "📤", "OUTBOUND_AI": "🤖"}.get(
                    call.get("call_type", ""), "📞"
                )
                call_id = str(call.get("id", ""))
                toggle_key = f"show_transcript_{call_id}"
                if toggle_key not in st.session_state:
                    st.session_state[toggle_key] = False

                with st.container(border=True):
                    header_col, btn_col = st.columns([4, 1])
                    with header_col:
                        st.markdown(
                            f"**{icon} {call.get('call_type','').replace('_',' ').title()}** &nbsp;|&nbsp; "
                            f"{format_datetime(call.get('started_at'))} &nbsp;|&nbsp; "
                            f"{status_badge(call.get('outcome',''))}",
                            unsafe_allow_html=True,
                        )
                    with btn_col:
                        expand_key = f"expand_{call_id}"
                        if expand_key not in st.session_state:
                            st.session_state[expand_key] = False
                        if st.button("▼ Details" if not st.session_state[expand_key] else "▲ Hide", key=f"expbtn_{call_id}"):
                            st.session_state[expand_key] = not st.session_state[expand_key]

                    if st.session_state.get(f"expand_{call_id}", False):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Type:** {call.get('call_type','—').replace('_',' ').title()}")
                            st.write(f"**Started:** {format_datetime(call.get('started_at'))}")
                            st.write(f"**Ended:** {format_datetime(call.get('ended_at'))}")
                            st.write(f"**Duration:** {format_duration(call.get('duration'))}")
                        with c2:
                            st.write(f"**Outcome:** {status_badge(call.get('outcome','—'))}")
                            st.write(f"**Customer ID:** `{str(call.get('customer_id','—'))[:8]}...`")
                        if call.get("summary"):
                            st.write(f"**Summary:** {call.get('summary')}")
                        if call.get("transcript"):
                            if st.button("📄 Show/Hide Transcript", key=f"btn_{call_id}"):
                                st.session_state[toggle_key] = not st.session_state[toggle_key]
                            if st.session_state[toggle_key]:
                                st.text_area("Transcript", value=call.get("transcript"), height=200, disabled=True, key=f"ta_{call_id}")

    # ── Tab 2: Record Call ────────────────────────────────────────
    with tab2:
        section_header("Record a New Call", "Log a human inbound or outbound call")

        customers_data = customer_service.get_customers(limit=200)
        if isinstance(customers_data, dict) and "error" in customers_data:
            show_api_error(customers_data)
            return

        if not customers_data:
            st.warning("No customers yet. Please create a customer first.")
            return

        customer_options = {f"{c['name']} ({c['phone']})": c["id"] for c in customers_data}

        with st.form("create_call_form", clear_on_submit=True):
            selected_customer_label = st.selectbox("Customer *", list(customer_options.keys()))
            call_type = st.selectbox("Call Type *", CALL_TYPES, index=0)
            outcome = st.selectbox("Outcome", OUTCOMES, index=0)
            col1, col2 = st.columns(2)
            with col1:
                duration_min = st.number_input("Duration (minutes)", min_value=0, max_value=120, value=0)
                duration_sec = st.number_input("Duration (seconds)", min_value=0, max_value=59, value=0)
            with col2:
                st.write("")  # spacer
            summary = st.text_area("Call Summary", placeholder="Briefly describe what was discussed...")
            transcript = st.text_area("Transcript (optional)", placeholder="Full call transcript...")
            submitted = st.form_submit_button("✅ Record Call", type="primary", use_container_width=True)

        if submitted:
            customer_id = customer_options[selected_customer_label]
            total_seconds = duration_min * 60 + duration_sec
            result = call_service.create_call({
                "customer_id": customer_id,
                "call_type": call_type,
                "outcome": outcome,
                "duration": total_seconds if total_seconds > 0 else None,
                "summary": summary.strip() or None,
                "transcript": transcript.strip() or None,
            })
            if "error" in result:
                show_error(result["error"])
            else:
                show_success("Call recorded successfully!")
                st.rerun()
