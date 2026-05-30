from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence


_VAGUE_PATTERNS = [
    r"\b(it|this|that|these|those)\b",
    r"^(how|what|why|where|when)\b.{0,25}\b(it|this|that)\b",
]

_VAGUE_REGEX = re.compile("|".join(_VAGUE_PATTERNS), re.IGNORECASE)


def is_vague_question(question: str) -> bool:
    if not question or not question.strip():
        return True

    q = question.strip()
    # very short questions are often vague
    if len(q.split()) <= 3:
        return True

    return bool(_VAGUE_REGEX.search(q))


def rewrite_query(user_query: str, chat_context: Optional[str] = None) -> str:
    """
    Backward-compatible wrapper around the conservative rewriter.
    """
    rewritten = rewrite_query_if_needed(user_query)
    if chat_context and rewritten == (user_query or "").strip():
        return f"{rewritten} Context: {chat_context}"
    return rewritten


def rewrite_query_if_needed(question: str, *, doc_hint: Optional[str] = None) -> str:
    """
    Rewrite only if vague. Otherwise return original question.
    This is intentionally conservative.
    """
    q = (question or "").strip()
    if not q:
        return ""

    if not is_vague_question(q):
        return q

    # Minimal safe rewriting rules (do NOT guess too much)
    lower = q.lower()

    if "install" in lower:
        return f"installation steps {doc_hint}".strip() if doc_hint else "installation steps"
    if "execute" in lower or "run" in lower:
        return f"how to execute or run {doc_hint}".strip() if doc_hint else "how to execute or run"
    if "setup" in lower or "configure" in lower:
        return f"setup and configuration {doc_hint}".strip() if doc_hint else "setup and configuration"

    # fallback: attach hint if we have it
    return f"{q} {doc_hint}".strip() if doc_hint else q


def build_clarification_options(chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build a deduped list of docs present in the session based on available chunks/metadatas.
    This is a fallback method.
    """
    seen = set()
    options: List[Dict[str, str]] = []

    for c in chunks:
        md = (c or {}).get("metadata", {}) or {}
        doc_id = md.get("doc_id")
        doc_name = md.get("doc_name")

        if not doc_id:
            continue

        if doc_id in seen:
            continue

        seen.add(doc_id)
        options.append({
            "doc_id": str(doc_id),
            "doc_name": str(doc_name or "Unknown document"),
        })

    return options