"""Versioned legal consent records for teacher voice processing."""

import enum
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VoiceConsentStatus(str, enum.Enum):
    granted = "granted"
    revoked = "revoked"


class VoiceConsentSource(str, enum.Enum):
    web = "web"
    android = "android"
    admin_recorded = "admin_recorded"
    imported = "import"


class VoiceConsentPolicy(Base):
    __tablename__ = "voice_consent_policies"
    __table_args__ = (
        UniqueConstraint(
            "policy_key",
            "version",
            name="uq_voice_consent_policies_key_version",
        ),
        Index(
            "ix_voice_consent_policies_key_effective",
            "policy_key",
            "effective_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_key: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    policy_text: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(CHAR(64))
    policy_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    consents: Mapped[list["TeacherVoiceConsent"]] = relationship(
        back_populates="policy"
    )


class TeacherVoiceConsent(Base):
    __tablename__ = "teacher_voice_consents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('granted', 'revoked')",
            name="ck_teacher_voice_consents_status",
        ),
        CheckConstraint(
            "source IN ('web', 'android', 'admin_recorded', 'import')",
            name="ck_teacher_voice_consents_source",
        ),
        CheckConstraint(
            "(status = 'granted' AND revoked_at IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL)",
            name="ck_teacher_voice_consents_state",
        ),
        Index(
            "uq_teacher_voice_consents_active_teacher_profile",
            "teacher_profile_id",
            unique=True,
            postgresql_where=text("status = 'granted'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teacher_profiles.id",
            name="fk_teacher_voice_consents_teacher_profile",
            ondelete="CASCADE",
        ),
        index=True,
    )
    consenting_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_teacher_voice_consents_consenting_user",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    policy_id: Mapped[int] = mapped_column(
        ForeignKey(
            "voice_consent_policies.id",
            name="fk_teacher_voice_consents_policy",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), index=True)
    source: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_teacher_voice_consents_revoked_by_user",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher_profile: Mapped["TeacherProfile"] = relationship(
        back_populates="voice_consents"
    )
    consenting_user: Mapped["User"] = relationship(
        foreign_keys=[consenting_user_id]
    )
    policy: Mapped["VoiceConsentPolicy"] = relationship(back_populates="consents")
    revoked_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[revoked_by_user_id]
    )
    voice_samples: Mapped[list["TeacherVoiceSample"]] = relationship(
        back_populates="voice_consent"
    )
