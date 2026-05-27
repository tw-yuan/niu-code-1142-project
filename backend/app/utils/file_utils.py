import uuid
from pathlib import Path

from app.config import UPLOAD_DIR, GENERATED_FILE_DIR


def get_upload_path(task_id: str, original_filename: str) -> Path:
    ext = Path(original_filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / task_id / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_generated_path(task_id: str, fmt: str) -> Path:
    filename = f"output.{fmt}"
    path = GENERATED_FILE_DIR / task_id / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
