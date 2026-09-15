package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.gamification.StudentGamificationApi
import com.rork.eduspark.data.remote.gamification.toAchievementList
import com.rork.eduspark.data.repository.AchievementRepository
import com.rork.eduspark.data.repository.AuthRepository

/**
 * ST-15 badge catalog from `GET /api/student/gamification`.
 *
 * XP / level / streak for the screen header continue to come from
 * [com.rork.eduspark.data.repository.LearningRepository.getGamification] so Home and
 * Achievements never diverge on those numbers.
 */
internal class RemoteAchievementRepository(
    private val api: StudentGamificationApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : AchievementRepository {

    override suspend fun getAchievements(): AppResult<List<Achievement>> =
        when (val response = authorizedRequest(api::profile)) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toAchievementList())
            else -> AppResult.Failure(handleFailure(response))
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
                else -> AppError.Domain(response.detail ?: "gamification_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
