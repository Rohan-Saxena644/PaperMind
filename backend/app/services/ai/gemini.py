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
def extract_concepts(full_text: str) -> dict:
    prompt = f"""Extract a compact knowledge graph from this academic paper. Return ONLY valid JSON.

Paper text:
{full_text[:12000]}

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

    response = _model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    data = json.loads(text)
    return {
        "concepts": data.get("concepts", []),
        "authors": data.get("authors", []),
        "relationships": data.get("relationships", []),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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

    response = _model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


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
