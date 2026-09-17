from pydantic import BaseModel, Field


class ParentTeacherContactOut(BaseModel):
    teacher_user_id: int
    teacher_profile_id: int
    teacher_name: str
    teacher_image_url: str | None = None
    subject_name: str
    course_id: int
    course_title: str
    student_id: int
    student_name: str
    thread_id: int | None = None
    last_message_preview: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0


class ParentTeachersListOut(BaseModel):
    teachers: list[ParentTeacherContactOut] = Field(default_factory=list)
    total_unread: int = 0


class ParentTeacherChatOpenIn(BaseModel):
    student_id: int
    course_id: int


class ParentTeacherChatOpenOut(BaseModel):
    thread_id: int
    created: bool = False
    teacher_name: str
    subject_name: str
    student_name: str
    context_label: str


class ParentMessagingRecentOut(BaseModel):
    thread_id: int
    teacher_name: str
    teacher_image_url: str | None = None
    student_name: str
    subject_name: str
    last_message_preview: str | None = None
    last_message_at: str | None = None
    unread_count: int = 0


class ParentMessagingSummaryOut(BaseModel):
    total_teachers: int = 0
    total_unread: int = 0
    recent: list[ParentMessagingRecentOut] = Field(default_factory=list)
