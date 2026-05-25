import fitz  # PyMuPDF
import os
from typing import List, Dict


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    doc_name = os.path.basename(pdf_path)
    pages_data = []

    try:
        pdf_document = fitz.open(pdf_path)

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text("text")

            text = text.strip()
            text = " ".join(text.split())

            if text:
                pages_data.append({
                    "doc_name": doc_name,
                    "page_number": page_num + 1,
                    "text": text
                })

        pdf_document.close()
        print(f"[PDF Extractor] Extracted {len(pages_data)} pages from '{doc_name}'")

    except Exception as e:
        print(f"[PDF Extractor] ERROR reading '{pdf_path}': {e}")

    return pages_data


def extract_multiple_pdfs(pdf_paths: List[str]) -> List[Dict]:
    all_pages = []

    for path in pdf_paths:
        pages = extract_text_from_pdf(path)
        all_pages.extend(pages)

    print(f"[PDF Extractor] Total pages extracted: {len(all_pages)}")
    return all_pages