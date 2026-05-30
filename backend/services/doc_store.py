from __future__ import annotations

import os
from typing import Dict, Any, List, Optional, Tuple

from backend.services.embedder import get_chroma_collection


def _safe_abspath(path: str) -> str:
    return os.path.abspath(path)


def find_doc_source_path(
    session_id: str,
    doc_id: str,
    collection_name: str = "documents",
) -> Optional[Tuple[str, str]]:
    """
    Returns (doc_name, source_path) for a given session_id + doc_id by reading
    Chroma metadata.
    """

    collection = get_chroma_collection(collection_name)

    res = collection.get(
        include=["metadatas"],
        where={"session_id": session_id},
        limit=2000,  # safe for small prototype; can be optimized later
    )

    metadatas: List[Dict[str, Any]] = res.get("metadatas", []) or []

    for md in metadatas:
        if not md:
            continue

        if str(md.get("doc_id")) == str(doc_id):
            doc_name = md.get("doc_name") or "document.pdf"
            source_path = md.get("source_path") or ""

            if source_path:
                return (doc_name, _safe_abspath(source_path))

    return None


def list_docs_for_session(
    session_id: str,
    collection_name: str = "documents",
) -> List[Dict[str, Any]]:
    """
    Returns a deduped list of docs in a session from Chroma metadata.
    """

    collection = get_chroma_collection(collection_name)

    res = collection.get(
        include=["metadatas"],
        where={"session_id": session_id},
        limit=2000,
    )

    metadatas: List[Dict[str, Any]] = res.get("metadatas", []) or []

    seen = set()
    docs: List[Dict[str, Any]] = []

    for md in metadatas:
        if not md:
            continue

        doc_id = md.get("doc_id")
        if not doc_id:
            continue

        if doc_id in seen:
            continue

        seen.add(doc_id)

        docs.append(
            {
                "doc_id": doc_id,
                "doc_name": md.get("doc_name"),
                "source_path": md.get("source_path"),
            }
        )

    return docs