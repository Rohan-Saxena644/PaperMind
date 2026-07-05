from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import hashlib
import random

from app.db.session import get_db
from app.models.models import User, Paper, PaperStatus, FlashcardReview, Workspace
from app.schemas.schemas import (
    CompareRequest,
    CompareResponse,
    QuizResponse,
    QuizQuestion,
    QuizReviewRequest,
    QuizReviewResponse,
)
from app.api.deps import get_current_user, get_current_workspace
from app.services.ai.gemini import AIRateLimitError, compare_papers

router = APIRouter(prefix="/papers", tags=["papers"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_flashcard(fc: dict) -> tuple[str, str] | None:
    question = str(fc.get("question", "")).strip()
    answer = str(fc.get("answer", "")).strip()
    if not question or not answer:
        return None
    return question, answer


def _card_key(paper_id, question: str, answer: str) -> str:
    raw = f"{paper_id}:{question}:{answer}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _is_due(due_at: datetime, now: datetime) -> bool:
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return due_at <= now


def _apply_sm2(review: FlashcardReview, quality: int, now: datetime) -> None:
    if quality < 3:
        review.repetitions = 0
        review.interval_days = 1
        review.lapses += 1
    else:
        if review.repetitions == 0:
            review.interval_days = 1
        elif review.repetitions == 1:
            review.interval_days = 6
        else:
            review.interval_days = max(1, round(review.interval_days * review.ease_factor))

        review.repetitions += 1

    difficulty = 5 - quality
    review.ease_factor = max(
        1.3,
        review.ease_factor + (0.1 - difficulty * (0.08 + difficulty * 0.02)),
    )
    review.last_reviewed_at = now
    review.due_at = now + timedelta(days=review.interval_days)


@router.post("/compare", response_model=CompareResponse)
def compare(
    payload: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    if len(payload.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 papers to compare")
    if len(payload.paper_ids) > 4:
        raise HTTPException(status_code=400, detail="Compare at most 4 papers at once")

    papers = (
        db.query(Paper)
        .filter(
            Paper.id.in_(payload.paper_ids),
            Paper.user_id == current_user.id,
            Paper.workspace_id == workspace.id,
        )
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
    workspace: Workspace = Depends(get_current_workspace),
):
    """Pull due flashcards first, then fill with future/new cards if needed."""
    papers = (
        db.query(Paper)
        .filter(
            Paper.user_id == current_user.id,
            Paper.workspace_id == workspace.id,
            Paper.status == PaperStatus.READY,
        )
        .all()
    )

    raw_cards = []
    for paper in papers:
        if not paper.flashcards:
            continue
        for fc in paper.flashcards:
            normalized = _normalize_flashcard(fc)
            if normalized is None:
                continue
            question, answer = normalized
            key = _card_key(paper.id, question, answer)
            raw_cards.append((paper, key, question, answer))

    if not raw_cards:
        raise HTTPException(status_code=404, detail="No flashcards available yet. Upload and process some papers first.")

    reviews = (
        db.query(FlashcardReview)
        .filter(
            FlashcardReview.user_id == current_user.id,
            FlashcardReview.workspace_id == workspace.id,
            FlashcardReview.card_key.in_([card[1] for card in raw_cards]),
        )
        .all()
    )
    reviews_by_key = {review.card_key: review for review in reviews}
    now = _utcnow()

    due_pool: list[QuizQuestion] = []
    later_pool: list[QuizQuestion] = []
    for paper, key, question, answer in raw_cards:
        review = reviews_by_key.get(key)
        question_out = QuizQuestion(
            card_key=key,
            question=question,
            answer=answer,
            paper_id=paper.id,
            paper_title=paper.title,
            due_at=review.due_at if review else now,
            repetitions=review.repetitions if review else 0,
            ease_factor=review.ease_factor if review else 2.5,
        )
        if review is None or _is_due(review.due_at, now):
            due_pool.append(question_out)
        else:
            later_pool.append(question_out)

    random.shuffle(due_pool)
    random.shuffle(later_pool)
    return QuizResponse(questions=(due_pool + later_pool)[:count])


@router.post("/quiz/review", response_model=QuizReviewResponse)
def review_quiz_card(
    payload: QuizReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    paper = (
        db.query(Paper)
        .filter(
            Paper.id == payload.paper_id,
            Paper.user_id == current_user.id,
            Paper.workspace_id == workspace.id,
        )
        .first()
    )
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    expected_key = _card_key(payload.paper_id, payload.question.strip(), payload.answer.strip())
    if payload.card_key != expected_key:
        raise HTTPException(status_code=400, detail="Flashcard key does not match the submitted card")

    card_exists = False
    for fc in paper.flashcards or []:
        normalized = _normalize_flashcard(fc)
        if normalized is None:
            continue
        question, answer = normalized
        if _card_key(paper.id, question, answer) == payload.card_key:
            card_exists = True
            break
    if not card_exists:
        raise HTTPException(status_code=404, detail="Flashcard no longer exists on this paper")

    review = (
        db.query(FlashcardReview)
        .filter(
            FlashcardReview.user_id == current_user.id,
            FlashcardReview.workspace_id == workspace.id,
            FlashcardReview.card_key == payload.card_key,
        )
        .first()
    )
    if review is None:
        review = FlashcardReview(
            user_id=current_user.id,
            workspace_id=workspace.id,
            paper_id=paper.id,
            card_key=payload.card_key,
            question=payload.question.strip(),
            answer=payload.answer.strip(),
            paper_title=paper.title,
        )
        db.add(review)

    now = _utcnow()
    _apply_sm2(review, payload.quality, now)
    db.commit()
    db.refresh(review)

    return QuizReviewResponse(
        card_key=review.card_key,
        quality=payload.quality,
        repetitions=review.repetitions,
        ease_factor=review.ease_factor,
        interval_days=review.interval_days,
        due_at=review.due_at,
        lapses=review.lapses,
    )
