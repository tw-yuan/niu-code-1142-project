from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import get_session
from app.models.session import Session


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Session:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登入，請先登入系統")
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=401, detail="登入已過期，請重新登入")
    return session


async def require_student(session: Session = Depends(get_current_session)) -> Session:
    if session.role not in ("student", "admin"):
        raise HTTPException(status_code=403, detail="權限不足")
    return session


async def require_admin(session: Session = Depends(get_current_session)) -> Session:
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理者權限")
    return session
