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


class MindmapRequest(BaseModel):
    doc_id: str


class FlashcardStreamRequest(BaseModel):
    doc_id: str
    count: int = Field(default=10, ge=1, le=50)


class QuizAttemptRequest(BaseModel):
    answers: dict[str, Any] | list[Any]
    duration_sec: int | None = Field(default=None, ge=0)


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
    role: Literal["student", "admin"] = "student"
    quota_mb: int = Field(default=500, ge=1)
    token_quota: int = Field(default=1_000_000, ge=1)
    is_active: int = Field(default=1, ge=0, le=1)


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None
    quota_mb: int | None = Field(default=None, ge=1)
    token_quota: int | None = Field(default=None, ge=1)
    is_active: int | None = Field(default=None, ge=0, le=1)
    role: Literal["student", "admin"] | None = None


class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


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


class CourseJoinRequest(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)


class CourseDocumentRequest(BaseModel):
    doc_id: str


class LegalConsentRequest(BaseModel):
    consent_type: Literal["copyright_declaration"]


class DeleteConfirmRequest(BaseModel):
    confirmation_code: str
