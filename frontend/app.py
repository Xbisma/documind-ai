import requests
import streamlit as st


BACKEND_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="DocuMind AI",
    page_icon="🤖",
    layout="wide"
)

st.title("DocuMind AI")
st.write("Upload technical PDFs and ask questions from them.")


# -----------------------------
# Session state init
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "last_clarification_options" not in st.session_state:
    st.session_state.last_clarification_options = []

if "selected_doc_id" not in st.session_state:
    st.session_state.selected_doc_id = None


# -----------------------------
# Backend health check + session display
# -----------------------------
with st.sidebar:
    st.header("Backend Status")

    try:
        health_response = requests.get(f"{BACKEND_URL}/", timeout=5)

        if health_response.status_code == 200:
            st.success("Backend is running")
        else:
            st.error("Backend responded with an error")

    except requests.exceptions.RequestException:
        st.error("Backend is not running")
        st.caption("Start it with: uvicorn backend.main:app --reload")

    st.divider()
    st.header("Chat Session")

    if st.session_state.session_id:
        st.code(st.session_state.session_id, language="text")
        if st.button("Start New Chat (new session)"):
            st.session_state.session_id = None
            st.session_state.last_clarification_options = []
            st.session_state.selected_doc_id = None
            st.rerun()
    else:
        st.info("No active session yet. Upload PDFs to create one.")


# -----------------------------
# PDF Upload Section
# -----------------------------
st.header("1. Upload PDFs")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

col_u1, col_u2 = st.columns([1, 1])

with col_u1:
    process_btn = st.button("Process PDFs", type="primary")

with col_u2:
    use_existing = st.checkbox(
        "Upload into existing session (if set)",
        value=True,
        help="If unchecked, backend will generate a new session_id for this upload."
    )

if process_btn:
    if not uploaded_files:
        st.warning("Please upload at least one PDF file.")
    else:
        files = []
        for uploaded_file in uploaded_files:
            files.append(
                (
                    "files",
                    (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf"
                    )
                )
            )

        params = {}
        # If you want to continue adding docs to same chat session, pass session_id
        if use_existing and st.session_state.session_id:
            params["session_id"] = st.session_state.session_id

        try:
            response = requests.post(
                f"{BACKEND_URL}/upload-pdfs/",
                params=params,
                files=files,
                timeout=300
            )

            if response.status_code == 200:
                data = response.json()

                # Save session_id returned by backend
                returned_session_id = data.get("session_id")
                if returned_session_id:
                    st.session_state.session_id = returned_session_id

                st.success(
                    f"Processed {data['successful_uploads']} out of {data['total_files']} file(s)."
                )

                st.caption(f"Session ID: {st.session_state.session_id}")

                for result in data["uploaded"]:
                    if result.get("status") == "success":
                        with st.expander(f"{result['filename']} - success"):
                            st.write(f"Doc ID: {result.get('doc_id')}")
                            st.write(f"Pages extracted: {result['pages_extracted']}")
                            st.write(f"Chunks created: {result['chunks_created']}")
                            st.write(f"Chunks stored: {result['chunks_stored']}")
                            st.write(f"Duplicates skipped: {result['duplicates_skipped']}")
                    else:
                        with st.expander(f"{result['filename']} - failed"):
                            st.error(result.get("error", "Unknown error"))

            else:
                st.error("PDF upload failed.")
                st.write(response.text)

        except requests.exceptions.RequestException as error:
            st.error("Could not connect to backend.")
            st.write(error)


# -----------------------------
# Retrieval Test Section
# -----------------------------
st.header("2. Test Retrieval (Session-scoped)")

st.write(
    "This tests vector retrieval. If retrieval does not return good chunks, the LLM answer will be weak."
)

retrieval_query = st.text_input(
    "Search uploaded documents (in this session)",
    placeholder="Example: pip install / git init / execute python script",
    key="retrieval_query"
)

col1, col2, col3 = st.columns(3)

with col1:
    top_k = st.slider("Top K chunks", min_value=1, max_value=20, value=5)

with col2:
    min_similarity = st.slider(
        "Minimum similarity",
        min_value=0.0,
        max_value=1.0,
        value=0.35,
        step=0.05
    )

with col3:
    include_session_filter = st.checkbox(
        "Filter by current session_id",
        value=True,
        help="Recommended: prevents mixing old uploads from other sessions."
    )

