"""Manual course quizzes — teacher builder + student attempts (AI lesson quizzes unchanged)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role, require_student_actor
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.course_quiz import (
    CourseQuizAnalyticsOut,
    CourseQuizCreate,
    CourseQuizDetailOut,
    CourseQuizOut,
    CourseQuizUpdate,
    GradeEssayRequest,
    QuizAnalyticsOut,
    QuizAttemptOut,
    QuizQuestionCreate,
    QuizQuestionOut,
    QuizQuestionUpdate,
    QuizResultsOut,
    SaveAnswersRequest,
    StudentQuizListItem,
    StudentQuizTakeOut,
)
from app.services import course_quiz_service

teacher_router = APIRouter(prefix="/teacher", tags=["Manual Quizzes"])
student_router = APIRouter(prefix="/student", tags=["Manual Quizzes"])


# —— Teacher ——


@teacher_router.get("/courses/{course_id}/manual-quizzes", response_model=list[CourseQuizOut])
async def list_manual_quizzes(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.list_teacher_quizzes(db, teacher, course_id)


@teacher_router.post("/courses/{course_id}/manual-quizzes", response_model=CourseQuizOut)
async def create_manual_quiz(
    course_id: int,
    body: CourseQuizCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await course_quiz_service.create_quiz(db, teacher, course_id, body)
    await db.commit()
    return result


@teacher_router.get(
    "/courses/{course_id}/manual-quizzes/{quiz_id}",
    response_model=CourseQuizDetailOut,
)
async def get_manual_quiz(
    course_id: int,
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.get_quiz_detail(db, teacher, course_id, quiz_id)


@teacher_router.put(
    "/courses/{course_id}/manual-quizzes/{quiz_id}",
    response_model=CourseQuizOut,
)
async def update_manual_quiz(
    course_id: int,
    quiz_id: int,
    body: CourseQuizUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await course_quiz_service.update_quiz(db, teacher, course_id, quiz_id, body)
    await db.commit()
    return result


@teacher_router.delete("/courses/{course_id}/manual-quizzes/{quiz_id}", status_code=204)
async def delete_manual_quiz(
    course_id: int,
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await course_quiz_service.delete_quiz(db, teacher, course_id, quiz_id)
    await db.commit()


@teacher_router.post(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/questions",
    response_model=QuizQuestionOut,
)
async def add_manual_question(
    course_id: int,
    quiz_id: int,
    body: QuizQuestionCreate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await course_quiz_service.add_question(db, teacher, course_id, quiz_id, body)
    await db.commit()
    return result


@teacher_router.put(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/questions/{question_id}",
    response_model=QuizQuestionOut,
)
async def update_manual_question(
    course_id: int,
    quiz_id: int,
    question_id: int,
    body: QuizQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await course_quiz_service.update_question(
        db, teacher, course_id, quiz_id, question_id, body
    )
    await db.commit()
    return result


@teacher_router.delete(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/questions/{question_id}",
    status_code=204,
)
async def delete_manual_question(
    course_id: int,
    quiz_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    await course_quiz_service.delete_question(db, teacher, course_id, quiz_id, question_id)
    await db.commit()


@teacher_router.get(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/results",
    response_model=QuizResultsOut,
)
async def manual_quiz_results(
    course_id: int,
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.list_quiz_results(db, teacher, course_id, quiz_id)


@teacher_router.get(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/attempts/{attempt_id}",
    response_model=QuizAttemptOut,
)
async def manual_quiz_attempt_detail(
    course_id: int,
    quiz_id: int,
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.get_attempt_for_teacher(
        db, teacher, course_id, quiz_id, attempt_id
    )


@teacher_router.post(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/attempts/{attempt_id}/questions/{question_id}/grade",
    response_model=QuizAttemptOut,
)
async def grade_manual_essay(
    course_id: int,
    quiz_id: int,
    attempt_id: int,
    question_id: int,
    body: GradeEssayRequest,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    result = await course_quiz_service.grade_essay_answer(
        db, teacher, course_id, quiz_id, attempt_id, question_id, body
    )
    await db.commit()
    return result


@teacher_router.get(
    "/courses/{course_id}/manual-quizzes/{quiz_id}/analytics",
    response_model=QuizAnalyticsOut,
)
async def manual_quiz_analytics(
    course_id: int,
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.quiz_analytics(db, teacher, course_id, quiz_id)


@teacher_router.get(
    "/courses/{course_id}/manual-quiz-analytics",
    response_model=CourseQuizAnalyticsOut,
)
async def course_manual_quiz_analytics(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(require_role(UserRole.teacher)),
):
    return await course_quiz_service.course_quiz_analytics(db, teacher, course_id)


# —— Student ——


@student_router.get("/courses/{course_id}/manual-quizzes", response_model=list[StudentQuizListItem])
async def list_student_manual_quizzes(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await course_quiz_service.list_student_quizzes(db, student.id, course_id)


@student_router.get("/manual-quizzes/{quiz_id}", response_model=StudentQuizTakeOut)
async def get_manual_quiz_take(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await course_quiz_service.get_student_quiz_take(db, student.id, quiz_id)


@student_router.post("/manual-quizzes/{quiz_id}/start", response_model=StudentQuizTakeOut)
async def start_manual_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await course_quiz_service.start_attempt(db, student.id, quiz_id)
    await db.commit()
    return result


@student_router.patch("/manual-quiz-attempts/{attempt_id}/answers", status_code=204)
async def save_manual_quiz_answers(
    attempt_id: int,
    body: SaveAnswersRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    await course_quiz_service.save_answers(db, student.id, attempt_id, body)
    await db.commit()


@student_router.post("/manual-quiz-attempts/{attempt_id}/submit", response_model=QuizAttemptOut)
async def submit_manual_quiz(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await course_quiz_service.submit_attempt(db, student.id, attempt_id)
    await db.commit()
    return result


@student_router.get("/manual-quiz-attempts/{attempt_id}", response_model=QuizAttemptOut)
async def get_manual_quiz_attempt(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await course_quiz_service.get_attempt_for_student(db, student.id, attempt_id)
