from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil

from services.pdf_extractor import extract_text_from_pdf
from services.chunker import chunk_pages
from services.embedder import embed_and_store

app = FastAPI(title="DocuMind AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"message": "DocuMind AI backend is running!"}


@app.post("/upload-pdfs/")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400, 
                detail=f"{file.filename} is not a PDF."
            )

        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        pages = extract_text_from_pdf(save_path)
        chunks = chunk_pages(pages)
        embed_and_store(chunks)

        results.append({
            "filename": file.filename,
            "pages_extracted": len(pages),
            "chunks_stored": len(chunks),
            "status": "success"
        })

    return {"uploaded": results}


@app.get("/test-chunks/")
def test_chunks():
    from services.embedder import get_chroma_collection
    collection = get_chroma_collection()
    results = collection.get(limit=5, include=["documents", "metadatas"])
    return results