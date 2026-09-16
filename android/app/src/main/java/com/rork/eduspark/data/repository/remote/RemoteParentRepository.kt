package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentFeatureSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNotesFeed
import com.rork.eduspark.data.model.ParentNotificationSnapshot
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.parent.ParentLinkStudentRequestDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyCreateDto
import com.rork.eduspark.data.remote.parent.toDomain
import com.rork.eduspark.data.remote.parent.toFeatureSnapshot
import com.rork.eduspark.data.remote.parent.toInsightsSnapshot
import com.rork.eduspark.data.remote.parent.toLessonDetailsSnapshot
import com.rork.eduspark.data.remote.parent.toLessonProgressSnapshot
import com.rork.eduspark.data.remote.parent.toNotificationSnapshot
import com.rork.eduspark.data.remote.parent.toPerformanceSnapshot
import com.rork.eduspark.data.remote.parent.toSubjectsTeachersSnapshot
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal class RemoteParentRepository(
    private val api: ParentApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : ParentRepository {

    private val _linkedStudents = MutableStateFlow<List<ParentLinkedStudent>>(emptyList())
    override val linkedStudents: Flow<List<ParentLinkedStudent>> = _linkedStudents.asStateFlow()

    private val _selectedStudentId = MutableStateFlow<String?>(null)
    override val selectedStudentId: Flow<String?> = _selectedStudentId.asStateFlow()

    override suspend fun getLinkedStudents(): AppResult<List<ParentLinkedStudent>> =
        when (val response = authorizedRequest(api::students)) {
            is ApiCallResult.Success -> {
                val students = response.value.map { it.toDomain() }
                _linkedStudents.value = students
                if (_selectedStudentId.value == null || students.none { it.id == _selectedStudentId.value }) {
                    _selectedStudentId.value = students.firstOrNull()?.id
                }
                AppResult.Success(students)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun selectStudent(studentId: String): AppResult<ParentLinkedStudent> {
        val student = _linkedStudents.value.firstOrNull { it.id == studentId }
            ?: return AppResult.Failure(AppError.NotFound)
        _selectedStudentId.value = studentId
        return AppResult.Success(student)
    }

    override suspend fun getDashboard(studentId: String): AppResult<ParentDashboard> {
        val numericId = parseStudentId(studentId) ?: return AppResult.Failure(invalidStudentId())
        return when (val response = authorizedRequest { token -> api.dashboard(token, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.toDomain(includeInsights = false),
            )
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getCourseProgress(studentId: String): AppResult<List<ParentCourseProgress>> {
        val numericId = parseStudentId(studentId) ?: return AppResult.Failure(invalidStudentId())
        return when (val response = authorizedRequest { token -> api.courseProgress(token, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.map { it.toDomain() })
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getRecentActivity(
        studentId: String,
        limit: Int,
    ): AppResult<List<ParentActivity>> {
        val numericId = parseStudentId(studentId) ?: return AppResult.Failure(invalidStudentId())
        return when (val response = authorizedRequest { token -> api.activity(token, numericId, limit) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.map { it.toDomain() })
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getChildOverview(studentId: String): AppResult<ParentDashboard> {
        val overview = when (val dashboard = getDashboard(studentId)) {
            is AppResult.Success -> dashboard.data
            is AppResult.Failure -> return dashboard
        }
        val courses = when (val result = getCourseProgress(studentId)) {
            is AppResult.Success -> result.data
            is AppResult.Failure -> emptyList()
        }
        val activity = when (val result = getRecentActivity(studentId)) {
            is AppResult.Success -> result.data
            is AppResult.Failure -> emptyList()
        }
        return AppResult.Success(
            overview.copy(
                courseProgress = courses,
                recentActivity = activity,
                insights = emptyList(),
            ),
        )
    }

    override suspend fun getParentNotes(studentId: String, limit: Int): AppResult<ParentNotesFeed> {
        val numericId = parseStudentId(studentId) ?: return AppResult.Failure(invalidStudentId())
        return when (val response = authorizedRequest { token -> api.notes(token, numericId, limit) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun markParentNoteRead(noteId: String): AppResult<ParentNote> {
        val numericId = parseNoteId(noteId) ?: return AppResult.Failure(invalidNoteId())
        return when (val response = authorizedRequest { token -> api.markNoteRead(token, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun acknowledgeParentNote(noteId: String): AppResult<ParentNote> {
        val numericId = parseNoteId(noteId) ?: return AppResult.Failure(invalidNoteId())
        return when (val response = authorizedRequest { token -> api.acknowledgeNote(token, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun replyToParentNote(noteId: String, body: String): AppResult<ParentNote> {
        val numericId = parseNoteId(noteId) ?: return AppResult.Failure(invalidNoteId())
        val trimmed = body.trim()
        if (trimmed.isEmpty()) return AppResult.Failure(AppError.Validation(mapOf("body" to "empty_reply")))
        return when (
            val response = authorizedRequest {
                token -> api.replyToNote(token, numericId, ParentViewerNoteReplyCreateDto(body = trimmed))
            }
        ) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toDomain())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun linkStudent(code: String): AppResult<ParentLinkedStudent> {
        val normalized = code.trim().uppercase()
        if (normalized.isEmpty()) {
            return AppResult.Failure(AppError.Validation(mapOf("link_code" to "empty_code")))
        }
        if (normalized.length !in LINK_CODE_MIN_LENGTH..LINK_CODE_MAX_LENGTH) {
            return AppResult.Failure(AppError.Validation(mapOf("link_code" to "invalid_length")))
        }
        return when (
            val response = authorizedRequest {
                token -> api.linkStudent(token, ParentLinkStudentRequestDto(linkCode = normalized))
            }
        ) {
            is ApiCallResult.Success -> {
                val linkedId = response.value.studentId.toString()
                when (val students = getLinkedStudents()) {
                    is AppResult.Success -> {
                        val linked = students.data.firstOrNull { it.id == linkedId }
                            ?: return AppResult.Failure(AppError.NotFound)
                        selectStudent(linked.id)
                        AppResult.Success(linked)
                    }
                    is AppResult.Failure -> students
                }
            }
            else -> AppResult.Failure(linkFailure(response))
        }
    }

    override suspend fun getPerformanceSummary(studentId: String): AppResult<ParentFeatureSnapshot> =
        when (val courses = getCourseProgress(studentId)) {
            is AppResult.Success -> AppResult.Success(courses.data.toPerformanceSnapshot())
            is AppResult.Failure -> courses
        }

    override suspend fun getAttendanceStudyTime(studentId: String): AppResult<ParentFeatureSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.attendance(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(
                    response.value.toFeatureSnapshot(
                        title = "الحضور ووقت الدراسة",
                        subtitle = "متابعة انتظام الطالب وساعات التعلم",
                    ),
                )
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getLessonProgress(studentId: String): AppResult<ParentLessonProgressSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.lessonProgress(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(response.value.toLessonProgressSnapshot())
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getLessonDetails(studentId: String, lessonId: String): AppResult<ParentLessonDetails> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.lessonDetails(token, numericId, lessonId) }) {
                is ApiCallResult.Success -> AppResult.Success(response.value.toLessonDetailsSnapshot(lessonId))
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getSubjectsTeachers(studentId: String): AppResult<ParentSubjectsTeachersSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.subjectsTeachers(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(response.value.toSubjectsTeachersSnapshot())
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getPlannerSnapshot(studentId: String): AppResult<ParentFeatureSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.plannerProgress(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(
                    response.value.toFeatureSnapshot(
                        title = "الخطة الأسبوعية",
                        subtitle = "جلسات الطالب وروتين الدراسة من الخادم",
                    ),
                )
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getInsightsSnapshot(studentId: String): AppResult<ParentFeatureSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val insights = authorizedRequest { token -> api.insights(token, numericId) }) {
                is ApiCallResult.Success -> {
                    val academic = when (
                        val response = authorizedRequest { token -> api.academicIntelligence(token, numericId) }
                    ) {
                        is ApiCallResult.Success -> response.value
                        else -> null
                    }
                    AppResult.Success(insights.value.toInsightsSnapshot(academic))
                }
                else -> AppResult.Failure(handleFailure(insights))
            }
        }

    override suspend fun getReportsSnapshot(studentId: String): AppResult<ParentFeatureSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.historicalReport(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(
                    response.value.toFeatureSnapshot(
                        title = "التقارير",
                        subtitle = "تقرير متابعة قابل للمراجعة من بيانات الطالب",
                    ),
                )
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getNotificationsSnapshot(studentId: String): AppResult<ParentNotificationSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val notifications = authorizedRequest { token -> api.notifications(token, numericId) }) {
                is ApiCallResult.Success -> {
                    val settings = when (
                        val response = authorizedRequest { token -> api.notificationSettings(token, numericId) }
                    ) {
                        is ApiCallResult.Success -> response.value
                        else -> null
                    }
                    AppResult.Success(notifications.value.toNotificationSnapshot(settings))
                }
                else -> AppResult.Failure(handleFailure(notifications))
            }
        }

    private fun parseStudentId(studentId: String): Int? = studentId.toIntOrNull()?.takeIf { it > 0 }

    private fun parseNoteId(noteId: String): Int? = noteId.toIntOrNull()?.takeIf { it > 0 }

    private fun invalidStudentId() = AppError.Validation(mapOf("studentId" to "invalid_student_id"))

    private fun invalidNoteId() = AppError.Validation(mapOf("noteId" to "invalid_note_id"))

    private suspend fun <T> withStudentId(
        studentId: String,
        block: suspend (Int) -> AppResult<T>,
    ): AppResult<T> {
        val numericId = parseStudentId(studentId) ?: return AppResult.Failure(invalidStudentId())
        return block(numericId)
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
            is ApiCallResult.HttpFailure -> when {
                response.statusCode == 401 -> AppError.SessionExpired
                !response.detail.isNullOrBlank() -> AppError.Domain(response.detail)
                response.statusCode == 403 -> AppError.Forbidden
                response.statusCode == 404 || response.statusCode == 410 -> AppError.NotFound
                response.statusCode == 422 -> AppError.Validation(response.fieldErrors)
                response.statusCode in 500..599 -> AppError.Server
                else -> AppError.Domain("parent_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }

    private suspend fun linkFailure(response: ApiCallResult<*>): AppError {
        if (response is ApiCallResult.HttpFailure && response.statusCode != 401 && !response.detail.isNullOrBlank()) {
            return AppError.Domain(response.detail)
        }
        return handleFailure(response)
    }

    private companion object {
        const val LINK_CODE_MIN_LENGTH = 6
        const val LINK_CODE_MAX_LENGTH = 16
    }
}
