package com.rork.eduspark.data.remote.media

import com.rork.eduspark.BuildConfig
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.remote.AuthRefreshCoordinator

/**
 * Resolves API media references into a short-lived playable/openable URL.
 *
 * - Public absolute → returned as-is
 * - Legacy `/uploads/...` → prefixed with [apiBaseUrl]
 * - `/api/media/{id}/download-url` → authenticated call; returns signed URL for this use only
 *
 * Signed URLs are never persisted by this class — callers must resolve again after expiry.
 */
data class ResolvedMediaUrl(
    /** Backend reference that was resolved (never a signed URL for private media). */
    val sourceRef: String,
    /** URL safe to open/load right now. */
    val url: String,
    val kind: MediaRefKind,
    val isSigned: Boolean = false,
    val expiresInSeconds: Int? = null,
    val mediaId: Int? = null,
)

class MediaUrlResolver internal constructor(
    private val api: MediaApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
    private val apiBaseUrl: String = BuildConfig.API_BASE_URL,
) {
    suspend fun resolve(path: String?): AppResult<ResolvedMediaUrl> {
        val raw = path?.trim().orEmpty()
        if (raw.isEmpty()) return AppResult.Failure(AppError.NotFound)

        return when (val kind = classifyMediaRef(raw)) {
            MediaRefKind.PublicAbsolute, MediaRefKind.LocalDevice ->
                AppResult.Success(
                    ResolvedMediaUrl(
                        sourceRef = raw,
                        url = raw,
                        kind = kind,
                        isSigned = false,
                    ),
                )

            MediaRefKind.LegacyUploads -> {
                val absolute = absoluteMediaUrl(raw, apiBaseUrl)
                    ?: return AppResult.Failure(AppError.NotFound)
                AppResult.Success(
                    ResolvedMediaUrl(
                        sourceRef = raw,
                        url = absolute,
                        kind = kind,
                        isSigned = false,
                    ),
                )
            }

            MediaRefKind.PrivateDownloadEndpoint -> {
                val mediaId = parsePrivateMediaId(raw)
                    ?: return AppResult.Failure(AppError.Domain("invalid_media_download_path"))
                when (val response = authorizedRequest { api.downloadUrl(it, mediaId) }) {
                    is ApiCallResult.Success -> {
                        val dto = response.value
                        val signed = dto.url.trim()
                        if (signed.isEmpty()) {
                            AppResult.Failure(AppError.NotFound)
                        } else {
                            AppResult.Success(
                                ResolvedMediaUrl(
                                    sourceRef = raw,
                                    url = signed,
                                    kind = kind,
                                    isSigned = dto.isSigned,
                                    expiresInSeconds = dto.expiresIn,
                                    mediaId = dto.mediaId,
                                ),
                            )
                        }
                    }
                    else -> AppResult.Failure(mapFailure(response))
                }
            }

            MediaRefKind.Unknown -> AppResult.Failure(AppError.Domain("unsupported_media_ref"))
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

    private suspend fun mapFailure(response: ApiCallResult<*>): AppError {
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
                else -> AppError.Domain(response.detail ?: "media_resolve_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
