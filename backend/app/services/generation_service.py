import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import GenerationTask, now_iso

ACTIVE_STATUSES = {"queued", "running"}


class GenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        user_id: str,
        kind: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = GenerationTask(
            user_id=user_id,
            kind=kind,
            status="queued",
            input_json=json.dumps(payload, ensure_ascii=False),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return self._out(task)

    async def get_task(self, user_id: str, task_id: str) -> dict[str, Any]:
        task = await self._get_task(user_id, task_id)
        return self._out(task)

    async def active_tasks(
        self,
        user_id: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = [
            GenerationTask.user_id == user_id,
            GenerationTask.status.in_(list(ACTIVE_STATUSES)),
        ]
        if kind:
            conditions.append(GenerationTask.kind == kind)
        rows = (
            (
                await self.db.execute(
                    select(GenerationTask)
                    .where(and_(*conditions))
                    .order_by(desc(GenerationTask.created_at))
                )
            )
            .scalars()
            .all()
        )
        return [self._out(row) for row in rows]

    async def mark_running(self, task_id: str) -> GenerationTask | None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return None
        task.status = "running"
        task.updated_at = now_iso()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_done(
        self,
        task_id: str,
        output: dict[str, Any],
        artifact_id: str | None = None,
    ) -> None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return
        task.status = "succeeded"
        task.output_json = json.dumps(output, ensure_ascii=False)
        task.artifact_id = artifact_id
        task.error_msg = None
        task.updated_at = now_iso()
        task.finished_at = now_iso()
        await self.db.commit()

    async def mark_failed(self, task_id: str, error: str) -> None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return
        task.status = "failed"
        task.error_msg = error[:2000]
        task.updated_at = now_iso()
        task.finished_at = now_iso()
        await self.db.commit()

    async def _get_task(self, user_id: str, task_id: str) -> GenerationTask:
        task = (
            await self.db.execute(
                select(GenerationTask).where(
                    and_(GenerationTask.id == task_id, GenerationTask.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    async def _get_task_by_id(self, task_id: str) -> GenerationTask | None:
        return (
            await self.db.execute(select(GenerationTask).where(GenerationTask.id == task_id))
        ).scalar_one_or_none()

    def _out(self, task: GenerationTask) -> dict[str, Any]:
        return {
            "id": task.id,
            "kind": task.kind,
            "status": task.status,
            "input": json.loads(task.input_json),
            "output": json.loads(task.output_json) if task.output_json else None,
            "error": task.error_msg,
            "artifact_id": task.artifact_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "finished_at": task.finished_at,
        }
