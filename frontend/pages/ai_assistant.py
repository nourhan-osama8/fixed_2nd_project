"""
AI Assistant page — bilingual (Arabic / English) chat interface for the NileConnect agent.

Features:
- Chat-style conversation history (persisted in session_state)
- Uses ai_post() with 120 s timeout — no more Read-timed-out errors
- Shows which language the user is writing in
- Loading spinner during response
- Clear conversation button
- Bilingual example prompts (Arabic + English)
"""

import streamlit as st
from services import api_client
from components.navbar import render_navbar

# ── Arabic character detection ─────────────────────────────────────────────────

def _is_arabic(text: str) -> bool:
    """Return True if the text contains Arabic script characters."""
    arabic_ranges = range(0x0600, 0x06FF + 1)  # Arabic block
    return any(ord(c) in arabic_ranges for c in text)


def show() -> None:
    render_navbar("🤖 AI Assistant")

    st.markdown(
        """
        <style>
        .chat-user {
            background: linear-gradient(135deg, #1e3a5f, #1a2a4a);
            border-left: 3px solid #4F8EF7;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin: 0.4rem 0;
        }
        .chat-ai {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-left: 3px solid #00c896;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin: 0.4rem 0;
        }
        .chat-label-user { color: #4F8EF7; font-size: 0.75rem; font-weight: 600; margin-bottom: 4px; }
        .chat-label-ai   { color: #00c896; font-size: 0.75rem; font-weight: 600; margin-bottom: 4px; }
        .lang-badge {
            display: inline-block;
            font-size: 0.7rem;
            background: #2a2a4a;
            color: #aaa;
            border-radius: 4px;
            padding: 1px 6px;
            margin-left: 6px;
            vertical-align: middle;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Session state ──────────────────────────────────────────────────────────
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    # ── Header bar ─────────────────────────────────────────────────────────────
    col_title, col_clear = st.columns([5, 1])
    with col_title:
        st.markdown(
            "Ask me about **customers**, **cases**, **calls**, **company policies**, or anything else. "
            "I respond in the **same language** you write in — Arabic or English."
        )
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.ai_messages = []
            st.rerun()

    st.divider()

    # ── Conversation history ───────────────────────────────────────────────────
    for msg in st.session_state.ai_messages:
        if msg["role"] == "user":
            lang_tag = '<span class="lang-badge">AR</span>' if _is_arabic(msg["content"]) else '<span class="lang-badge">EN</span>'
            st.markdown(
                f'<div class="chat-user"><div class="chat-label-user">👤 You {lang_tag}</div>'
                f'{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-ai"><div class="chat-label-ai">🤖 AI Assistant</div>'
                f'{msg["content"]}</div>',
                unsafe_allow_html=True,
            )

    # ── Input ──────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("ai_chat_form", clear_on_submit=True):
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input(
                "Your question",
                placeholder="e.g. What cases does Ahmed have open?  /  كم عدد الحالات المفتوحة؟",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Send ➤", use_container_width=True, type="primary")

    if submitted and user_input.strip():
        question = user_input.strip()

        # Add user message
        st.session_state.ai_messages.append({"role": "user", "content": question})

        # Call backend using ai_post (120 s timeout — fixes the Read timed out error)
        lang_hint = "The user wrote in Arabic. You MUST reply entirely in Arabic." if _is_arabic(question) else ""
        payload = {"question": question}
        if lang_hint:
            # Prepend a language directive so the LLM is crystal-clear
            payload["question"] = f"[{lang_hint}]\n\n{question}"

        with st.spinner("🤖 Thinking... / جاري التفكير..."):
            result = api_client.ai_post("/ai/ask", payload)

        if isinstance(result, dict) and "error" in result:
            answer = f"⚠️ Error: {result['error']}"
        else:
            answer = result.get("answer", "No response received.")

        st.session_state.ai_messages.append({"role": "assistant", "content": answer})
        st.rerun()

    # ── Empty state hint ───────────────────────────────────────────────────────
    if not st.session_state.ai_messages:
        st.markdown(
            """
            <div style="text-align:center; color:#555; padding: 3rem 0;">
                <div style="font-size:3rem;">🤖</div>
                <p style="font-size:1.1rem; margin-top:1rem;">Ask me anything about NileConnect</p>
                <p style="font-size:0.85rem; color:#666;">I speak both Arabic 🇪🇬 and English 🇬🇧</p>
                <p style="font-size:0.85rem; color:#4F8EF7;">
                    "How many open cases are there?" &nbsp;|&nbsp;
                    "كم عدد الحالات المفتوحة؟" &nbsp;|&nbsp;
                    "What is the refund policy?"&nbsp;|&nbsp;
                    "ما هي سياسة الاسترداد؟"
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
