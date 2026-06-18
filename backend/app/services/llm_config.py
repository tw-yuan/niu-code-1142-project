from typing import Any

from app.config import settings


def _timeout(value: float | None, fallback: float) -> float:
    return value if value is not None else fallback


def default_llm_config() -> dict[str, Any]:
    default_timeout = settings.LLM_TIMEOUT_SECONDS
    return {
        "chat": {
            "base_url": settings.LLM_CHAT_BASE_URL or settings.LLM_BASE_URL,
            "api_key": settings.LLM_CHAT_API_KEY or settings.LLM_API_KEY,
            "model": settings.LLM_CHAT_MODEL,
            "max_tokens": 4096,
            "temperature": 0.3,
            "timeout": _timeout(settings.LLM_CHAT_TIMEOUT_SECONDS, default_timeout),
        },
        "vision": {
            "base_url": settings.LLM_VISION_BASE_URL or settings.LLM_BASE_URL,
            "api_key": settings.LLM_VISION_API_KEY or settings.LLM_API_KEY,
            "model": settings.LLM_VISION_MODEL,
            "max_tokens": 2048,
            "timeout": _timeout(settings.LLM_VISION_TIMEOUT_SECONDS, default_timeout),
        },
        "embedding": {
            "base_url": settings.LLM_EMBED_BASE_URL or settings.LLM_BASE_URL,
            "api_key": settings.LLM_EMBED_API_KEY or settings.LLM_API_KEY,
            "model": settings.LLM_EMBED_MODEL,
            "dimensions": 1536,
            "timeout": _timeout(settings.LLM_EMBED_TIMEOUT_SECONDS, default_timeout),
        },
        "cost_per_1k_tokens": {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "text-embedding-3-small": {"input": 0.00002, "output": 0.00002},
        },
        "fallback_providers": {},
    }
