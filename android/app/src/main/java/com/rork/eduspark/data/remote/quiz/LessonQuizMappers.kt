package com.rork.eduspark.data.remote.quiz

import com.rork.eduspark.data.model.FeedbackMode
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizAttempt
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.QuizResult

/** Option ids are zero-based indices as strings — matches backend `selected_index` submit. */
internal fun LessonQuizQuestionDto.toDomainQuestion(): QuizQuestion {
    val options = options.mapIndexed { index, text ->
        QuizOption(id = index.toString(), text = text)
    }
    val type = if (options.size == 2) QuestionType.TrueFalse else QuestionType.MultipleChoice
    return QuizQuestion(
        id = id.toString(),
        type = type,
        prompt = question,
        options = options,
        correctAnswer = "",
        explanation = hint.orEmpty(),
        hint = hint,
    )
}

internal fun LessonQuizGeneratedQuestionDto.toDomainQuestion(): QuizQuestion {
    val options = options.mapIndexed { index, text ->
        QuizOption(id = index.toString(), text = text)
    }
    val type = if (options.size == 2) QuestionType.TrueFalse else QuestionType.MultipleChoice
    val correctId = correctIndex.coerceIn(0, (options.size - 1).coerceAtLeast(0)).toString()
    return QuizQuestion(
        id = id,
        type = type,
        prompt = question,
        options = options,
        correctAnswer = correctId,
        explanation = hint.orEmpty(),
        hint = hint,
    )
}

internal fun List<LessonQuizQuestionDto>.toDomainQuiz(
    clientQuizId: String,
    lessonId: Int,
    lessonTitle: String = "الدرس",
    teacherName: String = "المعلم",
): Quiz = Quiz(
    id = clientQuizId,
    origin = QuizOrigin.AiLesson,
    lessonId = lessonId.toString(),
    lessonTitle = lessonTitle,
    title = "اختبار: $lessonTitle",
    teacherName = teacherName,
    feedbackMode = FeedbackMode.Deferred,
    timerSeconds = null,
    questions = map { it.toDomainQuestion() },
    isRemedial = false,
)

internal fun List<LessonQuizGeneratedQuestionDto>.toRemedialDomainQuiz(
    clientQuizId: String,
    lessonId: Int,
    lessonTitle: String,
    teacherName: String,
): Quiz = Quiz(
    id = clientQuizId,
    origin = QuizOrigin.AiLesson,
    lessonId = lessonId.toString(),
    lessonTitle = lessonTitle,
    title = lessonTitle,
    teacherName = teacherName,
    feedbackMode = FeedbackMode.Immediate,
    timerSeconds = null,
    questions = map { it.toDomainQuestion() },
    isRemedial = true,
)

/**
 * Packs shell option-id answers into backend `{ questionId: optionIndex }` form.
 * Unknown / non-index responses become `-1` (unanswered).
 */
internal fun Map<String, QuizAnswer>.toLessonQuizAnswerIndices(
    questions: List<QuizQuestion>,
): Map<String, Int> {
    val byId = questions.associateBy { it.id }
    return mapNotNull { (questionId, answer) ->
        val question = byId[questionId] ?: return@mapNotNull null
        val index = answer.response.trim().toIntOrNull()
            ?: question.options.indexOfFirst { it.id == answer.response }.takeIf { it >= 0 }
            ?: -1
        questionId to index
    }.toMap()
}

internal fun LessonQuizSubmitResponseDto.toQuizResult(
    quiz: Quiz,
    answers: Map<String, QuizAnswer>,
): QuizResult {
    val attempt = QuizAttempt(
        quizId = quiz.id,
        currentQuestionIndex = 0,
        answers = answers,
        isCompleted = true,
        attemptId = null,
    )
    val annotatedQuestions = quiz.questions.map { question ->
        val item = feedback.firstOrNull { it.questionId?.toString() == question.id }
        val response = answers[question.id]?.response.orEmpty()
        when {
            item == null -> question
            item.correct -> question.copy(
                correctAnswer = response.ifBlank { question.correctAnswer },
                explanation = item.message ?: question.explanation,
            )
            else -> question.copy(
                // Keep mismatch so ST-07 wrong-filter works; key not returned by submit.
                correctAnswer = if (response.isBlank()) "__unanswered__" else "__other__",
                explanation = item.message ?: item.hint ?: question.explanation,
                hint = item.hint ?: question.hint,
            )
        }
    }
    return QuizResult(
        quiz = quiz.copy(questions = annotatedQuestions),
        attempt = attempt,
        correctCount = correctCount,
        totalCount = total.coerceAtLeast(quiz.questions.size),
        xpEarned = 0,
        timeTakenSeconds = 0,
        scorePercent = scorePercent,
        passed = scorePercent >= 60,
        hasPendingEssay = false,
        earnedScore = correctCount.toFloat(),
        maxScore = total.toFloat(),
    )
}

internal fun clientScoreAiQuiz(quiz: Quiz, answers: Map<String, QuizAnswer>): QuizResult {
    val correctCount = quiz.questions.count { q ->
        val response = answers[q.id]?.response
        response != null && response.trim() == q.correctAnswer.trim()
    }
    val total = quiz.questions.size
    val percent = if (total == 0) 0 else ((correctCount * 100f) / total).toInt()
    return QuizResult(
        quiz = quiz,
        attempt = QuizAttempt(
            quizId = quiz.id,
            answers = answers,
            isCompleted = true,
        ),
        correctCount = correctCount,
        totalCount = total,
        xpEarned = correctCount * 10,
        timeTakenSeconds = 0,
        scorePercent = percent,
        passed = percent >= 60,
    )
}
