from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Document, Flashcard, LearningArtifact, LearningGoal
from app.schemas import GoalCreate, GoalUpdate


class GoalsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, body: GoalCreate) -> dict[str, Any]:
        await self._get_document(user_id, body.doc_id)
        _parse_date(body.target_date)
        goal = LearningGoal(
            user_id=user_id,
            doc_id=body.doc_id,
            title=body.title,
            target_date=body.target_date,
            focus_hint=body.focus_hint,
        )
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        return self._out(goal)

    async def list(self, user_id: str) -> list[dict[str, Any]]:
        await self._abandon_expired(user_id)
        rows = (
            await self.db.execute(
                select(LearningGoal)
                .where(LearningGoal.user_id == user_id)
                .order_by(desc(LearningGoal.created_at))
            )
        ).scalars().all()
        return [self._out(row) for row in rows]

    async def update(self, user_id: str, goal_id: str, body: GoalUpdate) -> dict[str, Any]:
        goal = await self._get_goal(user_id, goal_id)
        if body.title is not None:
            goal.title = body.title
        if body.target_date is not None:
            _parse_date(body.target_date)
            goal.target_date = body.target_date
        if body.focus_hint is not None:
            goal.focus_hint = body.focus_hint
        if body.status is not None:
            goal.status = body.status
        await self.db.commit()
        return self._out(goal)

    async def delete(self, user_id: str, goal_id: str) -> None:
        goal = await self._get_goal(user_id, goal_id)
        await self.db.delete(goal)
        await self.db.commit()

    async def today(self, user_id: str) -> dict[str, Any]:
        await self._abandon_expired(user_id)
        today_iso = datetime.now(UTC).date().isoformat()
        due_count = (
            await self.db.execute(
                select(func.count(Flashcard.id)).where(
                    and_(Flashcard.user_id == user_id, Flashcard.next_review <= today_iso)
                )
            )
        ).scalar_one()
        tasks: list[dict[str, Any]] = []
        if due_count:
            tasks.append({"type": "flashcard_review", "due_count": due_count})

        goals = (
            await self.db.execute(
                select(LearningGoal)
                .where(and_(LearningGoal.user_id == user_id, LearningGoal.status == "active"))
                .order_by(LearningGoal.target_date)
            )
        ).scalars().all()
        for goal in goals[:5]:
            doc = await self._get_document(user_id, goal.doc_id)
            summary_exists = (
                await self.db.execute(
                    select(LearningArtifact.id).where(
                        and_(
                            LearningArtifact.user_id == user_id,
                            LearningArtifact.doc_id == goal.doc_id,
                            LearningArtifact.kind == "summary",
                        )
                    )
                )
            ).scalar_one_or_none()
            days_left = max(1, (_parse_date(goal.target_date) - date.today()).days + 1)
            daily_chunks = max(1, int((doc.chunk_count or 1) / days_left))
            if not summary_exists:
                tasks.append(
                    {
                        "type": "read_summary",
                        "doc_id": doc.id,
                        "doc_title": doc.filename,
                        "daily_chunk_target": daily_chunks,
                    }
                )
            tasks.append(
                {
                    "type": "take_quiz",
                    "doc_id": doc.id,
                    "suggested_doc_id": doc.id,
                    "suggested_count": min(10, max(3, daily_chunks)),
                    "doc_title": doc.filename,
                }
            )
        return {"tasks": tasks[:8], "streak_days": 0}

    async def _abandon_expired(self, user_id: str) -> None:
        today_value = date.today()
        rows = (
            await self.db.execute(
                select(LearningGoal).where(
                    and_(LearningGoal.user_id == user_id, LearningGoal.status == "active")
                )
            )
        ).scalars().all()
        changed = False
        for goal in rows:
            if _parse_date(goal.target_date) < today_value:
                goal.status = "abandoned"
                changed = True
        if changed:
            await self.db.commit()

    async def _get_goal(self, user_id: str, goal_id: str) -> LearningGoal:
        goal = (
            await self.db.execute(
                select(LearningGoal).where(
                    and_(LearningGoal.id == goal_id, LearningGoal.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if goal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        return goal

    async def _get_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    def _out(self, goal: LearningGoal) -> dict[str, Any]:
        return {
            "id": goal.id,
            "user_id": goal.user_id,
            "doc_id": goal.doc_id,
            "title": goal.title,
            "target_date": goal.target_date,
            "focus_hint": goal.focus_hint,
            "status": goal.status,
            "created_at": goal.created_at,
        }


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target_date") from exc
