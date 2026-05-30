import re
from pathlib import Path

_SAFE_NAME_RE = re.compile(r"[^\w\-\.一-鿿]+", re.UNICODE)


def sanitize_filename(name: str, default: str = "file") -> str:
    """Strip path separators and unsafe chars from a filename."""
    name = (name or "").strip()
    if not name:
        return default
    name = name.replace("\\", "/").split("/")[-1]
    name = name.replace("..", "_")
    cleaned = _SAFE_NAME_RE.sub("_", name)
    cleaned = cleaned.strip("._") or default
    if len(cleaned) > 100:
        stem = Path(cleaned).stem[:80]
        suffix = Path(cleaned).suffix[:20]
        cleaned = f"{stem}{suffix}"
    return cleaned


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext in {"pdf", "docx", "txt", "md", "xlsx", "csv", "png", "jpg", "jpeg", "webp"}:
        if ext == "jpeg":
            return "jpg"
        return ext
    return "unknown"


def make_task_upload_dir(base_dir: Path, task_id: str) -> Path:
    target = base_dir / task_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def make_task_generated_dir(base_dir: Path, task_id: str) -> Path:
    target = base_dir / task_id
    target.mkdir(parents=True, exist_ok=True)
    return target


def unique_storage_path(directory: Path, filename: str) -> Path:
    """Avoid clobbering existing files by appending -2, -3, ..."""
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    i = 2
    while True:
        candidate = directory / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1
