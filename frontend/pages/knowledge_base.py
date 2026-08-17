"""
Knowledge Base page — admin-only document management for RAG.

Features:
- Upload PDF, TXT, or DOCX files to the knowledge base
- PDF and TXT files are automatically indexed into the RAG engine
- DOCX files are stored for reference but not RAG-indexed
- List all uploaded documents with metadata
- Delete documents (removes from RAG too)
- Trigger manual RAG rebuild
- Show RAG index status
"""

import streamlit as st
from services import api_client, document_service
from components.navbar import render_navbar
from components.alerts import show_success, show_error, show_api_error
from utils.permissions import is_admin


def show() -> None:
    render_navbar("📚 Knowledge Base")

    if not is_admin():
        st.error("🚫 Access Denied — Admins only.")
        return

    # ── RAG Status ─────────────────────────────────────────────────────────────
    status = api_client.get("/ai/rag/status")
    if isinstance(status, dict) and "error" not in status:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("RAG Status", "✅ Ready" if status.get("is_ready") else "⚠️ Not Ready")
        with col2:
            st.metric("Indexed Chunks", status.get("document_count", 0))
        with col3:
            if st.button("🔄 Rebuild RAG Index", type="secondary"):
                with st.spinner("Rebuilding RAG index..."):
                    result = api_client.post("/ai/rag/rebuild", {})
                if isinstance(result, dict) and "error" in result:
                    show_error(result["error"])
                else:
                    show_success(result.get("message", "RAG index rebuilt!"))
                    st.rerun()
    st.divider()

    tab1, tab2 = st.tabs(["📋 Documents", "⬆️ Upload New Document"])

    # ── Tab 1: Document List ────────────────────────────────────────────────────
    with tab1:
        docs = document_service.get_documents(limit=100)

        if isinstance(docs, dict) and "error" in docs:
            show_api_error(docs)
        elif not docs:
            st.info("📭 No documents uploaded yet. Use the Upload tab to add files.")
        else:
            for doc in docs:
                with st.container(border=True):
                    col_info, col_status, col_del = st.columns([4, 1, 1])
                    with col_info:
                        st.markdown(f"**{doc.get('original_name', doc.get('filename', '—'))}**")
                        size_kb = round(doc.get("file_size", 0) / 1024, 1)
                        st.caption(
                            f"Type: `{doc.get('file_type','?').upper()}` &nbsp;|&nbsp; "
                            f"Size: `{size_kb} KB` &nbsp;|&nbsp; "
                            f"Uploaded: `{doc.get('created_at','')[:10]}`"
                        )
                    with col_status:
                        status_val = doc.get("status", "")
                        color = {"READY": "#00c896", "FAILED": "#ff4444", "PROCESSING": "#f0a500"}.get(status_val, "#888")
                        st.markdown(
                            f'<span style="color:{color}; font-weight:600;">● {status_val}</span>',
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        doc_id = doc.get("id", "")
                        if st.button("🗑️", key=f"del_{doc_id}", help="Delete document"):
                            result = api_client.delete(f"/documents/{doc_id}")
                            if isinstance(result, dict) and "error" in result:
                                show_error(result["error"])
                            else:
                                show_success("Document deleted and RAG index is updating.")
                                st.rerun()

    # ── Tab 2: Upload ───────────────────────────────────────────────────────────
    with tab2:
        st.markdown(
            """
            Upload **PDF**, **TXT**, or **DOCX** files. All formats are automatically
            indexed into the AI knowledge base — you can upload multiple documents
            and they will all be available for search without deleting previous ones.

            | Format | RAG Indexed? | Notes |
            |--------|-------------|-------|
            | PDF    | ✅ Yes       | Full text extracted page-by-page, searchable by AI |
            | TXT    | ✅ Yes       | Plain text indexed and searchable by AI |
            | DOCX   | ✅ Yes       | Paragraphs extracted and indexed, searchable by AI |
            """
        )

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "docx"],
            help="PDF and TXT are indexed for AI search. DOCX is stored for reference only.",
        )

        if uploaded_file:
            st.info(
                f"**Selected:** {uploaded_file.name} "
                f"({round(uploaded_file.size / 1024, 1)} KB)"
            )
            if st.button("⬆️ Upload & Index", type="primary"):
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    result = document_service.upload_document(uploaded_file)
                if isinstance(result, dict) and "error" in result:
                    show_error(result["error"])
                else:
                    show_success(
                        f"✅ **{uploaded_file.name}** uploaded! "
                        "The RAG index is rebuilding in the background."
                    )
                    st.rerun()
