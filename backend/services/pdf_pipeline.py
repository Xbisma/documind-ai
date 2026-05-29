import os
import shutil
from typing import Dict
from uuid import uuid4

from fastapi import UploadFile

from backend.services.chunker import chunk_pages
from backend.services.embedder import embed_and_store
from backend.services.pdf_extractor import extract_text_from_pdf

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../uploaded_pdfs")
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

def validate_pdf_file(file: UploadFile) -> None:
    if not file.filename:
        raise ValueError("Uploaded file must have a filename.")
    if not file.filename.lower().endswith(".pdf"):
        raise ValueError(f"{file.filename} is not a PDF file.")

def save_uploaded_pdf(file: UploadFile) -> str:
    validate_pdf_file(file)

    safe_filename = os.path.basename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return save_path

def process_uploaded_pdf(file: UploadFile, session_id: str) -> Dict:
    """
    Full ingestion pipeline:
    upload → extract → clean → chunk → embed → store
    """
    if not session_id:
        raise ValueError("session_id is required")

    doc_id = str(uuid4())  # stable id for this PDF within this session

    save_path = save_uploaded_pdf(file)

    # Extract now includes session/doc fields in each page record
    pages = extract_text_from_pdf(
        pdf_path=save_path,
        session_id=session_id,
        doc_id=doc_id,
    )

    # Chunker will propagate these fields into each chunk
    chunks = chunk_pages(pages)

    # Embedder will store session_id/doc_id in Chroma metadata
    storage_summary = embed_and_store(chunks)

    return {
        "session_id": session_id,
        "doc_id": doc_id,
        "filename": file.filename,
        "saved_path": save_path,
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "chunks_stored": storage_summary["stored_chunks"],
        "duplicates_skipped": storage_summary["skipped_duplicates"],
        "status": "success"
    }