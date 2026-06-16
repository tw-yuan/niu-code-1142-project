import asyncio
import json
from collections import defaultdict
from typing import Any

import redis.asyncio as redis
from fastapi import WebSocket

from app.config import settings


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        self.active[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        self.active[user_id].discard(websocket)
        if not self.active[user_id]:
            self.active.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in self.active.get(user_id, set()):
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(user_id, websocket)


manager = ConnectionManager()


async def push_to_user(user_id: str, message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False)
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.publish(_channel(user_id), payload)
    finally:
        await client.aclose()


async def subscribe_user(user_id: str, websocket: WebSocket) -> None:
    await manager.connect(user_id, websocket)
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(_channel(user_id))
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.01)
    finally:
        manager.disconnect(user_id, websocket)
        await pubsub.unsubscribe(_channel(user_id))
        await pubsub.aclose()
        await client.aclose()


def _channel(user_id: str) -> str:
    return f"user:{user_id}:events"
