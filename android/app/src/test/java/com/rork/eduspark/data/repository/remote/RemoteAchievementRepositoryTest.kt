package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.AchievementStatus
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
import com.rork.eduspark.data.remote.gamification.BadgeDto
import com.rork.eduspark.data.remote.gamification.GamificationProfileDto
import com.rork.eduspark.data.remote.gamification.StudentGamificationApi
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class RemoteAchievementRepositoryTest {
    @Test
    fun mapsBadgeCatalogIncludingEmptyLists() = runBlocking {
        val fixture = fixture(
            GamificationProfileDto(
                badges = listOf(
                    BadgeDto(
                        achievementKey = "first_lesson",
                        title = "أول درس",
                        unlocked = true,
                        unlockedAt = "2026-04-01T00:00:00Z",
                    ),
                    BadgeDto(
                        achievementKey = "lessons_10",
                        title = "10 دروس مكتملة",
                        unlocked = false,
                    ),
                ),
            ),
        )
        val result = assertIs<AppResult.Success<List<Achievement>>>(fixture.repository.getAchievements())
        assertEquals(2, result.data.size)
        assertEquals(AchievementStatus.Earned, result.data[0].status)
        assertEquals(AchievementStatus.Locked, result.data[1].status)
    }

    @Test
    fun emptyBackendCatalogReturnsEmptyList() = runBlocking {
        val fixture = fixture(GamificationProfileDto())
        val result = assertIs<AppResult.Success<List<Achievement>>>(fixture.repository.getAchievements())
        assertTrue(result.data.isEmpty())
    }

    private suspend fun fixture(profile: GamificationProfileDto): Fixture {
        val auth = FakeGamificationAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "42"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        val api = object : StudentGamificationApi {
            override suspend fun profile(accessToken: String): ApiCallResult<GamificationProfileDto> =
                ApiCallResult.Success(profile)
        }
        return Fixture(
            repository = RemoteAchievementRepository(
                api = api,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
            ),
        )
    }

    private data class Fixture(val repository: RemoteAchievementRepository)
}

private class FakeGamificationAuthApi : AuthApi {
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.InvalidResponse

    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) =
        ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(
        body: ResendTwoFactorRequestDto,
    ): ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
}
