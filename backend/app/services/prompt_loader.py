from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str, **kwargs: Any) -> tuple[str, dict[str, Any]]:
    path = PROMPTS_DIR / f"{name}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    system = data["system"].format(**kwargs)
    cfg = {k: v for k, v in data.items() if k not in ("system", "version", "description")}
    return system, cfg


def load_ocr_prompt() -> str:
    system, _ = load_prompt("ocr")
    return system

