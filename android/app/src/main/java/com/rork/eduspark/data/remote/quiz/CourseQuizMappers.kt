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
import com.rork.eduspark.data.model.StudentCourseQuizSummary
import com.rork.eduspark.data.model.TeacherCourseQuizAnalytics
import com.rork.eduspark.data.model.TeacherEssayResponse
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAnalytics
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizStatus
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.floatOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put

internal const val BACKEND_TYPE_MULTIPLE_CHOICE = "multiple_choice"
internal const val BACKEND_TYPE_TRUE_FALSE = "true_false"
internal const val BACKEND_TYPE_SHORT_ANSWER = "short_answer"
internal const val BACKEND_TYPE_ESSAY = "essay"

internal fun StudentQuizTakeOutDto.toDomainQuiz(
    clientQuizId: String,
    teacherName: String = "المعلم",
): Quiz {
    val questions = questions
        .sortedBy { it.sortOrder }
        .map { it.toDomainQuestion() }
    return Quiz(
        id = clientQuizId,
        origin = QuizOrigin.TeacherManual,
        lessonId = quiz.courseId.toString(),
        lessonTitle = quiz.title,
        title = quiz.title,
        teacherName = teacherName,
        feedbackMode = FeedbackMode.Deferred,
        timerSeconds = timeRemainingSeconds,
        questions = questions,
        isRemedial = false,
    )
}

internal fun StudentQuizTakeOutDto.toDomainAnswers(): Map<String, QuizAnswer> =
    answers.mapNotNull { (questionId, raw) ->
        val response = unpackStudentResponse(raw) ?: return@mapNotNull null
        questionId to QuizAnswer(questionId = questionId, response = response)
    }.toMap()

internal fun QuizAttemptOutDto.toQuizResult(quiz: Quiz): QuizResult {
    val answerMap = answers.associate { row ->
        val qid = row.questionId.toString()
        qid to QuizAnswer(questionId = qid, response = unpackStudentResponse(row.answer).orEmpty())
    }
    val attempt = QuizAttempt(
        quizId = quiz.id,
        currentQuestionIndex = 0,
        answers = answerMap,
        isCompleted = true,
        attemptId = id.toString(),
    )
    val correctCount = answers.count { it.isCorrect == true }
    val totalCount = quiz.questions.size.coerceAtLeast(answers.size)
    val percent = percent?.toInt()
    val pending = answers.any { it.pendingGrading }
    return QuizResult(
        quiz = quiz,
        attempt = attempt,
        correctCount = correctCount,
        totalCount = totalCount,
        xpEarned = 0,
        timeTakenSeconds = 0,
        scorePercent = percent,
        passed = passed,
        hasPendingEssay = pending,
        earnedScore = score,
        maxScore = maxScore,
    )
}

internal fun CourseQuizOutDto.toTeacherQuiz(
    courseTitle: String,
    questions: List<TeacherQuizQuestion> = emptyList(),
): TeacherQuiz = TeacherQuiz(
    id = id.toString(),
    courseId = courseId.toString(),
    courseTitle = courseTitle,
    title = title,
    instructions = description.orEmpty(),
    status = if (isPublished) TeacherQuizStatus.Published else TeacherQuizStatus.Draft,
    questions = questions,
    durationMinutes = durationMinutes,
    passMarkPercent = passingScorePercent,
    singleAttempt = true,
)

internal fun CourseQuizDetailOutDto.toTeacherQuiz(courseTitle: String): TeacherQuiz =
    CourseQuizOutDto(
        id = id,
        courseId = courseId,
        title = title,
        description = description,
        durationMinutes = durationMinutes,
        passingScorePercent = passingScorePercent,
        isPublished = isPublished,
        dueAt = dueAt,
        questionCount = questionCount,
        totalPoints = totalPoints,
        attemptCount = attemptCount,
        createdAt = createdAt,
    ).toTeacherQuiz(
        courseTitle = courseTitle,
        questions = questions.sortedBy { it.sortOrder }.map { it.toTeacherQuizQuestion() },
    )

