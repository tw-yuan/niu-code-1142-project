from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str = Field(default="dev-secret-change-me")
    DATA_DIR: str = "./data"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/db/learnai.db"
    CHROMA_PATH: str = "./data/chroma"
    REDIS_URL: str = "redis://redis:6379/0"

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_CHAT_MODEL: str = "gpt-4o-mini"
    LLM_VISION_MODEL: str = "gpt-4o"
    LLM_EMBED_MODEL: str = "text-embedding-3-small"

    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_PAGES_PER_DOC: int = 100
    DEFAULT_USER_QUOTA_MB: int = 500
    DEFAULT_TOKEN_QUOTA: int = 1_000_000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8081"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.ALLOWED_ORIGINS.split(",") if item.strip()]

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR)

    @property
    def upload_path(self) -> Path:
        return self.data_path / "uploads"

    @property
    def db_path(self) -> Path:
        return self.data_path / "db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
