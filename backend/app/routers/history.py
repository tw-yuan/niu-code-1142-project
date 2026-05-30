from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_session
from app.models import User
from app.services.auth_service import AuthResult, ROLE_ADMIN
from app.services.task_service import list_all_tasks, list_user_tasks

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItem(BaseModel):
    id: str
    status: str
    assignment_text: str
    agent_title: str | None
    iterations_used: int
    created_at: datetime
    updated_at: datetime
    owner_display_name: str | None


@router.get("", response_model=list[HistoryItem])
def list_history(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> list[HistoryItem]:
    if auth.role == ROLE_ADMIN:
        tasks = list_all_tasks(db, limit=200)
        owners: dict[str, str | None] = {}
        for t in tasks:
            if t.user_id and t.user_id not in owners:
                user = db.get(User, t.user_id)
                owners[t.user_id] = user.display_name if user else None
        return [
            HistoryItem(
                id=t.id,
                status=t.status,
                assignment_text=t.assignment_text,
                agent_title=t.agent_title,
                iterations_used=t.iterations_used,
                created_at=t.created_at,
                updated_at=t.updated_at,
                owner_display_name=owners.get(t.user_id) if t.user_id else None,
            )
            for t in tasks
        ]

    tasks = list_user_tasks(db, auth.user_id, limit=100)
    return [
        HistoryItem(
            id=t.id,
            status=t.status,
            assignment_text=t.assignment_text,
            agent_title=t.agent_title,
            iterations_used=t.iterations_used,
            created_at=t.created_at,
            updated_at=t.updated_at,
            owner_display_name=auth.display_name,
        )
        for t in tasks
    ]
