package com.rork.eduspark.data.remote.media

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
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
import com.rork.eduspark.data.remote.auth.OkResponseDto
import com.rork.eduspark.data.remote.auth.RefreshTokenRequestDto
import com.rork.eduspark.data.remote.auth.RegisterRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorResponseDto
import com.rork.eduspark.data.remote.auth.ResetPasswordRequestDto
import com.rork.eduspark.data.remote.auth.TokenResponseDto
import com.rork.eduspark.data.remote.auth.UserDto
import com.rork.eduspark.data.remote.auth.VerifyEmailRequestDto
import com.rork.eduspark.data.remote.auth.VerifyTwoFactorRequestDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.RegistrationOutcome
import com.rork.eduspark.data.repository.SignInOutcome
import com.rork.eduspark.data.repository.remote.AuthRefreshCoordinator
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue

class MediaUrlResolverTest {

    @Test
    fun publicAbsolutePassesThroughWithoutApiCall() = runBlocking {
        val api = FakeMediaApi()
        val resolver = resolver(api)
        val url = "https://cdn.supabase.co/storage/v1/object/public/edumind-public/avatars/a.png"

        val result = assertIs<AppResult.Success<ResolvedMediaUrl>>(resolver.resolve(url))
        assertEquals(url, result.data.url)
        assertEquals(MediaRefKind.PublicAbsolute, result.data.kind)
        assertFalse(result.data.isSigned)
        assertEquals(0, api.calls)
    }

    @Test
    fun legacyUploadsPrefixedWithApiBase() = runBlocking {
        val api = FakeMediaApi()
        val resolver = resolver(api)

        val result = assertIs<AppResult.Success<ResolvedMediaUrl>>(
            resolver.resolve("/uploads/lessons/1/notes.pdf"),
        )
        assertEquals("https://api.example.com/uploads/lessons/1/notes.pdf", result.data.url)
        assertEquals(MediaRefKind.LegacyUploads, result.data.kind)
        assertEquals(0, api.calls)
    }

    @Test
    fun privateDownloadResolvesSignedUrlEphemerally() = runBlocking {
        val api = FakeMediaApi(
            response = ApiCallResult.Success(
                MediaDownloadUrlDto(
                    mediaId = 7,
                    url = "https://signed.example/tmp?token=abc",
                    expiresIn = 60,
                    provider = "supabase",
                    isSigned = true,
                    bucket = "edumind-private",
                ),
            ),
        )
        val resolver = resolver(api)

        val first = assertIs<AppResult.Success<ResolvedMediaUrl>>(
            resolver.resolve("/api/media/7/download-url"),
        )
        assertEquals("https://signed.example/tmp?token=abc", first.data.url)
        assertTrue(first.data.isSigned)
        assertEquals(60, first.data.expiresInSeconds)
        assertEquals("/api/media/7/download-url", first.data.sourceRef)

        api.response = ApiCallResult.Success(
            MediaDownloadUrlDto(
                mediaId = 7,
                url = "https://signed.example/tmp?token=fresh",
                expiresIn = 60,
                provider = "supabase",
                isSigned = true,
            ),
        )
        val second = assertIs<AppResult.Success<ResolvedMediaUrl>>(
            resolver.resolve("/api/media/7/download-url"),
        )
        assertEquals("https://signed.example/tmp?token=fresh", second.data.url)
        assertEquals(2, api.calls)
        assertEquals(listOf(7, 7), api.requestedIds)
    }

    @Test
    fun privateUnauthorizedMapsToSessionExpired() = runBlocking {
        val api = FakeMediaApi(response = ApiCallResult.HttpFailure(401))
        val auth = RecordingAuthRepository()
        val resolver = resolver(api, authRepository = auth, clearTokens = true)

        val result = assertIs<AppResult.Failure>(resolver.resolve("/api/media/9/download-url"))
        assertEquals(AppError.SessionExpired, result.error)
        assertEquals(1, auth.signOutCalls)
    }

