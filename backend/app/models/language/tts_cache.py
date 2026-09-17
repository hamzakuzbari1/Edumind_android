"""Cache of generated lesson audio so we synthesize each (item, voice) only once."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LanguageLessonAudioCache(Base):
    __tablename__ = "language_lesson_audio_cache"
    __table_args__ = (
        UniqueConstraint("content_item_id", "voice_source", "teacher_id", name="uq_language_lesson_audio_cache"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_item_id: Mapped[int] = mapped_column(
        ForeignKey("language_content_items.id", ondelete="CASCADE"), index=True
    )
    voice_source: Mapped[str] = mapped_column(String(32))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    audio_storage_key: Mapped[str] = mapped_column(String(1024))
    public_url: Mapped[str] = mapped_column(String(2048))
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
