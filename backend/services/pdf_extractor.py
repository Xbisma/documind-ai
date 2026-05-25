import os
from typing import Dict, List

import fitz  # PyMuPDF

from backend.services.text_cleaner import clean_pdf_text, remove_repeated_lines


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extracts text from a PDF page by page.
    Preserves document name, source path, and page number for citations.
    """

    doc_name = os.path.basename(pdf_path)
    pages_data = []

    try:
        pdf_document = fitz.open(pdf_path)

        raw_pages = []

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            raw_text = page.get_text("text")
            raw_pages.append(raw_text)

        pdf_document.close()

        # Remove repeated headers/footers before final cleaning
        raw_pages = remove_repeated_lines(raw_pages)

        for page_num, raw_text in enumerate(raw_pages, start=1):
            cleaned_text = clean_pdf_text(raw_text)

            if cleaned_text:
                pages_data.append({
                    "doc_name": doc_name,
                    "source_path": pdf_path,
                    "page_number": page_num,
                    "text": cleaned_text
                })

        print(f"[PDF Extractor] Extracted {len(pages_data)} pages from '{doc_name}'")

    except Exception as error:
        print(f"[PDF Extractor] ERROR reading '{pdf_path}': {error}")

    return pages_data


def extract_multiple_pdfs(pdf_paths: List[str]) -> List[Dict]:
    """
    Extracts text from multiple PDFs.
    """

    all_pages = []

    for path in pdf_paths:
        pages = extract_text_from_pdf(path)
        all_pages.extend(pages)

    print(f"[PDF Extractor] Total pages extracted: {len(all_pages)}")
    return all_pages