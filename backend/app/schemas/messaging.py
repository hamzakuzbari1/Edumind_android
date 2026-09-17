from pydantic import BaseModel, Field

from app.models.conversation import (
    ConversationParticipantRole,
    ConversationThreadType,
    MessageDeliveryStatus,
    MessageKind,
)


class ConversationParticipantOut(BaseModel):
    user_id: int
    name: str
    role: ConversationParticipantRole
    display_name: str = ""
    role_label: str = ""
    avatar_url: str | None = None


class ConversationMessageOut(BaseModel):
    id: int
    thread_id: int
    sender_id: int
    sender_name: str
    sender_avatar_url: str | None = None
    body: str
    message_kind: MessageKind = MessageKind.text
    attachment_media_id: int | None = None
    attachment_url: str | None = None
    attachment_name: str | None = None
    attachment_mime: str | None = None
    voice_duration_ms: int | None = None
    is_deleted: bool = False
    status: MessageDeliveryStatus
    created_at: str
    is_mine: bool = False


class ConversationOut(BaseModel):
    id: int
    title: str
    thread_type: ConversationThreadType
    conversation_kind_label: str | None = None
    student_id: int
    student_name: str | None = None
    course_id: int | None = None
    course_context_label: str | None = None
    course_subject_name: str | None = None
    include_parent: bool = False
    participants: list[ConversationParticipantOut] = Field(default_factory=list)
    other_participants: list[ConversationParticipantOut] = Field(default_factory=list)
    last_message_preview: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0
    is_pinned: bool = False
    is_archived: bool = False
    created_at: str


class ConversationDetailOut(ConversationOut):
    messages: list[ConversationMessageOut] = Field(default_factory=list)


class ConversationListOut(BaseModel):
    conversations: list[ConversationOut] = Field(default_factory=list)
    total_unread: int = 0


class ConversationCreateIn(BaseModel):
    student_id: int
    parent_ids: list[int] = Field(default_factory=list)
    include_student: bool = True
    title: str | None = Field(default=None, max_length=255)


class MessageCreateIn(BaseModel):
    body: str = Field(default="", max_length=8000)


class ParticipantSettingsIn(BaseModel):
    is_pinned: bool | None = None
    is_archived: bool | None = None


class ThreadParticipantsUpdateIn(BaseModel):
    add_parent_ids: list[int] = Field(default_factory=list)
    remove_parent_ids: list[int] = Field(default_factory=list)
    include_student: bool | None = None


class MessageSearchOut(BaseModel):
    messages: list[ConversationMessageOut] = Field(default_factory=list)
    query: str


class MessagingContactOut(BaseModel):
    user_id: int
    name: str
    role: str
    student_id: int | None = None
    student_name: str | None = None


class MessagingContactsOut(BaseModel):
    students: list[MessagingContactOut] = Field(default_factory=list)
    parents: list[MessagingContactOut] = Field(default_factory=list)


class MessagingSnapshotItemOut(BaseModel):
    title: str
    subtitle: str | None = None
    occurred_at: str | None = None


class MessagingSnapshotOut(BaseModel):
    latest_quiz: MessagingSnapshotItemOut | None = None
    latest_lesson_activity: MessagingSnapshotItemOut | None = None
    latest_teacher_note: MessagingSnapshotItemOut | None = None
    latest_parent_interaction: MessagingSnapshotItemOut | None = None


class MessagingStudentContextOut(BaseModel):
    student_id: int
    full_name: str
    grade: int | None = None
    status: str = "نشط"
    is_active: bool = True
    last_activity_at: str | None = None
    completion_percent: int = 0
    average_quiz_percent: int = 0
    current_streak: int = 0
    enrolled_subjects: list[str] = Field(default_factory=list)
    avatar_url: str | None = None


class MessagingParentContextOut(BaseModel):
    parent_id: int
    parent_name: str
    linked_student_id: int
    linked_student_name: str
    student_grade: int | None = None


class MessagingThreadContextOut(BaseModel):
    thread_id: int
    thread_type: ConversationThreadType
    course_context_label: str | None = None
    student: MessagingStudentContextOut | None = None
    parent: MessagingParentContextOut | None = None
    snapshot: MessagingSnapshotOut | None = None


class CourseMessageTeacherIn(BaseModel):
    include_parent: bool = False


class CourseMessageTeacherOut(BaseModel):
    thread_id: int
    created: bool = False
    course_context_label: str
