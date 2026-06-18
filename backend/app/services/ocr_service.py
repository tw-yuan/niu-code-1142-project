import base64
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import now_iso
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_ocr_prompt


async def ocr_document(
    image_paths: list[str],
    cache_path: str,
    user_id: str,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    db: AsyncSession | None = None,
) -> str:
    cache_file = Path(cache_path)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache = _load_cache(cache_file)
    llm = LLMClient(db)
    provider = await llm.provider_summary("vision")
    prompt = load_ocr_prompt()
    texts: list[str] = []

    for i, img_path in enumerate(image_paths, 1):
        page_key = str(i)
        if page_key not in cache:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            try:
                text = await llm.vision(b64, prompt, user_id=user_id)
            except Exception as exc:
                fallback_text = (
                    "no fallback provider"
                    if provider["fallback_count"] == 0
                    else f"{provider['fallback_count']} fallback provider(s)"
                )
                raise RuntimeError(
                    "OCR failed on "
                    f"page {i}/{len(image_paths)} ({Path(img_path).name}) "
                    f"using vision model {provider['model']} via {provider['base_url']} "
                    f"with timeout {provider['timeout']}s and {fallback_text}: "
                    f"{exc.__class__.__name__}: {exc}"
                ) from exc
            cache[page_key] = {
                "text": text,
                "model": provider["model"] or "vision",
                "provider": provider["base_url"] or "",
                "cached_at": now_iso(),
            }
            _save_cache(cache_file, cache)
        texts.append(f"=== 第 {i} 頁 ===\n{cache[page_key]['text']}")
        if on_progress:
            await on_progress(i, len(image_paths))
    return "\n\n".join(texts)


def _load_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
