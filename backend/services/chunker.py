from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict


def chunk_pages(pages_data: List[Dict]) -> List[Dict]:
    """
    Takes extracted page data and splits text into smaller chunks.
    Preserves metadata: doc_name, page_number, chunk_index.
    
    Why RecursiveCharacterTextSplitter?
    - It tries to split on sentences/paragraphs first (not mid-word)
    - Keeps semantic meaning intact
    - chunk_overlap ensures context isn't lost at boundaries
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,        # ~500 characters per chunk
        chunk_overlap=50,      # 50 chars overlap so context isn't cut off
        separators=["\n\n", "\n", ". ", " ", ""]  # tries these in order
    )

    all_chunks = []

    for page in pages_data:
        text = page["text"]
        doc_name = page["doc_name"]
        page_number = page["page_number"]

        # Split the page text into chunks
        chunks = splitter.split_text(text)

        for idx, chunk_text in enumerate(chunks):
            all_chunks.append({
                "doc_name": doc_name,
                "page_number": page_number,
                "chunk_index": idx,          # position of chunk within this page
                "text": chunk_text
            })

    print(f"[Chunker] Total chunks created: {len(all_chunks)}")
    return all_chunks