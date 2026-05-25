from typing import Dict, List

from backend.services.embedder import embed_texts, get_chroma_collection


def distance_to_similarity(distance: float) -> float:
    """
    Converts Chroma cosine distance into similarity score.
    Smaller distance means better match.
    Similarity = 1 - distance.
    """

    return 1 - distance


def format_retrieval_results(results: Dict, min_similarity: float) -> List[Dict]:
    """
    Converts raw ChromaDB results into clean retrieval results.
    Applies threshold filtering.
    """

    formatted_results = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    for chunk_id, document, metadata, distance in zip(
        ids,
        documents,
        metadatas,
        distances
    ):
        similarity_score = distance_to_similarity(distance)

        if similarity_score < min_similarity:
            continue

        formatted_results.append({
            "chunk_id": chunk_id,
            "text": document,
            "similarity_score": round(similarity_score, 4),
            "distance": round(distance, 4),
            "metadata": {
                "doc_name": metadata.get("doc_name"),
                "page_number": metadata.get("page_number"),
                "page_chunk_index": metadata.get("page_chunk_index"),
                "global_chunk_index": metadata.get("global_chunk_index"),
                "snippet": metadata.get("snippet"),
                "uploaded_at": metadata.get("uploaded_at"),
            }
        })

    return formatted_results


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.35,
    collection_name: str = "documents"
) -> Dict:
    """
    Retrieves relevant chunks from ChromaDB using semantic search.
    Applies similarity threshold to avoid weak/hallucination-prone context.
    """

    if not query or not query.strip():
        return {
            "query": query,
            "results": [],
            "message": "Query cannot be empty."
        }

    collection = get_chroma_collection(collection_name)

    query_embedding = embed_texts([query.strip()])

    raw_results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    filtered_results = format_retrieval_results(
        raw_results,
        min_similarity=min_similarity
    )

    if not filtered_results:
        return {
            "query": query,
            "results": [],
            "message": "No reliable answer found in uploaded documents."
        }

    return {
        "query": query,
        "results": filtered_results,
        "message": "Relevant chunks retrieved successfully."
    }