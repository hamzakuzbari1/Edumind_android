package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.StudentOnboardingStatus
import com.rork.eduspark.data.model.StudentOnboardingStep
import com.rork.eduspark.data.model.SubjectOption
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
import com.rork.eduspark.data.remote.onboarding.GradeUpdateDto
import com.rork.eduspark.data.remote.onboarding.OnboardingCompleteDto
import com.rork.eduspark.data.remote.onboarding.OnboardingStatusDto
import com.rork.eduspark.data.remote.onboarding.StudentOnboardingApi
import com.rork.eduspark.data.remote.onboarding.SubjectDto
import com.rork.eduspark.data.remote.onboarding.SubjectsUpdateDto
import com.rork.eduspark.data.remote.onboarding.TeacherDto
import com.rork.eduspark.data.remote.onboarding.TeachersUpdateDto
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull

class RemoteStudentOnboardingRepositoryTest {
    @Test
    fun mapsPersistedStateAndNumericCatalogIdsAtRepositoryBoundary() = runBlocking {
        val fixture = fixture()
        fixture.onboarding.subjectsResult = ApiCallResult.Success(
            listOf(SubjectDto(4, "الرياضيات", "math", 12))
        )
        fixture.onboarding.teachersResult = ApiCallResult.Success(
            listOf(
                TeacherDto(
                    id = 2,
                    fullName = "DEV Teacher",
                    rating = 4.5f,
                    studentCount = 3,
                    subjectId = 4,
                    subjectName = "الرياضيات",
                )
            )
        )

        val status = assertIs<AppResult.Success<StudentOnboardingStatus>>(
            fixture.repository.getStatus()
        ).data
        val subject = assertIs<AppResult.Success<List<SubjectOption>>>(
            fixture.repository.getSubjects(Grade.Baccalaureate)
        ).data.single()
        val teacher = assertIs<AppResult.Success<List<OnboardingTeacher>>>(
            fixture.repository.getTeachers("4", Grade.Baccalaureate)
        ).data.single()

        assertEquals(StudentOnboardingStep.Subjects, status.step)
        assertEquals(setOf("4"), status.selectedSubjectIds)
        assertEquals("4", subject.id)
        assertEquals("2", teacher.id)
    }

    @Test
    fun saveCallsKeepTransportIdsNumericAndCompleteRefreshesStatus() = runBlocking {
        val fixture = fixture()

        assertIs<AppResult.Success<*>>(fixture.repository.saveSubjects(setOf("7", "4")))
        assertIs<AppResult.Success<*>>(fixture.repository.saveTeachers(mapOf("4" to "2")))
        assertIs<AppResult.Success<*>>(fixture.repository.complete())

        assertEquals(listOf(4, 7), fixture.onboarding.lastSubjects?.subjectIds)
        assertEquals(4, fixture.onboarding.lastTeachers?.choices?.single()?.subjectId)
        assertEquals(2, fixture.onboarding.lastTeachers?.choices?.single()?.teacherProfileId)
        assertEquals(1, fixture.onboarding.completeCalls)
        assertEquals(1, fixture.onboarding.statusCalls)
    }

    @Test
    fun invalidDraftIdsFailWithoutSendingRemoteMutation() = runBlocking {
        val fixture = fixture()

        val result = fixture.repository.saveSubjects(setOf("math"))

        assertEquals(AppError.Domain("invalid_subject_id"), assertIs<AppResult.Failure>(result).error)
        assertNull(fixture.onboarding.lastSubjects)
    }

    @Test
    fun unauthorizedRequestRefreshesExactlyOnceAndRetries() = runBlocking {
        val fixture = fixture()
        fixture.onboarding.statusHandler = { token ->
            if (token == "access-old") ApiCallResult.HttpFailure(401)
            else ApiCallResult.Success(status())
        }
        fixture.auth.refreshResult = ApiCallResult.Success(tokens())

        assertIs<AppResult.Success<*>>(fixture.repository.getStatus())

        assertEquals(2, fixture.onboarding.statusCalls)
        assertEquals(1, fixture.auth.refreshCalls)
        assertEquals("access-new", fixture.store.read()?.accessToken)
    }

    @Test
    fun refreshFailureExpiresAndClearsSession() = runBlocking {
        val fixture = fixture()
        fixture.onboarding.statusHandler = { ApiCallResult.HttpFailure(401) }
        fixture.auth.refreshResult = ApiCallResult.HttpFailure(401)

        val result = fixture.repository.getStatus()

        assertEquals(AppError.SessionExpired, assertIs<AppResult.Failure>(result).error)
        assertEquals(1, fixture.auth.refreshCalls)
        assertNull(fixture.store.read())
    }

    private suspend fun fixture(): Fixture {
        val onboarding = FakeStudentOnboardingApi()
        val auth = FakeRefreshAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access-old", "refresh-old", 7, "42"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        return Fixture(
            onboarding = onboarding,
            auth = auth,
            store = store,
            repository = RemoteStudentOnboardingRepository(
                api = onboarding,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
            ),
        )
    }

    private data class Fixture(
        val onboarding: FakeStudentOnboardingApi,
        val auth: FakeRefreshAuthApi,
        val store: InMemoryTokenStore,
        val repository: RemoteStudentOnboardingRepository,
    )
}

private class FakeStudentOnboardingApi : StudentOnboardingApi {
    var statusCalls = 0
    var completeCalls = 0
    var lastSubjects: SubjectsUpdateDto? = null
    var lastTeachers: TeachersUpdateDto? = null
    var statusHandler: suspend (String) -> ApiCallResult<OnboardingStatusDto> = {
        ApiCallResult.Success(status())
    }
    var subjectsResult: ApiCallResult<List<SubjectDto>> = ApiCallResult.Success(emptyList())
    var teachersResult: ApiCallResult<List<TeacherDto>> = ApiCallResult.Success(emptyList())

    override suspend fun status(accessToken: String): ApiCallResult<OnboardingStatusDto> {
        statusCalls++
        return statusHandler(accessToken)
    }

    override suspend fun subjects(accessToken: String, grade: Int) = subjectsResult

    override suspend fun saveGrade(accessToken: String, body: GradeUpdateDto) =
        ApiCallResult.Success(status())

    override suspend fun saveSubjects(
        accessToken: String,
        body: SubjectsUpdateDto,
    ): ApiCallResult<OnboardingStatusDto> {
        lastSubjects = body
        return ApiCallResult.Success(status())
    }

    override suspend fun teachers(accessToken: String, subjectId: Int, grade: Int) =
        teachersResult

    override suspend fun saveTeachers(
        accessToken: String,
        body: TeachersUpdateDto,
    ): ApiCallResult<OnboardingStatusDto> {
        lastTeachers = body
        return ApiCallResult.Success(status())
    }

    override suspend fun complete(accessToken: String): ApiCallResult<OnboardingCompleteDto> {
        completeCalls++
        return ApiCallResult.Success(OnboardingCompleteDto())
    }
}

private class FakeRefreshAuthApi : AuthApi {
    var refreshCalls = 0
    var refreshResult: ApiCallResult<TokenResponseDto> = ApiCallResult.InvalidResponse

    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> {
        refreshCalls++
        return refreshResult
    }

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

private fun status() = OnboardingStatusDto(
    step = "subjects",
    grade = 12,
    selectedSubjectIds = listOf(4),
)

private fun tokens() = TokenResponseDto(
    accessToken = "access-new",
    refreshToken = "refresh-new",
    sessionId = 7,
    user = UserDto(42, "Abeer", "abeer@example.com", "student"),
)
