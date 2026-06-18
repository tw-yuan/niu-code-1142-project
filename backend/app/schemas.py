from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str
    quota_mb: int
    token_quota: int
    is_active: int
    token_used_this_month: int = 0
    quota_percent: int = 0
    quota_status: Literal["ok", "warning", "exceeded"] = "ok"
    created_at: str

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentOut(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    page_count: int | None
    chunk_count: int | None
    error_msg: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DocumentContentPage(BaseModel):
    page_num: int
    text: str


class DocumentContentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    page_count: int | None
    pages: list[DocumentContentPage]
    content: str


class DocumentUploadResult(BaseModel):
    filename: str
    ok: bool
    document: DocumentOut | None = None
    error: str | None = None


class ChatSessionCreate(BaseModel):
    title: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    course_id: str | None = None
    mode: Literal["enhanced", "strict", "socratic"] = "enhanced"


class ChatSessionOut(BaseModel):
    id: str
    title: str | None
    doc_ids: list[str]
    course_id: str | None = None
    mode: str
    created_at: str
    updated_at: str


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict[str, Any]]
    token_count: int | None
    created_at: str


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut]


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class SummaryRequest(BaseModel):
    doc_id: str
    kind: Literal["full", "bullets"] = "full"
    count: int = Field(default=10, ge=3, le=30)


class QuizStreamRequest(BaseModel):
    doc_ids: list[str] = Field(min_length=1)
    types: list[str] = Field(default_factory=lambda: ["MC"])
    count: int = Field(default=10, ge=1, le=50)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    title: str | None = Field(default=None, min_length=1, max_length=120)
    course_id: str | None = None
    publish_to_course: bool = False
    due_at: str | None = None
    available_from: str | None = None
    answer_visible_at: str | None = None
    attempt_limit: int | None = Field(default=None, ge=1, le=20)


class MindmapRequest(BaseModel):
    doc_id: str
    format: Literal["tree_json", "markdown"] = "tree_json"


class MindmapExpandRequest(BaseModel):
    max_children: int = Field(default=5, ge=1, le=6)


class FlashcardStreamRequest(BaseModel):
    doc_id: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    course_id: str | None = None
    count: int = Field(default=10, ge=1, le=50)


class QuizAttemptRequest(BaseModel):
    answers: dict[str, Any] | list[Any]
    duration_sec: int | None = Field(default=None, ge=0)


class CourseQuizPublishRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    due_at: str | None = None
    available_from: str | None = None
    answer_visible_at: str | None = None
    attempt_limit: int | None = Field(default=None, ge=1, le=20)
    status: Literal["published", "draft"] = "published"


class CourseQuizBatchUpdateRequest(BaseModel):
    course_quiz_ids: list[str] = Field(min_length=1, max_length=100)
    due_at: str | None = None
    available_from: str | None = None
    answer_visible_at: str | None = None
    attempt_limit: int | None = Field(default=None, ge=1, le=20)
    status: Literal["published", "draft"] | None = None


class CourseQuestionReviewUpdate(BaseModel):
    status: Literal["draft", "approved", "rejected", "archived"]
    review_note: str | None = Field(default=None, max_length=1000)


class CourseQuestionReviewBatchUpdate(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=500)
    status: Literal["draft", "approved", "rejected", "archived"]
    review_note: str | None = Field(default=None, max_length=1000)


class WrongbookFlashcardRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)
    quiz_id: str | None = None


class FlashcardCreate(BaseModel):
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)
    doc_id: str | None = None
    source_page: int | None = Field(default=None, ge=1)


class FlashcardUpdate(BaseModel):
    front: str | None = Field(default=None, min_length=1)
    back: str | None = Field(default=None, min_length=1)
    source_page: int | None = Field(default=None, ge=1)


class FlashcardReviewRequest(BaseModel):
    quality: int = Field(ge=0, le=5)


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "teacher", "admin"] = "student"
    quota_mb: int = Field(default=500, ge=1)
    token_quota: int = Field(default=1_000_000, ge=1)
    is_active: int = Field(default=1, ge=0, le=1)


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None
    quota_mb: int | None = Field(default=None, ge=1)
    token_quota: int | None = Field(default=None, ge=1)
    is_active: int | None = Field(default=None, ge=0, le=1)
    role: Literal["student", "teacher", "admin"] | None = None


class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class AdminCourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    is_active: int | None = Field(default=None, ge=0, le=1)


class AdminCourseMemberUpdate(BaseModel):
    user_id: str
    role: Literal["student", "ta", "instructor"] = "student"


class AdminConfigUpdate(BaseModel):
    chat: dict[str, Any] | None = None
    vision: dict[str, Any] | None = None
    embedding: dict[str, Any] | None = None
    cost_per_1k_tokens: dict[str, Any] | None = None
    fallback_providers: dict[str, Any] | None = None


class NoteCreate(BaseModel):
    content: str = Field(min_length=1)
    doc_id: str | None = None
    session_id: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    source_type: Literal["chat", "summary", "manual"] = "manual"


class NoteUpdate(BaseModel):
    content: str = Field(min_length=1)


class GoalCreate(BaseModel):
    doc_id: str
    title: str = Field(min_length=1)
    target_date: str
    focus_hint: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    target_date: str | None = None
    focus_hint: str | None = None
    status: Literal["active", "completed", "abandoned"] | None = None


class CourseCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None


class CourseJoinRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)


class CourseMemberRoleUpdate(BaseModel):
    role: Literal["student", "ta", "instructor"]


class CourseMemberBatchUpdate(BaseModel):
    user_ids: list[str] = Field(min_length=1, max_length=200)
    role: Literal["student", "ta", "instructor"] | None = None
    action: Literal["update_role", "remove"] = "update_role"


class CourseDocumentRequest(BaseModel):
    doc_id: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    version_label: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=1000)


class CourseAssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    kind: Literal["custom", "quiz", "read_summary", "note", "flashcards"] = "custom"
    doc_id: str | None = None
    quiz_id: str | None = None
    due_at: str | None = None
    status: Literal["published", "draft"] = "published"


class CourseAssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    kind: Literal["custom", "quiz", "read_summary", "note", "flashcards"] | None = None
    doc_id: str | None = None
    quiz_id: str | None = None
    due_at: str | None = None
    status: Literal["published", "draft", "archived"] | None = None


class CourseAssignmentSubmit(BaseModel):
    response: str | None = None


class CourseAnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    status: Literal["published", "draft"] = "published"


class CourseAnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1)
    status: Literal["published", "draft", "archived"] | None = None


class CourseHelpRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str | None = None
    session_id: str | None = None
    priority: Literal["low", "normal", "high"] = "normal"


class CourseHelpRequestUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved"] | None = None
    assigned_to: str | None = None
    priority: Literal["low", "normal", "high"] | None = None
    comment: str | None = Field(default=None, max_length=4000)
    internal: bool = False
    resolution_summary: str | None = Field(default=None, max_length=4000)


class CourseHelpRequestCommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    internal: bool = False


class LegalConsentRequest(BaseModel):
    consent_type: Literal["copyright_declaration"]


class DeleteConfirmRequest(BaseModel):
    confirmation_code: str
