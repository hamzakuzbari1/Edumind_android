package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.teacher.TeacherLessonUploadApi
import com.rork.eduspark.data.remote.teacher.TeacherLessonUploadAssetType
import com.rork.eduspark.data.remote.teacher.TeacherLessonUploadFilePart
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherLessonSelectedFile
import com.rork.eduspark.data.repository.TeacherLessonUploadKind
import com.rork.eduspark.data.repository.TeacherLessonUploadRepository

internal class RemoteTeacherLessonUploadRepository(
    private val api: TeacherLessonUploadApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : TeacherLessonUploadRepository {

    override suspend fun uploadLessonFile(
        courseId: String,
        title: String,
        order: Int,
        file: TeacherLessonSelectedFile,
        kind: TeacherLessonUploadKind,
        generateQuiz: Boolean,
        generateNarration: Boolean,
        indexForTutor: Boolean,
    ): AppResult<TeacherLessonUploadDraft> {
        val numericCourseId = courseId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val response = authorizedRequest {
            api.createLessonWithFile(
                accessToken = it,
                courseId = numericCourseId,
                title = title,
                order = order,
                file = TeacherLessonUploadFilePart(
                    assetType = kind.toRemoteType(),
                    bytes = file.bytes,
                    filename = file.filename,
                    mimeType = file.mimeType,
                ),
            )
        }
        return when (response) {
            is ApiCallResult.Success -> AppResult.Success(
                TeacherLessonUploadDraft(
                    courseId = courseId,
                    contentType = if (kind == TeacherLessonUploadKind.Video) LessonContentType.Video else LessonContentType.Pdf,
                    mockFileName = file.filename,
                    mockTotalBytes = file.sizeBytes,
                    title = response.value.title.ifBlank { title },
                    order = order,
                    generateQuiz = generateQuiz,
                    generateNarration = generateNarration,
                    indexForTutor = indexForTutor,
                    uploadedBytes = file.sizeBytes,
                    stage = LessonUploadStage.Completed,
                    createdLessonId = response.value.id.toString(),
                ),
            )
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
                413 -> AppError.Domain("file_too_large")
                415 -> AppError.Domain("unsupported_file_type")
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "lesson_upload_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private fun TeacherLessonUploadKind.toRemoteType(): TeacherLessonUploadAssetType = when (this) {
    TeacherLessonUploadKind.Video -> TeacherLessonUploadAssetType.Video
    TeacherLessonUploadKind.Pdf -> TeacherLessonUploadAssetType.Pdf
    TeacherLessonUploadKind.Homework -> TeacherLessonUploadAssetType.Homework
    TeacherLessonUploadKind.Audio -> TeacherLessonUploadAssetType.Audio
}

private fun String.toRemoteIdOrNull(): Int? =
    toIntOrNull()
        ?: substringAfter("course-", missingDelimiterValue = "").toIntOrNull()
