import redis
import json
import uuid
import logging
import time
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Paper, PaperChunk, PaperSource, PaperStatus
from app.services.ingestion.pdf_processor import process_pdf
from app.services.ingestion.text_processor import process_text_file
from app.services.ai.gemini import (
    get_embedding,
    analyze_paper,
)
from app.services.ai.vector_store import delete_paper_chunks, upsert_chunk
from app.services.ai.graph import write_paper_graph

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

QUEUE_NAME = "paper_processing"
RETRY_QUEUE_NAME = "paper_processing_retry"
DEAD_LETTER_QUEUE_NAME = "paper_processing_dead_letter"


def get_redis():
    return redis.from_url(settings.redis_url)


def enqueue_paper(paper_id: str, attempt: int = 1) -> str:
    r = get_redis()
    job_id = str(uuid.uuid4())
    payload = json.dumps({
        "job_id": job_id,
        "paper_id": paper_id,
        "attempt": attempt,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    })
    r.rpush(QUEUE_NAME, payload)
    logger.info(f"Enqueued paper {paper_id} as job {job_id}, attempt {attempt}")
    return job_id


def process_paper_job(paper_id: str, job_id: str | None = None, attempt: int = 1):
    db = SessionLocal()
    try:
        paper = db.get(Paper, uuid.UUID(paper_id))
        if not paper:
            logger.error(f"Paper {paper_id} not found")
            return

        paper.status = PaperStatus.PROCESSING
        paper.processing_attempts = attempt
        paper.error_message = None
        paper.next_retry_at = None
        paper.failed_at = None
        db.commit()

        _clear_existing_outputs(db, paper)

        # 1. Extract text and chunk
        if paper.source_type == PaperSource.PDF or paper.source_type == PaperSource.ARXIV:
            full_text, chunks = process_pdf(paper.file_path)
        else:
            full_text, chunks = process_text_file(paper.file_path)

        # 2. Analyze the paper once. This keeps free-tier usage sane by
        # combining summary, flashcards, and graph extraction into one call.
        logger.info(f"Analyzing paper {paper_id}")
        analysis = analyze_paper(full_text)
        metadata = analysis.get("metadata", {})

        paper.title = metadata.get("title", paper.title)
        paper.authors = metadata.get("authors", paper.authors or "")
        paper.abstract = metadata.get("abstract", "")
        paper.publication_year = _safe_year(metadata.get("publication_year")) or paper.publication_year
        paper.summary_short = metadata.get("summary_short", "")
        paper.summary_long = metadata.get("summary_long", "")
        paper.key_contributions = metadata.get("key_contributions", [])
        paper.keywords = metadata.get("keywords", [])

        paper.flashcards = analysis.get("flashcards", [])

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

        # 5. Extract and persist knowledge graph data. This is best effort:
        # graph issues should not fail an otherwise usable paper ingestion.
        try:
            logger.info(f"Writing graph concepts for paper {paper_id}")
            graph_data = analysis.get("graph", {})
            write_paper_graph(
                user_id=str(paper.user_id),
                paper_id=paper_id,
                title=paper.title,
                authors=graph_data.get("authors") or _split_authors(paper.authors),
                concepts=graph_data.get("concepts", []),
                relationships=graph_data.get("relationships", []),
            )
        except Exception as graph_error:
            logger.warning(f"Knowledge graph write failed for paper {paper_id}: {graph_error}")

        paper.total_chunks = len(chunks)
        paper.status = PaperStatus.READY
        paper.processed_at = datetime.now(timezone.utc)
        paper.next_retry_at = None
        paper.failed_at = None
        db.commit()

        logger.info(f"Paper {paper_id} processed successfully")

    except Exception as e:
        logger.error(f"Failed to process paper {paper_id}: {e}")
        _handle_job_failure(db, paper_id, job_id, attempt, e)
    finally:
        db.close()


def _clear_existing_outputs(db, paper: Paper) -> None:
    for chunk in list(paper.chunks):
        db.delete(chunk)
    db.flush()

    try:
        delete_paper_chunks(str(paper.id))
    except Exception as exc:
        logger.warning(f"Could not clear old vectors for paper {paper.id}: {exc}")


def _handle_job_failure(db, paper_id: str, job_id: str | None, attempt: int, error: Exception) -> None:
    paper = db.get(Paper, uuid.UUID(paper_id))
    if not paper:
        return

    paper.processing_attempts = attempt
    paper.error_message = str(error)

    if attempt < settings.worker_max_retries:
        delay = min(
            settings.worker_retry_base_seconds * (2 ** max(attempt - 1, 0)),
            settings.worker_retry_max_seconds,
        )
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        paper.status = PaperStatus.PENDING
        paper.next_retry_at = retry_at
        db.commit()
        _schedule_retry(paper_id, attempt + 1, retry_at)
        logger.info(f"Scheduled retry for paper {paper_id} in {delay}s")
        return

    paper.status = PaperStatus.FAILED
    paper.failed_at = datetime.now(timezone.utc)
    paper.next_retry_at = None
    db.commit()
    _dead_letter(paper_id, job_id, attempt, error)


def _split_authors(authors: str | None) -> list[str]:
    if not authors:
        return []
    return [author.strip() for author in authors.replace(";", ",").split(",") if author.strip()]


def _safe_year(value) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    current_year = datetime.now(timezone.utc).year + 1
    return year if 1900 <= year <= current_year else None


def _schedule_retry(paper_id: str, attempt: int, retry_at: datetime) -> None:
    payload = json.dumps({
        "job_id": str(uuid.uuid4()),
        "paper_id": paper_id,
        "attempt": attempt,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    })
    get_redis().zadd(RETRY_QUEUE_NAME, {payload: retry_at.timestamp()})


def _dead_letter(paper_id: str, job_id: str | None, attempt: int, error: Exception) -> None:
    payload = json.dumps({
        "job_id": job_id,
        "paper_id": paper_id,
        "attempt": attempt,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": str(error),
    })
    get_redis().rpush(DEAD_LETTER_QUEUE_NAME, payload)


def _release_due_retries(r) -> int:
    due = r.zrangebyscore(RETRY_QUEUE_NAME, min=0, max=time.time())
    if not due:
        return 0

    released = 0
    for payload in due:
        if r.zrem(RETRY_QUEUE_NAME, payload):
            r.rpush(QUEUE_NAME, payload)
            released += 1
    return released


def run_worker():
    r = get_redis()
    logger.info(f"Worker started, listening on queue: {QUEUE_NAME}")

    while True:
        # Blocking pop — waits up to 5s then loops
        released = _release_due_retries(r)
        if released:
            logger.info(f"Released {released} retry job(s)")

        result = r.blpop(QUEUE_NAME, timeout=5)
        if result:
            _, payload_bytes = result
            payload = json.loads(payload_bytes)
            paper_id = payload["paper_id"]
            job_id = payload["job_id"]
            attempt = int(payload.get("attempt", 1))
            logger.info(f"Processing job {job_id} for paper {paper_id}, attempt {attempt}")
            process_paper_job(paper_id, job_id=job_id, attempt=attempt)


if __name__ == "__main__":
    run_worker()
