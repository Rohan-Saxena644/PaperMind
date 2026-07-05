from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.models import Paper, PaperStatus, User, Workspace
from app.schemas.schemas import TimelinePaper, TimelineResponse, TimelineYear

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/", response_model=TimelineResponse)
def paper_timeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    papers = (
        db.query(Paper)
        .filter(
            Paper.user_id == current_user.id,
            Paper.workspace_id == workspace.id,
            Paper.status == PaperStatus.READY,
        )
        .order_by(Paper.created_at.asc())
        .all()
    )

    grouped: dict[int, list[Paper]] = defaultdict(list)
    for paper in papers:
        year = paper.publication_year or paper.created_at.year
        grouped[year].append(paper)

    years = []
    for year in sorted(grouped.keys()):
        year_papers = grouped[year]
        concept_counts: Counter[str] = Counter()
        for paper in year_papers:
            for keyword in paper.keywords or []:
                if isinstance(keyword, str) and keyword.strip():
                    concept_counts[keyword.strip()] += 1

        years.append(TimelineYear(
            year=year,
            papers=[
                TimelinePaper(
                    id=paper.id,
                    title=paper.title,
                    authors=paper.authors,
                    summary_short=paper.summary_short,
                    keywords=[kw for kw in (paper.keywords or []) if isinstance(kw, str)],
                    reading_status=paper.reading_status,
                    publication_year=paper.publication_year,
                    created_at=paper.created_at,
                )
                for paper in year_papers
            ],
            concepts=[concept for concept, _ in concept_counts.most_common(8)],
        ))

    return TimelineResponse(years=years)
