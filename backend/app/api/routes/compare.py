from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from app.db.session import get_db
from app.models.models import User, Paper, PaperStatus
from app.schemas.schemas import CompareRequest, CompareResponse, QuizResponse, QuizQuestion
from app.api.deps import get_current_user
from app.services.ai.gemini import AIRateLimitError, compare_papers

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/compare", response_model=CompareResponse)
def compare(
    payload: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(payload.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 papers to compare")
    if len(payload.paper_ids) > 4:
        raise HTTPException(status_code=400, detail="Compare at most 4 papers at once")

    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(payload.paper_ids), Paper.user_id == current_user.id)
        .all()
    )

    if len(papers) != len(payload.paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found")

    not_ready = [p.title for p in papers if p.status != PaperStatus.READY]
    if not_ready:
        raise HTTPException(
            status_code=400,
            detail=f"These papers are still processing: {', '.join(not_ready)}"
        )

    # Preserve the order the user requested
    papers_by_id = {str(p.id): p for p in papers}
    ordered_papers = [papers_by_id[str(pid)] for pid in payload.paper_ids]

    comparison_input = [
        {
            "title": p.title,
            "summary_long": p.summary_long or p.summary_short or "",
            "key_contributions": p.key_contributions or [],
        }
        for p in ordered_papers
    ]

    try:
        result = compare_papers(comparison_input)
    except AIRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    result["paper_titles"] = [p.title for p in ordered_papers]

    return CompareResponse(**result)


@router.get("/quiz/random", response_model=QuizResponse)
def random_quiz(
    count: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pull flashcards from all ready papers and shuffle them into a quiz."""
    papers = (
        db.query(Paper)
        .filter(Paper.user_id == current_user.id, Paper.status == PaperStatus.READY)
        .all()
    )

    pool: list[QuizQuestion] = []
    for paper in papers:
        if not paper.flashcards:
            continue
        for fc in paper.flashcards:
            pool.append(QuizQuestion(
                question=fc["question"],
                answer=fc["answer"],
                paper_id=paper.id,
                paper_title=paper.title,
            ))

    if not pool:
        raise HTTPException(status_code=404, detail="No flashcards available yet. Upload and process some papers first.")

    random.shuffle(pool)
    return QuizResponse(questions=pool[:count])
