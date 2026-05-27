import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me")
SHARED_LOGIN_PASSWORD = os.getenv("SHARED_LOGIN_PASSWORD", "student123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

OPENAI_COMPATIBLE_BASE_URL = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_COMPATIBLE_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
OPENAI_COMPATIBLE_MODEL = os.getenv("OPENAI_COMPATIBLE_MODEL", "openai/gpt-4o-mini")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app.db'}")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
GENERATED_FILE_DIR = Path(os.getenv("GENERATED_FILE_DIR", str(BASE_DIR / "data" / "generated")))

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

SESSION_EXPIRE_MINUTES = int(os.getenv("SESSION_EXPIRE_MINUTES", "480"))
