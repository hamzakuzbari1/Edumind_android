package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.TwoFactorChallengeInfo
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.auth.AuthApi
import com.rork.eduspark.data.remote.auth.ForgotPasswordRequestDto
import com.rork.eduspark.data.remote.auth.LoginRequestDto
import com.rork.eduspark.data.remote.auth.LoginResponseDto
import com.rork.eduspark.data.remote.auth.LogoutRequestDto
import com.rork.eduspark.data.remote.auth.RefreshTokenRequestDto
import com.rork.eduspark.data.remote.auth.RegisterRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.ResetPasswordRequestDto
import com.rork.eduspark.data.remote.auth.TokenResponseDto
import com.rork.eduspark.data.remote.auth.VerifyEmailRequestDto
import com.rork.eduspark.data.remote.auth.VerifyTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.toDomain
import com.rork.eduspark.data.remote.auth.toStoredSession
import com.rork.eduspark.data.remote.auth.toTokenResponse
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.RegistrationOutcome
import com.rork.eduspark.data.repository.SignInOutcome
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

internal data class PendingTwoFactorChallenge(
    val token: String,
    val info: TwoFactorChallengeInfo,
)

internal class AuthRefreshCoordinator(
    private val api: AuthApi,
    private val tokenStore: SecureTokenStore,
) {
    private val mutex = Mutex()

    suspend fun refreshAfterUnauthorized(failedAccessToken: String): AppResult<StoredSession> =
        mutex.withLock {
            val current = tokenStore.read()
                ?: return@withLock AppResult.Failure(AppError.SessionExpired)
            if (current.accessToken != failedAccessToken) {
                return@withLock AppResult.Success(current)
            }

            when (val response = api.refresh(RefreshTokenRequestDto(current.refreshToken))) {
                is ApiCallResult.Success -> {
                    val rotated = runCatching { response.value.toStoredSession() }.getOrNull()
                    if (rotated == null) {
                        tokenStore.clear()
                        AppResult.Failure(AppError.SessionExpired)
                    } else {
                        tokenStore.write(rotated)
                        AppResult.Success(rotated)
                    }
                }
                else -> {
                    tokenStore.clear()
                    AppResult.Failure(AppError.SessionExpired)
                }
            }
        }
}

