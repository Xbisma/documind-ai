import hashlib
import os
from functools import lru_cache
from datetime import datetime, timezone
from typing import Dict, List

import chromadb
from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

CHROMA_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../chroma_db")
)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Lazily loads the embedding model.

    This avoids downloading or initializing the model during application
    startup, which keeps Uvicorn startup quieter and faster.
    """

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_chroma_collection(collection_name: str = "documents"):
    """
    Returns or creates a ChromaDB collection.
    This collection stores PDF chunks, embeddings, and citation metadata.
    """

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    return collection


def backfill_chunk_metadata(collection_name: str = "documents") -> Dict[str, int]:
    """
    Normalizes older stored chunks so they expose the metadata newer code writes.

    Older Chroma rows in this project may be missing snippet/uploaded_at because
    they were created before those fields were added. This backfill updates the
    stored metadata in place when possible.
    """

    collection = get_chroma_collection(collection_name)
    stored = collection.get(include=["documents", "metadatas"])

    ids = stored.get("ids", [])
    documents = stored.get("documents", [])
    metadatas = stored.get("metadatas", [])

    updated_count = 0

    for chunk_id, document, metadata in zip(ids, documents, metadatas):
        metadata = metadata or {}
        snippet = metadata.get("snippet") or (document[:300] if document else "")
        uploaded_at = metadata.get("uploaded_at") or "unknown"

        if metadata.get("snippet") == snippet and metadata.get("uploaded_at") == uploaded_at:
            continue

        metadata["snippet"] = snippet
        metadata["uploaded_at"] = uploaded_at

        collection.update(ids=[chunk_id], metadatas=[metadata])
        updated_count += 1

    return {
        "total_chunks": len(ids),
        "updated_chunks": updated_count
    }


def build_chunk_id(chunk: Dict) -> str:
    """
    Builds a stable unique ID for every chunk.
    This helps prevent duplicate chunks when the same PDF is uploaded again.
    """

    raw_id = (
        f"{chunk['doc_name']}|"
        f"{chunk['page_number']}|"
        f"{chunk['page_chunk_index']}|"
        f"{chunk['text'][:100]}"
    )

    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()


def filter_new_chunks(collection, chunks: List[Dict]) -> List[Dict]:
    """
    Removes chunks that already exist in ChromaDB.
    """

    if not chunks:
        return []

    chunk_ids = [build_chunk_id(chunk) for chunk in chunks]

    existing = collection.get(ids=chunk_ids)
    existing_ids = set(existing.get("ids", []))

    new_chunks = []

    for chunk, chunk_id in zip(chunks, chunk_ids):
        if chunk_id not in existing_ids:
            chunk["chunk_id"] = chunk_id
            new_chunks.append(chunk)

    skipped = len(chunks) - len(new_chunks)

    if skipped:
        print(f"[Embedder] Skipped {skipped} duplicate chunks.")

    return new_chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Converts text chunks into embedding vectors.
    """

    if not texts:
        return []

    return get_embedding_model().encode(
        texts,
        show_progress_bar=True
    ).tolist()


def embed_and_store(chunks: List[Dict], collection_name: str = "documents") -> Dict:
    """
    Generates embeddings and stores chunks in ChromaDB.
    Returns storage summary for API response.
    """

    collection = get_chroma_collection(collection_name)

    new_chunks = filter_new_chunks(collection, chunks)

    if not new_chunks:
        return {
            "received_chunks": len(chunks),
            "stored_chunks": 0,
            "skipped_duplicates": len(chunks)
        }

    texts = [chunk["text"] for chunk in new_chunks]

    print(f"[Embedder] Generating embeddings for {len(texts)} chunks...")

    embeddings = embed_texts(texts)

    metadatas = []
    ids = []

    uploaded_at = datetime.now(timezone.utc).isoformat()

    for chunk in new_chunks:
        ids.append(chunk["chunk_id"])

        metadatas.append({
            "chunk_id": chunk["chunk_id"],
            "doc_name": chunk["doc_name"],
            "source_path": chunk.get("source_path", ""),
            "page_number": str(chunk["page_number"]),
            "page_chunk_index": str(chunk["page_chunk_index"]),
            "global_chunk_index": str(chunk["global_chunk_index"]),
            "snippet": chunk["snippet"],
            "char_count": str(chunk["char_count"]),
            "uploaded_at": uploaded_at,
            "embedding_model": EMBEDDING_MODEL_NAME
        })

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"[Embedder] Stored {len(new_chunks)} new chunks in ChromaDB.")

    return {
        "received_chunks": len(chunks),
        "stored_chunks": len(new_chunks),
        "skipped_duplicates": len(chunks) - len(new_chunks)
    }