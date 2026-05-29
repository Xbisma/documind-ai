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
# Backend health check
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
        st.caption("Start it with: python -m uvicorn backend.main:app --reload")


# -----------------------------
# PDF Upload Section
# -----------------------------

st.header("1. Upload PDFs")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

if st.button("Process PDFs"):
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

        try:
            response = requests.post(
                f"{BACKEND_URL}/upload-pdfs/",
                files=files,
                timeout=300
            )

            if response.status_code == 200:
                data = response.json()

                st.success(
                    f"Processed {data['successful_uploads']} out of {data['total_files']} file(s)."
                )

                for result in data["uploaded"]:
                    if result.get("status") == "success":
                        with st.expander(f"{result['filename']} - success"):
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

st.header("2. Test Retrieval")

st.write(
    "Use this before asking questions. If retrieval does not return good chunks, the LLM answer will be garbage. That is not AI magic, that is bad input."
)

retrieval_query = st.text_input(
    "Search uploaded documents",
    placeholder="Example: installation steps",
    key="retrieval_query"
)

col1, col2 = st.columns(2)

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

if st.button("Test Retrieval"):
    if not retrieval_query.strip():
        st.warning("Please enter a search query.")
    else:
        try:
            response = requests.get(
                f"{BACKEND_URL}/search-test/",
                params={
                    "q": retrieval_query,
                    "top_k": top_k,
                    "min_similarity": min_similarity
                },
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()

                st.write(data["message"])

                results = data.get("results", [])

                if not results:
                    st.warning("No reliable chunks found.")
                else:
                    for index, result in enumerate(results, start=1):
                        metadata = result["metadata"]

                        with st.expander(
                            f"Result {index} | Score: {result['similarity_score']} | {metadata.get('doc_name')}"
                        ):
                            st.write(f"Document: {metadata.get('doc_name')}")
                            st.write(f"Page: {metadata.get('page_number')}")
                            st.write(f"Chunk: {metadata.get('page_chunk_index')}")
                            st.write(f"Similarity Score: {result['similarity_score']}")
                            st.write("Text:")
                            st.write(result["text"])

            else:
                st.error("Retrieval test failed.")
                st.write(response.text)

        except requests.exceptions.RequestException as error:
            st.error("Could not connect to backend.")
            st.write(error)


# -----------------------------
# Ask Question Section
# -----------------------------

st.header("3. Ask a Question")

question = st.text_input(
    "Ask a question from your uploaded documents",
    placeholder="Example: How do I install it?"
)

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            response = requests.post(
                f"{BACKEND_URL}/ask",
                json={"question": question},
                timeout=180
            )

            if response.status_code == 200:
                data = response.json()

                st.subheader("Answer")
                st.write(data.get("answer", "No answer returned."))

                st.subheader("Rewritten Query")
                st.write(data.get("rewritten_query", "No rewritten query returned."))

                citations = data.get("citations", [])

                if citations:
                    st.subheader("Citations")

                    for citation in citations:
                        st.markdown(
                            f"""
                            **Document:** {citation.get("doc_name")}  
                            **Page:** {citation.get("page_number")}  
                            **Relevance Score:** {citation.get("relevance_score")}  
                            **Snippet:** {citation.get("snippet")}
                            """
                        )
                else:
                    st.info("No citations returned.")

            elif response.status_code == 404:
                st.warning(
                    "The /ask endpoint is not implemented yet. Complete the RAG answer generation module first."
                )

            else:
                st.error("Something went wrong while asking the question.")
                st.write(response.text)

        except requests.exceptions.RequestException as error:
            st.error("Could not connect to backend.")
            st.write(error)