class RemoteAuthRepository internal constructor(
    private val api: AuthApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val deviceName: String = "Android",
) : AuthRepository {
    private val _session = MutableStateFlow<SessionUser?>(null)
    override val session: Flow<SessionUser?> = _session.asStateFlow()

    private val _pendingChallenge = MutableStateFlow<TwoFactorChallengeInfo?>(null)
    override val pendingTwoFactorChallenge: Flow<TwoFactorChallengeInfo?> =
        _pendingChallenge.asStateFlow()
    private var pendingChallenge: PendingTwoFactorChallenge? = null

    override suspend fun restoreSession(): AppResult<SessionUser?> {
        val stored = tokenStore.read()
        if (stored == null) {
            _session.value = null
            return AppResult.Success(null)
        }
        return when (val response = authorizedRequest(stored, api::me)) {
            is ApiCallResult.Success -> {
                val user = mapUser(response.value)
                if (user is AppResult.Success) _session.value = user.data
                user
            }
            else -> {
                val error = response.toAppError(ApiOperation.Authenticated)
                if (error == AppError.SessionExpired) clearLocalSession()
                AppResult.Failure(error)
            }
        }
    }

    override suspend fun signIn(email: String, password: String): AppResult<SignInOutcome> {
        clearPendingChallenge()
        val response = api.login(
            LoginRequestDto(
                email = email,
                password = password,
                deviceName = deviceName,
            )
        )
        return when (response) {
            is ApiCallResult.Success -> handleLoginResponse(email, response.value)
            else -> AppResult.Failure(response.toAppError(ApiOperation.Login))
        }
    }

    override suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<RegistrationOutcome> {
        val response = api.register(
            RegisterRequestDto(
                name = name,
                email = email,
                password = password,
                role = role.name.lowercase(),
                deviceName = deviceName,
            )
        )
        return when (response) {
            is ApiCallResult.Success -> when (val accepted = acceptTokens(response.value)) {
                is AppResult.Success -> AppResult.Success(RegistrationOutcome.Authenticated(accepted.data))
                is AppResult.Failure -> accepted
            }
            else -> AppResult.Failure(response.toAppError(ApiOperation.Register))
        }
    }

    override suspend fun verifyEmail(code: String): AppResult<Unit> =
        api.verifyEmail(VerifyEmailRequestDto(token = code)).toUnitResult(ApiOperation.VerifyEmail)

    override suspend fun resendEmailCode(): AppResult<Unit> {
        val response = authorizedRequest { api.resendVerification(it) }
        return response.toUnitResult(ApiOperation.Authenticated)
    }

    override suspend fun verifyTwoFactor(
        code: String,
        trustDevice: Boolean,
    ): AppResult<SessionUser> {
        val challenge = pendingChallenge
            ?: return AppResult.Failure(AppError.Domain("two_factor_challenge_missing"))
        val response = api.verifyTwoFactor(
            VerifyTwoFactorRequestDto(challengeToken = challenge.token, code = code)
        )
        return when (response) {
            is ApiCallResult.Success -> {
                val tokens = runCatching { response.value.toTokenResponse() }.getOrNull()
                    ?: return AppResult.Failure(AppError.Domain("invalid_auth_response"))
                val accepted = acceptTokens(tokens)
                if (accepted is AppResult.Success) clearPendingChallenge()
                accepted
            }
            else -> AppResult.Failure(response.toAppError(ApiOperation.VerifyTwoFactor))
        }
    }

    override suspend fun resendTwoFactor(): AppResult<TwoFactorChallengeInfo> {
        val challenge = pendingChallenge
            ?: return AppResult.Failure(AppError.Domain("two_factor_challenge_missing"))
        return when (
            val response = api.resendTwoFactor(ResendTwoFactorRequestDto(challenge.token))
        ) {
            is ApiCallResult.Success -> {
                val updated = challenge.info.copy(
                    expiresInSeconds = response.value.expiresInSeconds,
                    resendAvailableInSeconds = response.value.resendAvailableInSeconds,
                )
                pendingChallenge = challenge.copy(info = updated)
                _pendingChallenge.value = updated
                AppResult.Success(updated)
            }
            else -> AppResult.Failure(response.toAppError(ApiOperation.VerifyTwoFactor))
        }
    }

    override suspend fun requestPasswordReset(email: String): AppResult<Unit> =
        api.forgotPassword(ForgotPasswordRequestDto(email)).toUnitResult(ApiOperation.General)

    override suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit> =
        api.resetPassword(
            ResetPasswordRequestDto(
                token = token,
                newPassword = newPassword,
                confirmPassword = newPassword,
            )
        ).toUnitResult(ApiOperation.General)

    override suspend fun completeOnboarding(): AppResult<Unit> {
        val user = _session.value ?: return AppResult.Failure(AppError.SessionExpired)
        val response = when (user.role) {
            UserRole.Student -> authorizedRequest { api.completeStudentOnboarding(it) }
            UserRole.Teacher -> authorizedRequest { api.completeTeacherSetup(it) }
            UserRole.Parent -> return AppResult.Success(Unit)
        }
        if (response is ApiCallResult.Success) {
            _session.value = user.copy(hasCompletedOnboarding = true)
        }
        return response.toUnitResult(ApiOperation.Authenticated)
    }

    override suspend fun signOut() {
        val stored = tokenStore.read()
        try {
            if (stored != null) {
                api.logout(
                    accessToken = stored.accessToken,
                    body = LogoutRequestDto(refreshToken = stored.refreshToken),
                )
            }
        } finally {
            clearLocalSession()
        }
    }

    private suspend fun handleLoginResponse(
        email: String,
        response: LoginResponseDto,
    ): AppResult<SignInOutcome> {
        if (response.requiresTwoFactor) {
            val token = response.challengeToken
                ?: return AppResult.Failure(AppError.Domain("invalid_two_factor_challenge"))
            val info = TwoFactorChallengeInfo(
                email = email,
                maskedEmail = response.maskedEmail,
                expiresInSeconds = response.expiresInSeconds,
                resendAvailableInSeconds = response.resendAvailableInSeconds,
            )
            pendingChallenge = PendingTwoFactorChallenge(token = token, info = info)
            _pendingChallenge.value = info
            return AppResult.Success(SignInOutcome.TwoFactorRequired(info))
        }
        val tokens = runCatching { response.toTokenResponse() }.getOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_auth_response"))
        return when (val accepted = acceptTokens(tokens)) {
            is AppResult.Success -> AppResult.Success(SignInOutcome.Authenticated(accepted.data))
            is AppResult.Failure -> accepted
        }
    }

    private suspend fun acceptTokens(tokens: TokenResponseDto): AppResult<SessionUser> =
        runCatching {
            val user = tokens.user.toDomain()
            tokenStore.write(tokens.toStoredSession())
            _session.value = user
            user
        }.fold(
            onSuccess = { AppResult.Success(it) },
            onFailure = {
                clearLocalSession()
                AppResult.Failure(AppError.Domain("invalid_auth_response"))
            },
        )

    private fun mapUser(userDto: com.rork.eduspark.data.remote.auth.UserDto): AppResult<SessionUser> =
        runCatching { userDto.toDomain() }.fold(
            onSuccess = { AppResult.Success(it) },
            onFailure = { AppResult.Failure(AppError.Domain("unsupported_role")) },
        )

    private suspend fun <T> authorizedRequest(
        initial: StoredSession? = null,
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = initial ?: tokenStore.read()
            ?: return ApiCallResult.HttpFailure(statusCode = 401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> {
                val retry = call(refreshed.data.accessToken)
                if (retry is ApiCallResult.HttpFailure && retry.statusCode == 401) {
                    clearLocalSession()
                }
                retry
            }
            is AppResult.Failure -> {
                clearLocalSession()
                ApiCallResult.HttpFailure(statusCode = 401)
            }
        }
    }

    private suspend fun clearLocalSession() {
        tokenStore.clear()
        _session.value = null
        clearPendingChallenge()
    }

    private fun clearPendingChallenge() {
        pendingChallenge = null
        _pendingChallenge.value = null
    }
}

