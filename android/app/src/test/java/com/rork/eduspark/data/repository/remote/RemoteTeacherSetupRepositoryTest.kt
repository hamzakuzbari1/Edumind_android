package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherDocumentKind
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherSetupStepId
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.model.VoiceSampleState
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
import com.rork.eduspark.data.remote.teacher.TeacherPortfolioDto
import com.rork.eduspark.data.remote.teacher.TeacherProfileCvDto
import com.rork.eduspark.data.remote.teacher.TeacherProfileUpdateDto
import com.rork.eduspark.data.remote.teacher.TeacherQualificationDto
import com.rork.eduspark.data.remote.teacher.TeacherQualificationWriteDto
import com.rork.eduspark.data.remote.teacher.TeacherSetupApi
import com.rork.eduspark.data.remote.teacher.TeacherSetupCompleteDto
import com.rork.eduspark.data.remote.teacher.TeacherSetupStatusDto
import com.rork.eduspark.data.remote.teacher.TeacherSubjectDto
import com.rork.eduspark.data.remote.teacher.TeacherTeachingExperienceDto
import com.rork.eduspark.data.remote.teacher.TeacherTeachingExperienceWriteDto
import com.rork.eduspark.data.remote.teacher.TeacherTeachingUpdateDto
import com.rork.eduspark.data.remote.teacher.TeacherWhyStudyPointDto
import com.rork.eduspark.data.remote.teacher.TeacherWhyStudyPointWriteDto
import com.rork.eduspark.data.remote.teacher.TeachingImpactDto
import com.rork.eduspark.data.remote.teacher.TeachingImpactUpdateDto
import com.rork.eduspark.data.remote.teacher.TeachingPhilosophyDto
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RemoteTeacherSetupRepositoryTest {
    @Test
    fun mapsCanonicalProfileCvPortfolioAndNumericSubjectIds() = runBlocking {
        val fixture = fixture()

        val state = success(fixture.repository.getSetupState("42"))

        assertEquals("Remote Teacher", state.identity.displayName)
        assertEquals("Server bio", state.identity.headline)
        assertEquals("Choose me", state.identity.whyStudyWithMe)
        assertEquals(setOf("math"), state.subjectsGrades.subjectIds)
        assertEquals(setOf(Grade.Baccalaureate), state.subjectsGrades.grades)
        assertEquals("9", state.qualifications.single().id)
        assertEquals(6, state.experience.yearsOfExperience)
        assertEquals("Classroom teaching", state.experience.description)
    }

    @Test
    fun savesCanonicalIdentityTeachingQualificationsAndExperience() = runBlocking {
        val fixture = fixture()
        fixture.repository.getSetupState("42")

        success(
            fixture.repository.saveIdentity(
                "42",
                TeacherIdentityInfo(
                    displayName = "Updated Teacher",
                    headline = "Updated bio",
                    whyStudyWithMe = "Updated reason",
                ),
            )
        )
        success(
            fixture.repository.saveSubjectsGrades(
                "42",
                TeacherSubjectsGrades(setOf("math"), setOf(Grade.Baccalaureate)),
            )
        )
        success(
            fixture.repository.saveQualifications(
                "42",
                listOf(TeacherQualification("local", "New degree", "University", "2024")),
            )
        )
        val experience = success(
            fixture.repository.saveExperience(
                "42",
                TeacherExperienceInfo(7, "Updated classroom work", setOf("online")),
            )
        )

        assertEquals("Updated Teacher", fixture.teacher.lastProfile?.fullName)
        assertEquals("Updated bio", fixture.teacher.lastProfile?.bio)
        assertEquals(listOf(4), fixture.teacher.lastTeaching?.subjectIds)
        assertEquals(listOf(12), fixture.teacher.lastTeaching?.grades)
        assertEquals("New degree", fixture.teacher.createdQualification?.title)
        assertEquals(setOf(9), fixture.teacher.deletedQualificationIds)
        assertEquals(7, fixture.teacher.lastImpact?.yearsTeachingSubject)
        assertEquals("Updated classroom work", fixture.teacher.lastExperience?.description)
        assertEquals(setOf("online"), experience.experience.teachingModes)
    }

    @Test
    fun documentsPricingAndVoiceRemainLocalWithoutRemoteCalls() = runBlocking {
        val fixture = fixture()
        fixture.repository.getSetupState("42")
        val documents = listOf(
            TeacherSetupDocument("local", TeacherDocumentKind.Qualification, "Degree", "degree.pdf")
        )

        val withDocuments = success(fixture.repository.saveDocuments("42", documents))
        val withPricing = success(
            fixture.repository.savePricing("42", TeacherPricingInfo("25", "USD"))
        )
        val withVoice = success(
            fixture.repository.saveVoiceSample(
                "42",
                TeacherVoiceSample(VoiceSampleState.Recorded, "00:30"),
            )
        )

        assertEquals(documents, withDocuments.documents)
        assertEquals("25", withPricing.pricing.sessionPriceLabel)
        assertEquals(VoiceSampleState.Recorded, withVoice.voiceSample.state)
        assertTrue(TeacherSetupStepId.Documents in withDocuments.completedStepIds)
        assertEquals(0, fixture.teacher.documentCalls)
        assertEquals(0, fixture.teacher.voiceCalls)
    }

    @Test
    fun completionReloadsMeAndSurvivesSessionRestore() = runBlocking {
        val fixture = fixture()

        val complete = success(fixture.repository.finishSetup("42"))
        val restored = success(fixture.authRepository.restoreSession())

        assertEquals(1, fixture.teacher.completeCalls)
        assertTrue(complete.completedStepIds.containsAll(TeacherSetupStepId.entries))
        assertEquals(true, restored?.hasCompletedOnboarding)
    }

    @Test
    fun failedSaveDoesNotMarkStepCompleteOrReplaceRemoteState() = runBlocking {
        val fixture = fixture()
        fixture.teacher.currentBio = null
        fixture.teacher.profileFailure = ApiCallResult.NetworkFailure

        val result = fixture.repository.saveIdentity(
            "42",
            TeacherIdentityInfo(displayName = "Unsaved", headline = "Draft"),
        )
        fixture.teacher.profileFailure = null
        val reloaded = success(fixture.repository.getSetupState("42"))

        assertEquals(AppError.Network, assertIs<AppResult.Failure>(result).error)
        assertFalse(TeacherSetupStepId.Identity in reloaded.completedStepIds)
        assertEquals("Remote Teacher", reloaded.identity.displayName)
    }

    @Test
    fun unauthorizedRequestRefreshesOnceAndRefreshFailureExpiresSession() = runBlocking {
        val fixture = fixture()
        fixture.teacher.rejectOldTokenOnce = true

        success(fixture.repository.getSetupState("42"))
        assertEquals(1, fixture.auth.refreshCalls)

        fixture.store.write(StoredSession("access-old", "refresh-old", 7, "42"))
        fixture.teacher.alwaysUnauthorized = true
        fixture.auth.refreshResult = ApiCallResult.HttpFailure(401)
        val result = fixture.repository.getSetupState("42")

        assertEquals(AppError.SessionExpired, assertIs<AppResult.Failure>(result).error)
        assertNull(fixture.store.read())
    }

    @Test
    fun uploadAvatarStoresAbsolutePhotoUrlAndReloads() = runBlocking {
        val fixture = fixture()
        val bytes = ByteArray(64) { 7 }

        val uploaded = success(
            fixture.repository.uploadAvatar(
                teacherId = "42",
                bytes = bytes,
                filename = "avatar.png",
                mimeType = "image/png",
            ),
        )
        val reloaded = success(fixture.repository.getSetupState("42"))

        assertEquals(1, fixture.teacher.avatarUploadCalls)
        assertEquals("avatar.png", fixture.teacher.lastAvatarFilename)
        assertEquals("image/png", fixture.teacher.lastAvatarMime)
        assertEquals(64, fixture.teacher.lastAvatarBytes)
        assertEquals(
            "https://example.test/uploads/teachers/42/avatar.png",
            uploaded.identity.photoUrl,
        )
        assertEquals(uploaded.identity.photoUrl, reloaded.identity.photoUrl)
    }

    private suspend fun fixture(): Fixture {
        val teacher = FakeTeacherSetupApi()
        val auth = FakeTeacherAuthApi(teacher)
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access-old", "refresh-old", 7, "42"))
        }
        val refresh = AuthRefreshCoordinator(auth, store)
        val authRepository = RemoteAuthRepository(auth, store, refresh)
        return Fixture(
            teacher,
            auth,
            store,
            authRepository,
            RemoteTeacherSetupRepository(
                teacher,
                store,
                refresh,
                authRepository,
                apiBaseUrl = "https://example.test",
            ),
        )
    }

    private inline fun <reified T> success(result: AppResult<T>) =
        assertIs<AppResult.Success<T>>(result).data

    private data class Fixture(
        val teacher: FakeTeacherSetupApi,
        val auth: FakeTeacherAuthApi,
        val store: InMemoryTokenStore,
        val authRepository: RemoteAuthRepository,
        val repository: RemoteTeacherSetupRepository,
    )
}

