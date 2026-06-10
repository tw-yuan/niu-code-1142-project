from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    shared_login_password: str = "student123"
    admin_login_password: str = "admin123"
    cookie_secure: bool = False
    openai_compatible_base_url: str = "https://openrouter.ai/api/v1"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    vision_model: str = "openai/gpt-4o-mini"
    demo_mode: bool = False
    # 每頁文字少於此字數視為掃描版，改用視覺模型
    pdf_text_threshold: int = 80
    max_file_size_mb: int = 20
    session_expire_minutes: int = 1440
    rag_token_threshold: int = 12000
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5
    data_dir: Path = BASE_DIR / "data"
    uploads_dir: Path = BASE_DIR / "data" / "uploads"
    chromadb_dir: Path = BASE_DIR / "data" / "chromadb"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
