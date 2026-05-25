from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.services.pdf_pipeline import process_uploaded_pdf
from backend.services.retriever import retrieve_relevant_chunks
from backend.services.embedder import backfill_chunk_metadata, get_chroma_collection


app = FastAPI(title="DocuMind AI", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "DocuMind AI backend is running!"}


@app.post("/upload-pdfs/")
async def upload_pdfs(file: UploadFile = File(...)):
    """
    Uploads one PDF and processes it into searchable vector chunks.
    """

    try:
        result = process_uploaded_pdf(file)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process {file.filename}: {error}"
        )

    return {"uploaded": [result]}


@app.get("/search-test/")
def search_test(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.35, ge=0.0, le=1.0)
):
    """
    Tests retrieval before connecting to LLM.
    This is for Bisma's retrieval + LLM work.
    """

    return retrieve_relevant_chunks(
        query=q,
        top_k=top_k,
        min_similarity=min_similarity
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