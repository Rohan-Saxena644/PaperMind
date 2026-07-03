from pathlib import Path

from app.services.ingestion.pdf_processor import chunk_text


def process_text_file(file_path: str) -> tuple[str, list[dict]]:
    text = Path(file_path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("No text could be extracted from this source.")

    pages = [{"page_number": 1, "text": text}]
    return text, chunk_text(pages)
