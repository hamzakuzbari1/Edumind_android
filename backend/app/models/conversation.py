"""Internal platform messaging (teacher / student / parent)."""

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ConversationThreadType(str, enum.Enum):
    teacher_student = "teacher_student"
    teacher_parent = "teacher_parent"
    teacher_student_parent = "teacher_student_parent"


class ConversationParticipantRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"
    parent = "parent"


class MessageDeliveryStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"


class MessageKind(str, enum.Enum):
    text = "text"
    image = "image"
    pdf = "pdf"
    document = "document"
    voice = "voice"


class AttachmentKind(str, enum.Enum):
    file = "file"
    image = "image"
    audio = "audio"
    video = "video"
    document = "document"


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_type: Mapped[ConversationThreadType] = mapped_column(
        Enum(
            ConversationThreadType,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        index=True,
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    teacher_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    include_parent: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ConversationParticipantRole] = mapped_column(
        Enum(
            ConversationParticipantRole,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(default=False, server_default="false")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    message_kind: Mapped[str] = mapped_column(String(24), default=MessageKind.text.value)
    attachment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voice_duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MessageDeliveryStatus] = mapped_column(
        Enum(
            MessageDeliveryStatus,
            native_enum=False,
            values_callable=lambda cls: [m.value for m in cls],
        ),
        default=MessageDeliveryStatus.sent,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    attachments: Mapped[list["ConversationMessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ConversationMessageAttachment.sort_order, ConversationMessageAttachment.id",
    )


class ConversationMessageAttachment(Base):
    __tablename__ = "conversation_message_attachments"
    __table_args__ = (
        CheckConstraint(
            "attachment_kind IN ('file', 'image', 'audio', 'video', 'document')",
            name="ck_conversation_message_attachments_kind",
        ),
        UniqueConstraint(
            "message_id",
            "media_object_id",
            name="uq_conversation_message_attachment_message_media",
        ),
        Index(
            "ix_conversation_message_attachments_message_order",
            "message_id",
            "sort_order",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey(
            "conversation_messages.id",
            name="fk_conversation_message_attachments_message_id_messages",
            ondelete="CASCADE",
        )
    )
    media_object_id: Mapped[int] = mapped_column(
        ForeignKey(
            "media_objects.id",
            name="fk_conversation_message_attachments_media_object",
            ondelete="RESTRICT",
        )
    )
    attachment_kind: Mapped[str] = mapped_column(String(24))
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    voice_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    message: Mapped["ConversationMessage"] = relationship(back_populates="attachments")
    media_object: Mapped["MediaObject"] = relationship(back_populates="message_attachments")


class ConversationMessageRead(Base):
    """Per-recipient read receipt."""

    __tablename__ = "conversation_message_reads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_messages.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
