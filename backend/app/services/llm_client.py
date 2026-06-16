import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import AdminConfig, SystemEvent, TokenUsage
from app.services.cost_service import check_quota, estimate_usage_cost, load_cost_config


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
        await check_quota(self.db, user_id)
        providers = await self._get_providers("chat")
        response, provider = await self._call_with_fallback(
            "chat",
            providers,
            lambda cfg: AsyncOpenAI(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                timeout=cfg.get("timeout", 10),
            )
            .chat.completions.create(
                model=cfg["model"],
                messages=messages,
                **self._chat_kwargs(cfg, temperature, max_tokens, response_format),
            ),
        )
        content = response.choices[0].message.content or ""
        tokens = self._usage_tokens(response) or self._estimate_tokens(content)
        input_tokens, output_tokens = self._usage_parts(response)
        if input_tokens == 0 and output_tokens == 0:
            output_tokens = tokens
        await self._record_usage(
            user_id,
            feature,
            tokens,
            provider["model"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider.get("base_url"),
        )
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
        await check_quota(self.db, user_id)
        providers = await self._get_providers("chat")
        stream, provider = await self._call_with_fallback(
            "chat",
            providers,
            lambda cfg: AsyncOpenAI(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                timeout=cfg.get("timeout", 10),
            )
            .chat.completions.create(
                model=cfg["model"],
                messages=messages,
                stream=True,
                **self._chat_kwargs(cfg, temperature, max_tokens, response_format),
            ),
        )

        input_tokens = self._estimate_messages_tokens(messages)
        token_count = 0
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                token_count += self._estimate_tokens(delta)
                yield delta
        await self._record_usage(
            user_id,
            feature,
            input_tokens + token_count,
            provider["model"],
            input_tokens=input_tokens,
            output_tokens=token_count,
            provider=provider.get("base_url"),
        )

    async def vision(
        self,
        image_base64: str,
        prompt: str,
        user_id: str | None = None,
    ) -> str:
        await check_quota(self.db, user_id)
        providers = await self._get_providers("vision")
        response, provider = await self._call_with_fallback(
            "vision",
            providers,
            lambda cfg: AsyncOpenAI(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                timeout=cfg.get("timeout", 10),
            )
            .chat.completions.create(
                model=cfg["model"],
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
                max_tokens=cfg.get("max_tokens", 2048),
            ),
        )
        content = response.choices[0].message.content or ""
        tokens = self._usage_tokens(response) or self._estimate_tokens(content)
        input_tokens, output_tokens = self._usage_parts(response)
        if input_tokens == 0 and output_tokens == 0:
            output_tokens = tokens
        await self._record_usage(
            user_id,
            "ocr",
            tokens,
            provider["model"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            image_count=1,
            provider=provider.get("base_url"),
        )
        return content

    async def embed(
        self,
        texts: list[str],
        user_id: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        await check_quota(self.db, user_id)
        providers = await self._get_providers("embedding")
        response, provider = await self._call_with_fallback(
            "embedding",
            providers,
            lambda cfg: AsyncOpenAI(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                timeout=cfg.get("timeout", 10),
            )
            .embeddings.create(input=texts, model=cfg["model"], **self._embed_kwargs(cfg)),
        )
        tokens = getattr(getattr(response, "usage", None), "total_tokens", None)
        if tokens is None:
            tokens = sum(self._estimate_tokens(text) for text in texts)
        await self._record_usage(
            user_id,
            "embedding",
            tokens,
            provider["model"],
            input_tokens=tokens,
            output_tokens=0,
            provider=provider.get("base_url"),
        )
        return [item.embedding for item in response.data]

    async def _get_config(self, feature: str) -> dict[str, Any]:
        return (await self._load_config())[feature]

    async def _load_config(self) -> dict[str, Any]:
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
        if self.db is not None:
            row = (
                await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
            ).scalar_one_or_none()
            if row:
                saved = json.loads(row.value)
                for key, value in saved.items():
                    if isinstance(value, dict) and key in defaults:
                        defaults[key].update(value)
                    else:
                        defaults[key] = value
        return defaults

    async def _get_providers(self, feature: str) -> list[dict[str, Any]]:
        full_config = await self._load_config()
        config = full_config[feature].copy()
        fallback_config = full_config.get("fallback_providers", {}).get(feature, {})
        providers: list[dict[str, Any]] = []
        primary = fallback_config.get("primary") if isinstance(fallback_config, dict) else None
        if primary:
            merged = config.copy()
            merged.update(primary)
            providers.append(merged)
        else:
            providers.append(config)
        fallback = fallback_config.get("fallback", []) if isinstance(fallback_config, dict) else []
        for item in fallback:
            merged = config.copy()
            merged.update(item)
            providers.append(merged)
        for provider in providers:
            if not provider.get("api_key"):
                raise RuntimeError("LLM_API_KEY is not configured")
        return providers

    async def _call_with_fallback(self, feature: str, providers: list[dict[str, Any]], call_fn):
        last_exc: Exception | None = None
        for index, provider in enumerate(providers):
            try:
                return await self._with_retry(
                    lambda provider=provider: call_fn(provider),
                    retry_fallback_errors=False,
                ), provider
            except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
                last_exc = exc
                await self._record_system_event(
                    "llm_fallback",
                    {
                        "feature": feature,
                        "model": provider.get("model"),
                        "reason": exc.__class__.__name__,
                        "fallback_available": index < len(providers) - 1,
                    },
                )
                if index == len(providers) - 1:
                    raise
                continue
            except HTTPException:
                raise
        assert last_exc is not None
        raise last_exc

    def _embed_kwargs(self, config: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if config.get("dimensions"):
            kwargs["dimensions"] = config["dimensions"]
        return kwargs

    async def _record_system_event(self, event_type: str, detail: dict[str, Any]) -> None:
        if self.db is None:
            return
        self.db.add(SystemEvent(event_type=event_type, severity="warning", detail=json.dumps(detail)))
        await self.db.commit()

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
        input_tokens: int = 0,
        output_tokens: int = 0,
        image_count: int = 0,
        page_count: int = 0,
        provider: str | None = None,
    ) -> None:
        if not user_id or self.db is None:
            return
        cost_config = await load_cost_config(self.db)
        cost, price_snapshot = estimate_usage_cost(input_tokens, output_tokens, model, feature, cost_config)
        self.db.add(
            TokenUsage(
                user_id=user_id,
                feature=feature,
                tokens_used=tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                image_count=image_count,
                page_count=page_count,
                model=model,
                provider=provider,
                request_id=str(uuid.uuid4()),
                unit_price_snapshot=json.dumps(price_snapshot, ensure_ascii=False),
                cost_usd=cost,
            )
        )
        await self.db.commit()

    async def _with_retry(self, factory, retry_fallback_errors: bool = True):
        delay = 1
        last_exc: Exception | None = None
        for _ in range(5):
            try:
                return await factory()
            except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
                last_exc = exc
                if not retry_fallback_errors:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
            except Exception as exc:  # SDK exception classes vary across compatible providers.
                last_exc = exc
                if not retry_fallback_errors:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        assert last_exc is not None
        raise last_exc

    def _usage_tokens(self, response: Any) -> int | None:
        usage = getattr(response, "usage", None)
        return getattr(usage, "total_tokens", None)

    def _usage_parts(self, response: Any) -> tuple[int, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0, 0
        prompt = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0
        completion = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0
        return int(prompt or 0), int(completion or 0)

    def _estimate_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        total = 0
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                total += self._estimate_tokens(content)
            elif isinstance(content, list):
                total += sum(
                    self._estimate_tokens(str(item.get("text", ""))) if isinstance(item, dict) else 1
                    for item in content
                )
            else:
                total += self._estimate_tokens(str(content or ""))
        return max(1, total)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
