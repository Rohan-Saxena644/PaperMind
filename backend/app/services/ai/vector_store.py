from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, FilterSelector, MatchAny, MatchValue
)
from app.core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)

_client = QdrantClient(url=settings.qdrant_url)

EMBEDDING_DIM = 768  # text-embedding-004 dimension


def ensure_collection():
    collections = _client.get_collections().collections
    names = [c.name for c in collections]
    if settings.qdrant_collection not in names:
        _client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")


def upsert_chunk(chunk_id: str, embedding: list[float], payload: dict) -> str:
    ensure_collection()
    _client.upsert(
        collection_name=settings.qdrant_collection,
        points=[PointStruct(id=chunk_id, vector=embedding, payload=payload)],
    )
    return chunk_id


def search_chunks(
    query_embedding: list[float],
    user_id: str,
    paper_ids: list[str] | None = None,
    top_k: int = 8,
) -> list[dict]:
    ensure_collection()

    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]

    if paper_ids:
        must_conditions.append(
            FieldCondition(key="paper_id", match=MatchAny(any=paper_ids))
        )

    results = _client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_embedding,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "chunk_id": str(r.id),
            "paper_id": r.payload.get("paper_id"),
            "paper_title": r.payload.get("paper_title"),
            "content": r.payload.get("content"),
            "page_number": r.payload.get("page_number"),
            "score": r.score,
        }
        for r in results
    ]


def delete_paper_chunks(paper_id: str):
    ensure_collection()
    _client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=FilterSelector(
            filter=Filter(must=[
                FieldCondition(key="paper_id", match=MatchValue(value=paper_id))
            ])
        ),
    )
