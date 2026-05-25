import re
from typing import List


def clean_pdf_text(text: str) -> str:
    """
    Cleans raw PDF text while keeping enough structure for chunking.
    This is intentionally simple and safe for technical documents.
    """

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove common standalone page number lines
    text = re.sub(r"(?m)^\s*page\s+\d+\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

    # Fix words broken by hyphen at line break
    # Example: "instal-\nlation" → "installation"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace single newlines inside paragraphs with spaces
    # But keep paragraph breaks
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Collapse 3+ newlines into max 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse repeated spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def remove_repeated_lines(pages_text: List[str], min_repetitions: int = 2) -> List[str]:
    """
    Removes lines repeated across multiple pages.
    Useful for headers/footers in PDFs.
    """

    line_counts = {}

    for page_text in pages_text:
        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        unique_lines = set(lines)

        for line in unique_lines:
            if len(line) <= 120:
                line_counts[line] = line_counts.get(line, 0) + 1

    repeated_lines = {
        line for line, count in line_counts.items()
        if count >= min_repetitions
    }

    cleaned_pages = []

    for page_text in pages_text:
        lines = page_text.split("\n")
        kept_lines = [
            line for line in lines
            if line.strip() not in repeated_lines
        ]
        cleaned_pages.append("\n".join(kept_lines).strip())

    return cleaned_pages