internal fun QuizQuestionOutDto.toTeacherQuizQuestion(): TeacherQuizQuestion {
    val domain = toDomainQuestion(includeCorrectAnswer = true)
    return TeacherQuizQuestion(
        question = domain,
        points = points,
        isAiOrigin = false,
    )
}

internal fun QuizQuestionStudentOutDto.toDomainQuestion(): QuizQuestion =
    mapQuestion(
        id = id.toString(),
        questionType = questionType,
        questionText = questionText,
        options = options,
        requiresManualGrading = requiresManualGrading,
        correctAnswerRaw = null,
    )

internal fun QuizQuestionOutDto.toDomainQuestion(includeCorrectAnswer: Boolean): QuizQuestion =
    mapQuestion(
        id = id.toString(),
        questionType = questionType,
        questionText = questionText,
        options = options,
        requiresManualGrading = requiresManualGrading,
        correctAnswerRaw = if (includeCorrectAnswer) correctAnswer else null,
    )

internal fun QuizAttemptSummaryOutDto.toTeacherQuizAttempt(
    detail: QuizAttemptOutDto? = null,
): TeacherQuizAttempt {
    val status = mapAttemptStatus(status)
    val essayFromDetail = detail?.toEssayResponses().orEmpty()
    val essays = if (essayFromDetail.isNotEmpty()) {
        essayFromDetail
    } else if (pendingEssayCount > 0) {
        // Placeholder pending slots until detail is loaded.
        (0 until pendingEssayCount).associate { index ->
            val key = "pending-$index"
            key to TeacherEssayResponse(questionId = key, studentText = "", pending = true)
        }
    } else {
        emptyMap()
    }
    val answers = detail?.toAutoAnswers().orEmpty()
    return TeacherQuizAttempt(
        studentId = studentId.toString(),
        studentName = studentName.ifBlank { detail?.studentName.orEmpty() },
        status = status,
        submittedLabel = submittedAt?.take(16)?.replace('T', ' '),
        answers = answers,
        essayResponses = essays,
        attemptId = id.toString(),
    )
}

internal fun QuizAttemptOutDto.toTeacherQuizAttempt(): TeacherQuizAttempt =
    TeacherQuizAttempt(
        studentId = studentId.toString(),
        studentName = studentName.orEmpty(),
        status = mapAttemptStatus(status),
        submittedLabel = submittedAt?.take(16)?.replace('T', ' '),
        answers = toAutoAnswers(),
        essayResponses = toEssayResponses(),
        attemptId = id.toString(),
    )

internal fun QuizAnalyticsOutDto.toDomain() = TeacherQuizAnalytics(
    quizId = quizId.toString(),
    quizTitle = quizTitle,
    enrolledStudents = enrolledStudents,
    attemptedCount = attemptedCount,
    completionRate = completionRate,
    averageScore = averageScore,
    highestScore = highestScore,
    lowestScore = lowestScore,
)

internal fun CourseQuizAnalyticsOutDto.toDomain() = TeacherCourseQuizAnalytics(
    courseId = courseId.toString(),
    courseTitle = courseTitle,
    quizCount = quizCount,
    enrolledStudents = enrolledStudents,
    totalAttempts = totalAttempts,
    averageScore = averageScore,
    completionRate = completionRate,
    quizzes = quizzes.map { it.toDomain() },
)

/** Pack a runner response into the backend answer payload. */
internal fun packAnswerForApi(questionType: QuestionType, response: String, backendType: String? = null): JsonElement {
    val trimmed = response.trim()
    val type = backendType ?: when (questionType) {
        QuestionType.MultipleChoice -> BACKEND_TYPE_MULTIPLE_CHOICE
        QuestionType.TrueFalse -> BACKEND_TYPE_TRUE_FALSE
        QuestionType.ShortAnswer, QuestionType.GapFill -> BACKEND_TYPE_SHORT_ANSWER
    }
    return when (type) {
        BACKEND_TYPE_MULTIPLE_CHOICE -> {
            val index = trimmed.toIntOrNull() ?: 0
            buildJsonObject {
                put("index", index)
                // Backend auto-grader reads selected_index for student answers.
                put("selected_index", index)
            }
        }
        BACKEND_TYPE_TRUE_FALSE -> JsonPrimitive(
            when (trimmed.lowercase()) {
                "true", "1", "صح" -> true
                else -> false
            },
        )
        else -> JsonPrimitive(trimmed)
    }
}

