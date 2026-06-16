import base64
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.models.tables import now_iso
from app.services.llm_client import LLMClient
from app.services.prompt_loader import load_ocr_prompt


async def ocr_document(
    image_paths: list[str],
    cache_path: str,
    user_id: str,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> str:
    cache_file = Path(cache_path)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache = _load_cache(cache_file)
    llm = LLMClient()
    prompt = load_ocr_prompt()
    texts: list[str] = []

    for i, img_path in enumerate(image_paths, 1):
        page_key = str(i)
        if page_key not in cache:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            text = await llm.vision(b64, prompt, user_id=user_id)
            cache[page_key] = {"text": text, "model": "vision", "cached_at": now_iso()}
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