    @Test
    fun privateForbiddenMapsSafely() = runBlocking {
        val api = FakeMediaApi(response = ApiCallResult.HttpFailure(403))
        val resolver = resolver(api)

        val result = assertIs<AppResult.Failure>(resolver.resolve("/api/media/9/download-url"))
        assertEquals(AppError.Forbidden, result.error)
    }

    @Test
    fun missingMediaMapsToNotFound() = runBlocking {
        val api = FakeMediaApi(response = ApiCallResult.HttpFailure(404))
        val resolver = resolver(api)

        val result = assertIs<AppResult.Failure>(resolver.resolve("/api/media/404/download-url"))
        assertEquals(AppError.NotFound, result.error)
    }

    private fun resolver(
        api: MediaApi,
        authRepository: AuthRepository = RecordingAuthRepository(),
        clearTokens: Boolean = false,
    ): MediaUrlResolver {
        val store = InMemoryTokenStore()
        if (!clearTokens) {
            runBlocking {
                store.write(StoredSession("access", "refresh", 60, "1"))
            }
        }
        val refresh = AuthRefreshCoordinator(NoopAuthApi(), store)
        return MediaUrlResolver(
            api = api,
            tokenStore = store,
            refreshCoordinator = refresh,
            authRepository = authRepository,
            apiBaseUrl = "https://api.example.com",
        )
    }
}

private class FakeMediaApi(
    var response: ApiCallResult<MediaDownloadUrlDto> = ApiCallResult.NetworkFailure,
) : MediaApi {
    var calls = 0
    val requestedIds = mutableListOf<Int>()

    override suspend fun downloadUrl(
        accessToken: String,
        mediaId: Int,
        expiresIn: Int?,
    ): ApiCallResult<MediaDownloadUrlDto> {
        calls += 1
        requestedIds += mediaId
        return response
    }
}

private class RecordingAuthRepository : AuthRepository {
    var signOutCalls = 0
    override val session: Flow<SessionUser?> = MutableStateFlow(null)
    override suspend fun restoreSession(): AppResult<SessionUser?> = AppResult.Success(null)
    override suspend fun signIn(email: String, password: String): AppResult<SignInOutcome> =
        AppResult.Failure(AppError.Unknown)
    override suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<RegistrationOutcome> = AppResult.Failure(AppError.Unknown)
    override suspend fun verifyEmail(code: String): AppResult<Unit> = AppResult.Success(Unit)
    override suspend fun resendEmailCode(): AppResult<Unit> = AppResult.Success(Unit)
    override val pendingTwoFactorChallenge: Flow<TwoFactorChallengeInfo?> = MutableStateFlow(null)
    override suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): AppResult<SessionUser> =
        AppResult.Failure(AppError.Unknown)
    override suspend fun resendTwoFactor(): AppResult<TwoFactorChallengeInfo> =
        AppResult.Failure(AppError.Unknown)
    override suspend fun requestPasswordReset(email: String): AppResult<Unit> = AppResult.Success(Unit)
    override suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit> =
        AppResult.Success(Unit)
    override suspend fun completeOnboarding(): AppResult<Unit> = AppResult.Success(Unit)
    override suspend fun signOut() {
        signOutCalls += 1
    }
}

private class NoopAuthApi : AuthApi {
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun register(body: RegisterRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.NetworkFailure
    override suspend fun logout(accessToken: String, body: LogoutRequestDto): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun verifyEmail(body: VerifyEmailRequestDto): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun resendVerification(accessToken: String): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto): ApiCallResult<ResendTwoFactorResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun resetPassword(body: ResetPasswordRequestDto): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun completeStudentOnboarding(accessToken: String): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
    override suspend fun completeTeacherSetup(accessToken: String): ApiCallResult<OkResponseDto> =
        ApiCallResult.NetworkFailure
}