internal fun packCorrectAnswerForApi(
    backendType: String,
    correctAnswer: String,
    options: List<QuizOption>,
): JsonElement? = when (backendType) {
    BACKEND_TYPE_MULTIPLE_CHOICE -> {
        val index = options.indexOfFirst { it.id == correctAnswer }
            .takeIf { it >= 0 }
            ?: correctAnswer.toIntOrNull()
            ?: 0
        buildJsonObject { put("index", index) }
    }
    BACKEND_TYPE_TRUE_FALSE -> JsonPrimitive(
        when (correctAnswer.lowercase()) {
            "true", "1", "صح" -> true
            else -> false
        },
    )
    BACKEND_TYPE_SHORT_ANSWER -> JsonPrimitive(correctAnswer)
    BACKEND_TYPE_ESSAY -> null
    else -> JsonPrimitive(correctAnswer)
}

internal fun TeacherQuizQuestion.toCreateDto(sortOrder: Int): QuizQuestionCreateDto {
    val backendType = question.toBackendType()
    return QuizQuestionCreateDto(
        questionType = backendType,
        questionText = question.prompt,
        options = question.options.takeIf { it.isNotEmpty() }?.map { it.text },
        correctAnswer = packCorrectAnswerForApi(backendType, question.correctAnswer, question.options),
        points = points,
        sortOrder = sortOrder,
    )
}

internal fun TeacherQuizQuestion.toUpdateDto(sortOrder: Int): QuizQuestionUpdateDto {
    val backendType = question.toBackendType()
    return QuizQuestionUpdateDto(
        questionType = backendType,
        questionText = question.prompt,
        options = question.options.takeIf { it.isNotEmpty() }?.map { it.text },
        correctAnswer = packCorrectAnswerForApi(backendType, question.correctAnswer, question.options),
        points = points,
        sortOrder = sortOrder,
    )
}

internal fun QuizQuestion.toBackendType(): String = when (type) {
    QuestionType.MultipleChoice -> BACKEND_TYPE_MULTIPLE_CHOICE
    QuestionType.TrueFalse -> BACKEND_TYPE_TRUE_FALSE
    QuestionType.GapFill -> BACKEND_TYPE_SHORT_ANSWER
    QuestionType.ShortAnswer -> {
        if (correctAnswer.isBlank()) BACKEND_TYPE_ESSAY else BACKEND_TYPE_SHORT_ANSWER
    }
}

internal fun mapAttemptStatus(raw: String): TeacherQuizAttemptStatus = when (raw.lowercase()) {
    "in_progress" -> TeacherQuizAttemptStatus.NotSubmitted
    "submitted", "graded" -> TeacherQuizAttemptStatus.Completed
    else -> TeacherQuizAttemptStatus.NotSubmitted
}

internal fun isAttemptSubmittedStatus(raw: String?): Boolean {
    val status = raw?.lowercase() ?: return false
    return status == "submitted" || status == "graded"
}

private fun mapQuestion(
    id: String,
    questionType: String,
    questionText: String,
    options: List<String>,
    requiresManualGrading: Boolean,
    correctAnswerRaw: JsonElement?,
): QuizQuestion {
    val type = when {
        questionType == BACKEND_TYPE_MULTIPLE_CHOICE -> QuestionType.MultipleChoice
        questionType == BACKEND_TYPE_TRUE_FALSE -> QuestionType.TrueFalse
        // Essay and short_answer both surface as ShortAnswer in the runner UI.
        questionType == BACKEND_TYPE_ESSAY || requiresManualGrading -> QuestionType.ShortAnswer
        questionType == BACKEND_TYPE_SHORT_ANSWER -> QuestionType.ShortAnswer
        else -> QuestionType.ShortAnswer
    }
    val domainOptions = when (type) {
        QuestionType.TrueFalse -> listOf(
            QuizOption("true", options.getOrNull(0) ?: "صح"),
            QuizOption("false", options.getOrNull(1) ?: "خطأ"),
        )
        QuestionType.MultipleChoice -> options.mapIndexed { index, text ->
            QuizOption(id = index.toString(), text = text)
        }
        else -> emptyList()
    }
    val correct = unpackCorrectAnswer(type, correctAnswerRaw, domainOptions)
    return QuizQuestion(
        id = id,
        type = type,
        prompt = questionText,
        options = domainOptions,
        correctAnswer = correct,
        explanation = "",
        hint = null,
    )
}

