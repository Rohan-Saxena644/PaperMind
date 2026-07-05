from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine
from app.models.models import Base
from app.api.routes import auth, papers, chat, compare, graph, timeline, workspaces

# Create all tables on startup
Base.metadata.create_all(bind=engine)


def ensure_lightweight_schema_updates():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "users" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    updates = []
    if "oauth_provider" not in existing_columns:
        updates.append("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)")
    if "oauth_subject" not in existing_columns:
        updates.append("ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255)")

    if updates:
        with engine.begin() as connection:
            for statement in updates:
                connection.execute(text(statement))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_users_oauth_subject ON users (oauth_subject)"
            ))

    if "papers" not in table_names:
        return

    paper_columns = {column["name"] for column in inspector.get_columns("papers")}
    paper_updates = []
    if "workspace_id" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN workspace_id UUID")
    if "reading_status" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN reading_status VARCHAR(20) NOT NULL DEFAULT 'UNREAD'")
    if "personal_notes" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN personal_notes TEXT")
    if "highlights" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN highlights JSON")
    if "publication_year" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN publication_year INTEGER")
    if "source_type" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'PDF'")
    if "source_url" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN source_url VARCHAR(1000)")
    if "processing_attempts" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN processing_attempts INTEGER NOT NULL DEFAULT 0")
    if "next_retry_at" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN next_retry_at TIMESTAMP WITH TIME ZONE")
    if "failed_at" not in paper_columns:
        paper_updates.append("ALTER TABLE papers ADD COLUMN failed_at TIMESTAMP WITH TIME ZONE")

    if paper_updates:
        with engine.begin() as connection:
            for statement in paper_updates:
                connection.execute(text(statement))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_papers_workspace_id ON papers (workspace_id)"
            ))

    chat_columns = {column["name"] for column in inspector.get_columns("chats")} if "chats" in table_names else set()
    flashcard_review_columns = (
        {column["name"] for column in inspector.get_columns("flashcard_reviews")}
        if "flashcard_reviews" in table_names else set()
    )
    extra_updates = []
    if "chats" in table_names and "workspace_id" not in chat_columns:
        extra_updates.append("ALTER TABLE chats ADD COLUMN workspace_id UUID")
    if "flashcard_reviews" in table_names and "workspace_id" not in flashcard_review_columns:
        extra_updates.append("ALTER TABLE flashcard_reviews ADD COLUMN workspace_id UUID")

    if extra_updates:
        with engine.begin() as connection:
            for statement in extra_updates:
                connection.execute(text(statement))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_chats_workspace_id ON chats (workspace_id)"
            ))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_flashcard_reviews_workspace_id ON flashcard_reviews (workspace_id)"
            ))

    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO workspaces (id, user_id, name, description, is_default, created_at)
            SELECT gen_random_uuid(), users.id, 'My Research', NULL, TRUE, NOW()
            FROM users
            WHERE NOT EXISTS (
                SELECT 1 FROM workspaces WHERE workspaces.user_id = users.id
            )
        """))
        connection.execute(text("""
            UPDATE papers
            SET workspace_id = workspaces.id
            FROM workspaces
            WHERE papers.user_id = workspaces.user_id
              AND workspaces.is_default = TRUE
              AND papers.workspace_id IS NULL
        """))
        if "chats" in table_names:
            connection.execute(text("""
                UPDATE chats
                SET workspace_id = workspaces.id
                FROM workspaces
                WHERE chats.user_id = workspaces.user_id
                  AND workspaces.is_default = TRUE
                  AND chats.workspace_id IS NULL
            """))
        if "flashcard_reviews" in table_names:
            connection.execute(text("""
                UPDATE flashcard_reviews
                SET workspace_id = papers.workspace_id
                FROM papers
                WHERE flashcard_reviews.paper_id = papers.id
                  AND flashcard_reviews.workspace_id IS NULL
            """))


ensure_lightweight_schema_updates()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered research paper workspace",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(compare.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(timeline.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
