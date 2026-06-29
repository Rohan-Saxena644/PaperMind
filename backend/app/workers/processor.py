import redis
import json
import uuid
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Paper, PaperChunk, PaperStatus
from app.services.ingestion.pdf_processor import process_pdf
from app.services.ai.gemini import (
    get_embedding,
    generate_paper_summary,
    generate_flashcards,
)
from app.services.ai.vector_store import upsert_chunk

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

QUEUE_NAME = "paper_processing"


def get_redis():
    return redis.from_url(settings.redis_url)


def enqueue_paper(paper_id: str) -> str:
    r = get_redis()
    job_id = str(uuid.uuid4())
    payload = json.dumps({"job_id": job_id, "paper_id": paper_id})
    r.rpush(QUEUE_NAME, payload)
    logger.info(f"Enqueued paper {paper_id} as job {job_id}")
    return job_id


def process_paper_job(paper_id: str):
    db = SessionLocal()
    try:
        paper = db.get(Paper, uuid.UUID(paper_id))
        if not paper:
            logger.error(f"Paper {paper_id} not found")
            return

        paper.status = PaperStatus.PROCESSING
        db.commit()

        # 1. Extract text and chunk
        full_text, chunks = process_pdf(paper.file_path)

        # 2. Generate AI metadata
        logger.info(f"Generating summary for paper {paper_id}")
        metadata = generate_paper_summary(full_text)

        paper.title = metadata.get("title", paper.title)
        paper.authors = metadata.get("authors", "")
        paper.abstract = metadata.get("abstract", "")
        paper.summary_short = metadata.get("summary_short", "")
        paper.summary_long = metadata.get("summary_long", "")
        paper.key_contributions = metadata.get("key_contributions", [])
        paper.keywords = metadata.get("keywords", [])

        # 3. Generate flashcards
        logger.info(f"Generating flashcards for paper {paper_id}")
        paper.flashcards = generate_flashcards(full_text)

        # 4. Embed chunks and store in Qdrant + Postgres
        logger.info(f"Embedding {len(chunks)} chunks for paper {paper_id}")
        for chunk_data in chunks:
            embedding = get_embedding(chunk_data["content"])

            qdrant_id = str(uuid.uuid4())
            upsert_chunk(
                chunk_id=qdrant_id,
                embedding=embedding,
                payload={
                    "paper_id": paper_id,
                    "paper_title": paper.title,
                    "user_id": str(paper.user_id),
                    "content": chunk_data["content"],
                    "page_number": chunk_data["page_number"],
                    "chunk_index": chunk_data["chunk_index"],
                },
            )

            db_chunk = PaperChunk(
                paper_id=paper.id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data["page_number"],
                qdrant_id=qdrant_id,
            )
            db.add(db_chunk)

        paper.total_chunks = len(chunks)
        paper.status = PaperStatus.READY
        paper.processed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Paper {paper_id} processed successfully")

    except Exception as e:
        logger.error(f"Failed to process paper {paper_id}: {e}")
        paper = db.get(Paper, uuid.UUID(paper_id))
        if paper:
            paper.status = PaperStatus.FAILED
            paper.error_message = str(e)
            db.commit()
    finally:
        db.close()


def run_worker():
    r = get_redis()
    logger.info(f"Worker started, listening on queue: {QUEUE_NAME}")

    while True:
        # Blocking pop — waits up to 5s then loops
        result = r.blpop(QUEUE_NAME, timeout=5)
        if result:
            _, payload_bytes = result
            payload = json.loads(payload_bytes)
            paper_id = payload["paper_id"]
            job_id = payload["job_id"]
            logger.info(f"Processing job {job_id} for paper {paper_id}")
            process_paper_job(paper_id)


if __name__ == "__main__":
    run_worker()
