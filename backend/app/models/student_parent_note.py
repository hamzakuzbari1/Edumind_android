"""Structured notes from teachers to parents about a student (with threaded replies)."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParentNoteCategory(str, enum.Enum):
    academic = "academic"
    attendance = "attendance"
    homework = "homework"
    behavior = "behavior"
    achievement = "achievement"
    warning = "warning"


class ParentNoteStatus(str, enum.Enum):
    new = "new"
    read = "read"
    replied = "replied"
    closed = "closed"


class ParentNotePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ParentNoteAuthorRole(str, enum.Enum):
    teacher = "teacher"
    parent = "parent"


class StudentParentNote(Base):
    __tablename__ = "student_parent_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_profile_id: Mapped[int] = mapped_column(
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[ParentNoteCategory] = mapped_column(
        Enum(
            ParentNoteCategory,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        index=True,
    )
    status: Mapped[ParentNoteStatus] = mapped_column(
        Enum(
            ParentNoteStatus,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        default=ParentNoteStatus.new,
        index=True,
    )
    priority: Mapped[ParentNotePriority] = mapped_column(
        Enum(
            ParentNotePriority,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        default=ParentNotePriority.medium,
        index=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StudentParentNoteRead(Base):
    __tablename__ = "student_parent_note_reads"
    __table_args__ = (UniqueConstraint("note_id", "parent_id", name="uq_parent_note_read"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("student_parent_notes.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentParentNoteReply(Base):
    __tablename__ = "student_parent_note_replies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        ForeignKey("student_parent_notes.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author_role: Mapped[ParentNoteAuthorRole] = mapped_column(
        Enum(
            ParentNoteAuthorRole,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        index=True,
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