if st.button("Test Retrieval"):
    if not retrieval_query.strip():
        st.warning("Please enter a search query.")
    elif include_session_filter and not st.session_state.session_id:
        st.warning("No session_id yet. Upload PDFs first (or disable session filter).")
    else:
        try:
            params = {
                "q": retrieval_query,
                "top_k": top_k,
                "min_similarity": min_similarity
            }
            if include_session_filter and st.session_state.session_id:
                params["session_id"] = st.session_state.session_id

            response = requests.get(
                f"{BACKEND_URL}/search-test/",
                params=params,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()

                st.write(data.get("message", ""))

                results = data.get("results", [])
                if not results:
                    st.warning("No reliable chunks found.")
                else:
                    for index, result in enumerate(results, start=1):
                        metadata = result.get("metadata", {}) or {}

                        with st.expander(
                            f"Result {index} | Score: {result.get('similarity_score')} | {metadata.get('doc_name')}"
                        ):
                            st.write(f"Chunk ID: {result.get('chunk_id')}")
                            st.write(f"Doc ID: {metadata.get('doc_id')}")
                            st.write(f"Document: {metadata.get('doc_name')}")
                            st.write(f"Page: {metadata.get('page_number')}")
                            st.write(f"Chunk: {metadata.get('page_chunk_index')}")
                            st.write(f"Similarity Score: {result.get('similarity_score')}")
                            st.write("Text:")
                            st.write(result.get("text", ""))

            else:
                st.error("Retrieval test failed.")
                st.write(response.text)

        except requests.exceptions.RequestException as error:
            st.error("Could not connect to backend.")
            st.write(error)


# -----------------------------
# Ask Question Section
# -----------------------------
st.header("3. Ask a Question (RAG)")

question = st.text_input(
    "Ask a question from your uploaded documents (in this session)",
    placeholder="Example: How do I create a git repo? / How do I execute it?",
    key="question_input"
)

ask_btn = st.button("Ask", type="primary")

if ask_btn:
    if not question.strip():
        st.warning("Please enter a question.")
    elif not st.session_state.session_id:
        st.warning("No session_id yet. Upload PDFs first.")
    else:
        try:
            payload = {
                "question": question.strip(),
                "session_id": st.session_state.session_id,
            }

            response = requests.post(
                f"{BACKEND_URL}/ask",
                json=payload,
                timeout=180
            )

            if response.status_code == 200:
                data = response.json()

                status = data.get("status")
                st.caption(f"Status: {status}")

                # Handle clarification flow
                if status == "needs_clarification":
                    st.warning(data.get("answer", "Question needs clarification."))

                    options = data.get("clarification_options", []) or []
                    st.session_state.last_clarification_options = options

                    if options:
                        label_map = {f"{o.get('doc_name')} ({o.get('doc_id')})": o.get("doc_id") for o in options}
                        choice = st.selectbox(
                            "Select the document you meant (then re-ask more specifically):",
                            options=list(label_map.keys())
                        )
                        st.session_state.selected_doc_id = label_map.get(choice)

                        st.info(
                            "Backend currently asks you to clarify, but it does not yet accept selected_doc_id. "
                            "For now: re-ask your question mentioning the chosen doc/topic explicitly.\n\n"
                            "Example:\n"
                            "- Instead of: 'How do I execute it?'\n"
                            "- Ask: 'How do I execute a Python script?'"
                        )
                    else:
                        st.info("No clarification options returned.")

                else:
                    st.subheader("Answer")
                    st.write(data.get("answer", "No answer returned."))

                    st.subheader("Rewritten Query")
                    st.write(data.get("rewritten_query", ""))

                    used_doc_ids = data.get("used_doc_ids")
                    if used_doc_ids:
                        st.subheader("Doc Routing (used_doc_ids)")
                        st.write(used_doc_ids)

                    citations = data.get("citations", [])
                    if citations:
                        st.subheader("Citations")
                        for citation in citations:
                            st.markdown(
                                f"""
**Document:** {citation.get("doc_name")}  
**Doc ID:** {citation.get("doc_id")}  
**Page:** {citation.get("page_number")}  
**Chunk ID:** {citation.get("chunk_id")}  
**Similarity Score:** {citation.get("similarity_score")}  
**Snippet:** {citation.get("snippet")}
"""
                            )
                    else:
                        st.info("No citations returned.")

            else:
                st.error("Something went wrong while asking the question.")
                st.write(response.text)

        except requests.exceptions.RequestException as error:
            st.error("Could not connect to backend.")
            st.write(error)