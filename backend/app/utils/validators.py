import re

_NICKNAME_RE = re.compile(r"^[\w一-鿿\-\. ]{1,40}$", re.UNICODE)


def validate_nickname(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("暱稱不可空白")
    if len(value) > 40:
        raise ValueError("暱稱長度不可超過 40 字")
    if not _NICKNAME_RE.fullmatch(value):
        raise ValueError("暱稱只允許中英文、數字、底線、連字號、句點與空白")
    return value
