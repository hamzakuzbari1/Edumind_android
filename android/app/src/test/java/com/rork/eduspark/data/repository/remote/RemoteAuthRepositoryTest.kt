package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
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
import com.rork.eduspark.data.repository.SignInOutcome
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RemoteAuthRepositoryTest {
    @Test
    fun noStoredSessionRestoresSignedOutState() = runBlocking {
        val fixture = fixture()

        val result = fixture.repository.restoreSession()

        assertNull(assertIs<AppResult.Success<*>>(result).data)
        assertEquals(0, fixture.api.meCalls)
    }

    @Test
    fun meRestoresStoredSession() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.meHandler = { ApiCallResult.Success(user()) }

        val result = fixture.repository.restoreSession()

        assertEquals("42", assertIs<AppResult.Success<*>>(result).data.let { it as com.rork.eduspark.data.model.SessionUser }.id)
        assertEquals("42", fixture.repository.session.first()?.id)
    }

    @Test
    fun expiredMeRefreshesOnceRotatesTokensAndRetriesMe() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.meHandler = { token ->
            if (token == "access-old") ApiCallResult.HttpFailure(401)
            else ApiCallResult.Success(user())
        }
        fixture.api.refreshResult = ApiCallResult.Success(tokens("access-new", "refresh-new"))

        val result = fixture.repository.restoreSession()

        assertIs<AppResult.Success<*>>(result)
        assertEquals(1, fixture.api.refreshCalls)
        assertEquals(2, fixture.api.meCalls)
        assertEquals(stored("access-new", "refresh-new"), fixture.store.read())
    }

    @Test
    fun concurrentUnauthorizedRequestsShareOneRefresh() = runBlocking {
        val api = FakeAuthApi().apply {
            refreshHandler = {
                delay(50)
                ApiCallResult.Success(tokens("access-new", "refresh-new"))
            }
        }
        val store = InMemoryTokenStore().apply { write(stored()) }
        val coordinator = AuthRefreshCoordinator(api, store)

        val first = async(Dispatchers.Default) { coordinator.refreshAfterUnauthorized("access-old") }
        val second = async(Dispatchers.Default) { coordinator.refreshAfterUnauthorized("access-old") }

        assertIs<AppResult.Success<*>>(first.await())
        assertIs<AppResult.Success<*>>(second.await())
        assertEquals(1, api.refreshCalls)
    }

    @Test
    fun retriedUnauthorizedResponseIsNotRefreshedAgainAndClearsSession() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.meHandler = { ApiCallResult.HttpFailure(401) }
        fixture.api.refreshResult = ApiCallResult.Success(tokens("access-new", "refresh-new"))

        val result = fixture.repository.restoreSession()

        assertIs<AppResult.Failure>(result)
        assertEquals(1, fixture.api.refreshCalls)
        assertEquals(2, fixture.api.meCalls)
        assertNull(fixture.store.read())
    }

    @Test
    fun refreshFailureClearsStoredSession() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.meHandler = { ApiCallResult.HttpFailure(401) }
        fixture.api.refreshResult = ApiCallResult.HttpFailure(401)

        val result = fixture.repository.restoreSession()

        assertEquals(AppError.SessionExpired, assertIs<AppResult.Failure>(result).error)
        assertNull(fixture.store.read())
    }

    @Test
    fun logoutAlwaysClearsLocalStateWhenNetworkFails() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.meHandler = { ApiCallResult.Success(user()) }
        fixture.repository.restoreSession()
        fixture.api.logoutResult = ApiCallResult.NetworkFailure

        fixture.repository.signOut()

        assertNull(fixture.store.read())
        assertNull(fixture.repository.session.first())
    }

    @Test
    fun loginUnauthorizedMapsToCredentialsAndNeverRefreshes() = runBlocking {
        val fixture = fixture(stored = stored())
        fixture.api.loginResult = ApiCallResult.HttpFailure(401, detail = "Incorrect email or password")

        val result = fixture.repository.signIn("student@example.com", "wrong")

        assertEquals(AppError.Domain("invalid_credentials"), assertIs<AppResult.Failure>(result).error)
        assertEquals(0, fixture.api.refreshCalls)
    }

    @Test
    fun twoFactorChallengeKeepsPublicMetadataAndResendUsesChallengeInternally() = runBlocking {
        val fixture = fixture()
        fixture.api.loginResult = ApiCallResult.Success(
            LoginResponseDto(
                requiresTwoFactor = true,
                challengeToken = "private-challenge",
                maskedEmail = "s***@example.com",
                expiresInSeconds = 300,
                resendAvailableInSeconds = 20,
            )
        )
        fixture.api.resendResult = ApiCallResult.Success(
            ResendTwoFactorResponseDto(expiresInSeconds = 300, resendAvailableInSeconds = 30)
        )

        val login = fixture.repository.signIn("student@example.com", "password")
        val challenge = assertIs<SignInOutcome.TwoFactorRequired>(
            assertIs<AppResult.Success<SignInOutcome>>(login).data
        ).challenge
        val resent = fixture.repository.resendTwoFactor()

        assertEquals("s***@example.com", challenge.maskedEmail)
        assertEquals(300, challenge.expiresInSeconds)
        assertEquals("private-challenge", fixture.api.lastResendChallenge)
        assertEquals(30, assertIs<AppResult.Success<*>>(resent).data.let { it as com.rork.eduspark.data.model.TwoFactorChallengeInfo }.resendAvailableInSeconds)
    }

    private suspend fun fixture(stored: StoredSession? = null): Fixture {
        val api = FakeAuthApi()
        val store = InMemoryTokenStore()
        stored?.let { store.write(it) }
        return Fixture(api, store, RemoteAuthRepository(api, store, AuthRefreshCoordinator(api, store)))
    }

    private data class Fixture(
        val api: FakeAuthApi,
        val store: InMemoryTokenStore,
        val repository: RemoteAuthRepository,
    )
}

private class FakeAuthApi : AuthApi {
    var meCalls = 0
    var refreshCalls = 0
    var lastResendChallenge: String? = null
    var loginResult: ApiCallResult<LoginResponseDto> = ApiCallResult.InvalidResponse
    var refreshResult: ApiCallResult<TokenResponseDto> = ApiCallResult.InvalidResponse
    var logoutResult: ApiCallResult<OkResponseDto> = ApiCallResult.Success(OkResponseDto())
    var resendResult: ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    var meHandler: suspend (String) -> ApiCallResult<UserDto> = { ApiCallResult.InvalidResponse }
    var refreshHandler: (suspend (RefreshTokenRequestDto) -> ApiCallResult<TokenResponseDto>)? = null

    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.Success(tokens())
    override suspend fun login(body: LoginRequestDto) = loginResult
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> {
        meCalls++
        return meHandler(accessToken)
    }
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> {
        refreshCalls++
        return refreshHandler?.invoke(body) ?: refreshResult
    }
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) = logoutResult
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) = loginResult
    override suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto): ApiCallResult<ResendTwoFactorResponseDto> {
        lastResendChallenge = body.challengeToken
        return resendResult
    }
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) = ApiCallResult.Success(OkResponseDto())
}

private fun user(role: String = "student") = UserDto(
    id = 42,
    name = "Student",
    email = "student@example.com",
    role = role,
    emailVerified = true,
    onboardingComplete = true,
    teacherSetupComplete = true,
)

private fun tokens(
    access: String = "access-new",
    refresh: String = "refresh-new",
) = TokenResponseDto(access, refresh, 7, user = user())

private fun stored(
    access: String = "access-old",
    refresh: String = "refresh-old",
) = StoredSession(access, refresh, 7, "42")
