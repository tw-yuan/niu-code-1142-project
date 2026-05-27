import mimetypes
from pathlib import Path

from app.config import ALLOWED_UPLOAD_EXTENSIONS, MAX_FILE_SIZE_BYTES


def validate_file_extension(filename: str) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return False, f"不支援的檔案格式：{ext}，支援格式：{', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
    return True, ""


def validate_file_size(size: int) -> tuple[bool, str]:
    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return False, f"檔案大小超過限制（最大 {max_mb:.0f} MB）"
    return True, ""


def validate_mime_type(filename: str, content_type: str | None) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    guessed_type, _ = mimetypes.guess_type(filename)
    if content_type in ("application/octet-stream", None):
        content_type = guessed_type
    ext_to_expected = {
        ".pdf": {"application/pdf"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ".txt": {"text/plain"},
        ".md": {"text/plain", "text/markdown", "text/x-markdown"},
        ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ".csv": {"text/csv", "text/plain", "application/csv"},
    }
    expected = ext_to_expected.get(ext, set())
    if expected and content_type and content_type not in expected:
        return False, f"檔案 MIME type 不符合預期（{content_type}），請確認檔案格式"
    return True, ""


BLOCKED_KEYWORDS = ["幫我直接提交", "繞過偵測", "規避AI偵測", "不要被老師發現", "繞過抄襲", "bypass detection"]


def check_assignment_text(text: str) -> tuple[bool, str | None]:
    text_lower = text.lower().strip()
    if len(text_lower) < 10:
        return False, "作業敘述需至少 10 個字"
    for kw in BLOCKED_KEYWORDS:
        if kw in text_lower:
            return True, kw
    return True, None
