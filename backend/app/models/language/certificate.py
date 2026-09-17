from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.language.enums import LanguageLevel


class LanguageCertificate(Base):
    __tablename__ = "language_certificates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), index=True)
    certificate_level: Mapped[LanguageLevel] = mapped_column(
        Enum(LanguageLevel, name="language_level", create_constraint=False, values_callable=lambda e: [x.value for x in e])
    )
    certificate_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    verification_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    certificate_status: Mapped[str] = mapped_column(String(32), default="issued")
    verification_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