private class FakeTeacherSetupApi : TeacherSetupApi {
    var currentName = "Remote Teacher"
    var currentBio: String? = "Server bio"
    var currentImageUrl: String? = null
    var setupComplete = false
    var profileFailure: ApiCallResult<TeacherSetupStatusDto>? = null
    var rejectOldTokenOnce = false
    var alwaysUnauthorized = false
    var statusCalls = 0
    var completeCalls = 0
    var avatarUploadCalls = 0
    var documentCalls = 0
    var voiceCalls = 0
    var lastProfile: TeacherProfileUpdateDto? = null
    var lastTeaching: TeacherTeachingUpdateDto? = null
    var createdQualification: TeacherQualificationWriteDto? = null
    val deletedQualificationIds = mutableSetOf<Int>()
    var lastImpact: TeachingImpactUpdateDto? = null
    var lastExperience: TeacherTeachingExperienceWriteDto? = null
    var lastAvatarFilename: String? = null
    var lastAvatarMime: String? = null
    var lastAvatarBytes: Int = 0

    override suspend fun status(accessToken: String): ApiCallResult<TeacherSetupStatusDto> {
        statusCalls++
        if (alwaysUnauthorized || (rejectOldTokenOnce && accessToken == "access-old")) {
            rejectOldTokenOnce = false
            return ApiCallResult.HttpFailure(401)
        }
        return ApiCallResult.Success(statusValue())
    }

