from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import (
    CourseAnnouncementCreate,
    CourseAnnouncementUpdate,
    CourseAssignmentCreate,
    CourseAssignmentSubmit,
    CourseAssignmentUpdate,
    CourseCreate,
    CourseDocumentRequest,
    CourseHelpRequestCreate,
    CourseHelpRequestCommentCreate,
    CourseHelpRequestUpdate,
    CourseJoinRequest,
    CourseMemberBatchUpdate,
    CourseMemberRoleUpdate,
    CourseQuestionReviewBatchUpdate,
    CourseQuestionReviewUpdate,
    CourseQuizBatchUpdateRequest,
    CourseQuizPublishRequest,
    CourseUpdate,
)
from app.services.audit_service import AuditService
from app.services.courses_service import CoursesService
from app.services.learning_service import LearningService

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


@router.get("/dashboard")
async def course_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).dashboard(current_user.id)


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


@router.post("/{course_id}/members/batch")
async def batch_course_members(
    course_id: str,
    body: CourseMemberBatchUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CoursesService(db).batch_members(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.members_batch",
        user_id=current_user.id,
        resource=f"course:{course_id}:members",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return result


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


@router.get("/{course_id}/progress.csv")
async def course_progress_csv(
    course_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    csv_text = await CoursesService(db).progress_csv(current_user.id, course_id)
    await AuditService(db).log(
        "course.progress_export",
        user_id=current_user.id,
        resource=f"course:{course_id}",
        request=request,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="course-{course_id}-progress.csv"'},
    )


@router.get("/{course_id}/quizzes")
async def course_quizzes(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).course_quizzes(current_user.id, course_id)


@router.put("/{course_id}/quizzes/batch")
async def update_course_quizzes_batch(
    course_id: str,
    body: CourseQuizBatchUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = []
    for course_quiz_id in body.course_quiz_ids:
        items.append(
            await LearningService(db).update_course_quiz(
                current_user.id,
                course_id,
                course_quiz_id,
                title=None,
                due_at=body.due_at,
                available_from=body.available_from,
                answer_visible_at=body.answer_visible_at,
                attempt_limit=body.attempt_limit,
                status_value=body.status,
            )
        )
    await AuditService(db).log(
        "course.quizzes_batch_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:quizzes",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return {"ok": True, "updated": len(items), "items": items}


@router.put("/{course_id}/quizzes/{course_quiz_id}")
async def update_course_quiz(
    course_id: str,
    course_quiz_id: str,
    body: CourseQuizPublishRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await LearningService(db).update_course_quiz(
        current_user.id,
        course_id,
        course_quiz_id,
        title=body.title,
        due_at=body.due_at,
        available_from=body.available_from,
        answer_visible_at=body.answer_visible_at,
        attempt_limit=body.attempt_limit,
        status_value=body.status,
    )
    await AuditService(db).log(
        "course.quiz_update",
        user_id=current_user.id,
        resource=f"course_quiz:{course_quiz_id}",
        request=request,
        detail=body.model_dump(),
    )
    return item


@router.get("/{course_id}/question-bank")
async def course_question_bank(
    course_id: str,
    status_filter: str | None = None,
    question_type: str | None = None,
    quiz_id: str | None = None,
    q: str | None = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).question_bank(
        current_user.id,
        course_id,
        status_filter=status_filter,
        question_type=question_type,
        quiz_id=quiz_id,
        q=q,
        include_archived=include_archived,
    )


@router.put("/{course_id}/question-bank/batch")
async def update_course_question_reviews_batch(
    course_id: str,
    body: CourseQuestionReviewBatchUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CoursesService(db).update_question_reviews(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.question_reviews_batch_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:question_bank",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return result


@router.put("/{course_id}/question-bank/{item_id}")
async def update_course_question_review(
    course_id: str,
    item_id: str,
    body: CourseQuestionReviewUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await CoursesService(db).update_question_review(
        current_user.id, course_id, item_id, body
    )
    await AuditService(db).log(
        "course.question_review_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:question:{item_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return item


@router.get("/{course_id}/announcements")
async def course_announcements(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).announcements(current_user.id, course_id)


@router.post("/{course_id}/announcements")
async def create_course_announcement(
    course_id: str,
    body: CourseAnnouncementCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    announcement = await CoursesService(db).create_announcement(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.announcement_create",
        user_id=current_user.id,
        resource=f"course:{course_id}:announcement:{announcement['id']}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return announcement


@router.put("/{course_id}/announcements/{announcement_id}")
async def update_course_announcement(
    course_id: str,
    announcement_id: str,
    body: CourseAnnouncementUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    announcement = await CoursesService(db).update_announcement(
        current_user.id,
        course_id,
        announcement_id,
        body,
    )
    await AuditService(db).log(
        "course.announcement_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:announcement:{announcement_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return announcement


@router.delete("/{course_id}/announcements/{announcement_id}")
async def delete_course_announcement(
    course_id: str,
    announcement_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).delete_announcement(current_user.id, course_id, announcement_id)
    await AuditService(db).log(
        "course.announcement_delete",
        user_id=current_user.id,
        resource=f"course:{course_id}:announcement:{announcement_id}",
        request=request,
    )
    return {"ok": True}


@router.post("/{course_id}/announcements/{announcement_id}/read")
async def mark_course_announcement_read(
    course_id: str,
    announcement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).mark_announcement_read(
        current_user.id, course_id, announcement_id
    )


@router.get("/{course_id}/help-requests")
async def course_help_requests(
    course_id: str,
    status_filter: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    q: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).help_requests(
        current_user.id,
        course_id,
        status_filter=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        q=q,
    )


@router.post("/{course_id}/help-requests")
async def create_course_help_request(
    course_id: str,
    body: CourseHelpRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    help_request = await CoursesService(db).create_help_request(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.help_request_create",
        user_id=current_user.id,
        resource=f"course:{course_id}:help_request:{help_request['id']}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return help_request


@router.post("/{course_id}/help-requests/{request_id}/comments")
async def create_course_help_request_comment(
    course_id: str,
    request_id: str,
    body: CourseHelpRequestCommentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    help_request = await CoursesService(db).create_help_request_comment(
        current_user.id,
        course_id,
        request_id,
        body.message,
        internal=body.internal,
    )
    await AuditService(db).log(
        "course.help_request_comment",
        user_id=current_user.id,
        resource=f"course:{course_id}:help_request:{request_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return help_request


@router.put("/{course_id}/help-requests/{request_id}")
async def update_course_help_request(
    course_id: str,
    request_id: str,
    body: CourseHelpRequestUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    help_request = await CoursesService(db).update_help_request(
        current_user.id,
        course_id,
        request_id,
        body,
    )
    await AuditService(db).log(
        "course.help_request_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:help_request:{request_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return help_request


@router.get("/{course_id}/assignments")
async def course_assignments(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CoursesService(db).assignments(current_user.id, course_id)


@router.post("/{course_id}/assignments")
async def create_course_assignment(
    course_id: str,
    body: CourseAssignmentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assignment = await CoursesService(db).create_assignment(current_user.id, course_id, body)
    await AuditService(db).log(
        "course.assignment_create",
        user_id=current_user.id,
        resource=f"course:{course_id}:assignment:{assignment['id']}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return assignment


@router.put("/{course_id}/assignments/{assignment_id}")
async def update_course_assignment(
    course_id: str,
    assignment_id: str,
    body: CourseAssignmentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assignment = await CoursesService(db).update_assignment(
        current_user.id, course_id, assignment_id, body
    )
    await AuditService(db).log(
        "course.assignment_update",
        user_id=current_user.id,
        resource=f"course:{course_id}:assignment:{assignment_id}",
        request=request,
        detail=body.model_dump(exclude_none=True),
    )
    return assignment


@router.delete("/{course_id}/assignments/{assignment_id}")
async def delete_course_assignment(
    course_id: str,
    assignment_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).delete_assignment(current_user.id, course_id, assignment_id)
    await AuditService(db).log(
        "course.assignment_delete",
        user_id=current_user.id,
        resource=f"course:{course_id}:assignment:{assignment_id}",
        request=request,
    )
    return {"ok": True}


@router.post("/{course_id}/assignments/{assignment_id}/submit")
async def submit_course_assignment(
    course_id: str,
    assignment_id: str,
    body: CourseAssignmentSubmit,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assignment = await CoursesService(db).submit_assignment(
        current_user.id, course_id, assignment_id, body
    )
    await AuditService(db).log(
        "course.assignment_submit",
        user_id=current_user.id,
        resource=f"course:{course_id}:assignment:{assignment_id}",
        request=request,
    )
    return assignment


@router.post("/{course_id}/documents")
async def add_course_document(
    course_id: str,
    body: CourseDocumentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CoursesService(db).add_document(current_user.id, course_id, body)
    doc_ids = body.doc_ids or ([body.doc_id] if body.doc_id else [])
    await AuditService(db).log(
        "course.document_add",
        user_id=current_user.id,
        resource=f"course:{course_id}:documents:{','.join(doc_ids)}",
        request=request,
    )
    return result


@router.delete("/{course_id}/documents/{doc_id}")
async def remove_course_document(
    course_id: str,
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CoursesService(db).remove_document(current_user.id, course_id, doc_id)
    await AuditService(db).log(
        "course.document_remove",
        user_id=current_user.id,
        resource=f"course:{course_id}:document:{doc_id}",
        request=request,
    )
    return {"ok": True}


@router.post("/{course_id}/documents/batch-remove")
async def remove_course_documents_batch(
    course_id: str,
    body: CourseDocumentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_ids = body.doc_ids or ([body.doc_id] if body.doc_id else [])
    result = await CoursesService(db).remove_documents(current_user.id, course_id, doc_ids)
    await AuditService(db).log(
        "course.documents_batch_remove",
        user_id=current_user.id,
        resource=f"course:{course_id}:documents:{','.join(doc_ids)}",
        request=request,
        detail={"doc_ids": doc_ids},
    )
    return result
