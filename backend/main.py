import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.services.doc_store import (
    find_doc_source_path,
    list_docs_for_session,
)

app = FastAPI()


# After /ask endpoint, add:

@app.get("/sessions/{session_id}/docs")
def get_session_docs(session_id: str):
    """
    Lists uploaded documents in a session (from Chroma metadata).
    """

    docs = list_docs_for_session(session_id=session_id)

    return {
        "session_id": session_id,
        "docs": docs,
    }


@app.get("/sessions/{session_id}/docs/{doc_id}/download")
def download_doc(session_id: str, doc_id: str):
    """
    Downloads the original uploaded PDF for a given session_id + doc_id.
    """

    info = find_doc_source_path(
        session_id=session_id,
        doc_id=doc_id,
    )

    if not info:
        raise HTTPException(
            status_code=404,
            detail="Document not found for this session_id/doc_id.",
        )

    doc_name, source_path = info

    if not source_path or not os.path.exists(source_path):
        raise HTTPException(
            status_code=404,
            detail="PDF file missing on server.",
        )

    # Return as application/pdf with the original filename
    return FileResponse(
        source_path,
        media_type="application/pdf",
        filename=doc_name,
    )