    override suspend fun updateProfile(accessToken: String, body: TeacherProfileUpdateDto): ApiCallResult<TeacherSetupStatusDto> {
        profileFailure?.let { return it }
        lastProfile = body
        currentName = body.fullName
        currentBio = body.bio
        return ApiCallResult.Success(statusValue())
    }

    override suspend fun uploadAvatar(
        accessToken: String,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
    ): ApiCallResult<TeacherSetupStatusDto> {
        avatarUploadCalls++
        lastAvatarFilename = filename
        lastAvatarMime = mimeType
        lastAvatarBytes = bytes.size
        currentImageUrl = "/uploads/teachers/42/$filename"
        return ApiCallResult.Success(statusValue())
    }

    override suspend fun subjects(accessToken: String, grade: Int) = ApiCallResult.Success(
        listOf(TeacherSubjectDto(4, "Math", 12, "math"))
    )

    override suspend fun updateTeaching(accessToken: String, body: TeacherTeachingUpdateDto): ApiCallResult<TeacherSetupStatusDto> {
        lastTeaching = body
        return ApiCallResult.Success(statusValue())
    }

    override suspend fun cv(accessToken: String) = ApiCallResult.Success(
        TeacherProfileCvDto(
            qualifications = if (deletedQualificationIds.contains(9)) emptyList() else listOf(
                TeacherQualificationDto(9, "Degree", "University", 2020, sortOrder = 0)
            ),
            teachingExperiences = listOf(
                TeacherTeachingExperienceDto(
                    id = 8,
                    title = "Teaching",
                    description = "Classroom teaching",
                )
            ),
        )
    )

