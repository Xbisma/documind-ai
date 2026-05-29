import re
from typing import List

_CODE_LIKE = re.compile(
    r"""
    ^\s*(
        \$\s|                # shell prompt
        >>>\s|               # python prompt
        \.\.\.\s|            # python continuation
        (pip|python|conda|git|npm|yarn|curl|wget)\b|
        (sudo)\b|
        ([A-Za-z]:\\)|
        (/usr/|/etc/|~/)|
        (\{|\}|\[|\])|
        (`{1,3})|
        (-{1,2}[A-Za-z])     # flags
    )
    """,
    re.VERBOSE,
)

def _looks_like_code(line: str) -> bool:
    line = line.rstrip("\n")
    if not line.strip():
        return False
    if _CODE_LIKE.search(line):
        return True
    # lots of symbols often indicates code/config
    symbol_ratio = sum(1 for c in line if c in "{}[]();=<>|`") / max(len(line), 1)
    return symbol_ratio > 0.08

def clean_pdf_text(text: str) -> str:
    """
    Cleans raw PDF text while keeping enough structure for chunking.
    Safer for technical documents: preserves code blocks/commands.
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove common standalone page number lines
    text = re.sub(r"(?m)^\s*page\s+\d+\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

    # Fix words broken by hyphen at line break
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Work line-by-line to preserve commands/code
    lines = [ln.rstrip() for ln in text.split("\n")]
    cleaned_lines: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            cleaned_lines.append("")  # keep paragraph breaks
            i += 1
            continue

        # If current line looks like code, keep newline structure
        if _looks_like_code(line):
            cleaned_lines.append(line)
            i += 1
            continue

        # For prose lines, join with next line if next is also prose
        buf = line
        while i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if not nxt:
                break
            if _looks_like_code(nxt):
                break
            # join prose lines
            buf = f"{buf} {nxt}"
            i += 1

        cleaned_lines.append(buf)
        i += 1

    text = "\n".join(cleaned_lines)

    # Collapse 3+ newlines into max 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse repeated spaces/tabs (but don't destroy newlines)
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

    repeated_lines = {line for line, count in line_counts.items() if count >= min_repetitions}

    cleaned_pages = []
    for page_text in pages_text:
        lines = page_text.split("\n")
        kept_lines = [line for line in lines if line.strip() not in repeated_lines]
        cleaned_pages.append("\n".join(kept_lines).strip())

    return cleaned_pages