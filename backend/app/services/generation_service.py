import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import GenerationTask, User, now_iso

ACTIVE_STATUSES = {"queued", "running"}
DEFAULT_PROGRESS_TOTALS = {
    "quiz": 3,
    "flashcards": 3,
    "mindmap": 3,
}


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
            progress_current=0,
            progress_total=DEFAULT_PROGRESS_TOTALS.get(kind, 1),
            progress_message="排隊中",
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
        return await self.list_tasks(user_id, kind=kind, active_only=True)

    async def list_tasks(
        self,
        user_id: str,
        kind: str | None = None,
        status_value: str | None = None,
        active_only: bool = True,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        conditions = [
            GenerationTask.user_id == user_id,
        ]
        if active_only:
            conditions.append(GenerationTask.status.in_(list(ACTIVE_STATUSES)))
        elif status_value:
            conditions.append(GenerationTask.status == status_value)
        if kind:
            conditions.append(GenerationTask.kind == kind)
        rows = (
            (
                await self.db.execute(
                    select(GenerationTask)
                    .where(and_(*conditions))
                    .order_by(desc(GenerationTask.updated_at), desc(GenerationTask.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [self._out(row) for row in rows]

    async def admin_tasks(
        self,
        kind: str | None = None,
        status_value: str | None = None,
        active_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        conditions = []
        if active_only:
            conditions.append(GenerationTask.status.in_(list(ACTIVE_STATUSES)))
        elif status_value:
            conditions.append(GenerationTask.status == status_value)
        if kind:
            conditions.append(GenerationTask.kind == kind)
        stmt = (
            select(GenerationTask, User)
            .join(User, User.id == GenerationTask.user_id)
            .order_by(desc(GenerationTask.updated_at), desc(GenerationTask.created_at))
            .limit(limit)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows = (await self.db.execute(stmt)).all()
        return [self._out(task, user=user) for task, user in rows]

    async def mark_running(self, task_id: str) -> GenerationTask | None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return None
        task.status = "running"
        task.progress_message = task.progress_message or "準備生成"
        task.updated_at = now_iso()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_progress(
        self,
        task_id: str,
        current: int,
        total: int | None = None,
        message: str | None = None,
    ) -> GenerationTask | None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return None
        next_total = max(1, total if total is not None else task.progress_total)
        task.progress_total = next_total
        task.progress_current = min(max(0, current), next_total)
        task.progress_message = message
        task.updated_at = now_iso()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_done(
        self,
        task_id: str,
        output: dict[str, Any],
        artifact_id: str | None = None,
    ) -> GenerationTask | None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return None
        task.status = "succeeded"
        task.output_json = json.dumps(output, ensure_ascii=False)
        task.artifact_id = artifact_id
        task.error_msg = None
        task.progress_current = max(1, task.progress_total)
        task.progress_message = "完成"
        task.updated_at = now_iso()
        task.finished_at = now_iso()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_failed(self, task_id: str, error: str) -> GenerationTask | None:
        task = await self._get_task_by_id(task_id)
        if task is None:
            return None
        task.status = "failed"
        task.error_msg = error[:2000]
        task.progress_message = f"失敗：{error[:120]}"
        task.updated_at = now_iso()
        task.finished_at = now_iso()
        await self.db.commit()
        await self.db.refresh(task)
        return task

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

    def _out(self, task: GenerationTask, user: User | None = None) -> dict[str, Any]:
        data = {
            "id": task.id,
            "kind": task.kind,
            "status": task.status,
            "input": json.loads(task.input_json),
            "output": json.loads(task.output_json) if task.output_json else None,
            "error": task.error_msg,
            "artifact_id": task.artifact_id,
            "progress": self.progress_payload(task),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "finished_at": task.finished_at,
        }
        if user is not None:
            data["user"] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        return data

    @staticmethod
    def progress_payload(task: GenerationTask) -> dict[str, Any]:
        total = max(1, task.progress_total or 1)
        current = min(max(0, task.progress_current or 0), total)
        return {
            "current": current,
            "total": total,
            "percent": round((current / total) * 100),
            "message": task.progress_message,
        }
