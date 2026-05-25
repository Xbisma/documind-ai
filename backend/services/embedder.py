from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from typing import List, Dict
import os


# Load the embedding model once (free, runs locally)
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# ChromaDB will store data in this local folder
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "../../chroma_db")


def get_chroma_collection(collection_name: str = "documents"):
    """
    Returns (or creates) a ChromaDB collection.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # cosine similarity for text
    )
    return collection


def embed_and_store(chunks: List[Dict], collection_name: str = "documents") -> None:
    """
    Generates embeddings for each chunk and stores them in ChromaDB
    along with citation metadata.
    """
    collection = get_chroma_collection(collection_name)

    texts = [chunk["text"] for chunk in chunks]
    print(f"[Embedder] Generating embeddings for {len(texts)} chunks...")

    # Generate embeddings (list of vectors)
    embeddings = EMBEDDING_MODEL.encode(texts, show_progress_bar=True).tolist()

    # Build metadata and unique IDs for each chunk
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        metadatas.append({
            "doc_name": chunk["doc_name"],
            "page_number": str(chunk["page_number"]),  # ChromaDB needs strings
            "chunk_index": str(chunk["chunk_index"])
        })
        # Unique ID: docname_page_chunkindex
        unique_id = f"{chunk['doc_name']}_p{chunk['page_number']}_c{chunk['chunk_index']}"
        ids.append(unique_id)

    # Store everything in ChromaDB
    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"[Embedder] Successfully stored {len(chunks)} chunks in ChromaDB.")


def query_collection(query_text: str, n_results: int = 5, collection_name: str = "documents"):
    """
    Query ChromaDB with a search string.
    Returns top-n most similar chunks with their metadata.
    """
    collection = get_chroma_collection(collection_name)

    query_embedding = EMBEDDING_MODEL.encode([query_text]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    return results