package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.teacher.ParentNoteReplyCreateDto
import com.rork.eduspark.data.remote.teacher.TeacherParentNotesApi
import com.rork.eduspark.data.remote.teacher.buildParentNoteCreateBody
import com.rork.eduspark.data.remote.teacher.parseTeacherStudentNumericId
import com.rork.eduspark.data.remote.teacher.toTeacherParentNote
import com.rork.eduspark.data.remote.teacher.toTeacherParentNotes
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository

/**
 * Keeps the full [TeacherRepository] surface on [delegate] (typically MOCK for A2 teacher
 * product data) while routing parent-note list/create/reply/close to the hosted FastAPI.
 */
internal class TeacherRepositoryWithRemoteParentNotes(
    private val delegate: TeacherRepository,
    private val api: TeacherParentNotesApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : TeacherRepository by delegate {

    override suspend fun getParentNotes(studentId: String): AppResult<List<TeacherParentNote>> {
        val numericId = parseTeacherStudentNumericId(studentId)
            ?: return AppResult.Failure(AppError.Domain("invalid_student_id"))
        return when (val response = authorizedRequest { api.list(it, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toTeacherParentNotes(studentId))
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun sendParentNote(studentId: String, message: String): AppResult<TeacherParentNote> {
        val numericId = parseTeacherStudentNumericId(studentId)
            ?: return AppResult.Failure(AppError.Domain("invalid_student_id"))
        val trimmed = message.trim()
        if (trimmed.isEmpty()) return AppResult.Failure(AppError.Domain("empty_parent_note"))

        val openNoteId = when (val listed = authorizedRequest { api.list(it, numericId) }) {
            is ApiCallResult.Success -> listed.value.notes
                .sortedByDescending { it.createdAt }
                .firstOrNull { !it.isClosed && it.canReply && it.status != "closed" }
                ?.id
            else -> null
        }

        val response = if (openNoteId != null) {
            authorizedRequest {
                api.reply(it, numericId, openNoteId, ParentNoteReplyCreateDto(body = trimmed))
            }
        } else {
            authorizedRequest {
                api.create(it, numericId, buildParentNoteCreateBody(trimmed))
            }
        }

        return when (response) {
            is ApiCallResult.Success -> {
                val note = response.value
                val latestReply = note.replies.maxByOrNull { it.createdAt }
                val mapped = if (openNoteId != null && latestReply != null) {
                    TeacherParentNote(
                        id = "reply-${latestReply.id}",
                        studentId = studentId,
                        message = latestReply.body,
                        sentLabel = latestReply.createdAt.take(16).replace('T', ' '),
                    )
                } else {
                    note.toTeacherParentNote(studentId)
                }
                AppResult.Success(mapped)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun closeParentNote(studentId: String, noteId: String): AppResult<TeacherParentNote> {
        val numericStudentId = parseTeacherStudentNumericId(studentId)
            ?: return AppResult.Failure(AppError.Domain("invalid_student_id"))
        val numericNoteId = noteId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_note_id"))
        return when (
            val response = authorizedRequest { api.close(it, numericStudentId, numericNoteId) }
        ) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toTeacherParentNote(studentId))
            else -> AppResult.Failure(handleFailure(response))
        }
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
                else -> AppError.Domain(response.detail ?: "parent_note_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
