from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.services.embedder import embed_texts, get_chroma_collection


def _to_int_if_numeric(value: Any) -> Any:
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def _distance_to_similarity(distance: float) -> float:
    return 1 - distance


@dataclass
class RetrievalConfig:
    top_k: int = 10
    # Start with a realistic threshold for PDFs
    min_similarity: float = 0.35
    # fallbacks go even lower (still safe because LLM is constrained by context rules)
    fallback_thresholds: Tuple[float, ...] = (0.30, 0.25, 0.20)


class DocumentRetriever:
    """
    Single retriever used by /ask and /search-test.

    Supports:
      - session_id filtering (required for real chats)
      - doc_id filtering (for doc routing)
      - adaptive thresholds
    """

    def __init__(self, collection_name: str = "documents", config: Optional[RetrievalConfig] = None):
        self.collection_name = collection_name
        self.config = config or RetrievalConfig()
        self.collection = get_chroma_collection(collection_name)

    def retrieve(
        self,
        query: str,
        *,
        session_id: Optional[str],
        doc_ids: Optional[Sequence[str]] = None,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        adaptive: bool = True,
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        query_embedding = embed_texts([query.strip()])

        n_results = top_k or self.config.top_k
        threshold = min_similarity if min_similarity is not None else self.config.min_similarity

        where: Dict[str, Any] = {}
        if session_id:
            where["session_id"] = session_id

        # Chroma supports simple metadata filters. For multiple doc_ids we do $in.
        # If your Chroma version doesn't support $in, we can do routing by repeated queries per doc_id.
        if doc_ids:
            where["doc_id"] = {"$in": list(doc_ids)}

        thresholds = [threshold]
        if adaptive:
            thresholds += [t for t in self.config.fallback_thresholds if t < threshold]

        for t in thresholds:
            raw = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
                where=where or None,
            )
            results = self._format(raw, min_similarity=t)
            if results:
                return results

        return []

    def _format(self, raw: Dict[str, Any], min_similarity: float) -> List[Dict[str, Any]]:
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        formatted: List[Dict[str, Any]] = []

        for doc, metadata, distance in zip(documents, metadatas, distances):
            similarity = _distance_to_similarity(distance)
            if similarity < min_similarity:
                continue

            metadata = metadata or {}
            formatted.append({
                "chunk_id": metadata.get("chunk_id"),
                "text": doc,
                "distance": round(distance, 4),
                "similarity_score": round(similarity, 4),
                "metadata": {
                    "session_id": metadata.get("session_id"),
                    "doc_id": metadata.get("doc_id"),
                    "doc_name": metadata.get("doc_name"),
                    "page_number": _to_int_if_numeric(metadata.get("page_number")),
                    "page_chunk_index": _to_int_if_numeric(metadata.get("page_chunk_index")),
                    "global_chunk_index": _to_int_if_numeric(metadata.get("global_chunk_index")),
                    "snippet": metadata.get("snippet"),
                    "char_start": _to_int_if_numeric(metadata.get("char_start")),
                    "char_end": _to_int_if_numeric(metadata.get("char_end")),
                    "uploaded_at": metadata.get("uploaded_at"),
                }
            })

        return formatted


# Backward-compatible helper for /search-test endpoint
def retrieve_relevant_chunks(
    query: str,
    session_id: Optional[str] = None,
    top_k: int = 5,
    min_similarity: float = 0.35,
    collection_name: str = "documents",
) -> Dict[str, Any]:
    retriever = DocumentRetriever(collection_name=collection_name)
    results = retriever.retrieve(
        query,
        session_id=session_id,
        top_k=top_k,
        min_similarity=min_similarity,
        adaptive=False,   # search-test should show strict behavior for debugging
    )

    if not results:
        return {"query": query, "results": [], "message": "No reliable answer found in uploaded documents."}

    return {"query": query, "results": results, "message": "Relevant chunks retrieved successfully."}