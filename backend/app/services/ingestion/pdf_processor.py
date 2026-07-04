import fitz  # PyMuPDF
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5000      # free-tier friendly: fewer embedding calls per paper
CHUNK_OVERLAP = 400    # enough overlap to preserve local context


def extract_text_from_pdf(file_path: str) -> tuple[str, list[dict]]:
    """
    Returns (full_text, pages) where pages is a list of
    {"page_number": int, "text": str}
    """
    doc = fitz.open(file_path)
    pages = []
    full_text_parts = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append({"page_number": page_num, "text": text})
            full_text_parts.append(text)

    doc.close()
    full_text = "\n\n".join(full_text_parts)
    return full_text, pages


def chunk_text(pages: list[dict]) -> list[dict]:
    """
    Chunk text with overlap, preserving page number metadata.
    Returns list of {"content": str, "chunk_index": int, "page_number": int}
    """
    chunks = []
    chunk_index = 0

    for page in pages:
        text = _normalize_text(page["text"])
        page_num = page["page_number"]

        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk_text = text[start:end]

            if end < len(text):
                boundary = max(
                    chunk_text.rfind("\n\n"),
                    chunk_text.rfind(". "),
                    chunk_text.rfind("? "),
                    chunk_text.rfind("! "),
                )
                if boundary > CHUNK_SIZE * 0.55:
                    end = start + boundary + 1
                    chunk_text = text[start:end]

            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text.strip(),
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                })
                chunk_index += 1

            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    paragraphs = []
    current: list[str] = []

    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def process_pdf(file_path: str) -> tuple[str, list[dict]]:
    """
    Main entry point. Returns (full_text, chunks).
    """
    logger.info(f"Extracting text from {file_path}")
    full_text, pages = extract_text_from_pdf(file_path)

    if not full_text.strip():
        raise ValueError("No text could be extracted from this PDF. It may be scanned.")

    logger.info(f"Extracted {len(pages)} pages, chunking...")
    chunks = chunk_text(pages)
    logger.info(f"Created {len(chunks)} chunks")

    return full_text, chunks
