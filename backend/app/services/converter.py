import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import settings


async def convert_to_images(file_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    return await asyncio.to_thread(_convert_to_images_sync, file_path, output_dir, dpi)


def _convert_to_images_sync(file_path: str, output_dir: str, dpi: int) -> list[str]:
    path = Path(file_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    if ext == ".md":
        return []
    if ext == ".pdf":
        return _pdf_to_images(path, out, dpi)
    if ext in {".pptx", ".docx"}:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = _office_to_pdf(path, Path(tmp))
            return _pdf_to_images(pdf_path, out, dpi)
    raise ValueError(f"Unsupported file type: {ext}")


def _office_to_pdf(file_path: Path, tmp_dir: Path) -> Path:
    libreoffice = shutil.which("libreoffice")
    if not libreoffice:
        raise RuntimeError("LibreOffice is not installed")
    subprocess.run(
        [
            libreoffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir),
            str(file_path),
        ],
        check=True,
        timeout=120,
        capture_output=True,
    )
    pdfs = list(tmp_dir.glob("*.pdf"))
    if not pdfs:
        raise RuntimeError("Office conversion did not produce a PDF")
    return pdfs[0]


def _pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int) -> list[str]:
    import fitz

    doc = fitz.open(pdf_path)
    image_paths: list[str] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    page_count = min(len(doc), settings.MAX_PAGES_PER_DOC)
    for index in range(page_count):
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        target = output_dir / f"page_{index + 1:03d}.png"
        pix.save(target)
        image_paths.append(str(target))
    doc.close()
    return image_paths
