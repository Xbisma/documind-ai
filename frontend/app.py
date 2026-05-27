import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.title("DocuMind AI")
st.write("Upload technical PDFs and ask questions from them.")

question = st.text_input("Ask a question from your uploaded documents")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": question},
        )

        if response.status_code == 200:
            data = response.json()

            st.subheader("Answer")
            st.write(data["answer"])

            st.subheader("Rewritten Query")
            st.write(data["rewritten_query"])

            if data.get("citations"):
                st.subheader("Citations")

                for citation in data["citations"]:
                    st.markdown(
                        f"""
                        **Document:** {citation["doc_name"]}  
                        **Page:** {citation["page_number"]}  
                        **Relevance Score:** {citation["relevance_score"]}  
                        **Snippet:** {citation["snippet"]}
                        """
                    )
        else:
            st.error("Something went wrong while asking the question.")