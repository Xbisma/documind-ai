from __future__ import annotations

import base64
import os
from typing import Optional
import streamlit as st


def _pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")


def render_pdf_viewer(
    *,
    pdf_bytes: Optional[bytes],
    doc_name: str,
    page_number: Optional[int] = None,
    height: int = 650,
) -> None:
    """
    Phase-1 PDF viewer:
    - embeds the PDF in an iframe using base64
    - shows which page to look at (page jump is browser-dependent)
    """

    st.subheader("PDF Viewer")

    if not pdf_bytes:
        st.info("No PDF selected. Click a citation (later) or upload PDFs.")
        return

    if page_number:
        st.caption(f"Suggested page: {page_number}")

    b64 = _pdf_to_base64(pdf_bytes)

    # Many browsers support #page= in PDF viewer, but not guaranteed.
    page_fragment = f"#page={page_number}" if page_number else ""

    pdf_display = f"""
    <iframe
        src="data:application/pdf;base64,{b64}{page_fragment}"
        width="100%"
        height="{height}"
        type="application/pdf"
    ></iframe>
    """

    st.markdown(f"**Document:** {doc_name}")
    st.components.v1.html(pdf_display, height=height)


def load_pdf_bytes_from_path(path: str) -> Optional[bytes]:
    """
    Utility loader if you have local PDF paths available.
    NOTE: In your current backend, PDFs are stored server-side. The frontend
    may not have local access. This is mainly for development/demo.
    A better production approach is adding a backend endpoint:
    GET /sessions/{session_id}/docs/{doc_id}/download
    """

    if not path:
        return None

    if not os.path.exists(path):
        return None

    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None