from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "PaperMind"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://papermind:papermind@localhost:5432/papermind"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papermind_papers"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "text-embedding-004"

    # Storage
    storage_backend: str = "local"
    local_storage_path: str = "/app/uploads"

    # Auth
    access_token_expire_minutes: int = 10080  # 7 days

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
