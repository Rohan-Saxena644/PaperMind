from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.session import engine
from app.models.models import Base
from app.api.routes import auth, papers, chat, compare

# Create all tables on startup
Base.metadata.create_all(bind=engine)


def ensure_lightweight_schema_updates():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    updates = []
    if "oauth_provider" not in existing_columns:
        updates.append("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)")
    if "oauth_subject" not in existing_columns:
        updates.append("ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255)")

    if not updates:
        return

    with engine.begin() as connection:
        for statement in updates:
            connection.execute(text(statement))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_users_oauth_subject ON users (oauth_subject)"
        ))


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
app.include_router(papers.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(compare.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
