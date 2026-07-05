from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil
import os

from app.db.session import get_db
from app.models.models import PaperSource, User, Paper, PaperStatus, Workspace
from app.schemas.schemas import (
    ArxivImportRequest,
    ArxivSearchResponse,
    PaperOut,
    PaperListOut,
    PaperReadingUpdate,
    UrlIngestRequest,
)
from app.api.deps import get_current_user, get_current_workspace
from app.workers.processor import enqueue_paper
from app.core.config import settings
from app.services.ingestion.arxiv_processor import download_arxiv_pdf, search_arxiv
from app.services.ingestion.url_processor import fetch_url_content

router = APIRouter(prefix="/papers", tags=["papers"])

ALLOWED_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=PaperOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
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
        workspace_id=workspace.id,
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
    workspace: Workspace = Depends(get_current_workspace),
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
        workspace_id=workspace.id,
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
    workspace: Workspace = Depends(get_current_workspace),
):
    papers = (
        db.query(Paper)
        .filter(Paper.user_id == current_user.id, Paper.workspace_id == workspace.id)
        .order_by(Paper.created_at.desc())
        .all()
    )
    return [PaperListOut.model_validate(p) for p in papers]


@router.get("/arxiv/search", response_model=ArxivSearchResponse)
def search_arxiv_papers(
    query: str = Query(min_length=2, max_length=200),
    max_results: int = Query(default=8, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    try:
        results = search_arxiv(query, max_results=max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not search arXiv: {exc}") from exc
    return ArxivSearchResponse(results=results)


@router.post("/arxiv/import", response_model=PaperOut, status_code=status.HTTP_202_ACCEPTED)
def import_arxiv_paper(
    payload: ArxivImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    try:
        content = download_arxiv_pdf(str(payload.pdf_url), max_bytes=MAX_FILE_SIZE)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not download arXiv PDF: {exc}") from exc

    upload_dir = Path(settings.local_storage_path) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"
    file_path.write_bytes(content)

    paper = Paper(
        user_id=current_user.id,
        workspace_id=workspace.id,
        title=payload.title,
        authors=", ".join(payload.authors),
        publication_year=payload.published_year,
        file_path=str(file_path),
        file_name=f"{payload.title[:180]}.pdf",
        file_size=len(content),
        source_type=PaperSource.ARXIV,
        source_url=str(payload.entry_url),
        status=PaperStatus.PENDING,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    enqueue_paper(str(paper.id))
    return PaperOut.model_validate(paper)


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


@router.post("/{paper_id}/retry", response_model=PaperOut, status_code=status.HTTP_202_ACCEPTED)
def retry_paper_processing(
    paper_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(
        Paper.id == paper_id, Paper.user_id == current_user.id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.status not in {PaperStatus.FAILED, PaperStatus.PENDING}:
        raise HTTPException(status_code=400, detail="Only failed or queued papers can be retried")

    paper.status = PaperStatus.PENDING
    paper.error_message = None
    paper.processing_attempts = 0
    paper.next_retry_at = None
    paper.failed_at = None
    db.commit()
    db.refresh(paper)

    enqueue_paper(str(paper.id), attempt=1)
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
