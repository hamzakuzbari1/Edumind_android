"""Student onboarding choices, payments, course access."""

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OnboardingStep(str, enum.Enum):
    grade = "grade"
    subjects = "subjects"
    teachers = "teachers"
    complete = "complete"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class PaymentMethod(str, enum.Enum):
    card = "card"
    transfer = "transfer"
    wallet = "wallet"
    cash = "cash"


class PaymentItemProductType(str, enum.Enum):
    course = "course"
    language = "language"


class CourseEnrollmentStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    paused = "paused"
    completed = "completed"
    withdrawn = "withdrawn"
    cancelled = "cancelled"


class EntitlementSource(str, enum.Enum):
    payment = "payment"
    manual_grant = "manual_grant"
    promotion = "promotion"
    admin = "admin"
    import_ = "import"
    legacy = "legacy"


class CourseAccessStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    expired = "expired"
    revoked = "revoked"


class StudentSubjectChoice(Base):
    __tablename__ = "student_subject_choices"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_student_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)

    subject: Mapped["Subject"] = relationship()


class StudentTeacherChoice(Base):
    __tablename__ = "student_teacher_choices"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_student_teacher_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    teacher_profile_id: Mapped[int] = mapped_column(ForeignKey("teacher_profiles.id"), index=True)

    subject: Mapped["Subject"] = relationship()
    teacher_profile: Mapped["TeacherProfile"] = relationship()


class StudentCourseAccess(Base):
    __tablename__ = "student_course_access"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_student_course"),
        CheckConstraint(
            "access_status IS NULL OR access_status IN "
            "('pending', 'active', 'suspended', 'expired', 'revoked')",
            name="ck_student_course_access_access_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "course_enrollments.id",
            name="fk_student_course_access_enrollment_id_course_enrollments",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    access_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_payment_item_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "payment_items.id",
            name="fk_student_course_access_source_payment_item_id_payment_items",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    granted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_student_course_access_granted_by_user_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="access_records")
    enrollment: Mapped["CourseEnrollment | None"] = relationship(back_populates="access_records")
    source_payment_item: Mapped["PaymentItem | None"] = relationship(
        foreign_keys=[source_payment_item_id]
    )
    granted_by_user: Mapped["User | None"] = relationship(foreign_keys=[granted_by_user_id])


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'paused', 'completed', 'withdrawn', 'cancelled')",
            name="ck_course_enrollments_status",
        ),
        CheckConstraint(
            "source IN ('payment', 'manual_grant', 'promotion', 'admin', 'import', 'legacy')",
            name="ck_course_enrollments_source",
        ),
        Index("ix_course_enrollments_student_course", "student_id", "course_id"),
        Index("ix_course_enrollments_course_student", "course_id", "student_id"),
        Index("ix_course_enrollments_status", "status"),
        Index(
            "uq_course_enrollments_current_student_course",
            "student_id",
            "course_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'active', 'paused')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_course_enrollments_student_id_users",
            ondelete="CASCADE",
        )
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            name="fk_course_enrollments_course_id_courses",
            ondelete="CASCADE",
        )
    )
    status: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(32))
    source_payment_item_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "payment_items.id",
            name="fk_course_enrollments_source_payment_item_id_payment_items",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_course_enrollments_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student: Mapped["User"] = relationship(foreign_keys=[student_id])
    course: Mapped["Course"] = relationship(back_populates="enrollments")
    source_payment_item: Mapped["PaymentItem | None"] = relationship(
        foreign_keys=[source_payment_item_id]
    )
    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])
    access_records: Mapped[list["StudentCourseAccess"]] = relationship(back_populates="enrollment")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    total_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="SYP")
    method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["PaymentItem"]] = relationship(back_populates="payment", cascade="all, delete-orphan")


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True)
    product_type: Mapped[PaymentItemProductType] = mapped_column(
        Enum(
            PaymentItemProductType,
            name="payment_item_product_type",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=PaymentItemProductType.course,
    )
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    language_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("language_products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    unit_price: Mapped[float] = mapped_column(Float)

    payment: Mapped["Payment"] = relationship(back_populates="items")
    course: Mapped["Course | None"] = relationship()
