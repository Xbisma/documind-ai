from typing import Dict, List, Optional, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

def _find_span(haystack: str, needle: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Best-effort span finder for highlighting.
    Returns (start, end) char offsets of needle within haystack, else (None, None).
    """
    if not haystack or not needle:
        return (None, None)
    start = haystack.find(needle)
    if start == -1:
        return (None, None)
    return (start, start + len(needle))

def chunk_pages(pages_data: List[Dict]) -> List[Dict]:
    """
    Splits extracted PDF pages into searchable chunks.
    Preserves citation metadata for retrieval and final answer citations.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            ""
        ],
    )

    all_chunks = []
    global_chunk_index = 0

    for page in pages_data:
        text = page["text"]
        doc_name = page["doc_name"]
        source_path = page.get("source_path", "")
        page_number = page["page_number"]

        session_id = page.get("session_id")
        doc_id = page.get("doc_id")
        if not session_id or not doc_id:
            # Fail early: ingestion must always tag chunks with session/doc
            raise ValueError("Missing session_id/doc_id on extracted page data")

        chunks = splitter.split_text(text)

        for page_chunk_index, chunk_text in enumerate(chunks):
            cleaned_chunk = chunk_text.strip()
            if not cleaned_chunk:
                continue

            char_start, char_end = _find_span(text, cleaned_chunk)

            all_chunks.append({
                "session_id": session_id,
                "doc_id": doc_id,

                "doc_name": doc_name,
                "source_path": source_path,
                "page_number": page_number,
                "page_chunk_index": page_chunk_index,
                "global_chunk_index": global_chunk_index,

                "text": cleaned_chunk,
                "snippet": cleaned_chunk[:300],
                "char_count": len(cleaned_chunk),

                # NEW: highlight anchors (optional but useful)
                "char_start": char_start,
                "char_end": char_end,
            })

            global_chunk_index += 1

    print(f"[Chunker] Total chunks created: {len(all_chunks)}")
    return all_chunks