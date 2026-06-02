import uuid
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from frontend.ui.evaluation_ui import render_evaluation_tab
from frontend.services.backend_client import upload_pdfs, search_test, ask
from frontend.storage.chat_store import init_db, create_chat, list_chats, delete_chat, add_message, get_messages, update_chat_title, get_chat

from frontend.storage.docs_store import init_docs_table, add_docs, list_docs
from frontend.ui.chat_ui import render_citations

from frontend.ui.chat_list_sidebar import render_chatgpt_sidebar


st.set_page_config(page_title="DocuMind AI", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; }
      h1, h2, h3 { letter-spacing: -0.02em; }
      /* make tabs look cleaner */
      div[data-baseweb="tab-list"] button {
        font-weight: 600;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("DocuMind AI")
st.caption("Upload PDFs, chat with citations, and run retrieval evaluation.")

# -----------------------------
# Init persistent storage
# -----------------------------
init_db()

st.sidebar.caption("DEBUG: DB file path")
from frontend.storage import chat_store
st.sidebar.code(chat_store.DB_PATH, language="text")

init_docs_table()

# -----------------------------
# Session State
# -----------------------------
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None

if "backend_ok" not in st.session_state:
    st.session_state.backend_ok = True

if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = None


# -----------------------------
# URL routing: ?chat=<chat_id>
# -----------------------------
try:
    qp = st.query_params
    url_chat = qp.get("chat")
except Exception:
    url_chat = None

if url_chat and "active_chat_id" in st.session_state:
    # if URL says a chat and it's different, load it
    if st.session_state.active_chat_id != url_chat:
        st.session_state.active_chat_id = url_chat
        # load session_id from DB if exists
        try:
            chat = get_chat(url_chat)
            st.session_state.active_session_id = chat["session_id"] if chat and chat.get("session_id") else None
        except Exception:
            pass

# -----------------------------
# Helpers
# -----------------------------
def _new_chat() -> str:
    chat_id = str(uuid.uuid4())
    title = "New chat"
    session_id = ""

    create_chat(chat_id=chat_id, title=title, session_id=session_id)

    st.session_state.active_chat_id = chat_id
    st.session_state.active_session_id = None
    st.session_state.pending_clarification = None

    return chat_id


def _load_chat(chat_id: str):
    chats = list_chats()
    match = next((c for c in chats if c["chat_id"] == chat_id), None)

    st.session_state.active_chat_id = chat_id
    st.session_state.active_session_id = (
        match["session_id"] if match and match["session_id"] else None
    )
    st.session_state.pending_clarification = None


def _ensure_active_chat():
    if not st.session_state.active_chat_id:
        _new_chat()

# -----------------------------
# Render sidebar
# -----------------------------
_ensure_active_chat()

chats = list_chats()

selected_chat_id, action = render_chatgpt_sidebar(
    chats=chats,
    active_chat_id=st.session_state.active_chat_id,
)

if action == "new_chat":
    _new_chat()
    st.query_params["chat"] = st.session_state.active_chat_id
    st.rerun()

if action == "select_chat" and selected_chat_id:
    _load_chat(selected_chat_id)
    st.query_params["chat"] = selected_chat_id
    st.rerun()

if action == "delete_chat" and selected_chat_id:
    delete_chat(selected_chat_id)
    # if deleted active, reset
    if selected_chat_id == st.session_state.active_chat_id:
        st.session_state.active_chat_id = None
        st.session_state.active_session_id = None
        st.toast("Chat deleted", icon="🗑️")
    st.rerun()

# keep URL in sync
if st.session_state.active_chat_id:
    st.query_params["chat"] = st.session_state.active_chat_id

# -----------------------------
# Tabs
# -----------------------------
tab_chat, tab_retrieval, tab_eval = st.tabs(
    ["Chat", "Retrieval Test", "Evaluation"]
)


# =========================================================
# TAB 1: CHAT
# =========================================================
with tab_chat:
    st.subheader("Chat")

    st.markdown("### Upload PDFs (adds to this chat’s session)")

    uploaded_files = st.file_uploader(
        "Upload one or more PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader_chat",
    )

    col_u1, col_u2 = st.columns([1, 1])

    with col_u1:
        do_upload = st.button("Process PDFs", type="primary")

    with col_u2:
        upload_into_existing = st.checkbox(
            "Upload into existing session (if set)", value=True
        )

    if do_upload:
        if not uploaded_files:
            st.warning("Please upload at least one PDF.")
        else:
            files = [
                ("files", (f.name, f.getvalue(), "application/pdf"))
                for f in uploaded_files
            ]

            session_id_to_use: Optional[str] = None

            if (
                upload_into_existing
                and st.session_state.active_session_id
            ):
                session_id_to_use = st.session_state.active_session_id

            try:
                data = upload_pdfs(
                    files=files,
                    session_id=session_id_to_use,
                )

                new_session_id = data.get("session_id")

                if new_session_id:
                    st.session_state.active_session_id = new_session_id

                    from frontend.storage.chat_store import (
                        update_chat_session_id,
                    )

                    update_chat_session_id(
                        st.session_state.active_chat_id,
                        new_session_id,
                    )

                st.success(
                    f"Processed {data['successful_uploads']} out of "
                    f"{data['total_files']} file(s)."
                )

                uploaded_results = data.get("uploaded", []) or []

                success_docs = [
                    {
                        "doc_id": r.get("doc_id"),
                        "filename": r.get("filename"),
                    }
                    for r in uploaded_results
                    if r.get("status") == "success"
                ]

                if (
                    st.session_state.active_session_id
                    and success_docs
                ):
                    add_docs(
                        st.session_state.active_session_id,
                        success_docs,
                    )

                for r in uploaded_results:
                    if r.get("status") == "success":
                        with st.expander(
                            f"{r.get('filename')} - success"
                        ):
                            st.write(f"Doc ID: {r.get('doc_id')}")
                            st.write(
                                f"Pages extracted: {r.get('pages_extracted')}"
                            )
                            st.write(
                                f"Chunks created: {r.get('chunks_created')}"
                            )
                            st.write(
                                f"Chunks stored: {r.get('chunks_stored')}"
                            )
                            st.write(
                                f"Duplicates skipped: {r.get('duplicates_skipped')}"
                            )
                    else:
                        with st.expander(
                            f"{r.get('filename')} - failed"
                        ):
                            st.error(r.get("error", "Unknown error"))

                st.rerun()

            except Exception as e:
                st.error("Upload failed.")
                st.write(str(e))

    st.divider()

    st.markdown("### Conversation")

    messages = get_messages(st.session_state.active_chat_id)

    if not messages:
        st.info(
            "No messages in this chat yet. Upload PDFs and ask a question."
        )
    else:
        for m in messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])

    st.divider()

    st.markdown("### Ask")

    question = st.text_input(
        "Ask a question (uses this chat session)",
        key="question_input",
    )

    if st.button("Send", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        elif not st.session_state.active_session_id:
            st.warning(
                "No session_id yet. Upload PDFs in this chat first."
            )
        else:
            add_message(
                st.session_state.active_chat_id,
                "user",
                question.strip(),
            )

            # If this chat is still default title, update it based on the first user question
            try:
                chats = list_chats()
                st.sidebar.caption(f"DEBUG: chats found = {len(chats)}")
                current = next((c for c in chats if c["chat_id"] == st.session_state.active_chat_id), None)
                if current and (current.get("title") in (None, "", "New chat")):
                    words = question.strip().split()
                    new_title = " ".join(words[:7])
                    if len(words) > 7:
                        new_title += "…"
                    update_chat_title(st.session_state.active_chat_id, new_title)
            except Exception:
                pass

            try:
                data = ask(
                    question=question.strip(),
                    session_id=st.session_state.active_session_id,
                )

                status = data.get("status")

                if status == "needs_clarification":
                    add_message(
                        st.session_state.active_chat_id,
                        "assistant",
                        data.get(
                            "answer",
                            "Your question needs clarification.",
                        ),
                    )

                    st.session_state.pending_clarification = data.get(
                        "clarification_options",
                        [],
                    )

                    st.rerun()

                answer_text = data.get("answer", "")

                add_message(
                    st.session_state.active_chat_id,
                    "assistant",
                    answer_text,
                )

                with st.chat_message("assistant"):
                    st.write(answer_text)
                    render_citations(data.get("citations", []))

                st.rerun()

            except Exception as e:
                add_message(
                    st.session_state.active_chat_id,
                    "assistant",
                    "Ask failed (backend error).",
                )
                st.error("Ask failed.")
                st.write(str(e))


# =========================================================
# TAB 2: RETRIEVAL
# =========================================================
with tab_retrieval:
    st.subheader("Retrieval Test (Session-scoped)")

    q = st.text_input(
        "Search query",
        key="retrieval_q",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        top_k = st.slider("Top K", 1, 20, 5)

    with col2:
        min_sim = st.slider(
            "Min similarity",
            0.0,
            1.0,
            0.35,
            0.05,
        )

    with col3:
        filter_session = st.checkbox(
            "Filter by current session_id",
            value=True,
        )

    if st.button("Run Retrieval Test"):
        if not q.strip():
            st.warning("Enter a query.")
        elif (
            filter_session
            and not st.session_state.active_session_id
        ):
            st.warning(
                "No session_id in this chat yet. Upload PDFs first."
            )
        else:
            session_id = (
                st.session_state.active_session_id
                if filter_session
                else None
            )

            try:
                data = search_test(
                    query=q.strip(),
                    session_id=session_id,
                    top_k=top_k,
                    min_similarity=min_sim,
                )

                st.write(data.get("message", ""))

                results = data.get("results", [])

                if not results:
                    st.warning("No reliable chunks found.")
                else:
                    for i, r in enumerate(results, start=1):
                        md = r.get("metadata", {}) or {}

                        with st.expander(
                            f"Result {i} | {md.get('doc_name')} | "
                            f"score={r.get('similarity_score')}"
                        ):
                            st.write(md.get("doc_name"))
                            st.write(md.get("page_number"))
                            st.write(r.get("text", ""))

            except Exception as e:
                st.error("Retrieval test failed.")
                st.write(str(e))


# =========================================================
# TAB 3: EVALUATION
# =========================================================
with tab_eval:
    render_evaluation_tab(
        default_session_id=st.session_state.active_session_id or ""
    )