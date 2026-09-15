package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNotesFeed
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyCreateDto
import com.rork.eduspark.data.remote.parent.toDomain
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

    private fun parseStudentId(studentId: String): Int? = studentId.toIntOrNull()?.takeIf { it > 0 }

    private fun parseNoteId(noteId: String): Int? = noteId.toIntOrNull()?.takeIf { it > 0 }

    private fun invalidStudentId() = AppError.Validation(mapOf("studentId" to "invalid_student_id"))

    private fun invalidNoteId() = AppError.Validation(mapOf("noteId" to "invalid_note_id"))

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
                else -> AppError.Domain(response.detail ?: "parent_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
