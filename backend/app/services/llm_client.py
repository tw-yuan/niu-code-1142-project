import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import AdminConfig, TokenUsage


class LLMClient:
    """
    OpenAI-compatible LLM 統一入口。
    所有 Chat / Vision / Embedding 呼叫必須經過此類別。
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        feature: str = "chat",
        user_id: str | None = None,
    ) -> str:
        config = await self._get_config("chat")
        client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
        kwargs = self._chat_kwargs(config, temperature, max_tokens, response_format)
        response = await self._with_retry(
            lambda: client.chat.completions.create(model=config["model"], messages=messages, **kwargs)
        )
        content = response.choices[0].message.content or ""
        tokens = self._usage_tokens(response) or self._estimate_tokens(content)
        await self._record_usage(user_id, feature, tokens, config["model"])
        return content

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        feature: str = "chat",
        user_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        config = await self._get_config("chat")
        client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
        kwargs = self._chat_kwargs(config, temperature, max_tokens, response_format)
        stream = await self._with_retry(
            lambda: client.chat.completions.create(
                model=config["model"], messages=messages, stream=True, **kwargs
            )
        )

        token_count = 0
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                token_count += self._estimate_tokens(delta)
                yield delta
        await self._record_usage(user_id, feature, token_count, config["model"])

    async def vision(
        self,
        image_base64: str,
        prompt: str,
        user_id: str | None = None,
    ) -> str:
        config = await self._get_config("vision")
        client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
        response = await self._with_retry(
            lambda: client.chat.completions.create(
                model=config["model"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                            },
                        ],
                    }
                ],
                max_tokens=config.get("max_tokens", 2048),
            )
        )
        content = response.choices[0].message.content or ""
        tokens = self._usage_tokens(response) or self._estimate_tokens(content)
        await self._record_usage(user_id, "vision_ocr", tokens, config["model"])
        return content

    async def embed(
        self,
        texts: list[str],
        user_id: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        config = await self._get_config("embedding")
        client = AsyncOpenAI(base_url=config["base_url"], api_key=config["api_key"])
        kwargs: dict[str, Any] = {}
        if config.get("dimensions"):
            kwargs["dimensions"] = config["dimensions"]
        response = await self._with_retry(
            lambda: client.embeddings.create(input=texts, model=config["model"], **kwargs)
        )
        tokens = getattr(getattr(response, "usage", None), "total_tokens", None)
        if tokens is None:
            tokens = sum(self._estimate_tokens(text) for text in texts)
        await self._record_usage(user_id, "embedding", tokens, config["model"])
        return [item.embedding for item in response.data]

    async def _get_config(self, feature: str) -> dict[str, Any]:
        defaults = {
            "chat": {
                "base_url": settings.LLM_BASE_URL,
                "api_key": settings.LLM_API_KEY,
                "model": settings.LLM_CHAT_MODEL,
                "max_tokens": 4096,
                "temperature": 0.3,
            },
            "vision": {
                "base_url": settings.LLM_BASE_URL,
                "api_key": settings.LLM_API_KEY,
                "model": settings.LLM_VISION_MODEL,
                "max_tokens": 2048,
            },
            "embedding": {
                "base_url": settings.LLM_BASE_URL,
                "api_key": settings.LLM_API_KEY,
                "model": settings.LLM_EMBED_MODEL,
                "dimensions": 1536,
            },
        }
        config = defaults[feature].copy()
        if self.db is not None:
            row = (
                await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
            ).scalar_one_or_none()
            if row:
                saved = json.loads(row.value)
                config.update(saved.get(feature, {}))
        if not config.get("api_key"):
            raise RuntimeError("LLM_API_KEY is not configured")
        return config

    def _chat_kwargs(
        self,
        config: dict[str, Any],
        temperature: float | None,
        max_tokens: int | None,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "temperature": temperature if temperature is not None else config.get("temperature", 0.3),
            "max_tokens": max_tokens if max_tokens is not None else config.get("max_tokens", 4096),
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        return kwargs

    async def _record_usage(
        self,
        user_id: str | None,
        feature: str,
        tokens: int,
        model: str,
    ) -> None:
        if not user_id or self.db is None:
            return
        self.db.add(TokenUsage(user_id=user_id, feature=feature, tokens_used=tokens, model=model))
        await self.db.commit()

    async def _with_retry(self, factory):
        delay = 1
        last_exc: Exception | None = None
        for _ in range(5):
            try:
                return await factory()
            except Exception as exc:  # SDK exception classes vary across compatible providers.
                last_exc = exc
                await asyncio.sleep(delay)
                delay *= 2
        assert last_exc is not None
        raise last_exc

    def _usage_tokens(self, response: Any) -> int | None:
        usage = getattr(response, "usage", None)
        return getattr(usage, "total_tokens", None)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

