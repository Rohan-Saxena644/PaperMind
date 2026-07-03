import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"


def search_arxiv(query: str, max_results: int = 8) -> list[dict]:
    cleaned = query.strip()
    if not cleaned:
        return []

    max_results = max(1, min(max_results, 10))
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        response = client.get(
            ARXIV_API_URL,
            params={
                "search_query": f"all:{cleaned}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        response.raise_for_status()

    root = ET.fromstring(response.text)
    results = []
    for entry in root.findall(f"{ATOM}entry"):
        entry_url = _text(entry, "id")
        arxiv_id = _arxiv_id(entry_url)
        title = _compact(_text(entry, "title"))
        summary = _compact(_text(entry, "summary"))
        authors = [
            _compact(author.findtext(f"{ATOM}name", default=""))
            for author in entry.findall(f"{ATOM}author")
        ]
        authors = [author for author in authors if author]
        published_year = _year(_text(entry, "published"))
        pdf_url = _pdf_url(entry, arxiv_id)

        if arxiv_id and pdf_url:
            results.append({
                "arxiv_id": arxiv_id,
                "title": title or arxiv_id,
                "authors": authors,
                "summary": summary,
                "published_year": published_year,
                "pdf_url": pdf_url,
                "entry_url": entry_url,
            })

    return results


def download_arxiv_pdf(pdf_url: str, max_bytes: int) -> bytes:
    with httpx.Client(timeout=40, follow_redirects=True) as client:
        response = client.get(pdf_url, headers={"User-Agent": "PaperMind/0.1"})
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
        raise ValueError("arXiv did not return a PDF file.")
    if len(response.content) > max_bytes:
        raise ValueError("File too large.")
    return response.content


def _text(entry: ET.Element, tag: str) -> str:
    return entry.findtext(f"{ATOM}{tag}", default="")


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _year(value: str) -> int | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        return None


def _arxiv_id(entry_url: str) -> str:
    return entry_url.rstrip("/").split("/")[-1]


def _pdf_url(entry: ET.Element, arxiv_id: str) -> str | None:
    for link in entry.findall(f"{ATOM}link"):
        attrs = link.attrib
        if attrs.get("title") == "pdf" or attrs.get("type") == "application/pdf":
            return attrs.get("href")
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
