import google.generativeai as genai
import redis
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential
from app.core.config import settings
import json
import logging
import hashlib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(settings.gemini_model)


class AIRateLimitError(RuntimeError):
    pass


def _redis_client():
    return redis.from_url(settings.redis_url, decode_responses=True)


def _consume_ai_quota(kind: str) -> None:
    """
    Shared guardrail for Gemini free-tier usage.
    Counts model and embedding calls together because both consume API quota.
    """
    now = datetime.now(timezone.utc)
    minute_key = f"ai:quota:{kind}:minute:{now:%Y%m%d%H%M}"
    day_key = f"ai:quota:{kind}:day:{now:%Y%m%d}"

    try:
        client = _redis_client()
        minute_count = client.incr(minute_key)
        if minute_count == 1:
            client.expire(minute_key, 90)

        day_count = client.incr(day_key)
        if day_count == 1:
            client.expire(day_key, 60 * 60 * 26)
    except Exception as exc:
        logger.warning(f"AI quota guard unavailable, continuing without Redis limiter: {exc}")
        return

    if minute_count > settings.ai_rpm_limit:
        raise AIRateLimitError("AI rate limit reached. Please try again in a minute.")
    if day_count > settings.ai_daily_limit:
        raise AIRateLimitError("Daily AI quota reached. Please try again tomorrow.")


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _generate_text(prompt: str) -> str:
    _consume_ai_quota("gemini")
    response = _model.generate_content(prompt)
    return response.text.strip()


def _json_from_prompt(prompt: str) -> dict:
    return json.loads(_clean_json(_generate_text(prompt)))


ai_retry = retry(
    retry=retry_if_not_exception_type(AIRateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)


@ai_retry
def get_embedding(text: str) -> list[float]:
    cached = _get_cached_embedding("document", text)
    if cached is not None:
        return cached

    _consume_ai_quota("gemini")
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_document",
    )
    embedding = result["embedding"]
    _set_cached_embedding("document", text, embedding)
    return embedding


@ai_retry
def get_query_embedding(text: str) -> list[float]:
    cached = _get_cached_embedding("query", text)
    if cached is not None:
        return cached

    _consume_ai_quota("gemini")
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_query",
    )
    embedding = result["embedding"]
    _set_cached_embedding("query", text, embedding)
    return embedding


