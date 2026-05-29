from typing import List, Optional
from uuid import uuid4
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from backend.services.pdf_pipeline import process_uploaded_pdf
from backend.services.retriever import retrieve_relevant_chunks
from backend.services.embedder import backfill_chunk_metadata, get_chroma_collection

from pydantic import BaseModel
from backend.services.rag_chain import RAGAnswerService

app = FastAPI(title="DocuMind AI", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    upload_schema = openapi_schema["components"]["schemas"]["Body_upload_pdfs_upload_pdfs__post"]
    upload_schema["properties"]["files"]["items"] = {
        "type": "string",
        "format": "binary",
    }

    openapi_schema["openapi"] = "3.0.3"
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


class QuestionRequest(BaseModel):
    question: str
    session_id: str # REQUIRED


rag_service = RAGAnswerService()

@app.get("/")
def home():
    return {"message": "DocuMind AI backend is running!"}


@app.post("/upload-pdfs/")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Uploads multiple PDFs and processes them into searchable vector chunks.
    """

    results = []
    for file in files:
        try:
            result = process_uploaded_pdf(file)
            results.append(result)

        except ValueError as error:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(error)
            })

        except Exception as error:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": f"Failed to process file: {error}"
            })

    successful_uploads = [
        result for result in results if result.get("status") == "success"
    ]

    failed_uploads = [
        result for result in results if result.get("status") == "failed"
    ]

    return {
        "total_files": len(files),
        "successful_uploads": len(successful_uploads),
        "failed_uploads": len(failed_uploads),
        "uploaded": results
    }


@app.get("/search-test/")
def search_test(
    q: str = Query(..., description="Search query"),
    session_id: Optional[str] = Query(None, description="Filter retrieval to this session_id"),
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.35, ge=0.0, le=1.0),
):
    return retrieve_relevant_chunks(
        query=q,
        session_id=session_id,
        top_k=top_k,
        min_similarity=min_similarity,
    )


@app.get("/test-chunks/")
def test_chunks():
    """
    Shows a few stored chunks from ChromaDB.
    Useful for checking whether ingestion worked.
    """

    backfill_summary = backfill_chunk_metadata()
    collection = get_chroma_collection()
    results = collection.get(limit=5, include=["documents", "metadatas"])

    return {
        "backfill": backfill_summary,
        "results": results,
    }

@app.post("/ask")
def ask_question(request: QuestionRequest):
    result = rag_service.answer_question(
        question=request.question,
        session_id=request.session_id,
    )
    return result