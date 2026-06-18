import asyncio
import shutil
import subprocess
import tempfile
import time
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
    errors: list[str] = []
    for attempt in range(1, 4):
        attempt_dir = tmp_dir / f"attempt_{attempt}"
        output_dir = attempt_dir / "out"
        profile_dir = attempt_dir / "profile"
        output_dir.mkdir(parents=True, exist_ok=True)
        profile_dir.mkdir(parents=True, exist_ok=True)
        command = [
            libreoffice,
            f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--nolockcheck",
            "--nodefault",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(file_path),
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                timeout=120,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            errors.append(
                _format_office_error(
                    attempt,
                    command,
                    "timeout",
                    _as_text(exc.stdout),
                    _as_text(exc.stderr),
                )
            )
        else:
            pdfs = list(output_dir.glob("*.pdf"))
            if result.returncode == 0 and pdfs:
                return pdfs[0]
            reason = f"exit code {result.returncode}"
            if result.returncode == 0:
                reason = "no PDF produced"
            errors.append(
                _format_office_error(
                    attempt,
                    command,
                    reason,
                    result.stdout,
                    result.stderr,
                )
            )
        if attempt < 3:
            time.sleep(attempt)
    raise RuntimeError("Office conversion failed after 3 attempts:\n" + "\n\n".join(errors))


def _format_office_error(
    attempt: int,
    command: list[str],
    reason: str,
    stdout: str,
    stderr: str,
) -> str:
    return (
        f"attempt {attempt}: {reason}\n"
        f"command: {' '.join(command)}\n"
        f"stdout: {stdout.strip() or '<empty>'}\n"
        f"stderr: {stderr.strip() or '<empty>'}"
    )


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


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
