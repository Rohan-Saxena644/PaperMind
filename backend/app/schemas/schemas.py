from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.models import PaperStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str


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


# ── Papers ────────────────────────────────────────────────────────────────────

class PaperOut(BaseModel):
    id: UUID
    title: str
    authors: Optional[str]
    abstract: Optional[str]
    file_name: str
    file_size: int
    status: PaperStatus
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
    title: str
    authors: Optional[str]
    status: PaperStatus
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
    title: str
    created_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}


class ChatAskRequest(BaseModel):
    question: str
    paper_ids: Optional[list[UUID]] = None  # None = search all papers


# ── Worker job ────────────────────────────────────────────────────────────────

class JobStatus(BaseModel):
    job_id: str
    status: str
    paper_id: Optional[UUID] = None
