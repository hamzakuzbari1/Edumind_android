import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LessonStatus(str, enum.Enum):
    draft = "draft"
    processing = "processing"
    processed = "processed"
    error = "error"


class LessonContentType(str, enum.Enum):
    """Legacy display hint — prefer lesson_assets for storage."""
    video = "video"
    pdf = "pdf"
    homework = "homework"
    ai = "ai"


class LessonAssetType(str, enum.Enum):
    video = "video"
    pdf = "pdf"
    homework = "homework"
    audio = "audio"
    image = "image"
    attachment = "attachment"


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "unit_id"],
            ["course_units.course_id", "course_units.id"],
            name="fk_lessons_course_unit",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "unit_id IS NULL OR course_id IS NOT NULL",
            name="ck_lessons_unit_requires_course",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(500), default="درس جديد")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    homework_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[LessonContentType] = mapped_column(
        Enum(LessonContentType), default=LessonContentType.video
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(default=True)
    subject: Mapped[str] = mapped_column(String(120))
    grade: Mapped[str] = mapped_column(String(50))
    status: Mapped[LessonStatus] = mapped_column(default=LessonStatus.draft)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    voice_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    persona_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher: Mapped["User"] = relationship(back_populates="lessons")
    course: Mapped["Course | None"] = relationship(
        back_populates="lessons",
        foreign_keys=[course_id],
    )
    unit: Mapped["CourseUnit | None"] = relationship(
        back_populates="lessons",
        primaryjoin="and_(Lesson.course_id == CourseUnit.course_id, Lesson.unit_id == CourseUnit.id)",
        foreign_keys=[unit_id],
    )
    chunks: Mapped[list["ContentChunk"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    quiz_questions: Mapped[list["QuizQuestion"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    assets: Mapped[list["LessonAsset"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonAsset.sort_order",
    )


class LessonAsset(Base):
    """Multiple assets per lesson (ordered). Media blobs referenced via media_objects."""

    __tablename__ = "lesson_assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    media_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_objects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asset_type: Mapped[LessonAssetType] = mapped_column(
        Enum(
            LessonAssetType,
            name="lessonassettype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(1024))
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lesson: Mapped["Lesson"] = relationship(back_populates="assets")
    media_object: Mapped["MediaObject | None"] = relationship()


class ContentChunk(Base):
    """Text chunks from PDF — no vector column unless ENABLE_PGVECTOR is enabled."""

    __tablename__ = "content_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    lesson: Mapped["Lesson"] = relationship(back_populates="chunks")
