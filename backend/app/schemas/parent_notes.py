from pydantic import BaseModel, Field

from app.models.student_parent_note import (
    ParentNoteCategory,
    ParentNotePriority,
    ParentNoteStatus,
    ParentNoteAuthorRole,
)


class ParentNoteReadByOut(BaseModel):
    parent_id: int
    parent_name: str
    read_at: str


class ParentNoteReplyOut(BaseModel):
    id: int
    note_id: int
    author_id: int
    author_name: str
    author_role: ParentNoteAuthorRole
    body: str
    created_at: str
    updated_at: str
    can_edit: bool = False
    can_delete: bool = False


class ParentNoteReplyCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ParentNoteReplyUpdateIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ParentNoteOut(BaseModel):
    id: int
    student_id: int
    student_name: str | None = None
    title: str
    description: str
    category: ParentNoteCategory
    category_label_ar: str
    status: ParentNoteStatus
    status_label_ar: str
    priority: ParentNotePriority
    priority_label_ar: str
    created_by_name: str
    created_by_teacher_profile_id: int
    created_at: str
    updated_at: str
    is_read_by_viewer: bool = False
    read_at_by_viewer: str | None = None
    parents_linked: int = 0
    parents_read_count: int = 0
    read_by: list[ParentNoteReadByOut] = Field(default_factory=list)
    reply_count: int = 0
    replies: list[ParentNoteReplyOut] = Field(default_factory=list)
    is_closed: bool = False
    closed_at: str | None = None
    can_edit: bool = False
    can_delete: bool = False
    can_reply: bool = True
    can_close: bool = False


class ParentNoteListOut(BaseModel):
    notes: list[ParentNoteOut] = Field(default_factory=list)
    total: int = 0
    unread_count: int = 0


class ParentNoteCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    category: ParentNoteCategory
    priority: ParentNotePriority = ParentNotePriority.medium


class ParentNoteUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    category: ParentNoteCategory | None = None
    priority: ParentNotePriority | None = None


class ParentNoteCategoryOptionOut(BaseModel):
    value: ParentNoteCategory
    label_ar: str


class ParentNoteStatusOptionOut(BaseModel):
    value: ParentNoteStatus
    label_ar: str


class ParentNotePriorityOptionOut(BaseModel):
    value: ParentNotePriority
    label_ar: str
