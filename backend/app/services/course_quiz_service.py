"""Teacher manual course quizzes — CRUD, attempts, grading, analytics."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import selectinload

from app.models.catalog import Course
from app.models.course_quiz import (
    CourseQuiz,
    CourseQuizAnswer,
    CourseQuizAttempt,
    CourseQuizAttemptStatus,
    CourseQuizQuestion,
    CourseQuizQuestionType,
)
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.user import User
from app.services.audit_service import log_audit
from app.schemas.course_quiz import (
    CourseQuizAnalyticsOut,
    CourseQuizCreate,
    CourseQuizDetailOut,
    CourseQuizOut,
    CourseQuizUpdate,
    GradeEssayRequest,
    QuizAnalyticsOut,
    QuizAttemptOut,
    QuizAttemptSummaryOut,
    QuizQuestionCreate,
    QuizQuestionOut,
    QuizQuestionStudentOut,
    QuizQuestionUpdate,
    QuizResultsOut,
    QuizAnswerOut,
    SaveAnswersRequest,
    StudentQuizListItem,
    StudentQuizTakeOut,
)
from app.services.teacher_courses_service import _owned_course


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _loads(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _dumps(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_due_at(due_at: datetime | None) -> None:
    if due_at is None:
        return
    if _as_utc(due_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="موعد التسليم يجب أن يكون في المستقبل")


def _quiz_questions_if_loaded(quiz: CourseQuiz) -> list[CourseQuizQuestion] | None:
    """Return questions only when already eager-loaded — never lazy-load in async."""
    state = sa_inspect(quiz)
    if state is None or not state.has_identity or "questions" in state.unloaded:
        return None
    return list(quiz.questions or [])


def _total_points(quiz: CourseQuiz, *, explicit: int | None = None) -> int:
    if explicit is not None:
        return explicit
    questions = _quiz_questions_if_loaded(quiz)
    if questions is None:
        return 0
    return sum(int(q.points or 0) for q in questions)


def _time_remaining_seconds(quiz: CourseQuiz, attempt: CourseQuizAttempt | None) -> int | None:
    if not quiz.duration_minutes or not attempt or attempt.status != CourseQuizAttemptStatus.in_progress:
        return None
    started = _as_utc(attempt.started_at)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return max(0, int(quiz.duration_minutes * 60 - elapsed))


def _ensure_attempt_in_time(quiz: CourseQuiz, attempt: CourseQuizAttempt) -> None:
    remaining = _time_remaining_seconds(quiz, attempt)
    if remaining is not None and remaining <= 0:
        raise HTTPException(status_code=400, detail="انتهى وقت الكويز — يرجى تسليم الإجابات")


def _question_requires_manual(qtype: CourseQuizQuestionType) -> bool:
    return qtype == CourseQuizQuestionType.essay


def _validate_question_payload(body: QuizQuestionCreate | QuizQuestionUpdate, *, is_create: bool) -> None:
    qtype = getattr(body, "question_type", None)
    if is_create and not qtype:
        raise HTTPException(status_code=400, detail="نوع السؤال مطلوب")
    if qtype == CourseQuizQuestionType.multiple_choice.value or qtype == "multiple_choice":
        opts = body.options or []
        if len(opts) < 2:
            raise HTTPException(status_code=400, detail="اختر خيارين على الأقل للسؤال متعدد الخيارات")
        ca = body.correct_answer
        if ca is None or (isinstance(ca, dict) and ca.get("index") is None and ca.get("correct_index") is None):
            raise HTTPException(status_code=400, detail="حدد الإجابة الصحيحة")
    elif qtype in (CourseQuizQuestionType.true_false.value, "true_false"):
        if body.correct_answer is None:
            raise HTTPException(status_code=400, detail="حدد الإجابة الصحيحة (صح / خطأ)")
    elif qtype in (CourseQuizQuestionType.short_answer.value, "short_answer"):
        if not body.correct_answer:
            raise HTTPException(status_code=400, detail="حدد الإجابة النموذجية")
    elif qtype in (CourseQuizQuestionType.essay.value, "essay"):
        pass


def _pack_correct_answer(qtype: str, correct_answer) -> str | None:
    if qtype == CourseQuizQuestionType.essay.value:
        return None
    return _dumps(correct_answer)


def _question_to_out(q: CourseQuizQuestion, *, include_key: bool = False) -> QuizQuestionOut | QuizQuestionStudentOut:
    opts = _loads(q.options_json) or []
    base = {
        "id": q.id,
        "question_type": q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
        "question_text": q.question_text,
        "options": opts if isinstance(opts, list) else [],
        "points": q.points,
        "sort_order": q.sort_order,
        "requires_manual_grading": q.requires_manual_grading,
    }
    if include_key:
        return QuizQuestionOut(**base, correct_answer=_loads(q.correct_answer_json))
    return QuizQuestionStudentOut(**base)


async def _get_quiz_owned(db: AsyncSession, user: User, course_id: int, quiz_id: int) -> CourseQuiz:
    await _owned_course(db, user, course_id)
    result = await db.execute(
        select(CourseQuiz)
        .where(CourseQuiz.id == quiz_id, CourseQuiz.course_id == course_id)
        .options(selectinload(CourseQuiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="الكويز غير موجود")
    return quiz


async def _enrolled_paid_count(db: AsyncSession, course_id: int) -> int:
    from app.services.subscription_access_service import is_access_active

    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.course_id == course_id,
            StudentCourseAccess.payment_status == PaymentStatus.paid,
        )
    )
    return sum(1 for a in result.scalars().all() if is_access_active(a))


async def _student_has_paid_access(db: AsyncSession, student_id: int, course_id: int) -> bool:
    from app.services.subscription_access_service import is_access_active

    result = await db.execute(
        select(StudentCourseAccess).where(
            StudentCourseAccess.student_id == student_id,
            StudentCourseAccess.course_id == course_id,
        )
    )
    return is_access_active(result.scalar_one_or_none())


def _quiz_out(
    quiz: CourseQuiz,
    *,
    question_count: int | None = None,
    attempt_count: int | None = None,
    total_points: int | None = None,
) -> CourseQuizOut:
    loaded_questions = _quiz_questions_if_loaded(quiz)
    if question_count is None:
        question_count = len(loaded_questions) if loaded_questions is not None else 0
    if total_points is None:
        total_points = (
            sum(int(q.points or 0) for q in loaded_questions)
            if loaded_questions is not None
            else 0
        )
    return CourseQuizOut(
        id=quiz.id,
        course_id=quiz.course_id,
        title=quiz.title,
        description=quiz.description,
        duration_minutes=quiz.duration_minutes,
        passing_score_percent=quiz.passing_score_percent,
        is_published=quiz.is_published,
        due_at=_iso(quiz.due_at),
        question_count=question_count,
        total_points=total_points,
        attempt_count=attempt_count or 0,
        created_at=_iso(quiz.created_at),
    )


async def list_teacher_quizzes(db: AsyncSession, user: User, course_id: int) -> list[CourseQuizOut]:
    await _owned_course(db, user, course_id)
    result = await db.execute(
        select(CourseQuiz)
        .where(CourseQuiz.course_id == course_id)
        .options(selectinload(CourseQuiz.questions))
        .order_by(CourseQuiz.created_at.desc())
    )
    quizzes = result.scalars().all()
    out: list[CourseQuizOut] = []
    for q in quizzes:
        ac = await db.execute(
            select(func.count()).select_from(CourseQuizAttempt).where(CourseQuizAttempt.quiz_id == q.id)
        )
        out.append(_quiz_out(q, attempt_count=int(ac.scalar() or 0)))
    return out


async def create_quiz(db: AsyncSession, user: User, course_id: int, body: CourseQuizCreate) -> CourseQuizOut:
    await _owned_course(db, user, course_id)
    if not body.title or not body.title.strip():
        raise HTTPException(status_code=400, detail="عنوان الكويز مطلوب")
    _validate_due_at(body.due_at)
    if body.passing_score_percent is not None and not (0 <= body.passing_score_percent <= 100):
        raise HTTPException(status_code=400, detail="درجة النجاح يجب أن تكون بين 0 و 100")
    if body.duration_minutes is not None and body.duration_minutes < 1:
        raise HTTPException(status_code=400, detail="مدة الكويز غير صالحة")
    quiz = CourseQuiz(
        course_id=course_id,
        title=body.title.strip(),
        description=body.description,
        duration_minutes=body.duration_minutes,
        passing_score_percent=body.passing_score_percent,
        is_published=body.is_published,
        due_at=body.due_at,
    )
    db.add(quiz)
    await db.flush()
    await log_audit(
        db,
        action="create",
        entity_type="quiz",
        entity_id=quiz.id,
        actor_user_id=user.id,
        new_values={"course_id": course_id, "title": quiz.title},
    )
    if quiz.is_published:
        from app.services.integration_hooks import notify_quiz_published

        await notify_quiz_published(
            db, course_id=course_id, quiz_title=quiz.title, quiz_id=quiz.id
        )
    return _quiz_out(quiz, question_count=0, attempt_count=0, total_points=0)


async def get_quiz_detail(db: AsyncSession, user: User, course_id: int, quiz_id: int) -> CourseQuizDetailOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    ac = await db.execute(
        select(func.count()).select_from(CourseQuizAttempt).where(CourseQuizAttempt.quiz_id == quiz.id)
    )
    questions = sorted(quiz.questions, key=lambda q: (q.sort_order, q.id))
    return CourseQuizDetailOut(
        **_quiz_out(quiz, attempt_count=int(ac.scalar() or 0)).model_dump(),
        questions=[_question_to_out(q, include_key=True) for q in questions],
    )


async def update_quiz(
    db: AsyncSession, user: User, course_id: int, quiz_id: int, body: CourseQuizUpdate
) -> CourseQuizOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    if body.due_at is not None:
        _validate_due_at(body.due_at)
    if body.passing_score_percent is not None and not (0 <= body.passing_score_percent <= 100):
        raise HTTPException(status_code=400, detail="درجة النجاح يجب أن تكون بين 0 و 100")
    if body.duration_minutes is not None and body.duration_minutes < 1:
        raise HTTPException(status_code=400, detail="مدة الكويز غير صالحة")
    for field in ("title", "description", "duration_minutes", "passing_score_percent", "is_published", "due_at"):
        val = getattr(body, field, None)
        if val is not None:
            if field == "title":
                val = val.strip()
            setattr(quiz, field, val)
    await db.flush()
    await log_audit(
        db,
        action="update",
        entity_type="quiz",
        entity_id=quiz.id,
        actor_user_id=user.id,
        new_values=body.model_dump(exclude_unset=True),
    )
    if body.is_published is True and quiz.is_published:
        from app.services.integration_hooks import notify_quiz_published

        await notify_quiz_published(
            db, course_id=course_id, quiz_title=quiz.title, quiz_id=quiz.id
        )
    return _quiz_out(quiz)


async def delete_quiz(db: AsyncSession, user: User, course_id: int, quiz_id: int) -> None:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    await db.delete(quiz)


async def add_question(
    db: AsyncSession, user: User, course_id: int, quiz_id: int, body: QuizQuestionCreate
) -> QuizQuestionOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    _validate_question_payload(body, is_create=True)
    qtype = CourseQuizQuestionType(body.question_type)
    row = CourseQuizQuestion(
        quiz_id=quiz.id,
        question_type=qtype,
        question_text=body.question_text.strip(),
        options_json=_dumps(body.options) if body.options else None,
        correct_answer_json=_pack_correct_answer(body.question_type, body.correct_answer),
        points=max(1, body.points),
        sort_order=body.sort_order,
        requires_manual_grading=_question_requires_manual(qtype),
    )
    db.add(row)
    await db.flush()
    return _question_to_out(row, include_key=True)


async def update_question(
    db: AsyncSession,
    user: User,
    course_id: int,
    quiz_id: int,
    question_id: int,
    body: QuizQuestionUpdate,
) -> QuizQuestionOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    result = await db.execute(
        select(CourseQuizQuestion).where(
            CourseQuizQuestion.id == question_id, CourseQuizQuestion.quiz_id == quiz.id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="السؤال غير موجود")
    if body.question_type is not None:
        row.question_type = CourseQuizQuestionType(body.question_type)
        row.requires_manual_grading = _question_requires_manual(row.question_type)
    if body.question_text is not None:
        row.question_text = body.question_text.strip()
    if body.options is not None:
        row.options_json = _dumps(body.options)
    if body.correct_answer is not None or body.question_type == CourseQuizQuestionType.essay.value:
        qtype = row.question_type.value if hasattr(row.question_type, "value") else str(row.question_type)
        row.correct_answer_json = _pack_correct_answer(qtype, body.correct_answer)
    if body.points is not None:
        row.points = max(1, body.points)
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    qtype_str = row.question_type.value if hasattr(row.question_type, "value") else str(row.question_type)
    _validate_question_payload(
        QuizQuestionCreate(
            question_type=qtype_str,
            question_text=row.question_text,
            options=_loads(row.options_json) or [],
            correct_answer=_loads(row.correct_answer_json),
            points=row.points,
            sort_order=row.sort_order,
        ),
        is_create=True,
    )
    await db.flush()
    return _question_to_out(row, include_key=True)


async def delete_question(
    db: AsyncSession, user: User, course_id: int, quiz_id: int, question_id: int
) -> None:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    result = await db.execute(
        select(CourseQuizQuestion).where(
            CourseQuizQuestion.id == question_id, CourseQuizQuestion.quiz_id == quiz.id
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="السؤال غير موجود")
    await db.delete(row)


def _grade_answer(question: CourseQuizQuestion, answer_raw: str | None) -> tuple[float, bool | None]:
    """Auto-grade non-essay. Returns (points_earned, is_correct)."""
    if question.requires_manual_grading:
        return 0.0, None
    answer = _loads(answer_raw)
    correct = _loads(question.correct_answer_json)
    qtype = question.question_type.value if hasattr(question.question_type, "value") else str(question.question_type)
    pts = float(question.points)

    if qtype == CourseQuizQuestionType.multiple_choice.value:
        selected = answer.get("selected_index") if isinstance(answer, dict) else answer
        idx = correct.get("index") if isinstance(correct, dict) else correct.get("correct_index") if isinstance(correct, dict) else correct
        ok = selected is not None and idx is not None and int(selected) == int(idx)
        return (pts if ok else 0.0, ok)

    if qtype == CourseQuizQuestionType.true_false.value:
        sel = answer.get("value") if isinstance(answer, dict) else answer
        cor = correct.get("value") if isinstance(correct, dict) else correct
        ok = bool(sel) == bool(cor)
        return (pts if ok else 0.0, ok)

    if qtype == CourseQuizQuestionType.short_answer.value:
        sel = answer.get("text") if isinstance(answer, dict) else str(answer or "")
        cor = correct.get("text") if isinstance(correct, dict) else str(correct or "")
        ok = _normalize_text(str(sel)) == _normalize_text(str(cor))
        return (pts if ok else 0.0, ok)

    return 0.0, None


async def _recalculate_attempt(db: AsyncSession, attempt: CourseQuizAttempt, quiz: CourseQuiz) -> None:
    result = await db.execute(
        select(CourseQuizAnswer)
        .where(CourseQuizAnswer.attempt_id == attempt.id)
        .options(selectinload(CourseQuizAnswer.question))
    )
    rows = result.scalars().all()
    max_score = float(sum(int(q.points or 0) for q in quiz.questions))
    score = 0.0
    pending = 0
    for ans in rows:
        q = ans.question
        if q.requires_manual_grading:
            if ans.points_earned is None:
                pending += 1
            else:
                earned = min(float(ans.points_earned), float(q.points))
                ans.points_earned = earned
                score += earned
        elif ans.points_earned is not None:
            earned = min(float(ans.points_earned), float(q.points))
            ans.points_earned = earned
            score += earned

    score = min(score, max_score) if max_score > 0 else 0.0
    attempt.score = score
    attempt.max_score = max_score
    if max_score > 0 and pending == 0:
        attempt.percent = round((score / max_score) * 100, 1)
        attempt.passed = attempt.percent >= quiz.passing_score_percent
    elif max_score > 0 and pending > 0 and attempt.status != CourseQuizAttemptStatus.in_progress:
        attempt.percent = round((score / max_score) * 100, 1)
        attempt.passed = None
    else:
        attempt.percent = None
        attempt.passed = None


async def list_student_quizzes(db: AsyncSession, student_id: int, course_id: int) -> list[StudentQuizListItem]:
    if not await _student_has_paid_access(db, student_id, course_id):
        raise HTTPException(status_code=403, detail="يجب الاشتراك في الدورة أولاً")
    result = await db.execute(
        select(CourseQuiz)
        .where(CourseQuiz.course_id == course_id, CourseQuiz.is_published.is_(True))
        .options(selectinload(CourseQuiz.questions))
        .order_by(CourseQuiz.due_at.nulls_last(), CourseQuiz.created_at.desc())
    )
    items: list[StudentQuizListItem] = []
    for quiz in result.scalars().all():
        att = await db.execute(
            select(CourseQuizAttempt).where(
                CourseQuizAttempt.quiz_id == quiz.id,
                CourseQuizAttempt.student_id == student_id,
            )
        )
        attempt = att.scalar_one_or_none()
        items.append(
            StudentQuizListItem(
                id=quiz.id,
                course_id=quiz.course_id,
                title=quiz.title,
                description=quiz.description,
                duration_minutes=quiz.duration_minutes,
                passing_score_percent=quiz.passing_score_percent,
                due_at=_iso(quiz.due_at),
                question_count=len(quiz.questions),
                total_points=_total_points(quiz),
                attempt_status=attempt.status.value if attempt and hasattr(attempt.status, "value") else (str(attempt.status) if attempt else None),
                percent=attempt.percent if attempt else None,
                passed=attempt.passed if attempt else None,
                score=attempt.score if attempt else None,
                max_score=attempt.max_score if attempt else None,
            )
        )
    return items


async def get_student_quiz_take(
    db: AsyncSession, student_id: int, quiz_id: int
) -> StudentQuizTakeOut:
    result = await db.execute(
        select(CourseQuiz)
        .where(CourseQuiz.id == quiz_id)
        .options(selectinload(CourseQuiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz or not quiz.is_published:
        raise HTTPException(status_code=404, detail="الكويز غير متاح")
    if not await _student_has_paid_access(db, student_id, quiz.course_id):
        raise HTTPException(status_code=403, detail="يجب الاشتراك في الدورة أولاً")
    if quiz.due_at and quiz.due_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="انتهى موعد تسليم الكويز")

    att_result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.quiz_id == quiz.id, CourseQuizAttempt.student_id == student_id)
        .options(selectinload(CourseQuizAttempt.answer_rows))
    )
    attempt = att_result.scalar_one_or_none()
    answers_map: dict[int, dict | str | bool | int | None] = {}
    if attempt:
        for row in attempt.answer_rows:
            answers_map[row.question_id] = _loads(row.answer_json)

    questions = sorted(quiz.questions, key=lambda q: (q.sort_order, q.id))
    time_remaining = _time_remaining_seconds(quiz, attempt)

    return StudentQuizTakeOut(
        quiz=StudentQuizListItem(
            id=quiz.id,
            course_id=quiz.course_id,
            title=quiz.title,
            description=quiz.description,
            duration_minutes=quiz.duration_minutes,
            passing_score_percent=quiz.passing_score_percent,
            due_at=_iso(quiz.due_at),
            question_count=len(questions),
            total_points=_total_points(quiz),
            attempt_status=attempt.status.value if attempt and hasattr(attempt.status, "value") else (str(attempt.status) if attempt else None),
            percent=attempt.percent if attempt else None,
            passed=attempt.passed if attempt else None,
            score=attempt.score if attempt else None,
            max_score=attempt.max_score if attempt else None,
        ),
        questions=[_question_to_out(q, include_key=False) for q in questions],
        attempt_id=attempt.id if attempt else None,
        answers=answers_map,
        time_remaining_seconds=time_remaining,
    )


async def start_attempt(db: AsyncSession, student_id: int, quiz_id: int) -> StudentQuizTakeOut:
    take = await get_student_quiz_take(db, student_id, quiz_id)
    if take.attempt_id:
        status_val = take.quiz.attempt_status
        if status_val in (CourseQuizAttemptStatus.submitted.value, CourseQuizAttemptStatus.graded.value):
            raise HTTPException(status_code=400, detail="لقد سلّمت هذا الكويز مسبقاً")
        return take

    result = await db.execute(
        select(CourseQuiz)
        .where(CourseQuiz.id == quiz_id)
        .options(selectinload(CourseQuiz.questions))
    )
    quiz = result.scalar_one()
    if not quiz.questions:
        raise HTTPException(status_code=400, detail="الكويز لا يحتوي على أسئلة")

    attempt = CourseQuizAttempt(quiz_id=quiz.id, student_id=student_id)
    db.add(attempt)
    await db.flush()
    for q in quiz.questions:
        db.add(CourseQuizAnswer(attempt_id=attempt.id, question_id=q.id))
    await db.flush()
    return await get_student_quiz_take(db, student_id, quiz_id)


async def save_answers(
    db: AsyncSession, student_id: int, attempt_id: int, body: SaveAnswersRequest
) -> None:
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.id == attempt_id, CourseQuizAttempt.student_id == student_id)
        .options(selectinload(CourseQuizAttempt.answer_rows), selectinload(CourseQuizAttempt.quiz))
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")
    if attempt.status != CourseQuizAttemptStatus.in_progress:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل إجابات بعد التسليم")

    _ensure_attempt_in_time(attempt.quiz, attempt)

    by_q = {a.question_id: a for a in attempt.answer_rows}
    for item in body.answers:
        row = by_q.get(item.question_id)
        if row:
            row.answer_json = _dumps(item.answer)
    await db.flush()


async def submit_attempt(db: AsyncSession, student_id: int, attempt_id: int) -> QuizAttemptOut:
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.id == attempt_id, CourseQuizAttempt.student_id == student_id)
        .options(
            selectinload(CourseQuizAttempt.answer_rows).selectinload(CourseQuizAnswer.question),
            selectinload(CourseQuizAttempt.quiz).selectinload(CourseQuiz.questions),
            selectinload(CourseQuizAttempt.student),
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")
    if attempt.status != CourseQuizAttemptStatus.in_progress:
        raise HTTPException(status_code=400, detail="تم التسليم مسبقاً")

    quiz = attempt.quiz
    for ans in attempt.answer_rows:
        if ans.question.requires_manual_grading:
            ans.points_earned = None
            ans.is_correct = None
        else:
            pts, ok = _grade_answer(ans.question, ans.answer_json)
            ans.points_earned = pts
            ans.is_correct = ok

    attempt.status = CourseQuizAttemptStatus.submitted
    attempt.submitted_at = datetime.now(timezone.utc)
    await _recalculate_attempt(db, attempt, quiz)

    pending = sum(
        1
        for a in attempt.answer_rows
        if a.question.requires_manual_grading and a.points_earned is None
    )
    if pending == 0:
        attempt.status = CourseQuizAttemptStatus.graded
        attempt.graded_at = datetime.now(timezone.utc)

    await db.flush()
    if quiz.course_id:
        from app.services.integration_hooks import after_quiz_submitted

        score_percent = int(round(float(attempt.percent))) if attempt.percent is not None else 0
        await after_quiz_submitted(
            db,
            student_id,
            quiz.id,
            quiz.course_id,
            attempt_id=attempt.id,
            score_percent=score_percent,
        )
    return _attempt_detail_out(attempt, include_keys=True)


async def get_attempt_for_student(
    db: AsyncSession, student_id: int, attempt_id: int
) -> QuizAttemptOut:
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.id == attempt_id, CourseQuizAttempt.student_id == student_id)
        .options(
            selectinload(CourseQuizAttempt.answer_rows).selectinload(CourseQuizAnswer.question),
            selectinload(CourseQuizAttempt.quiz),
            selectinload(CourseQuizAttempt.student),
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")
    show_keys = attempt.status in (CourseQuizAttemptStatus.graded, CourseQuizAttemptStatus.submitted)
    return _attempt_detail_out(attempt, include_keys=show_keys)


def _attempt_detail_out(attempt: CourseQuizAttempt, *, include_keys: bool = False) -> QuizAttemptOut:
    answers: list[QuizAnswerOut] = []
    for ans in sorted(attempt.answer_rows, key=lambda a: (a.question.sort_order, a.question_id)):
        q = ans.question
        pending = q.requires_manual_grading and ans.points_earned is None and attempt.status != CourseQuizAttemptStatus.in_progress
        answers.append(
            QuizAnswerOut(
                question_id=q.id,
                question_type=q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
                question_text=q.question_text,
                answer=_loads(ans.answer_json),
                points_earned=ans.points_earned,
                max_points=q.points,
                is_correct=ans.is_correct if include_keys or ans.is_correct is not None else None,
                teacher_feedback=ans.teacher_feedback,
                requires_manual_grading=q.requires_manual_grading,
                pending_grading=pending,
            )
        )
    st = attempt.student
    return QuizAttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        student_id=attempt.student_id,
        student_name=st.name if st else None,
        status=attempt.status.value if hasattr(attempt.status, "value") else str(attempt.status),
        score=attempt.score,
        max_score=attempt.max_score,
        percent=attempt.percent,
        passed=attempt.passed,
        started_at=_iso(attempt.started_at),
        submitted_at=_iso(attempt.submitted_at),
        graded_at=_iso(attempt.graded_at),
        answers=answers,
    )


async def list_quiz_results(
    db: AsyncSession, user: User, course_id: int, quiz_id: int
) -> QuizResultsOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.quiz_id == quiz.id)
        .options(
            selectinload(CourseQuizAttempt.student),
            selectinload(CourseQuizAttempt.answer_rows).selectinload(CourseQuizAnswer.question),
        )
        .order_by(CourseQuizAttempt.submitted_at.desc().nulls_last())
    )
    summaries: list[QuizAttemptSummaryOut] = []
    for att in result.scalars().all():
        if att.status != CourseQuizAttemptStatus.in_progress:
            await _recalculate_attempt(db, att, quiz)
        pending = sum(
            1
            for a in att.answer_rows
            if a.question.requires_manual_grading
            and a.points_earned is None
            and att.status != CourseQuizAttemptStatus.in_progress
        )
        summaries.append(
            QuizAttemptSummaryOut(
                id=att.id,
                student_id=att.student_id,
                student_name=att.student.name if att.student else "",
                status=att.status.value if hasattr(att.status, "value") else str(att.status),
                score=att.score,
                max_score=att.max_score,
                percent=att.percent,
                passed=att.passed,
                submitted_at=_iso(att.submitted_at),
                pending_essay_count=pending,
            )
        )
    await db.flush()
    ac = len(summaries)
    return QuizResultsOut(quiz=_quiz_out(quiz, attempt_count=ac), attempts=summaries)


async def get_attempt_for_teacher(
    db: AsyncSession, user: User, course_id: int, quiz_id: int, attempt_id: int
) -> QuizAttemptOut:
    await _get_quiz_owned(db, user, course_id, quiz_id)
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.id == attempt_id, CourseQuizAttempt.quiz_id == quiz_id)
        .options(
            selectinload(CourseQuizAttempt.answer_rows).selectinload(CourseQuizAnswer.question),
            selectinload(CourseQuizAttempt.student),
            selectinload(CourseQuizAttempt.quiz),
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    if attempt.status != CourseQuizAttemptStatus.in_progress:
        await _recalculate_attempt(db, attempt, quiz)
        await db.flush()
    return _attempt_detail_out(attempt, include_keys=True)


async def grade_essay_answer(
    db: AsyncSession,
    user: User,
    course_id: int,
    quiz_id: int,
    attempt_id: int,
    question_id: int,
    body: GradeEssayRequest,
) -> QuizAttemptOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    result = await db.execute(
        select(CourseQuizAttempt)
        .where(CourseQuizAttempt.id == attempt_id, CourseQuizAttempt.quiz_id == quiz.id)
        .options(
            selectinload(CourseQuizAttempt.answer_rows).selectinload(CourseQuizAnswer.question),
            selectinload(CourseQuizAttempt.student),
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")

    ans = next((a for a in attempt.answer_rows if a.question_id == question_id), None)
    if not ans or not ans.question.requires_manual_grading:
        raise HTTPException(status_code=400, detail="هذا السؤال لا يتطلب تصحيحاً يدوياً")

    max_pts = float(ans.question.points)
    pts = min(max(0.0, body.points_earned), max_pts)
    ans.points_earned = pts
    ans.is_correct = pts >= max_pts * 0.5
    ans.teacher_feedback = body.teacher_feedback
    ans.graded_at = datetime.now(timezone.utc)
    ans.graded_by_user_id = user.id

    if body.publish:
        pending = sum(1 for a in attempt.answer_rows if a.question.requires_manual_grading and a.points_earned is None)
        if pending == 0:
            await _recalculate_attempt(db, attempt, quiz)
            attempt.status = CourseQuizAttemptStatus.graded
            attempt.graded_at = datetime.now(timezone.utc)
        else:
            await _recalculate_attempt(db, attempt, quiz)

    await db.flush()
    if body.publish and attempt.status == CourseQuizAttemptStatus.graded:
        from app.services.integration_hooks import notify_homework_graded

        pct = int(attempt.percent or 0) if attempt.percent is not None else None
        await notify_homework_graded(
            db,
            student_id=attempt.student_id,
            title=quiz.title,
            score=pct,
        )
    return _attempt_detail_out(attempt, include_keys=True)


async def quiz_analytics(
    db: AsyncSession, user: User, course_id: int, quiz_id: int
) -> QuizAnalyticsOut:
    quiz = await _get_quiz_owned(db, user, course_id, quiz_id)
    enrolled = await _enrolled_paid_count(db, course_id)
    result = await db.execute(
        select(CourseQuizAttempt, User.name)
        .join(User, User.id == CourseQuizAttempt.student_id)
        .where(
            CourseQuizAttempt.quiz_id == quiz.id,
            CourseQuizAttempt.status.in_(
                [CourseQuizAttemptStatus.submitted, CourseQuizAttemptStatus.graded]
            ),
        )
        .order_by(CourseQuizAttempt.percent.desc().nulls_last())
    )
    rows = result.all()
    percents = [float(r[0].percent) for r in rows if r[0].percent is not None]
    attempted = len(rows)
    ranking = [
        {
            "student_id": att.student_id,
            "student_name": name,
            "percent": att.percent,
            "passed": att.passed,
            "submitted_at": _iso(att.submitted_at),
        }
        for att, name in rows
    ]
    return QuizAnalyticsOut(
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        enrolled_students=enrolled,
        attempted_count=attempted,
        completion_rate=round((attempted / enrolled) * 100, 1) if enrolled else 0.0,
        average_score=round(sum(percents) / len(percents), 1) if percents else None,
        highest_score=max(percents) if percents else None,
        lowest_score=min(percents) if percents else None,
        ranking=ranking,
    )


async def course_quiz_analytics(db: AsyncSession, user: User, course_id: int) -> CourseQuizAnalyticsOut:
    course = await _owned_course(db, user, course_id)
    quizzes = await list_teacher_quizzes(db, user, course_id)
    enrolled = await _enrolled_paid_count(db, course_id)
    quiz_stats: list[QuizAnalyticsOut] = []
    all_percents: list[float] = []
    total_attempts = 0
    for q in quizzes:
        stat = await quiz_analytics(db, user, course_id, q.id)
        quiz_stats.append(stat)
        total_attempts += stat.attempted_count
        if stat.average_score is not None:
            all_percents.append(stat.average_score)

    completion = 0.0
    if enrolled and quiz_stats:
        rates = [s.completion_rate for s in quiz_stats]
        completion = round(sum(rates) / len(rates), 1)

    return CourseQuizAnalyticsOut(
        course_id=course.id,
        course_title=course.title,
        quiz_count=len(quizzes),
        enrolled_students=enrolled,
        total_attempts=total_attempts,
        average_score=round(sum(all_percents) / len(all_percents), 1) if all_percents else None,
        completion_rate=completion,
        quizzes=quiz_stats,
    )
