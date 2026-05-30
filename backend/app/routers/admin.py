from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError, APITimeoutError, OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_admin
from app.services.auth_service import AuthResult
from app.services.system_setting_service import (
    ALL_TOOL_NAMES,
    DEFAULT_SYSTEM_PROMPT,
    KEY_BASE_URL,
    KEY_DISABLED_TOOLS,
    KEY_MAX_FILE_SIZE_MB,
    KEY_MAX_FILES_PER_TASK,
    KEY_MAX_ITERATIONS,
    KEY_MAX_OUTPUT_TOKENS,
    KEY_MODEL_NAME,
    KEY_SYSTEM_PROMPT,
    KEY_TEMPERATURE,
    NEVER_DISABLE_TOOLS,
    get_runtime_config,
    set_value,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminSettingsView(BaseModel):
    system_prompt: str
    model_name: str
    base_url: str
    temperature: float
    max_output_tokens: int
    max_iterations: int
    max_file_size_mb: int
    max_files_per_task: int
    disabled_tools: list[str]
    available_tools: list[str]
    api_key_configured: bool
    api_key_preview: str | None
    default_system_prompt: str


class AdminSettingsUpdate(BaseModel):
    system_prompt: str | None = Field(default=None, max_length=10_000)
    model_name: str | None = Field(default=None, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=256, le=32768)
    max_iterations: int | None = Field(default=None, ge=1, le=100)
    max_file_size_mb: int | None = Field(default=None, ge=1, le=200)
    max_files_per_task: int | None = Field(default=None, ge=1, le=50)
    disabled_tools: list[str] | None = None


class TestApiBody(BaseModel):
    base_url: str | None = None
    model_name: str | None = None


def _mask_key(key: str) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return key[:4] + "…" + key[-4:]


def _view(db: Session) -> AdminSettingsView:
    cfg = get_runtime_config(db)
    settings = get_settings()
    return AdminSettingsView(
        system_prompt=cfg["system_prompt"],
        model_name=cfg["model_name"],
        base_url=cfg["base_url"],
        temperature=cfg["temperature"],
        max_output_tokens=cfg["max_output_tokens"],
        max_iterations=cfg["max_iterations"],
        max_file_size_mb=cfg["max_file_size_mb"],
        max_files_per_task=cfg["max_files_per_task"],
        disabled_tools=cfg["disabled_tools"],
        available_tools=list(ALL_TOOL_NAMES),
        api_key_configured=bool(settings.openai_compatible_api_key),
        api_key_preview=_mask_key(settings.openai_compatible_api_key),
        default_system_prompt=DEFAULT_SYSTEM_PROMPT,
    )


@router.get("/settings", response_model=AdminSettingsView)
def get_settings_view(
    db: Session = Depends(get_db),
    _: AuthResult = Depends(require_admin),
) -> AdminSettingsView:
    return _view(db)


@router.put("/settings", response_model=AdminSettingsView)
def update_settings(
    body: AdminSettingsUpdate,
    db: Session = Depends(get_db),
    admin: AuthResult = Depends(require_admin),
) -> AdminSettingsView:
    updates: list[tuple[str, str]] = []

    if body.system_prompt is not None:
        prompt = body.system_prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="system_prompt 不可為空白")
        updates.append((KEY_SYSTEM_PROMPT, prompt))

    if body.model_name is not None:
        name = body.model_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="model_name 不可為空白")
        updates.append((KEY_MODEL_NAME, name))

    if body.base_url is not None:
        url = body.base_url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="base_url 需以 http(s):// 開頭")
        updates.append((KEY_BASE_URL, url))

    if body.temperature is not None:
        updates.append((KEY_TEMPERATURE, str(body.temperature)))

    if body.max_output_tokens is not None:
        updates.append((KEY_MAX_OUTPUT_TOKENS, str(body.max_output_tokens)))

    if body.max_iterations is not None:
        updates.append((KEY_MAX_ITERATIONS, str(body.max_iterations)))

    if body.max_file_size_mb is not None:
        updates.append((KEY_MAX_FILE_SIZE_MB, str(body.max_file_size_mb)))

    if body.max_files_per_task is not None:
        updates.append((KEY_MAX_FILES_PER_TASK, str(body.max_files_per_task)))

    if body.disabled_tools is not None:
        invalid = [t for t in body.disabled_tools if t not in ALL_TOOL_NAMES]
        if invalid:
            raise HTTPException(status_code=400, detail=f"未知 tool：{invalid}")
        normalized = [t for t in body.disabled_tools if t not in NEVER_DISABLE_TOOLS]
        updates.append((KEY_DISABLED_TOOLS, ",".join(sorted(set(normalized)))))

    for key, value in updates:
        set_value(db, key, value, admin.user_id)

    db.commit()
    return _view(db)


class TestApiResult(BaseModel):
    ok: bool
    latency_ms: int | None
    model: str
    base_url: str
    tool_calling_supported: bool | None
    detail: str | None


@router.post("/test-api", response_model=TestApiResult)
def test_api(
    body: TestApiBody,
    db: Session = Depends(get_db),
    _: AuthResult = Depends(require_admin),
) -> TestApiResult:
    cfg = get_runtime_config(db)
    settings = get_settings()
    base_url = body.base_url or cfg["base_url"]
    model = body.model_name or cfg["model_name"]

    if not settings.openai_compatible_api_key:
        return TestApiResult(
            ok=False,
            latency_ms=None,
            model=model,
            base_url=base_url,
            tool_calling_supported=None,
            detail="OPENAI_COMPATIBLE_API_KEY 尚未設定（僅限環境變數）",
        )

    client = OpenAI(api_key=settings.openai_compatible_api_key, base_url=base_url, timeout=20)
    t0 = time.perf_counter()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply briefly in Traditional Chinese."},
                {"role": "user", "content": "回 'OK'。"},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "ping",
                        "description": "Test tool for capability detection. Do NOT call.",
                        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                    },
                }
            ],
            tool_choice="auto",
        )
    except APITimeoutError as exc:
        return TestApiResult(
            ok=False,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=model,
            base_url=base_url,
            tool_calling_supported=None,
            detail=f"連線逾時：{exc}",
        )
    except APIError as exc:
        return TestApiResult(
            ok=False,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=model,
            base_url=base_url,
            tool_calling_supported=None,
            detail=f"API 錯誤：{type(exc).__name__}: {exc}"[:300],
        )
    except Exception as exc:  # noqa: BLE001
        return TestApiResult(
            ok=False,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            model=model,
            base_url=base_url,
            tool_calling_supported=None,
            detail=f"未預期錯誤：{type(exc).__name__}: {exc}"[:300],
        )

    elapsed = int((time.perf_counter() - t0) * 1000)
    msg = completion.choices[0].message
    # tool_calling supported if API accepted the tools array without erroring
    tool_calls_present = bool(getattr(msg, "tool_calls", None))
    snippet = (msg.content or "")[:80]
    return TestApiResult(
        ok=True,
        latency_ms=elapsed,
        model=model,
        base_url=base_url,
        tool_calling_supported=True,
        detail=f"模型回應：{snippet}" + (" (含 tool_call)" if tool_calls_present else ""),
    )
