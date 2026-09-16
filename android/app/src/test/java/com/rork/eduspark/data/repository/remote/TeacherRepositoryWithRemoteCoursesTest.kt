package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.TeacherCourseCreateRequest
import com.rork.eduspark.data.model.TeacherCourseFormSubject
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonStatus
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
import com.rork.eduspark.data.remote.teacher.TeacherCourseCreateRequestDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseFormContextDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseLessonDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseSubjectOptionDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseUpdateRequestDto
import com.rork.eduspark.data.remote.teacher.TeacherCoursesApi
import com.rork.eduspark.data.repository.mock.MockTeacherRepository
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class TeacherRepositoryWithRemoteCoursesTest {

    @Test
    fun listsNumericPublishedMathCourseAndSkipsMockIds() = runBlocking {
        val api = FakeTeacherCoursesApi(
            courses = mutableListOf(
                TeacherCourseDto(
                    id = 41,
                    title = "رياضيات",
                    subjectName = "رياضيات",
                    subjectId = 4,
                    grade = 12,
                    isPublished = true,
                    lessonCount = 3,
                ),
                TeacherCourseDto(
                    id = 42,
                    title = "فيزياء",
                    subjectName = "فيزياء",
                    subjectId = 8,
                    grade = 11,
                    isPublished = false,
                    lessonCount = 0,
                ),
            ),
        )
        val repository = fixture(api).repository

        val courses = assertIs<AppResult.Success<List<TeacherCourseSummary>>>(
            repository.getCourses("42"),
        )
        assertEquals(listOf("41", "42"), courses.data.map { it.id })
        assertTrue(courses.data.none { it.id.startsWith("c") })

        val math = courses.data.single { it.id == "41" }
        assertEquals("4", math.subjectId)
        assertEquals(Grade.Baccalaureate, math.grade)
        assertEquals(TeacherCourseStatus.Published, math.status)

        val draft = courses.data.single { it.id == "42" }
        assertEquals(TeacherCourseStatus.Draft, draft.status)
        assertEquals(Grade.Grade11, draft.grade)

        val fetched = assertIs<AppResult.Success<TeacherCourseSummary>>(repository.getCourse("41"))
        assertEquals("41", fetched.data.id)
        assertEquals("رياضيات", fetched.data.title)
    }

    @Test
    fun rejectsMockCourseIdInsteadOfLeakingLocalCatalog() = runBlocking {
        val repository = fixture(FakeTeacherCoursesApi()).repository
        val result = assertIs<AppResult.Failure>(repository.getCourse("c2"))
        assertEquals(AppError.Domain("invalid_course_id"), result.error)
    }

    @Test
    fun createsPublishedMathBaccalaureateCourse() = runBlocking {
        val api = FakeTeacherCoursesApi(
            formContext = TeacherCourseFormContextDto(
                grades = listOf(10, 11, 12),
                subjects = listOf(TeacherCourseSubjectOptionDto(id = 4, nameAr = "رياضيات", grade = 12)),
            ),
        )
        val repository = fixture(api).repository

        val subjects = assertIs<AppResult.Success<List<TeacherCourseFormSubject>>>(
            repository.getCourseFormSubjects(Grade.Baccalaureate),
        )
        assertEquals("4", subjects.data.first().id)
        assertEquals("رياضيات", subjects.data.first().name)

        val created = assertIs<AppResult.Success<TeacherCourseSummary>>(
            repository.createCourse(
                TeacherCourseCreateRequest(
                    title = "رياضيات البكالوريا",
                    subjectId = "4",
                    subjectTitle = "رياضيات",
                    grade = Grade.Baccalaureate,
                    description = "صف الرياضيات للصف الثاني عشر",
                    published = true,
                ),
            ),
        )
        assertEquals("99", created.data.id)
        assertEquals(Grade.Baccalaureate, created.data.grade)
        assertEquals(TeacherCourseStatus.Published, created.data.status)
        assertEquals("4", created.data.subjectId)
        assertEquals(true, api.lastCreate?.isPublished)
        assertEquals(12, api.lastCreate?.grade)
        assertEquals(4, api.lastCreate?.subjectId)
        assertEquals(0f, api.lastCreate?.price)
        assertEquals("SYP", api.lastCreate?.currency)

        val listed = assertIs<AppResult.Success<List<TeacherCourseSummary>>>(repository.getCourses("42"))
        assertEquals(listOf("99"), listed.data.map { it.id })
    }

    @Test
    fun unpublishedCourseStaysDraftAndCanBePublished() = runBlocking {
        val api = FakeTeacherCoursesApi(
            courses = mutableListOf(
                TeacherCourseDto(
                    id = 7,
                    title = "رياضيات",
                    subjectName = "رياضيات",
                    subjectId = 4,
                    grade = 12,
                    isPublished = false,
                    lessonCount = 0,
                ),
            ),
        )
        val repository = fixture(api).repository
        val before = assertIs<AppResult.Success<TeacherCourseSummary>>(repository.getCourse("7"))
        assertEquals(TeacherCourseStatus.Draft, before.data.status)

        val published = assertIs<AppResult.Success<TeacherCourseSummary>>(
            repository.setCoursePublished("7", published = true),
        )
        assertEquals(TeacherCourseStatus.Published, published.data.status)
        assertEquals(true, api.lastUpdate?.isPublished)
    }

    @Test
    fun listsRemoteLessonsAndHidesInvisibleOnesAsDraft() = runBlocking {
        val api = FakeTeacherCoursesApi(
            lessonsByCourse = mutableMapOf(
                41 to listOf(
                    TeacherCourseLessonDto(
                        id = 501,
                        title = "النهايات",
                        hasPdf = true,
                        sortOrder = 1,
                        status = "processed",
                        isVisible = true,
                    ),
                    TeacherCourseLessonDto(
                        id = 502,
                        title = "المشتقات",
                        hasVideo = true,
                        videoUrl = "https://example.com/v.mp4",
                        sortOrder = 2,
                        status = "processed",
                        isVisible = false,
                    ),
                    TeacherCourseLessonDto(
                        id = 503,
                        title = "التكامل",
                        hasPdf = true,
                        sortOrder = 3,
                        status = "processing",
                        isVisible = true,
                    ),
                ),
            ),
        )
        val repository = fixture(api).repository
        val lessons = assertIs<AppResult.Success<List<TeacherLesson>>>(repository.getLessons("41"))
        assertEquals(listOf("501", "502", "503"), lessons.data.map { it.id })
        assertEquals(TeacherLessonStatus.Published, lessons.data[0].status)
        assertEquals(LessonContentType.Pdf, lessons.data[0].contentType)
        assertEquals(TeacherLessonStatus.Draft, lessons.data[1].status)
        assertEquals(LessonContentType.Video, lessons.data[1].contentType)
        assertEquals(TeacherLessonStatus.Processing, lessons.data[2].status)

        val hidden = assertIs<AppResult.Success<TeacherLesson>>(
            repository.setLessonVisible("41", "501", visible = false),
        )
        assertEquals(TeacherLessonStatus.Draft, hidden.data.status)
        assertEquals(false, api.lastLessonVisible)
    }

    private suspend fun fixture(api: FakeTeacherCoursesApi): Fixture {
        val auth = FakeTeacherCoursesAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "42"))
        }
        val coordinator = AuthRefreshCoordinator(auth, store)
        return Fixture(
            repository = TeacherRepositoryWithRemoteCourses(
                delegate = MockTeacherRepository(),
                api = api,
                tokenStore = store,
                refreshCoordinator = coordinator,
                authRepository = RemoteAuthRepository(auth, store, coordinator),
            ),
        )
    }

    private data class Fixture(val repository: TeacherRepositoryWithRemoteCourses)
}

