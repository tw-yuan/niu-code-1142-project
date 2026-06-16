from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_admin
from app.models.tables import User
from app.schemas import (
    AdminConfigUpdate,
    AdminCourseMemberUpdate,
    AdminCourseUpdate,
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserUpdate,
    CourseDocumentRequest,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    q: str | None = None,
    role: str | None = Query(default=None, pattern="^(student|teacher|admin)$"),
    is_active: int | None = Query(default=None, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).list_users(q, role, is_active, limit, offset)


@router.post("/users")
async def create_user(
    body: AdminUserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).create_user(body, actor_id=current_user.id)


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).user_detail(user_id)


@router.get("/users/{user_id}/usage")
async def user_usage(
    user_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).user_usage(user_id)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_user(user_id, body, actor_id=current_user.id)


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    body: AdminPasswordReset,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).reset_user_password(user_id, body, actor_id=current_user.id)


@router.get("/stats")
async def stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).stats()


@router.get("/config")
async def get_config(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).get_llm_config()


@router.put("/config")
async def update_config(
    body: AdminConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_llm_config(body, actor_id=current_user.id)


@router.get("/stats/cost")
async def cost_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).cost_stats()


@router.get("/stats/reliability")
async def reliability_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).reliability_stats()


@router.get("/audit-logs")
async def audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).audit_logs(user_id, action, from_date, to_date, limit, offset)


@router.get("/deletions")
async def deletion_status(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).deletion_status()


@router.get("/users/{user_id}/deletion-status")
async def user_deletion_status(
    user_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).user_deletion_status(user_id)


@router.post("/users/{user_id}/force-purge")
async def force_purge_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).force_purge_user(user_id, current_user.id)


@router.get("/documents")
async def list_documents(
    q: str | None = None,
    user_id: str | None = None,
    status_value: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).list_documents(q, user_id, status_value, limit, offset)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).delete_document(doc_id, actor_id=current_user.id, request=request)


@router.get("/chat-sessions")
async def list_chat_sessions(
    q: str | None = None,
    user_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).list_chat_sessions(q, user_id, limit, offset)


@router.get("/chat-sessions/{session_id}")
async def chat_session_detail(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).chat_session_detail(
        session_id, actor_id=current_user.id, request=request
    )


@router.delete("/chat-sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).delete_chat_session(
        session_id, actor_id=current_user.id, request=request
    )


@router.get("/courses")
async def list_courses(
    q: str | None = None,
    owner_id: str | None = None,
    is_active: int | None = Query(default=None, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).list_courses(q, owner_id, is_active, limit, offset)


@router.get("/courses/{course_id}")
async def course_detail(
    course_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).course_detail(course_id)


@router.put("/courses/{course_id}")
async def update_course(
    course_id: str,
    body: AdminCourseUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_course(
        course_id, body, actor_id=current_user.id, request=request
    )


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).delete_course(course_id, actor_id=current_user.id, request=request)


@router.put("/courses/{course_id}/members")
async def upsert_course_member(
    course_id: str,
    body: AdminCourseMemberUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).upsert_course_member(
        course_id, body, actor_id=current_user.id, request=request
    )


@router.delete("/courses/{course_id}/members/{user_id}")
async def remove_course_member(
    course_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).remove_course_member(
        course_id, user_id, actor_id=current_user.id, request=request
    )


@router.post("/courses/{course_id}/documents")
async def add_course_document(
    course_id: str,
    body: CourseDocumentRequest,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).add_course_document(
        course_id, body, actor_id=current_user.id, request=request
    )


@router.delete("/courses/{course_id}/documents/{doc_id}")
async def remove_course_document(
    course_id: str,
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).remove_course_document(
        course_id, doc_id, actor_id=current_user.id, request=request
    )