def _embedding_cache_key(kind: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"ai:embedding:{settings.gemini_embedding_model}:{kind}:{digest}"


def _get_cached_embedding(kind: str, text: str) -> list[float] | None:
    try:
        cached = _redis_client().get(_embedding_cache_key(kind, text))
    except Exception:
        return None
    return json.loads(cached) if cached else None


def _set_cached_embedding(kind: str, text: str, embedding: list[float]) -> None:
    try:
        _redis_client().setex(
            _embedding_cache_key(kind, text),
            60 * 60 * 24 * 30,
            json.dumps(embedding),
        )
    except Exception:
        return


@ai_retry
def generate_paper_summary(full_text: str) -> dict:
    prompt = f"""You are a research assistant. Analyze this academic paper and return ONLY valid JSON.

Paper text:
{full_text[:settings.ai_max_paper_chars]}

Return this exact JSON structure:
{{
  "title": "paper title",
  "authors": "author names or empty string",
  "abstract": "original abstract or your summary",
  "summary_short": "one sentence summary",
  "summary_long": "2-3 paragraph summary for a graduate student",
  "key_contributions": ["contribution 1", "contribution 2", "contribution 3"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}"""

    return _json_from_prompt(prompt)


@ai_retry
def generate_flashcards(full_text: str, count: int = 10) -> list[dict]:
    prompt = f"""Generate {count} flashcards from this academic paper. Return ONLY valid JSON.

Paper text:
{full_text[:settings.ai_max_paper_chars]}

Return this exact JSON structure:
{{
  "flashcards": [
    {{"question": "Q1?", "answer": "A1"}},
    {{"question": "Q2?", "answer": "A2"}}
  ]
}}"""

    data = _json_from_prompt(prompt)
    return data.get("flashcards", [])


@ai_retry
def extract_concepts(full_text: str) -> dict:
    prompt = f"""Extract a compact knowledge graph from this academic paper. Return ONLY valid JSON.

Paper text:
{full_text[:settings.ai_max_paper_chars]}

Return this exact JSON structure:
{{
  "concepts": [
    {{"name": "concept name", "category": "method|dataset|metric|problem|theory|finding|tool|other"}}
  ],
  "authors": ["Author One", "Author Two"],
  "relationships": [
    {{"source": "concept name", "target": "related concept name", "type": "RELATED_TO"}}
  ]
}}

Rules:
- Return 8 to 18 important concepts.
- Use short canonical concept names.
- Only use concept names that appear in the concepts array as relationship endpoints.
- Relationship type must be RELATED_TO unless the paper clearly says one concept uses or introduces another."""

    data = _json_from_prompt(prompt)
    return {
        "concepts": data.get("concepts", []),
        "authors": data.get("authors", []),
        "relationships": data.get("relationships", []),
    }


@ai_retry
def analyze_paper(full_text: str, flashcard_count: int = 10) -> dict:
    cache_key = _analysis_cache_key(full_text, flashcard_count)
    cached = _get_cached_json(cache_key)
    if cached is not None:
        return cached

    prompt = f"""You are a research assistant. Analyze this academic paper and return ONLY valid JSON.

Paper text:
{full_text[:settings.ai_max_paper_chars]}

Return this exact JSON structure:
{{
    "metadata": {{
      "title": "paper title",
      "authors": "author names or empty string",
      "abstract": "original abstract or your summary",
      "publication_year": 2024,
      "summary_short": "one sentence summary",
    "summary_long": "2-3 paragraph summary for a graduate student",
    "key_contributions": ["contribution 1", "contribution 2", "contribution 3"],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
  }},
  "flashcards": [
    {{"question": "Q1?", "answer": "A1"}}
  ],
  "graph": {{
    "concepts": [
      {{"name": "concept name", "category": "method|dataset|metric|problem|theory|finding|tool|other"}}
    ],
    "authors": ["Author One", "Author Two"],
    "relationships": [
      {{"source": "concept name", "target": "related concept name", "type": "RELATED_TO"}}
    ]
  }}
}}

Rules:
- Generate exactly {flashcard_count} flashcards.
- Return 8 to 18 important concepts.
- Use short canonical concept names.
- Only use concept names that appear in the concepts array as relationship endpoints.
- Keep all strings concise."""

    data = _json_from_prompt(prompt)
    result = {
        "metadata": data.get("metadata", {}),
        "flashcards": data.get("flashcards", []),
        "graph": data.get("graph", {"concepts": [], "authors": [], "relationships": []}),
    }
    _set_cached_json(cache_key, result, ttl_seconds=60 * 60 * 24 * 30)
    return result


def _analysis_cache_key(full_text: str, flashcard_count: int) -> str:
    sample = full_text[:settings.ai_max_paper_chars]
    digest = hashlib.sha256(sample.encode("utf-8")).hexdigest()
    return f"ai:analysis:{settings.gemini_model}:{flashcard_count}:{digest}"


def _get_cached_json(key: str) -> dict | None:
    try:
        cached = _redis_client().get(key)
    except Exception:
        return None
    return json.loads(cached) if cached else None


def _set_cached_json(key: str, value: dict, ttl_seconds: int) -> None:
    try:
        _redis_client().setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        return


@ai_retry
def compare_papers(papers: list[dict]) -> dict:
    """
    papers: list of {"title": str, "summary_long": str, "key_contributions": list[str]}
    Returns structured comparison JSON.
    """
    papers_text = "\n\n".join([
        f"--- Paper: {p['title']} ---\n"
        f"Summary: {p['summary_long']}\n"
        f"Key contributions: {', '.join(p['key_contributions'] or [])}"
        for p in papers
    ])

    prompt = f"""You are a research assistant comparing multiple academic papers. Return ONLY valid JSON.

{papers_text}

Return this exact JSON structure:
{{
  "overview": "2-3 sentence high level comparison",
  "similarities": ["similarity 1", "similarity 2", "similarity 3"],
  "differences": ["difference 1", "difference 2", "difference 3"],
  "comparison_table": [
    {{"aspect": "Approach", "values": ["paper 1 value", "paper 2 value"]}},
    {{"aspect": "Key innovation", "values": ["paper 1 value", "paper 2 value"]}},
    {{"aspect": "Limitations", "values": ["paper 1 value", "paper 2 value"]}}
  ],
  "recommendation": "1-2 sentences on when to use which approach, or how they complement each other"
}}

The comparison_table "values" array must have exactly {len(papers)} items, in the same order as the papers above."""

    return _json_from_prompt(prompt)


@ai_retry
def answer_question(question: str, context_chunks: list[dict]) -> str:
    context_parts = []
    current_size = 0
    for chunk in context_chunks:
        part = f"[From: {chunk['paper_title']}]\n{chunk['content']}"
        if current_size + len(part) > settings.ai_max_chat_context_chars:
            break
        context_parts.append(part)
        current_size += len(part)

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a research assistant with access to the user's paper library.
Answer the question using ONLY the provided context. Be precise and cite which paper each fact comes from.
If the context doesn't contain enough information, say so clearly.

Context from papers:
{context}

Question: {question}

Answer:"""

    return _generate_text(prompt)