private enum class ApiOperation { Login, Register, VerifyTwoFactor, VerifyEmail, Authenticated, General }

private fun ApiCallResult<*>.toAppError(operation: ApiOperation): AppError = when (this) {
    ApiCallResult.NetworkFailure -> AppError.Network
    ApiCallResult.InvalidResponse -> AppError.Server
    is ApiCallResult.Success -> AppError.Unknown
    is ApiCallResult.HttpFailure -> when {
        statusCode == 401 && operation == ApiOperation.Login ->
            AppError.Domain("invalid_credentials")
        statusCode == 401 && operation == ApiOperation.VerifyTwoFactor ->
            AppError.Domain("invalid_code")
        statusCode == 401 -> AppError.SessionExpired
        statusCode == 403 -> AppError.Forbidden
        statusCode == 404 || statusCode == 410 -> AppError.NotFound
        statusCode == 422 -> AppError.Validation(fieldErrors.ifEmpty { mapOf("form" to "invalid") })
        statusCode == 400 && operation == ApiOperation.Register ->
            AppError.Validation(mapOf("email" to "already_registered"))
        statusCode >= 500 -> AppError.Server
        else -> AppError.Domain("request_rejected")
    }
}

private fun ApiCallResult<*>.toUnitResult(operation: ApiOperation): AppResult<Unit> = when (this) {
    is ApiCallResult.Success -> AppResult.Success(Unit)
    else -> AppResult.Failure(toAppError(operation))
}
