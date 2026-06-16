from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import (
    CourseCreate,
    CourseDocumentRequest,
    CourseJoinRequest,
    CourseMemberRoleUpdate,
    CourseUpdate,
)
from app.services.audit_service import AuditService
from app.services.courses_service import CoursesService

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("")
async def create_course(
    body: CourseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await CoursesService(db).create(current_user.id, body)
    await AuditService(db).log(
        "course.create",
        user_id=current_user.id,
        resource=f"course:{course['id']}",
        request=request,
        detail={"title": body.title},
    )
    return course


@router.get("")
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).list(current_user.id)


@router.post("/join")
async def join_course(
    body: CourseJoinRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await CoursesService(db).join(current_user.id, body)
    await AuditService(db).log(
        "course.join",
        user_id=current_user.id,
        resource=f"course:{course['id']}",
        request=request,
        detail={"join_code": body.join_code.upper()},
    )
    return course


@router.get("/{course_id}")
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).get(current_user.id, course_id)


@router.put("/{course_id}")
async def update_course(
    course_id: str,
    body: CourseUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await CoursesService(db).update(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.update",
        user_id=current_user.id,
        resource=f"course:{course_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return course


@router.post("/{course_id}/join-code/reset")
async def reset_join_code(
    course_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await CoursesService(db).reset_join_code(current_user.id, course_id)
    await AuditService(db).log(
        "course.join_code_reset",
        user_id=current_user.id,
        resource=f"course:{course_id}",
        request=request,
    )
    return course


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).delete(current_user.id, course_id)
    await AuditService(db).log(
        "course.delete",
        user_id=current_user.id,
        resource=f"course:{course_id}",
        request=request,
    )
    return {"ok": True}


@router.get("/{course_id}/members")
async def course_members(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).members(current_user.id, course_id)


@router.put("/{course_id}/members/{member_user_id}")
async def update_member_role(
    course_id: str,
    member_user_id: str,
    body: CourseMemberRoleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CoursesService(db).update_member_role(
        current_user.id, course_id, member_user_id, body
    )
    await AuditService(db).log(
        "course.member_role_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:user:{member_user_id}",
        request=request,
        detail={"role": body.role},
    )
    return result


@router.delete("/{course_id}/members/{member_user_id}")
async def remove_member(
    course_id: str,
    member_user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).remove_member(current_user.id, course_id, member_user_id)
    await AuditService(db).log(
        "course.member_remove",
        user_id=current_user.id,
        resource=f"course:{course_id}:user:{member_user_id}",
        request=request,
    )
    return {"ok": True}


@router.post("/{course_id}/leave")
async def leave_course(
    course_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).leave(current_user.id, course_id)
    await AuditService(db).log(
        "course.leave",
        user_id=current_user.id,
        resource=f"course:{course_id}",
        request=request,
    )
    return {"ok": True}


@router.get("/{course_id}/progress")
async def course_progress(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).progress(current_user.id, course_id)


@router.post("/{course_id}/documents")
async def add_course_document(
    course_id: str,
    body: CourseDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).add_document(current_user.id, course_id, body)


@router.delete("/{course_id}/documents/{doc_id}")
async def remove_course_document(
    course_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).remove_document(current_user.id, course_id, doc_id)
    return {"ok": True}
