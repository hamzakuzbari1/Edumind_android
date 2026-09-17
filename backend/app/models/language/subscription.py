from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base
from app.models.enrollment import PaymentStatus

if TYPE_CHECKING:
    from app.models.language.catalog import LanguageProduct


class LanguageSubscription(Base):
    __tablename__ = "language_subscriptions"
    __table_args__ = (UniqueConstraint("student_id", "product_id", name="uq_language_subscription_student_product"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("language_products.id", ondelete="CASCADE"), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus", create_constraint=False),
        default=PaymentStatus.pending,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["LanguageProduct"] = relationship()
