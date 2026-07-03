import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import YouTubeTranscriptApi


MAX_URL_TEXT_CHARS = 120_000


@dataclass
class UrlContent:
    title: str
    text: str
    source_type: str


class ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag in {"p", "br", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
        if self._skip_depth == 0:
            self._parts.append(text)

    def readable_text(self) -> str:
        raw = " ".join(self._parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def fetch_url_content(url: str) -> UrlContent:
    if _is_youtube_url(url):
        return _fetch_youtube_transcript(url)
    return _fetch_webpage(url)


def _fetch_webpage(url: str) -> UrlContent:
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "PaperMind/0.1"})
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ValueError("This URL does not look like a readable webpage.")

    if "text/plain" in content_type:
        title = urlparse(str(response.url)).netloc or "Imported URL"
        text = response.text
    else:
        parser = ReadableHTMLParser()
        parser.feed(response.text)
        title = parser.title or urlparse(str(response.url)).netloc or "Imported URL"
        text = parser.readable_text()

    text = text[:MAX_URL_TEXT_CHARS]
    if len(text) < 500:
        raise ValueError("Not enough readable text found at this URL.")

    return UrlContent(title=title[:500], text=text, source_type="url")


def _fetch_youtube_transcript(url: str) -> UrlContent:
    video_id = _youtube_video_id(url)
    if not video_id:
        raise ValueError("Could not find a YouTube video id in this URL.")

    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    text = "\n".join(item["text"] for item in transcript if item.get("text"))
    if len(text.strip()) < 500:
        raise ValueError("No usable transcript found for this YouTube video.")

    title = f"YouTube video {video_id}"
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
            )
            if response.status_code == 200:
                title = response.json().get("title") or title
    except Exception:
        pass

    return UrlContent(title=title[:500], text=text[:MAX_URL_TEXT_CHARS], source_type="youtube")


def _is_youtube_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "youtube.com" in host or "youtu.be" in host


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/") or None
    params = parse_qs(parsed.query)
    if "v" in params and params["v"]:
        return params["v"][0]
    match = re.search(r"/(?:shorts|embed)/([^/?]+)", parsed.path)
    return match.group(1) if match else None
