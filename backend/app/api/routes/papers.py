from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil
import os

from app.db.session import get_db
from app.models.models import User, Paper, PaperStatus
from app.schemas.schemas import PaperOut, PaperListOut
from app.api.deps import get_current_user
from app.workers.processor import enqueue_paper
from app.core.config import settings

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
        status=PaperStatus.PENDING,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Enqueue background processing
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
