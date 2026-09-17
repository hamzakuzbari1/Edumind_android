package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentAiInsightsSnapshot
import com.rork.eduspark.data.model.ParentAlertPreferenceKey
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNotesFeed
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPlannerSnapshot
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportExport
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.parent.ParentLinkStudentRequestDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyCreateDto
import com.rork.eduspark.data.remote.parent.buildAlertsSnapshot
import com.rork.eduspark.data.remote.parent.buildAiInsightsSnapshot
import com.rork.eduspark.data.remote.parent.buildAttendanceSnapshot
import com.rork.eduspark.data.remote.parent.buildPerformanceSnapshot
import com.rork.eduspark.data.remote.parent.toAiInsightsSnapshot
import com.rork.eduspark.data.remote.parent.toDashboardSnapshot
import com.rork.eduspark.data.remote.parent.toDomain
import com.rork.eduspark.data.remote.parent.toLessonDetails
import com.rork.eduspark.data.remote.parent.toLessonProgressSnapshot
import com.rork.eduspark.data.remote.parent.toPlannerSnapshot
import com.rork.eduspark.data.remote.parent.toReportsSnapshot
import com.rork.eduspark.data.remote.parent.toSubjectsTeachersSnapshot
import com.rork.eduspark.data.remote.parent.toUpdateDto
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

    private val _unreadAlertCount = MutableStateFlow(0)
    override val unreadAlertCount: Flow<Int> = _unreadAlertCount.asStateFlow()

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

    override suspend fun getDashboardSnapshot(studentId: String): AppResult<ParentDashboardSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.dashboard(token, numericId) }) {
                is ApiCallResult.Success -> {
                    val alerts = authorizedRequest { token -> api.notifications(token, numericId) }
                    val unread = (alerts as? ApiCallResult.Success)?.value?.unreadCount ?: 0
                    _unreadAlertCount.value = unread
                    val latestNote = authorizedRequest { token -> api.notes(token, numericId, limit = 1) }
                        .valueOrNull()
                        ?.notes
                        ?.firstOrNull()
                        ?.toDomain()
                    AppResult.Success(
                        response.value.toDashboardSnapshot(
                            alertCount = unread,
                            latestTeacherNote = latestNote,
                        ),
                    )
                }
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getPerformanceSnapshot(studentId: String): AppResult<ParentPerformanceSnapshot> =
        withStudentId(studentId) { numericId ->
            when (
                val academic = authorizedRequest { token -> api.academicIntelligence(token, numericId) }
            ) {
                is ApiCallResult.Success -> AppResult.Success(
                    buildPerformanceSnapshot(
                        academic = academic.value,
                        quiz = authorizedRequest { token -> api.quizTracking(token, numericId) }.valueOrNull(),
                        report = authorizedRequest { token ->
                            api.historicalReport(token, numericId, period = ParentReportPeriod.ThisMonth.apiValue)
                        }.valueOrNull(),
                        lessonProgress = authorizedRequest { token -> api.lessonProgress(token, numericId) }
                            .valueOrNull(),
                        gamification = authorizedRequest { token -> api.dashboard(token, numericId) }
                            .valueOrNull()
                            ?.gamification,
                    ),
                )
                else -> AppResult.Failure(handleFailure(academic))
            }
        }

    override suspend fun getAttendanceStudyTime(studentId: String): AppResult<ParentAttendanceStudyTimeSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.attendance(token, numericId) }) {
                is ApiCallResult.Success -> {
                    val analytics = authorizedRequest { token ->
                        api.activityTrackingAnalytics(token, numericId)
                    }.valueOrNull()
                    val sessions = authorizedRequest { token ->
                        api.activityTrackingSessions(token, numericId)
                    }.valueOrNull().orEmpty()
                    AppResult.Success(
                        buildAttendanceSnapshot(
                            attendance = response.value,
                            analytics = analytics,
                            activitySessions = sessions,
                        ),
                    )
                }
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
                is ApiCallResult.Success -> AppResult.Success(response.value.toLessonDetails())
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

    override suspend fun getPlannerSnapshot(studentId: String): AppResult<ParentPlannerSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val response = authorizedRequest { token -> api.plannerProgress(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(
                    response.value.toPlannerSnapshot(
                        routine = authorizedRequest { token -> api.studentRoutine(token, numericId) }.valueOrNull(),
                    ),
                )
                else -> AppResult.Failure(handleFailure(response))
            }
        }

    override suspend fun getAiInsightsSnapshot(studentId: String): AppResult<ParentAiInsightsSnapshot> =
        withStudentId(studentId) { numericId ->
            when (val executive = authorizedRequest { token -> api.executiveSummary(token, numericId) }) {
                is ApiCallResult.Success -> AppResult.Success(
                    executive.value.toAiInsightsSnapshot(
                        extraInsights = authorizedRequest { token -> api.insights(token, numericId) }
                            .valueOrNull()
                            .orEmpty(),
                        academic = authorizedRequest { token -> api.academicIntelligence(token, numericId) }
                            .valueOrNull(),
                        attendance = authorizedRequest { token -> api.attendance(token, numericId) }
                            .valueOrNull(),
                    ),
                )
                else -> {
                    val extraInsights = authorizedRequest { token -> api.insights(token, numericId) }
                        .valueOrNull()
                        .orEmpty()
                    val academic = authorizedRequest { token -> api.academicIntelligence(token, numericId) }
                        .valueOrNull()
                    val attendance = authorizedRequest { token -> api.attendance(token, numericId) }
                        .valueOrNull()
                    val fallback = buildAiInsightsSnapshot(extraInsights, academic, attendance)
                    if (fallback.hasData) {
                        AppResult.Success(fallback)
                    } else {
                        AppResult.Failure(handleFailure(executive))
                    }
                }
            }
        }

    override suspend fun getReportsSnapshot(
        studentId: String,
        period: ParentReportPeriod,
        customDateRange: ParentReportDateRange?,
    ): AppResult<ParentReportsSnapshot> = withStudentId(studentId) { numericId ->
        val range = customDateRange.takeIf { period == ParentReportPeriod.Custom }
        when (
            val response = authorizedRequest { token ->
                api.historicalReport(
                    accessToken = token,
                    studentId = numericId,
                    period = period.apiValue,
                    startDate = range?.startDateMillis?.let(::formatIsoDate),
                    endDate = range?.endDateMillis?.let(::formatIsoDate),
                )
            }
        ) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toReportsSnapshot())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun exportHistoricalReport(
        studentId: String,
        period: ParentReportPeriod,
        customDateRange: ParentReportDateRange?,
        format: String,
    ): AppResult<ParentReportExport> = withStudentId(studentId) { numericId ->
        val range = customDateRange.takeIf { period == ParentReportPeriod.Custom }
        when (
            val response = authorizedRequest { token ->
                api.exportHistoricalReport(
                    accessToken = token,
                    studentId = numericId,
                    period = period.apiValue,
                    startDate = range?.startDateMillis?.let(::formatIsoDate),
                    endDate = range?.endDateMillis?.let(::formatIsoDate),
                    format = format,
                )
            }
        ) {
            is ApiCallResult.Success -> AppResult.Success(
                ParentReportExport(
                    bytes = response.value.bytes,
                    filename = response.value.filename,
                    mimeType = response.value.mimeType,
                ),
            )
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getAlertsSnapshot(studentId: String): AppResult<ParentAlertsSnapshot> =
        withStudentId(studentId) { numericId -> loadAlerts(numericId) }

    override suspend fun markParentAlertRead(
        studentId: String,
        alertId: String,
    ): AppResult<ParentAlertsSnapshot> = withStudentId(studentId) { numericId ->
        val numericAlertId = alertId.toIntOrNull()?.takeIf { it > 0 }
            ?: return@withStudentId AppResult.Failure(AppError.Validation(mapOf("alertId" to "invalid_alert_id")))
        when (
            val response = authorizedRequest { token ->
                api.markNotificationRead(token, numericId, numericAlertId)
            }
        ) {
            is ApiCallResult.Success -> loadAlerts(numericId)
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun markAllParentAlertsRead(studentId: String): AppResult<ParentAlertsSnapshot> =
        withStudentId(studentId) { numericId ->
            val current = when (val snapshot = loadAlerts(numericId)) {
                is AppResult.Success -> snapshot.data
                is AppResult.Failure -> return@withStudentId snapshot
            }
            current.alerts.filter { it.isUnread }.forEach { alert ->
                val numericAlertId = alert.id.toIntOrNull() ?: return@forEach
                authorizedRequest { token -> api.markNotificationRead(token, numericId, numericAlertId) }
            }
            loadAlerts(numericId)
        }

    override suspend fun setParentAlertPreferenceEnabled(
        studentId: String,
        key: ParentAlertPreferenceKey,
        enabled: Boolean,
    ): AppResult<ParentAlertsSnapshot> = withStudentId(studentId) { numericId ->
        when (
            val response = authorizedRequest { token ->
                api.updateNotificationSettings(token, numericId, key.toUpdateDto(enabled))
            }
        ) {
            is ApiCallResult.Success -> loadAlerts(numericId)
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private suspend fun loadAlerts(numericId: Int): AppResult<ParentAlertsSnapshot> =
        when (val notifications = authorizedRequest { token -> api.notifications(token, numericId) }) {
            is ApiCallResult.Success -> {
                val settings = authorizedRequest { token -> api.notificationSettings(token, numericId) }
                    .valueOrNull()
                _unreadAlertCount.value = notifications.value.unreadCount
                AppResult.Success(buildAlertsSnapshot(notifications.value, settings))
            }
            else -> AppResult.Failure(handleFailure(notifications))
        }

    private fun <T> ApiCallResult<T>.valueOrNull(): T? = (this as? ApiCallResult.Success)?.value

    private fun formatIsoDate(epochMillis: Long): String =
        java.time.Instant.ofEpochMilli(epochMillis)
            .atZone(java.time.ZoneId.systemDefault())
            .toLocalDate()
            .toString()

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
