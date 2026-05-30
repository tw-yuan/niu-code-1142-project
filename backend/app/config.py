from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_secret_key: str = "change-me-in-env"
    shared_login_password: str = "student123"
    admin_password: str = "admin123"

    openai_compatible_base_url: str = "https://openrouter.ai/api/v1"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = "openai/gpt-5-mini"

    database_url: str = "sqlite:////data/db/app.db"
    upload_dir: str = "/data/uploads"
    generated_file_dir: str = "/data/generated"

    max_file_size_mb: int = 10
    session_expire_minutes: int = 60 * 24

    frontend_dist_dir: str = "/app/frontend_dist"

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def generated_path(self) -> Path:
        return Path(self.generated_file_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