private class FakeTeacherCoursesApi(
    private val courses: MutableList<TeacherCourseDto> = mutableListOf(),
    private val lessonsByCourse: MutableMap<Int, List<TeacherCourseLessonDto>> = mutableMapOf(),
    private val formContext: TeacherCourseFormContextDto = TeacherCourseFormContextDto(),
) : TeacherCoursesApi {
    var lastCreate: TeacherCourseCreateRequestDto? = null
    var lastUpdate: TeacherCourseUpdateRequestDto? = null
    var lastLessonVisible: Boolean? = null

    override suspend fun listCourses(accessToken: String) = ApiCallResult.Success(courses.toList())

    override suspend fun getFormContext(accessToken: String, grade: Int) =
        ApiCallResult.Success(formContext)

    override suspend fun createCourse(
        accessToken: String,
        body: TeacherCourseCreateRequestDto,
    ): ApiCallResult<TeacherCourseDto> {
        lastCreate = body
        val created = TeacherCourseDto(
            id = 99,
            title = body.title,
            description = body.description,
            subjectName = "رياضيات",
            subjectId = body.subjectId,
            grade = body.grade,
            isPublished = body.isPublished,
            lessonCount = 0,
        )
        courses += created
        return ApiCallResult.Success(created)
    }

    override suspend fun updateCourse(
        accessToken: String,
        courseId: Int,
        body: TeacherCourseUpdateRequestDto,
    ): ApiCallResult<TeacherCourseDto> {
        lastUpdate = body
        val index = courses.indexOfFirst { it.id == courseId }
        if (index < 0) return ApiCallResult.HttpFailure(404)
        val current = courses[index]
        val updated = current.copy(isPublished = body.isPublished ?: current.isPublished)
        courses[index] = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun listLessons(accessToken: String, courseId: Int) =
        ApiCallResult.Success(lessonsByCourse[courseId].orEmpty())

    override suspend fun updateLessonVisibility(
        accessToken: String,
        courseId: Int,
        lessonId: Int,
        visible: Boolean,
    ): ApiCallResult<TeacherCourseLessonDto> {
        lastLessonVisible = visible
        val current = lessonsByCourse[courseId].orEmpty().firstOrNull { it.id == lessonId }
            ?: return ApiCallResult.HttpFailure(404)
        return ApiCallResult.Success(current.copy(isVisible = visible))
    }
}

private class FakeTeacherCoursesAuthApi : AuthApi {
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto): ApiCallResult<ResendTwoFactorResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) = ApiCallResult.Success(OkResponseDto())
}
