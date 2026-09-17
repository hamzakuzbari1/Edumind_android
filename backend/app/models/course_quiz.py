"""Teacher-authored course quizzes (separate from AI lesson quiz_questions)."""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseQuizQuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    short_answer = "short_answer"
    essay = "essay"


class CourseQuizAttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"


class CourseQuiz(Base):
    __tablename__ = "course_quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_score_percent: Mapped[int] = mapped_column(Integer, default=60)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="manual_quizzes")
    questions: Mapped[list["CourseQuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="CourseQuizQuestion.sort_order"
    )
    attempts: Mapped[list["CourseQuizAttempt"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class CourseQuizQuestion(Base):
    __tablename__ = "course_quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("course_quizzes.id", ondelete="CASCADE"), index=True)
    question_type: Mapped[CourseQuizQuestionType] = mapped_column(String(32))
    question_text: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_answer_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    requires_manual_grading: Mapped[bool] = mapped_column(Boolean, default=False)

    quiz: Mapped["CourseQuiz"] = relationship(back_populates="questions")
    answers: Mapped[list["CourseQuizAnswer"]] = relationship(back_populates="question")


class CourseQuizAttempt(Base):
    __tablename__ = "course_quiz_attempts"
    __table_args__ = (UniqueConstraint("quiz_id", "student_id", name="uq_course_quiz_attempt"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("course_quizzes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[CourseQuizAttemptStatus] = mapped_column(String(32), default=CourseQuizAttemptStatus.in_progress)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz: Mapped["CourseQuiz"] = relationship(back_populates="attempts")
    student: Mapped["User"] = relationship()
    answer_rows: Mapped[list["CourseQuizAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class CourseQuizAnswer(Base):
    __tablename__ = "course_quiz_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_course_quiz_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("course_quiz_attempts.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("course_quiz_questions.id", ondelete="CASCADE"), index=True
    )
    answer_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_earned: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    attempt: Mapped["CourseQuizAttempt"] = relationship(back_populates="answer_rows")
    question: Mapped["CourseQuizQuestion"] = relationship(back_populates="answers")
