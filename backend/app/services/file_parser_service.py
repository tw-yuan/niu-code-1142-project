import io
from pathlib import Path

import chardet


def parse_file(file_path: str, file_type: str) -> tuple[str | None, dict | None, str]:
    try:
        ext = file_type.lower().lstrip(".")
        if ext == "pdf":
            return _parse_pdf(file_path)
        elif ext == "docx":
            return _parse_docx(file_path)
        elif ext in ("txt", "md"):
            return _parse_text(file_path)
        elif ext == "xlsx":
            return _parse_xlsx(file_path)
        elif ext == "csv":
            return _parse_csv(file_path)
        elif ext in ("png", "jpg", "jpeg", "webp"):
            return _parse_image(file_path, ext)
        else:
            return _parse_unknown(file_path, ext)
    except Exception as e:
        return None, None, f"解析失敗：{str(e)}"


def _parse_pdf(file_path: str) -> tuple[str | None, dict | None, str]:
    import fitz
    doc = fitz.open(file_path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    full_text = "\n".join(texts).strip()
    if not full_text:
        return None, None, "PDF 無法擷取文字內容（可能為純圖片 PDF）"
    return full_text, None, "success"


def _parse_docx(file_path: str) -> tuple[str | None, dict | None, str]:
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    tables_data = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
        tables_data.append(rows)
    full_text = "\n".join(paragraphs)
    table_json = tables_data if tables_data else None
    if not full_text and not table_json:
        return None, None, "DOCX 無法擷取內容"
    return full_text or None, table_json, "success"


def _parse_text(file_path: str) -> tuple[str | None, dict | None, str]:
    raw = Path(file_path).read_bytes()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = raw.decode("utf-8", errors="replace")
    text = text.strip()
    if not text:
        return None, None, "檔案內容為空"
    return text, None, "success"


def _parse_xlsx(file_path: str) -> tuple[str | None, dict | None, str]:
    import pandas as pd
    xls = pd.ExcelFile(file_path)
    all_tables = {}
    all_text_parts = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        all_tables[sheet_name] = df.head(100).to_dict(orient="records")
        summary = f"工作表「{sheet_name}」：{len(df)} 列，欄位：{', '.join(str(c) for c in df.columns)}"
        all_text_parts.append(summary)
    full_text = "\n".join(all_text_parts) if all_text_parts else None
    return full_text, all_tables if all_tables else None, "success"


def _parse_csv(file_path: str) -> tuple[str | None, dict | None, str]:
    import pandas as pd
    raw = Path(file_path).read_bytes()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"
    df = pd.read_csv(io.BytesIO(raw), encoding=encoding)
    table_data = {"data": df.head(100).to_dict(orient="records")}
    summary = f"CSV 檔案：{len(df)} 列，欄位：{', '.join(str(c) for c in df.columns)}"
    return summary, table_data, "success"


def _parse_image(file_path: str, ext: str) -> tuple[str | None, dict | None, str]:
    size = Path(file_path).stat().st_size
    summary = f"圖片檔案（{ext.upper()}，{size} bytes）已附加至 AI 請求，可由支援 vision 的模型判讀。"
    return summary, {"image_format": ext, "file_size": size}, "success"


def _parse_unknown(file_path: str, ext: str) -> tuple[str | None, dict | None, str]:
    size = Path(file_path).stat().st_size
    file_format = ext.upper() if ext else "未知格式"
    summary = (
        f"未解析的檔案（{file_format}，{size} bytes）已保留為附件 metadata；"
        "目前僅能提供檔名、格式與大小給 AI 參考。"
    )
    return summary, {"file_format": ext or "unknown", "file_size": size, "parser": "metadata_only"}, "success"
