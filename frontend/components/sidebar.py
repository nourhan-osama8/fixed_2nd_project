import streamlit as st
from utils.session import get_user, get_role, logout
from utils.permissions import is_admin


def render_sidebar() -> str:
    """Render the navigation sidebar and return the selected page key."""
    user = get_user()
    role = get_role()

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
                <h2 style="color:#4F8EF7; margin:0;">🌐 NileConnect</h2>
                <p style="color:#888; font-size:0.8rem; margin:0;">AI Contact Center</p>
            </div>
            <hr style="border-color:#2a2a2a; margin: 0.5rem 0 1rem 0;">
            """,
            unsafe_allow_html=True,
        )

        if user:
            st.markdown(
                f"<p style='color:#ccc; font-size:0.85rem;'>👤 <b>{user.get('name','')}</b><br>"
                f"<span style='color:#888; font-size:0.75rem;'>{role.replace('_',' ').title() if role else ''}</span></p>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Common pages
        pages = {}
        if is_admin():
            pages = {
                "dashboard": "📊 Dashboard",
                "success_metrics": "🏆 Success Metrics",
                "customers": "👥 Customers",
                "cases": "📋 Cases",
                "calls": "📞 Calls",
                "followups": "🔔 Follow-ups",
                "ai_assistant": "🤖 AI Assistant",
                "knowledge_base": "📚 Knowledge Base",
                "documents": "📄 Documents",
                "users": "⚙️ Users",
                "reports": "📈 Reports",
                "audit_logs": "🔍 Audit Logs",
            }
        else:
            pages = {
                "dashboard": "🏠 My Dashboard",
                "customers": "👥 Customers",
                "cases": "📋 Cases",
                "calls": "📞 Calls",
                "followups": "🔔 Follow-ups",
                "ai_assistant": "🤖 AI Assistant",
            }

        # Initialize selected page
        if "current_page" not in st.session_state:
            st.session_state.current_page = "dashboard"

        for key, label in pages.items():
            is_selected = st.session_state.current_page == key
            if st.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.current_page = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            logout()

    return st.session_state.current_page
