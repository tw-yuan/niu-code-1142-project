from app.config import MAX_FILE_SIZE_BYTES


def validate_file_extension(_filename: str) -> tuple[bool, str]:
    return True, ""


def validate_file_size(size: int) -> tuple[bool, str]:
    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return False, f"檔案大小超過限制（最大 {max_mb:.0f} MB）"
    return True, ""


def validate_mime_type(_filename: str, _content_type: str | None) -> tuple[bool, str]:
    return True, ""


BLOCKED_KEYWORDS = ["繞過偵測", "規避AI偵測", "不要被老師發現", "繞過抄襲", "bypass detection"]


def check_assignment_text(text: str, has_files: bool = False) -> tuple[bool, str | None]:
    text_lower = text.lower().strip()
    if not has_files and len(text_lower) < 10:
        return False, "未上傳作業檔案時，作業敘述需至少 10 個字"
    for kw in BLOCKED_KEYWORDS:
        if kw in text_lower:
            return True, kw
    return True, None
