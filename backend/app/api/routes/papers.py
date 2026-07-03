from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil
import os

from app.db.session import get_db
from app.models.models import PaperSource, User, Paper, PaperStatus
from app.schemas.schemas import PaperOut, PaperListOut, PaperReadingUpdate, UrlIngestRequest
from app.api.deps import get_current_user
from app.workers.processor import enqueue_paper
from app.core.config import settings
from app.services.ingestion.url_processor import fetch_url_content

router = APIRouter(prefix="/papers", tags=["papers"])

ALLOWED_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=PaperOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save file to storage
    upload_dir = Path(settings.local_storage_path) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    paper = Paper(
        user_id=current_user.id,
        title=file.filename or "Untitled",
        file_path=str(file_path),
        file_name=file.filename or "untitled.pdf",
        file_size=len(content),
        source_type=PaperSource.PDF,
        status=PaperStatus.PENDING,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Enqueue background processing
    enqueue_paper(str(paper.id))

    return PaperOut.model_validate(paper)


@router.post("/ingest-url", response_model=PaperOut, status_code=status.HTTP_202_ACCEPTED)
def ingest_url(
    payload: UrlIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        url_content = fetch_url_content(str(payload.url))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not ingest URL: {exc}") from exc

    upload_dir = Path(settings.local_storage_path) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.txt"
    encoded = url_content.text.encode("utf-8")
    file_path.write_bytes(encoded)

    source_type = PaperSource.YOUTUBE if url_content.source_type == "youtube" else PaperSource.URL
    paper = Paper(
        user_id=current_user.id,
        title=url_content.title or str(payload.url),
        file_path=str(file_path),
        file_name=url_content.title or str(payload.url),
        file_size=len(encoded),
        source_type=source_type,
        source_url=str(payload.url),
        status=PaperStatus.PENDING,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    enqueue_paper(str(paper.id))
    return PaperOut.model_validate(paper)


@router.get("/", response_model=list[PaperListOut])
def list_papers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    papers = (
        db.query(Paper)
        .filter(Paper.user_id == current_user.id)
        .order_by(Paper.created_at.desc())
        .all()
    )
    return [PaperListOut.model_validate(p) for p in papers]


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(
        Paper.id == paper_id, Paper.user_id == current_user.id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperOut.model_validate(paper)


@router.patch("/{paper_id}/reading", response_model=PaperOut)
def update_reading_progress(
    paper_id: uuid.UUID,
    payload: PaperReadingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(
        Paper.id == paper_id, Paper.user_id == current_user.id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper.reading_status = payload.reading_status
    paper.personal_notes = payload.personal_notes.strip() if payload.personal_notes else None
    paper.highlights = [
        highlight.strip()
        for highlight in payload.highlights
        if highlight.strip()
    ][:50]

    db.commit()
    db.refresh(paper)
    return PaperOut.model_validate(paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(
        Paper.id == paper_id, Paper.user_id == current_user.id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete file from storage
    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)

    # Delete vector embeddings
    from app.services.ai.vector_store import delete_paper_chunks
    delete_paper_chunks(str(paper_id))

    db.delete(paper)
    db.commit()
