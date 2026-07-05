from pydantic import BaseModel, EmailStr, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.models import PaperSource, PaperStatus, ReadingStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Papers ────────────────────────────────────────────────────────────────────

class PaperOut(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    authors: Optional[str]
    abstract: Optional[str]
    publication_year: Optional[int]
    file_name: str
    file_size: int
    source_type: PaperSource
    source_url: Optional[str]
    status: PaperStatus
    error_message: Optional[str]
    processing_attempts: int
    next_retry_at: Optional[datetime]
    failed_at: Optional[datetime]
    reading_status: ReadingStatus
    personal_notes: Optional[str]
    highlights: Optional[list[str]]
    summary_short: Optional[str]
    summary_long: Optional[str]
    key_contributions: Optional[list]
    keywords: Optional[list]
    flashcards: Optional[list]
    total_chunks: int
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaperListOut(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    authors: Optional[str]
    publication_year: Optional[int]
    source_type: PaperSource
    source_url: Optional[str]
    status: PaperStatus
    error_message: Optional[str]
    processing_attempts: int
    next_retry_at: Optional[datetime]
    reading_status: ReadingStatus
    summary_short: Optional[str]
    total_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatCreate(BaseModel):
    title: str = "New Chat"


class MessageSource(BaseModel):
    paper_id: UUID
    paper_title: str
    chunk_content: str
    score: float


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    sources: Optional[list[MessageSource]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatOut(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    created_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    paper_ids: Optional[list[UUID]] = None  # None = search all papers


class PaperReadingUpdate(BaseModel):
    reading_status: ReadingStatus
    personal_notes: Optional[str] = Field(default=None, max_length=10000)
    highlights: list[str] = Field(default_factory=list, max_length=50)


class UrlIngestRequest(BaseModel):
    url: HttpUrl


class ArxivSearchResult(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    summary: str
    published_year: Optional[int]
    pdf_url: str
    entry_url: str


class ArxivSearchResponse(BaseModel):
    results: list[ArxivSearchResult]


class ArxivImportRequest(BaseModel):
    pdf_url: HttpUrl
    entry_url: HttpUrl
    title: str
    authors: list[str] = []
    published_year: Optional[int] = None


# ── Compare ───────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    paper_ids: list[UUID]


class ComparisonTableRow(BaseModel):
    aspect: str
    values: list[str]


class CompareResponse(BaseModel):
    overview: str
    similarities: list[str]
    differences: list[str]
    comparison_table: list[ComparisonTableRow]
    recommendation: str
    paper_titles: list[str]


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    card_key: str
    question: str
    answer: str
    paper_id: UUID
    paper_title: str
    due_at: datetime
    repetitions: int = 0
    ease_factor: float = 2.5


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]


class QuizReviewRequest(BaseModel):
    card_key: str = Field(min_length=64, max_length=64)
    paper_id: UUID
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    quality: int = Field(ge=0, le=5)


class QuizReviewResponse(BaseModel):
    card_key: str
    quality: int
    repetitions: int
    ease_factor: float
    interval_days: int
    due_at: datetime
    lapses: int


# ── Worker job ────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    x: float = 0.5
    y: float = 0.5
    centrality: float = 0.0


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class TopConcept(BaseModel):
    id: str
    label: str
    centrality: float


class GraphInsights(BaseModel):
    node_count: int
    edge_count: int
    paper_count: int
    concept_count: int
    author_count: int
    research_thread_count: int
    density: float
    top_concepts: list[TopConcept]


class TimelinePaper(BaseModel):
    id: UUID
    title: str
    authors: Optional[str]
    summary_short: Optional[str]
    keywords: list[str]
    reading_status: ReadingStatus
    publication_year: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineYear(BaseModel):
    year: int
    papers: list[TimelinePaper]
    concepts: list[str]


class TimelineResponse(BaseModel):
    years: list[TimelineYear]


class JobStatus(BaseModel):
    job_id: str
    status: str
    paper_id: Optional[UUID] = None
