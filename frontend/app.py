import streamlit as st
import sys
import os

# ── Path setup: allow imports from frontend root ──────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import APP_NAME, PAGE_ICON
from utils.session import init_session, is_authenticated, get_role
from utils.permissions import is_admin

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Dark background */
    .stApp { background-color: #0f0f1a; color: #e0e0e0; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d1f 0%, #111128 100%);
        border-right: 1px solid #1e1e3a;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,142,247,0.3); }

    /* Form inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background-color: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 8px;
        color: #e0e0e0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #1a1a2e; border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #888; border-radius: 8px; }
    .stTabs [aria-selected="true"] { background-color: #4F8EF7; color: white; }

    /* Expander */
    .streamlit-expanderHeader { background-color: #1a1a2e !important; border-radius: 8px; }

    /* Metrics */
    [data-testid="metric-container"] { background-color: #1a1a2e; border-radius: 10px; padding: 1rem; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f0f1a; }
    ::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session init ──────────────────────────────────────────────────────────────
init_session()

# ── Route: not authenticated → login ─────────────────────────────────────────
if not is_authenticated():
    from pages.login import show as show_login
    show_login()
    st.stop()

# ── Route: authenticated → dashboard ─────────────────────────────────────────
from components.sidebar import render_sidebar

current_page = render_sidebar()

# ── Page dispatcher ───────────────────────────────────────────────────────────
if current_page == "dashboard":
    if is_admin():
        from pages.admin_dashboard import show
    else:
        from pages.agent_dashboard import show
    show()

elif current_page == "customers":
    from pages.customers import show
    show()

elif current_page == "cases":
    from pages.cases import show
    show()

elif current_page == "calls":
    from pages.calls import show
    show()

elif current_page == "followups":
    from pages.followups import show
    show()

elif current_page == "documents":
    from pages.documents import show
    show()

elif current_page == "ai_assistant":
    from pages.ai_assistant import show
    show()

elif current_page == "knowledge_base":
    if is_admin():
        from pages.knowledge_base import show
        show()
    else:
        st.error("🚫 Access Denied")

elif current_page == "users":
    if is_admin():
        from pages.users import show
        show()
    else:
        st.error("🚫 Access Denied")

elif current_page == "reports":
    if is_admin():
        from pages.reports import show
        show()
    else:
        st.error("🚫 Access Denied")

elif current_page == "success_metrics":
    if is_admin():
        from pages.success_metrics import show
        show()
    else:
        st.error("🚫 Access Denied")

elif current_page == "audit_logs":
    if is_admin():
        from pages.audit_logs import show
        show()
    else:
        st.error("🚫 Access Denied")

else:
    st.error(f"Unknown page: {current_page}")
