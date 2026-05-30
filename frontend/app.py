import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="DocuMind AI", page_icon="🤖", layout="wide")
st.title("DocuMind AI")
st.write("Upload technical PDFs and ask questions from them.")

# -----------------------------
# Session State
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "clarification_options" not in st.session_state:
    st.session_state.clarification_options = []

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Backend Status")
    try:
        r = requests.get(f"{BACKEND_URL}/", timeout=5)
        if r.status_code == 200:
            st.success("Backend is running")
        else:
            st.error(f"Backend error ({r.status_code})")
    except requests.exceptions.RequestException:
        st.error("Backend is not running")
        st.caption("Start it with: uvicorn backend.main:app --reload")

    st.divider()
    st.header("Session")

    if st.session_state.session_id:
        st.caption("Active session_id")
        st.code(st.session_state.session_id, language="text")
        if st.button("New chat (clear session)"):
            st.session_state.session_id = None
            st.session_state.clarification_options = []
            st.rerun()
    else:
        st.info("No session_id yet. Upload PDFs to create one.")

# -----------------------------
# 1) Upload PDFs
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
    upload_into_existing = st.checkbox(
        "Upload into existing session (if set)",
        value=True
    )

if process_btn:
    if not uploaded_files:
        st.warning("Please upload at least one PDF file.")
    else:
        files = [
            ("files", (f.name, f.getvalue(), "application/pdf"))
            for f in uploaded_files
        ]

        params = {}
        if upload_into_existing and st.session_state.session_id:
            params["session_id"] = st.session_state.session_id

        try:
            resp = requests.post(
                f"{BACKEND_URL}/upload-pdfs/",
                params=params,
                files=files,
                timeout=300
            )

            if resp.status_code != 200:
                st.error("PDF upload failed.")
                st.write(resp.text)
            else:
                data = resp.json()

                # Save session_id from backend
                new_session_id = data.get("session_id")
                if new_session_id:
                    st.session_state.session_id = new_session_id

                st.success(f"Processed {data['successful_uploads']} out of {data['total_files']} file(s).")
                st.caption(f"Session ID: {st.session_state.session_id}")

                for result in data.get("uploaded", []):
                    if result.get("status") == "success":
                        with st.expander(f"{result.get('filename')} - success"):
                            st.write(f"Doc ID: {result.get('doc_id')}")
                            st.write(f"Pages extracted: {result.get('pages_extracted')}")
                            st.write(f"Chunks created: {result.get('chunks_created')}")
                            st.write(f"Chunks stored: {result.get('chunks_stored')}")
                            st.write(f"Duplicates skipped: {result.get('duplicates_skipped')}")
                    else:
                        with st.expander(f"{result.get('filename')} - failed"):
                            st.error(result.get("error", "Unknown error"))

        except requests.exceptions.RequestException as e:
            st.error("Could not connect to backend.")
            st.write(e)

# -----------------------------
# 2) Retrieval Test (Session-scoped)
# -----------------------------
st.header("2. Test Retrieval (Session-scoped)")

retrieval_query = st.text_input(
    "Search uploaded documents (in this session)",
    placeholder="Example: install python modules / pip install / execute python script",
)

col1, col2, col3 = st.columns(3)
with col1:
    top_k = st.slider("Top K chunks", min_value=1, max_value=20, value=5)
with col2:
    min_similarity = st.slider("Minimum similarity", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
with col3:
    filter_session = st.checkbox("Filter by current session_id", value=True)

if st.button("Test Retrieval"):
    if not retrieval_query.strip():
        st.warning("Please enter a search query.")
    elif filter_session and not st.session_state.session_id:
        st.warning("No session_id yet. Upload PDFs first (or disable session filter).")
    else:
        params = {
            "q": retrieval_query.strip(),
            "top_k": top_k,
            "min_similarity": min_similarity,
        }
        if filter_session and st.session_state.session_id:
            params["session_id"] = st.session_state.session_id

        try:
            resp = requests.get(f"{BACKEND_URL}/search-test/", params=params, timeout=120)
            if resp.status_code != 200:
                st.error("Retrieval test failed.")
                st.write(resp.text)
            else:
                data = resp.json()
                st.write(data.get("message", ""))

                results = data.get("results", [])
                if not results:
                    st.warning("No reliable chunks found.")
                else:
                    for i, r in enumerate(results, start=1):
                        md = r.get("metadata", {}) or {}
                        with st.expander(f"Result {i} | Score: {r.get('similarity_score')} | {md.get('doc_name')}"):
                            st.write(f"Chunk ID: {r.get('chunk_id')}")
                            st.write(f"Doc ID: {md.get('doc_id')}")
                            st.write(f"Document: {md.get('doc_name')}")
                            st.write(f"Page: {md.get('page_number')}")
                            st.write(f"Chunk: {md.get('page_chunk_index')}")
                            st.write("Text:")
                            st.write(r.get("text", ""))

        except requests.exceptions.RequestException as e:
            st.error("Could not connect to backend.")
            st.write(e)

# -----------------------------
# 3) Ask a Question
# -----------------------------
st.header("3. Ask a Question (RAG)")

question = st.text_input(
    "Ask a question from your uploaded documents (in this session)",
    placeholder="Example: How do I create a git repo? / How do I execute it?",
)

if st.button("Ask", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    elif not st.session_state.session_id:
        st.warning("No session_id yet. Upload PDFs first.")
    else:
        payload = {"question": question.strip(), "session_id": st.session_state.session_id}

        try:
            resp = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=180)
            if resp.status_code != 200:
                st.error("Ask failed.")
                st.write(resp.text)
            else:
                data = resp.json()
                status = data.get("status")
                st.caption(f"Status: {status}")

                if status == "needs_clarification":
                    st.warning(data.get("answer", "Your question needs clarification."))
                    opts = data.get("clarification_options", []) or []
                    st.session_state.clarification_options = opts

                    if opts:
                        st.subheader("Choose a document to clarify (then re-ask more specifically)")
                        labels = [f"{o.get('doc_name')} ({o.get('doc_id')})" for o in opts]
                        st.selectbox("Documents", options=labels)

                        st.info(
                            "For now, re-ask with details.\n\n"
                            "Example:\n"
                            "- Instead of: 'How do I execute it?'\n"
                            "- Ask: 'How do I execute a Python script?'"
                        )
                    else:
                        st.info("No clarification options were returned.")

                else:
                    st.subheader("Answer")
                    st.write(data.get("answer", ""))

                    st.subheader("Rewritten Query")
                    st.write(data.get("rewritten_query", ""))

                    citations = data.get("citations", [])
                    if citations:
                        st.subheader("Citations")
                        for c in citations:
                            st.markdown(
                                f"""
**Document:** {c.get("doc_name")}   
**Page:** {c.get("page_number")}  
**Snippet:** {c.get("snippet")}
"""
                            )
                    else:
                        st.info("No citations returned.")

        except requests.exceptions.RequestException as e:
            st.error("Could not connect to backend.")
            st.write(e)