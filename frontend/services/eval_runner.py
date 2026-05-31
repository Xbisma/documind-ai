import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import requests

BACKEND_URL = "http://127.0.0.1:8000"


@dataclass
class EvalResult:
    question: str
    expected_doc: str
    top_docs: List[str]
    doc_at_1: bool
    doc_at_3: bool
    doc_at_5: bool
    keyword_hit_top1: bool
    keyword_hit_any5: bool


def _contains_keywords(
    text: str,
    keywords: List[str],
    min_hits: int = 2
) -> bool:
    t = (text or "").lower()
    hits = sum(1 for k in keywords if k.lower() in t)
    return hits >= min_hits


def run_retrieval_eval(
    test_questions_path: str,
    session_id: str,
    top_k: int = 5,
    min_similarity: float = 0.35
) -> Tuple[List[EvalResult], Dict[str, float]]:
    with open(test_questions_path, "r", encoding="utf-8") as f:
        tests = json.load(f)

    results: List[EvalResult] = []

    for t in tests:
        q = t["question"]
        expected_doc = t["expected_doc_name"]
        keywords = t.get("expected_answer_keywords", [])

        r = requests.get(
            f"{BACKEND_URL}/search-test/",
            params={
                "q": q,
                "session_id": session_id,
                "top_k": top_k,
                "min_similarity": min_similarity,
            },
            timeout=60,
        )

        data = r.json() if r.status_code == 200 else {"results": []}
        chunks = data.get("results", [])

        top_docs = []
        for c in chunks:
            md = c.get("metadata", {}) or {}
            top_docs.append(md.get("doc_name") or "Unknown")

        top1_doc = top_docs[0] if top_docs else ""
        top5_docs = top_docs[:5]

        doc_at_1 = top1_doc == expected_doc
        doc_at_3 = expected_doc in top_docs[:3]
        doc_at_5 = expected_doc in top_docs[:5]

        top1_text = chunks[0].get("text", "") if chunks else ""

        keyword_hit_top1 = _contains_keywords(
            top1_text,
            keywords,
            min_hits=2
        )

        keyword_hit_any5 = any(
            _contains_keywords(
                c.get("text", ""),
                keywords,
                min_hits=2
            )
            for c in chunks[:5]
        )

        results.append(
            EvalResult(
                question=q,
                expected_doc=expected_doc,
                top_docs=top5_docs,
                doc_at_1=doc_at_1,
                doc_at_3=doc_at_3,
                doc_at_5=doc_at_5,
                keyword_hit_top1=keyword_hit_top1,
                keyword_hit_any5=keyword_hit_any5,
            )
        )

    n = max(len(results), 1)

    summary = {
        "Doc@1": sum(r.doc_at_1 for r in results) / n,
        "Doc@3": sum(r.doc_at_3 for r in results) / n,
        "Doc@5": sum(r.doc_at_5 for r in results) / n,
        "KeywordHit@1": sum(r.keyword_hit_top1 for r in results) / n,
        "KeywordHit@5": sum(r.keyword_hit_any5 for r in results) / n,
        "NoContextRate": sum(
            1 for r in results if len(r.top_docs) == 0
        ) / n,
    }

    return results, summary


def write_report_md(
    out_path: str,
    results: List[EvalResult],
    summary: Dict[str, float]
) -> None:
    lines = []

    lines.append("# Retrieval Evaluation Report\n")
    lines.append("## Summary\n")

    for k, v in summary.items():
        lines.append(f"- **{k}**: {v:.2f}\n")

    lines.append("\n## Per-question results\n")

    lines.append(
        "| Question | Expected Doc | Top Docs | Doc@1 | Doc@3 | Doc@5 | Keyword@1 | Keyword@5 |\n"
    )
    lines.append(
        "|---|---|---|---:|---:|---:|---:|---:|\n"
    )

    for r in results:
        lines.append(
            f"| {r.question} | {r.expected_doc} | {', '.join(r.top_docs)} | "
            f"{'✅' if r.doc_at_1 else '❌'} | "
            f"{'✅' if r.doc_at_3 else '❌'} | "
            f"{'✅' if r.doc_at_5 else '❌'} | "
            f"{'✅' if r.keyword_hit_top1 else '❌'} | "
            f"{'✅' if r.keyword_hit_any5 else '❌'} |\n"
        )

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)