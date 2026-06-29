from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine
from app.models.models import Base
from app.api.routes import auth, papers, chat

# Create all tables on startup
Base.metadata.create_all(bind=engine)

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


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
