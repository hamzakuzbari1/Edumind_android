package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.TeacherCourseQuizAnalytics
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAnalytics
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.quiz.CourseQuizApi
import com.rork.eduspark.data.remote.quiz.CourseQuizCreateDto
import com.rork.eduspark.data.remote.quiz.CourseQuizUpdateDto
import com.rork.eduspark.data.remote.quiz.GradeEssayRequestDto
import com.rork.eduspark.data.remote.quiz.toCreateDto
import com.rork.eduspark.data.remote.quiz.toDomain
import com.rork.eduspark.data.remote.quiz.toTeacherQuiz
import com.rork.eduspark.data.remote.quiz.toTeacherQuizAttempt
import com.rork.eduspark.data.remote.quiz.toUpdateDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository

/**
 * Routes TC-10/TC-11 manual quiz methods to FastAPI while keeping the rest of
 * [TeacherRepository] on [delegate] (typically mock + optional parent-notes wrapper).
 */
internal class TeacherRepositoryWithRemoteQuizzes(
    private val delegate: TeacherRepository,
    private val api: CourseQuizApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : TeacherRepository by delegate {

    private val quizCourseIds = mutableMapOf<String, String>()
    private val quizCourseTitles = mutableMapOf<String, String>()
    private val cachedAttempts = mutableMapOf<String, List<TeacherQuizAttempt>>()

    override suspend fun getQuizzes(teacherId: String): AppResult<List<TeacherQuiz>> {
        val courses = when (val listed = delegate.getCourses(teacherId)) {
            is AppResult.Success -> listed.data
            is AppResult.Failure -> return listed
        }
        val quizzes = mutableListOf<TeacherQuiz>()
        for (course in courses) {
            val courseNumeric = parseCourseNumericId(course.id) ?: continue
            when (val response = authorizedRequest { api.listTeacherQuizzes(it, courseNumeric) }) {
                is ApiCallResult.Success -> {
                    for (dto in response.value) {
                        rememberCourse(dto.id.toString(), course.id, course.title)
                        quizzes += dto.toTeacherQuiz(courseTitle = course.title)
                    }
                }
                else -> return AppResult.Failure(handleFailure(response))
            }
        }
        return AppResult.Success(quizzes)
    }

    override suspend fun getQuiz(quizId: String): AppResult<TeacherQuiz> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        return when (val response = authorizedRequest { api.getQuizDetail(it, courseNumeric, quizNumeric) }) {
            is ApiCallResult.Success -> {
                val title = quizCourseTitles[quizId].orEmpty().ifBlank {
                    // Prefer cached title; fall back to course id label.
                    courseId
                }
                rememberCourse(quizId, courseId, title)
                AppResult.Success(
                    response.value.toTeacherQuiz(courseTitle = title).copy(courseId = courseId),
                )
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun createQuiz(courseId: String): AppResult<TeacherQuiz> {
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val courseTitle = when (val courses = delegate.getCourses("")) {
            is AppResult.Success -> courses.data.firstOrNull { it.id == courseId }?.title.orEmpty()
            is AppResult.Failure -> ""
        }
        val body = CourseQuizCreateDto(title = "كويز جديد", passingScorePercent = 60)
        return when (val created = authorizedRequest { api.createQuiz(it, courseNumeric, body) }) {
            is ApiCallResult.Success -> {
                val quizId = created.value.id
                rememberCourse(quizId.toString(), courseId, courseTitle)
                when (val detail = authorizedRequest { api.getQuizDetail(it, courseNumeric, quizId) }) {
                    is ApiCallResult.Success -> AppResult.Success(
                        detail.value.toTeacherQuiz(courseTitle = courseTitle).copy(courseId = courseId),
                    )
                    else -> AppResult.Success(
                        created.value.toTeacherQuiz(courseTitle = courseTitle).copy(courseId = courseId),
                    )
                }
            }
            else -> AppResult.Failure(handleFailure(created))
        }
    }

    override suspend fun saveQuizMetadata(
        quizId: String,
        title: String,
        instructions: String,
        durationMinutes: Int?,
        passMarkPercent: Int,
        singleAttempt: Boolean,
    ): AppResult<TeacherQuiz> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        // singleAttempt ignored — backend always enforces one completed attempt.
        val body = CourseQuizUpdateDto(
            title = title,
            description = instructions,
            durationMinutes = durationMinutes,
            passingScorePercent = passMarkPercent,
        )
        return when (val updated = authorizedRequest { api.updateQuiz(it, courseNumeric, quizNumeric, body) }) {
            is ApiCallResult.Success -> {
                val courseTitle = quizCourseTitles[quizId].orEmpty()
                when (val detail = authorizedRequest { api.getQuizDetail(it, courseNumeric, quizNumeric) }) {
                    is ApiCallResult.Success -> AppResult.Success(detail.value.toTeacherQuiz(courseTitle))
                    else -> AppResult.Success(updated.value.toTeacherQuiz(courseTitle))
                }
            }
            else -> AppResult.Failure(handleFailure(updated))
        }
    }

    override suspend fun publishQuiz(quizId: String): AppResult<TeacherQuiz> {
        val existing = when (val quiz = getQuiz(quizId)) {
            is AppResult.Success -> quiz.data
            is AppResult.Failure -> return quiz
        }
        if (existing.title.isBlank() || existing.questions.isEmpty()) {
            return AppResult.Failure(AppError.Validation(mapOf("publish" to "quiz_incomplete")))
        }
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        val body = CourseQuizUpdateDto(isPublished = true)
        return when (val updated = authorizedRequest { api.updateQuiz(it, courseNumeric, quizNumeric, body) }) {
            is ApiCallResult.Success -> {
                val courseTitle = quizCourseTitles[quizId].orEmpty()
                when (val detail = authorizedRequest { api.getQuizDetail(it, courseNumeric, quizNumeric) }) {
                    is ApiCallResult.Success -> AppResult.Success(
                        detail.value.toTeacherQuiz(courseTitle).copy(status = TeacherQuizStatus.Published),
                    )
                    else -> AppResult.Success(
                        updated.value.toTeacherQuiz(courseTitle).copy(status = TeacherQuizStatus.Published),
                    )
                }
            }
            else -> AppResult.Failure(handleFailure(updated))
        }
    }

    override suspend fun saveQuizQuestions(
        quizId: String,
        questions: List<TeacherQuizQuestion>,
    ): AppResult<TeacherQuiz> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))

        val detail = when (val response = authorizedRequest { api.getQuizDetail(it, courseNumeric, quizNumeric) }) {
            is ApiCallResult.Success -> response.value
            else -> return AppResult.Failure(handleFailure(response))
        }

        val remoteIds = detail.questions.map { it.id }.toSet()
        val desiredNumericIds = questions.mapNotNull { it.question.id.toIntOrNull() }.toSet()
        val toDelete = remoteIds - desiredNumericIds
        for (questionId in toDelete) {
            when (val deleted = authorizedRequest { api.deleteQuestion(it, courseNumeric, quizNumeric, questionId) }) {
                is ApiCallResult.Success -> Unit
                else -> return AppResult.Failure(handleFailure(deleted))
            }
        }

        questions.forEachIndexed { index, row ->
            val existingId = row.question.id.toIntOrNull()
            if (existingId != null && existingId in remoteIds) {
                when (
                    val updated = authorizedRequest {
                        api.updateQuestion(it, courseNumeric, quizNumeric, existingId, row.toUpdateDto(index))
                    }
                ) {
                    is ApiCallResult.Success -> Unit
                    else -> return AppResult.Failure(handleFailure(updated))
                }
            } else {
                when (
                    val created = authorizedRequest {
                        api.addQuestion(it, courseNumeric, quizNumeric, row.toCreateDto(index))
                    }
                ) {
                    is ApiCallResult.Success -> Unit
                    else -> return AppResult.Failure(handleFailure(created))
                }
            }
        }

        return getQuiz(quizId)
    }

    override suspend fun getQuizAttempts(quizId: String): AppResult<List<TeacherQuizAttempt>> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))

        val results = when (val response = authorizedRequest { api.getResults(it, courseNumeric, quizNumeric) }) {
            is ApiCallResult.Success -> response.value
            else -> return AppResult.Failure(handleFailure(response))
        }
        rememberCourse(quizId, courseId, quizCourseTitles[quizId].orEmpty())

        val attempts = results.attempts.map { summary ->
            val needsDetail = summary.pendingEssayCount > 0 ||
                summary.status.equals("submitted", ignoreCase = true) ||
                summary.status.equals("graded", ignoreCase = true)
            val detail = if (needsDetail) {
                when (
                    val attempt = authorizedRequest {
                        api.getTeacherAttempt(it, courseNumeric, quizNumeric, summary.id)
                    }
                ) {
                    is ApiCallResult.Success -> attempt.value
                    else -> null
                }
            } else {
                null
            }
            summary.toTeacherQuizAttempt(detail)
        }
        cachedAttempts[quizId] = attempts
        return AppResult.Success(attempts)
    }

    override suspend fun saveEssayGrade(
        quizId: String,
        studentId: String,
        questionId: String,
        assignedMark: Int,
        feedback: String,
    ): AppResult<TeacherQuizAttempt> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        val questionNumeric = questionId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_question_id"))

        val attempts = cachedAttempts[quizId] ?: when (val listed = getQuizAttempts(quizId)) {
            is AppResult.Success -> listed.data
            is AppResult.Failure -> return listed
        }
        val attempt = attempts.firstOrNull { it.studentId == studentId }
            ?: return AppResult.Failure(AppError.NotFound)
        val attemptId = attempt.attemptId?.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("missing_attempt_id"))

        val body = GradeEssayRequestDto(
            pointsEarned = assignedMark.toFloat(),
            teacherFeedback = feedback,
            publish = true,
        )
        return when (
            val graded = authorizedRequest {
                api.gradeEssay(it, courseNumeric, quizNumeric, attemptId, questionNumeric, body)
            }
        ) {
            is ApiCallResult.Success -> {
                val mapped = graded.value.toTeacherQuizAttempt()
                cachedAttempts[quizId] = attempts.map {
                    if (it.studentId == studentId) mapped else it
                }
                AppResult.Success(mapped)
            }
            else -> AppResult.Failure(handleFailure(graded))
        }
    }

    override suspend fun getQuizAnalytics(quizId: String): AppResult<TeacherQuizAnalytics> {
        val courseId = resolveCourseId(quizId)
            ?: return AppResult.Failure(AppError.Domain("unknown_quiz_course"))
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val quizNumeric = quizId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        return when (val response = authorizedRequest { api.getQuizAnalytics(it, courseNumeric, quizNumeric) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getCourseQuizAnalytics(courseId: String): AppResult<TeacherCourseQuizAnalytics> {
        val courseNumeric = parseCourseNumericId(courseId)
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return when (val response = authorizedRequest { api.getCourseQuizAnalytics(it, courseNumeric) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun generateAiQuizQuestionCandidates(quizId: String): AppResult<List<TeacherQuizQuestion>> =
        delegate.generateAiQuizQuestionCandidates(quizId)

    private fun rememberCourse(quizId: String, courseId: String, courseTitle: String) {
        quizCourseIds[quizId] = courseId
        if (courseTitle.isNotBlank()) quizCourseTitles[quizId] = courseTitle
    }

    private suspend fun resolveCourseId(quizId: String): String? {
        quizCourseIds[quizId]?.let { return it }
        // Last resort: scan courses via delegate and list quizzes until found.
        val courses = when (val listed = delegate.getCourses("")) {
            is AppResult.Success -> listed.data
            is AppResult.Failure -> return null
        }
        for (course in courses) {
            val courseNumeric = parseCourseNumericId(course.id) ?: continue
            when (val response = authorizedRequest { api.listTeacherQuizzes(it, courseNumeric) }) {
                is ApiCallResult.Success -> {
                    val match = response.value.firstOrNull { it.id.toString() == quizId }
                    if (match != null) {
                        rememberCourse(quizId, course.id, course.title)
                        return course.id
                    }
                }
                else -> Unit
            }
        }
        return null
    }

    private fun parseCourseNumericId(courseId: String): Int? {
        courseId.toIntOrNull()?.takeIf { it > 0 }?.let { return it }
        val digits = courseId.filter { it.isDigit() }
        return digits.toIntOrNull()?.takeIf { it > 0 }
    }

    private suspend fun <T> authorizedRequest(
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = tokenStore.read() ?: return ApiCallResult.HttpFailure(401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> call(refreshed.data.accessToken)
            is AppResult.Failure -> ApiCallResult.HttpFailure(401)
        }
    }

    private suspend fun handleFailure(response: ApiCallResult<*>): AppError {
        val error = when (response) {
            ApiCallResult.NetworkFailure -> AppError.Network
            ApiCallResult.InvalidResponse -> AppError.Unknown
            is ApiCallResult.Success -> AppError.Unknown
            is ApiCallResult.HttpFailure -> when (response.statusCode) {
                401 -> AppError.SessionExpired
                403 -> AppError.Forbidden
                404, 410 -> AppError.NotFound
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "quiz_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
