import os
from collections import Counter
from typing import Dict, Any, List, Optional, Sequence

from groq import Groq

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

from backend.services.query_rewriter import (
    is_vague_question,
    rewrite_query_if_needed,
)
from backend.services.retriever import DocumentRetriever
from backend.services.prompt_templates import SYSTEM_PROMPT, ANSWER_PROMPT_TEMPLATE

load_dotenv()


def _to_int_if_numeric(value):
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


class RAGAnswerService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.fallback_models = [
            self.model,
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
        ]
        self.retriever = DocumentRetriever()

    def _format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        context_parts = []

        for index, chunk in enumerate(retrieved_chunks, start=1):
            md = chunk.get("metadata", {}) or {}
            doc_name = md.get("doc_name", "Unknown document")
            page_number = md.get("page_number", "Unknown page")
            chunk_text = chunk.get("text", "")

            context_parts.append(
                f"""
Source {index}
Document: {doc_name}
Page: {page_number}
Text:
{chunk_text}
""".strip()
            )

        return "\n\n".join(context_parts)

    def _format_citations(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        citations = []

        for chunk in retrieved_chunks:
            md = chunk.get("metadata", {}) or {}
            citations.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "session_id": md.get("session_id"),
                    "doc_id": md.get("doc_id"),
                    "doc_name": md.get("doc_name", "Unknown document"),
                    "page_number": _to_int_if_numeric(md.get("page_number", "Unknown page")),
                    "page_chunk_index": _to_int_if_numeric(md.get("page_chunk_index")),
                    "char_start": _to_int_if_numeric(md.get("char_start")),
                    "char_end": _to_int_if_numeric(md.get("char_end")),
                    "snippet": (chunk.get("text", "") or "")[:300],
                    "similarity_score": round(float(chunk.get("similarity_score", 0.0)), 4),
                }
            )

        return citations

    def _pick_dominant_doc_ids(self, chunks: Sequence[Dict[str, Any]], max_docs: int = 1) -> List[str]:
        doc_ids = []
        for c in chunks:
            md = (c or {}).get("metadata", {}) or {}
            if md.get("doc_id"):
                doc_ids.append(str(md["doc_id"]))

        if not doc_ids:
            return []

        counts = Counter(doc_ids)
        return [doc_id for doc_id, _ in counts.most_common(max_docs)]

    def _list_docs_from_chunks(self, chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
        seen = set()
        out: List[Dict[str, str]] = []
        for c in chunks:
            md = (c or {}).get("metadata", {}) or {}
            doc_id = md.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            out.append({"doc_id": str(doc_id), "doc_name": str(md.get("doc_name") or "Unknown document")})
        return out

    def answer_question(self, question: str, session_id: str) -> Dict[str, Any]:
        if not question or not question.strip():
            return {
                "answer": "Please enter a valid question.",
                "rewritten_query": "",
                "citations": [],
                "status": "empty_question",
            }

        if not session_id or not str(session_id).strip():
            return {
                "answer": "session_id is required. Upload PDFs first, then ask questions in that session.",
                "rewritten_query": "",
                "citations": [],
                "status": "missing_session_id",
            }

        question = question.strip()

        # 1) Vague question → attempt clarification when multiple docs exist
        if is_vague_question(question):
            # Retrieve lightly to see what docs exist in this session.
            discovery_chunks = self.retriever.retrieve(
                query=question,
                session_id=session_id,
                min_similarity=0.25,
                top_k=12,
                adaptive=True,
            )
            docs = self._list_docs_from_chunks(discovery_chunks)

            if len(docs) >= 2:
                return {
                    "answer": "Your question is a bit unclear. Which document should I use?",
                    "rewritten_query": question,
                    "citations": [],
                    "status": "needs_clarification",
                    "clarification_options": docs,
                }

            # if only one doc exists, we can safely hint rewrite
            doc_hint = docs[0]["doc_name"] if docs else None
            rewritten_query = rewrite_query_if_needed(question, doc_hint=doc_hint)
        else:
            rewritten_query = question

        # 2) First pass retrieval (session-scoped)
        initial_chunks = self.retriever.retrieve(
            query=rewritten_query,
            session_id=session_id,
            adaptive=True,
        )

        if not initial_chunks:
            return {
                "answer": "I couldn't find a reliable answer in the uploaded documents.",
                "rewritten_query": rewritten_query,
                "citations": [],
                "status": "no_relevant_context",
            }

        # 3) Doc routing: pick dominant doc_id(s) then re-retrieve filtered
        dominant_doc_ids = self._pick_dominant_doc_ids(initial_chunks, max_docs=1)
        routed_chunks = initial_chunks

        if dominant_doc_ids:
            routed_chunks = self.retriever.retrieve(
                query=rewritten_query,
                session_id=session_id,
                doc_ids=dominant_doc_ids,
                adaptive=True,
            ) or initial_chunks

        context = self._format_context(routed_chunks)

        user_prompt = ANSWER_PROMPT_TEMPLATE.format(
            question=question,
            rewritten_query=rewritten_query,
            context=context,
        )

        if not self.client:
            return {
                "answer": "I couldn't generate an answer because the Groq API key is not configured.",
                "rewritten_query": rewritten_query,
                "citations": self._format_citations(routed_chunks),
                "status": "llm_unavailable",
            }

        response = None
        last_error: Optional[Exception] = None

        for model_name in self.fallback_models:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )
                self.model = model_name
                break
            except Exception as error:
                last_error = error

        if response is None:
            return {
                "answer": "I couldn't generate an answer from the uploaded documents right now.",
                "rewritten_query": rewritten_query,
                "citations": self._format_citations(routed_chunks),
                "status": "llm_error",
                "error": str(last_error) if last_error else "Unknown Groq error",
            }

        return {
            "answer": response.choices[0].message.content,
            "rewritten_query": rewritten_query,
            "citations": self._format_citations(routed_chunks),
            "status": "answered",
            "used_doc_ids": dominant_doc_ids,
        }