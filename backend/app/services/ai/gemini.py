import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(settings.gemini_model)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_query_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_paper_summary(full_text: str) -> dict:
    prompt = f"""You are a research assistant. Analyze this academic paper and return ONLY valid JSON.

Paper text:
{full_text[:15000]}

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

    response = _model.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_flashcards(full_text: str, count: int = 10) -> list[dict]:
    prompt = f"""Generate {count} flashcards from this academic paper. Return ONLY valid JSON.

Paper text:
{full_text[:10000]}

Return this exact JSON structure:
{{
  "flashcards": [
    {{"question": "Q1?", "answer": "A1"}},
    {{"question": "Q2?", "answer": "A2"}}
  ]
}}"""

    response = _model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    data = json.loads(text)
    return data.get("flashcards", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def answer_question(question: str, context_chunks: list[dict]) -> str:
    context = "\n\n---\n\n".join([
        f"[From: {c['paper_title']}]\n{c['content']}"
        for c in context_chunks
    ])

    prompt = f"""You are a research assistant with access to the user's paper library.
Answer the question using ONLY the provided context. Be precise and cite which paper each fact comes from.
If the context doesn't contain enough information, say so clearly.

Context from papers:
{context}

Question: {question}

Answer:"""

    response = _model.generate_content(prompt)
    return response.text.strip()
