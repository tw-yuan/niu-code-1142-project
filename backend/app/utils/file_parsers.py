import base64
import io
from pathlib import Path


# ── PDF ──────────────────────────────────────────────────────────────────────

def _pdf_text_per_page(doc) -> list[int]:
    """回傳每頁可萃取的字元數（含空白）"""
    return [len(doc[i].get_text().strip()) for i in range(len(doc))]


def _page_to_jpeg_b64(page, zoom: float = 1.5) -> str:
    import fitz
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    jpeg_bytes = pix.tobytes("jpeg", jpg_quality=80)
    return base64.b64encode(jpeg_bytes).decode()


def parse_pdf_text(file_bytes: bytes) -> str:
    """純文字 PDF：用 pymupdf4llm 輸出 Markdown。"""
    import fitz
    import pymupdf4llm
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return pymupdf4llm.to_markdown(doc)


async def parse_pdf_vision(file_bytes: bytes) -> str:
    """
    掃描版 PDF（或混合型）：
    - 文字充足的頁面用 pymupdf4llm
    - 文字稀少的頁面轉 JPEG 送視覺模型
    每 5 頁一批，避免單次請求過大。
    """
    import fitz
    import pymupdf4llm
    from openai import AsyncOpenAI
    from app.config import settings

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    chars_per_page = _pdf_text_per_page(doc)
    threshold = settings.pdf_text_threshold

    client = AsyncOpenAI(
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key or "none",
    )

    BATCH = 5
    results: list[str] = []

    for batch_start in range(0, len(doc), BATCH):
        batch_end = min(batch_start + BATCH, len(doc))
        image_pages: list[int] = []
        text_pages: list[int] = []

        for i in range(batch_start, batch_end):
            if chars_per_page[i] >= threshold:
                text_pages.append(i)
            else:
                image_pages.append(i)

        # 文字頁 → pymupdf4llm（只處理這批的頁次）
        if text_pages:
            # pymupdf4llm 支援指定頁碼列表
            md = pymupdf4llm.to_markdown(doc, pages=text_pages)
            results.append(md)

        # 圖片頁 → 視覺模型
        if image_pages:
            content: list[dict] = []
            for i in image_pages:
                b64 = _page_to_jpeg_b64(doc[i])
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "high",
                    },
                })
            page_range = f"第 {image_pages[0]+1}～{image_pages[-1]+1} 頁"
            content.append({
                "type": "text",
                "text": (
                    f"以上是 PDF {page_range} 的圖片。"
                    "請將內容完整轉換為繁體中文 Markdown，保留標題層級、粗體、表格。"
                    "直接輸出 Markdown，不需額外說明。"
                ),
            })
            resp = await client.chat.completions.create(
                model=settings.vision_model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
            )
            results.append(resp.choices[0].message.content or "")

    return "\n\n---\n\n".join(filter(None, results))


def _is_scanned_pdf(file_bytes: bytes, threshold: int) -> bool:
    """超過一半頁面文字不足閾值，判定為掃描版。"""
    import fitz
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    if len(doc) == 0:
        return False
    sparse = sum(1 for c in _pdf_text_per_page(doc) if c < threshold)
    return sparse / len(doc) > 0.5


# ── 其他格式 ─────────────────────────────────────────────────────────────────

def parse_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_text(file_bytes: bytes) -> str:
    for enc in ("utf-8", "big5", "gbk", "latin-1"):
        try:
            return file_bytes.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return file_bytes.decode("utf-8", errors="replace")


# ── 統一入口 ─────────────────────────────────────────────────────────────────

async def parse_file_async(filename: str, file_bytes: bytes) -> str:
    """非同步版本，PDF 視情況走視覺路徑。"""
    from app.config import settings
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        if _is_scanned_pdf(file_bytes, settings.pdf_text_threshold):
            return await parse_pdf_vision(file_bytes)
        return parse_pdf_text(file_bytes)
    if ext == ".docx":
        return parse_docx(file_bytes)
    return parse_text(file_bytes)


def count_tokens(text: str) -> int:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