private fun unpackCorrectAnswer(
    type: QuestionType,
    raw: JsonElement?,
    options: List<QuizOption>,
): String {
    if (raw == null || raw is JsonNull) return ""
    return when (type) {
        QuestionType.MultipleChoice -> {
            val index = raw.jsonObjectOrNull()
                ?.let { it["index"]?.jsonPrimitive?.intOrNull ?: it["correct_index"]?.jsonPrimitive?.intOrNull }
                ?: raw.jsonPrimitive.intOrNull
                ?: 0
            options.getOrNull(index)?.id ?: index.toString()
        }
        QuestionType.TrueFalse -> {
            val value = raw.jsonObjectOrNull()?.get("value")?.jsonPrimitive?.booleanOrNull
                ?: raw.jsonPrimitive.booleanOrNull
                ?: raw.jsonPrimitive.contentOrNull.equals("true", ignoreCase = true)
            if (value == true) "true" else "false"
        }
        else -> {
            raw.jsonObjectOrNull()?.get("text")?.jsonPrimitive?.contentOrNull
                ?: raw.jsonPrimitive.contentOrNull
                ?: ""
        }
    }
}

internal fun unpackStudentResponse(raw: JsonElement?): String? {
    if (raw == null || raw is JsonNull) return null
    val obj = raw.jsonObjectOrNull()
    if (obj != null) {
        obj["selected_index"]?.jsonPrimitive?.intOrNull?.let { return it.toString() }
        obj["index"]?.jsonPrimitive?.intOrNull?.let { return it.toString() }
        obj["value"]?.jsonPrimitive?.booleanOrNull?.let { return if (it) "true" else "false" }
        obj["text"]?.jsonPrimitive?.contentOrNull?.let { return it }
    }
    raw.jsonPrimitive.booleanOrNull?.let { return if (it) "true" else "false" }
    raw.jsonPrimitive.intOrNull?.let { return it.toString() }
    raw.jsonPrimitive.floatOrNull?.let { return it.toInt().toString() }
    return raw.jsonPrimitive.contentOrNull
}

private fun QuizAttemptOutDto.toEssayResponses(): Map<String, TeacherEssayResponse> =
    answers.filter { it.requiresManualGrading || it.questionType == BACKEND_TYPE_ESSAY }
        .associate { row ->
            val qid = row.questionId.toString()
            qid to TeacherEssayResponse(
                questionId = qid,
                studentText = unpackStudentResponse(row.answer).orEmpty(),
                pending = row.pendingGrading || row.pointsEarned == null,
                assignedMark = row.pointsEarned?.toInt(),
                teacherFeedback = row.teacherFeedback.orEmpty(),
            )
        }

private fun QuizAttemptOutDto.toAutoAnswers(): Map<String, Boolean> =
    answers.filterNot { it.requiresManualGrading || it.questionType == BACKEND_TYPE_ESSAY }
        .mapNotNull { row ->
            val correct = row.isCorrect ?: return@mapNotNull null
            row.questionId.toString() to correct
        }.toMap()

private fun JsonElement.jsonObjectOrNull(): JsonObject? =
    this as? JsonObject ?: runCatching { jsonObject }.getOrNull()

internal fun StudentQuizListItemDto.toStudentCourseQuizSummary(): StudentCourseQuizSummary =
    StudentCourseQuizSummary(
        id = id.toString(),
        courseId = courseId.toString(),
        title = title,
        questionCount = questionCount,
        durationMinutes = durationMinutes,
        attemptStatus = attemptStatus,
        scorePercent = percent?.toInt(),
        isCompleted = isAttemptSubmittedStatus(attemptStatus),
    )