    override suspend fun createQualification(accessToken: String, body: TeacherQualificationWriteDto): ApiCallResult<TeacherQualificationDto> {
        createdQualification = body
        return ApiCallResult.Success(TeacherQualificationDto(10, body.title, body.institution, body.year))
    }

    override suspend fun updateQualification(accessToken: String, id: Int, body: TeacherQualificationWriteDto) =
        ApiCallResult.Success(TeacherQualificationDto(id, body.title, body.institution, body.year))

    override suspend fun deleteQualification(accessToken: String, id: Int): ApiCallResult<Unit> {
        deletedQualificationIds += id
        return ApiCallResult.Success(Unit)
    }

    override suspend fun createExperience(accessToken: String, body: TeacherTeachingExperienceWriteDto): ApiCallResult<TeacherTeachingExperienceDto> {
        lastExperience = body
        return ApiCallResult.Success(TeacherTeachingExperienceDto(11, body.title, description = body.description))
    }

    override suspend fun updateExperience(accessToken: String, id: Int, body: TeacherTeachingExperienceWriteDto): ApiCallResult<TeacherTeachingExperienceDto> {
        lastExperience = body
        return ApiCallResult.Success(TeacherTeachingExperienceDto(id, body.title, description = body.description))
    }

    override suspend fun portfolio(accessToken: String) = ApiCallResult.Success(
        TeacherPortfolioDto(
            teachingImpact = TeachingImpactDto(
                totalStudentsTaught = 100,
                yearsTeachingSubject = lastImpact?.yearsTeachingSubject ?: 6,
            ),
            teachingPhilosophy = TeachingPhilosophyDto(),
            whyStudyPoints = listOf(TeacherWhyStudyPointDto(7, "Choose me", sortOrder = 0)),
        )
    )

    override suspend fun updateImpact(accessToken: String, body: TeachingImpactUpdateDto): ApiCallResult<TeachingImpactDto> {
        lastImpact = body
        return ApiCallResult.Success(TeachingImpactDto(yearsTeachingSubject = body.yearsTeachingSubject))
    }

    override suspend fun createWhyStudyPoint(accessToken: String, body: TeacherWhyStudyPointWriteDto) =
        ApiCallResult.Success(TeacherWhyStudyPointDto(7, body.title, body.description))

    override suspend fun updateWhyStudyPoint(accessToken: String, id: Int, body: TeacherWhyStudyPointWriteDto) =
        ApiCallResult.Success(TeacherWhyStudyPointDto(id, body.title, body.description))

    override suspend fun complete(accessToken: String): ApiCallResult<TeacherSetupCompleteDto> {
        completeCalls++
        setupComplete = true
        return ApiCallResult.Success(TeacherSetupCompleteDto())
    }

    private fun statusValue() = TeacherSetupStatusDto(
        setupComplete = setupComplete,
        fullName = currentName,
        displayName = currentName,
        imageUrl = currentImageUrl,
        avatarUrl = currentImageUrl,
        bio = currentBio,
        subjectIds = listOf(4),
        grades = listOf(12),
    )
}

private class FakeTeacherAuthApi(private val teacher: FakeTeacherSetupApi) : AuthApi {
    var refreshCalls = 0
    var refreshResult: ApiCallResult<TokenResponseDto> = ApiCallResult.Success(tokens())

    override suspend fun me(accessToken: String) = ApiCallResult.Success(
        UserDto(
            id = 42,
            name = teacher.currentName,
            email = "teacher@example.com",
            role = "teacher",
            teacherSetupComplete = teacher.setupComplete,
        )
    )

    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> {
        refreshCalls++
        return refreshResult
    }

    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto): ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) = ApiCallResult.Success(OkResponseDto())
}

private fun tokens() = TokenResponseDto(
    accessToken = "access-new",
    refreshToken = "refresh-new",
    sessionId = 7,
    user = UserDto(42, "Remote Teacher", "teacher@example.com", "teacher"),
)
