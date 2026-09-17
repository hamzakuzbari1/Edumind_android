"""Provider-agnostic media metadata — blobs live in S3/R2/MinIO/local disk."""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StorageProvider(str, enum.Enum):
    local = "local"
    s3 = "s3"
    r2 = "r2"
    minio = "minio"
    supabase = "supabase"


class MediaAccessScope(str, enum.Enum):
    private = "private"
    public = "public"
    legacy_public = "legacy_public"


class MediaStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"
    deleted = "deleted"


class MediaObject(Base):
    __tablename__ = "media_objects"
    __table_args__ = (
        CheckConstraint(
            "access_scope IN ('private', 'public', 'legacy_public')",
            name="ck_media_objects_access_scope",
        ),
        CheckConstraint(
            "status IN ('pending', 'ready', 'failed', 'deleted')",
            name="ck_media_objects_status",
        ),
        CheckConstraint(
            "storage_provider <> 'supabase' OR "
            "(storage_bucket IS NOT NULL AND btrim(storage_bucket) <> '')",
            name="ck_media_objects_supabase_bucket",
        ),
        Index(
            "uq_media_objects_canonical_storage_identity",
            "storage_provider",
            "storage_bucket",
            "storage_key",
            unique=True,
            postgresql_where=text(
                "storage_bucket IS NOT NULL "
                "AND btrim(storage_bucket) <> '' "
                "AND btrim(storage_key) <> '' "
                "AND status <> 'deleted'"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    storage_provider: Mapped[str] = mapped_column(String(32), default=StorageProvider.local.value, index=True)
    storage_key: Mapped[str] = mapped_column(String(1024), index=True)
    public_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(128), nullable=True)
    access_scope: Mapped[str] = mapped_column(
        String(24),
        default=MediaAccessScope.legacy_public.value,
        server_default=MediaAccessScope.legacy_public.value,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default=MediaStatus.ready.value,
        server_default=MediaStatus.ready.value,
    )
    checksum_sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    message_attachments: Mapped[list["ConversationMessageAttachment"]] = relationship(
        back_populates="media_object"
    )
