from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import CourseCreate, CourseDocumentRequest, CourseJoinRequest
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
