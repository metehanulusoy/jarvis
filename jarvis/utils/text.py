"""Text utilities: chunking, extraction, sanitization."""

from __future__ import annotations

import re
from pathlib import Path

# Patterns that look like prompt injection attempts
_INJECTION_PATTERNS = re.compile(
    r"(SYSTEM\s*OVERRIDE|IGNORE\s*(ALL\s*)?PREVIOUS\s*INSTRUCTIONS|"
    r"NEW\s*INSTRUCTIONS?:|YOU\s*ARE\s*NOW|FORGET\s*EVERYTHING|"
    r"DISREGARD\s*(ALL\s*)?PRIOR)",
    re.IGNORECASE,
)


def sanitize_untrusted(text: str, source_label: str = "external") -> str:
    """Wrap untrusted text with boundary markers and strip obvious injection attempts."""
    # Flag but don't remove — let the LLM see the data, but within clear boundaries
    flagged = _INJECTION_PATTERNS.sub(r"[FLAGGED: \g<0>]", text)
    return (
        f"\n--- BEGIN UNTRUSTED DATA from {source_label} ---\n"
        f"{flagged}\n"
        f"--- END UNTRUSTED DATA ---\n"
    )


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def extract_text(path: Path) -> str:
    """Extract plain text from a file (PDF, txt, md)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".txt", ".md", ".rst", ".org"):
        return path.read_text(errors="replace")
    else:
        # Try reading as text
        try:
            return path.read_text(errors="replace")
        except Exception:
            return ""


def _extract_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        return f"[PDF extraction failed: {e}]"
