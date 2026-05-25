from typing import Dict, List

from langchain_text_splitters import RecursiveCharacterTextSplitter


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

        chunks = splitter.split_text(text)

        for page_chunk_index, chunk_text in enumerate(chunks):
            cleaned_chunk = chunk_text.strip()

            if not cleaned_chunk:
                continue

            all_chunks.append({
                "doc_name": doc_name,
                "source_path": source_path,
                "page_number": page_number,
                "page_chunk_index": page_chunk_index,
                "global_chunk_index": global_chunk_index,
                "text": cleaned_chunk,
                "snippet": cleaned_chunk[:300],
                "char_count": len(cleaned_chunk)
            })

            global_chunk_index += 1

    print(f"[Chunker] Total chunks created: {len(all_chunks)}")
    return all_chunks