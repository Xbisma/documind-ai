import os
from typing import Dict, Any, List

from groq import Groq

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in constrained runtimes
    def load_dotenv(*args, **kwargs):
        return False

from backend.services.query_rewriter import rewrite_query
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
            metadata = chunk.get("metadata", {})

            doc_name = metadata.get("doc_name", "Unknown document")
            page_number = metadata.get("page_number", "Unknown page")
            chunk_text = chunk.get("text", "")

            context_parts.append(
                f"""
Source {index}
Document: {doc_name}
Page: {page_number}
Text:
{chunk_text}
"""
            )

        return "\n".join(context_parts)

    def _format_citations(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        citations = []

        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})

            citations.append(
                {
                    "doc_name": metadata.get("doc_name", "Unknown document"),
                    "page_number": _to_int_if_numeric(metadata.get("page_number", "Unknown page")),
                    "snippet": chunk.get("text", "")[:300],
                    "relevance_score": round(chunk.get("relevance_score", 0), 3),
                }
            )

        return citations

    def answer_question(self, question: str) -> Dict[str, Any]:
        if not question or not question.strip():
            return {
                "answer": "Please enter a valid question.",
                "rewritten_query": "",
                "citations": [],
                "status": "empty_question",
            }

        rewritten_query = rewrite_query(question)

        retrieved_chunks = self.retriever.retrieve(rewritten_query)

        if not retrieved_chunks:
            return {
                "answer": "I couldn't find a reliable answer in the uploaded documents.",
                "rewritten_query": rewritten_query,
                "citations": [],
                "status": "no_relevant_context",
            }

        context = self._format_context(retrieved_chunks)

        user_prompt = ANSWER_PROMPT_TEMPLATE.format(
            question=question,
            rewritten_query=rewritten_query,
            context=context,
        )

        if not self.client:
            return {
                "answer": "I couldn't generate an answer because the Groq API key is not configured.",
                "rewritten_query": rewritten_query,
                "citations": self._format_citations(retrieved_chunks),
                "status": "llm_unavailable",
            }

        response = None
        last_error = None

        for model_name in self.fallback_models:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
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
                "citations": self._format_citations(retrieved_chunks),
                "status": "llm_error",
                "error": str(last_error) if last_error else "Unknown Groq error",
            }

        return {
            "answer": response.choices[0].message.content,
            "rewritten_query": rewritten_query,
            "citations": self._format_citations(retrieved_chunks),
            "status": "answered",
        }