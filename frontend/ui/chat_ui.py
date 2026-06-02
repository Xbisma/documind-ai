import streamlit as st
from typing import List, Dict, Any


def render_citations(citations: List[Dict[str, Any]]) -> None:
    if not citations:
        st.info("No citations returned.")
        return

    st.subheader("Citations")

    for i, c in enumerate(citations, start=1):
        doc = c.get("doc_name")
        page = c.get("page_number")
        snippet = c.get("snippet")

        with st.expander(f"Citation {i}: {doc} (Page {page})"):
            st.markdown(
                f""" **Document:** {doc}  **Page:** {page}  **Snippet:** {snippet} """)