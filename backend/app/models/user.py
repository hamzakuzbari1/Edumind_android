import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"
    parent = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    two_factor_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    avatar_media_object_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "media_objects.id",
            name="fk_users_avatar_media_object_id_media_objects",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
    )

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="teacher")
    profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False)
    teacher_profile: Mapped["TeacherProfile | None"] = relationship(back_populates="user", uselist=False)
    avatar_media_object: Mapped["MediaObject | None"] = relationship(
        foreign_keys=[avatar_media_object_id]
    )
