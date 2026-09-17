package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.StudentCourseQuizSummary
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
import com.rork.eduspark.data.remote.quiz.CourseQuizAnalyticsOutDto
import com.rork.eduspark.data.remote.quiz.CourseQuizApi
import com.rork.eduspark.data.remote.quiz.CourseQuizCreateDto
import com.rork.eduspark.data.remote.quiz.CourseQuizDetailOutDto
import com.rork.eduspark.data.remote.quiz.CourseQuizOutDto
import com.rork.eduspark.data.remote.quiz.CourseQuizUpdateDto
import com.rork.eduspark.data.remote.quiz.GradeEssayRequestDto
import com.rork.eduspark.data.remote.quiz.LessonQuizApi
import com.rork.eduspark.data.remote.quiz.LessonQuizFeedbackItemDto
import com.rork.eduspark.data.remote.quiz.LessonQuizGeneratedQuestionDto
import com.rork.eduspark.data.remote.quiz.LessonQuizQuestionDto
import com.rork.eduspark.data.remote.quiz.LessonQuizRegenerateResponseDto
import com.rork.eduspark.data.remote.quiz.LessonQuizRemedialRequestDto
import com.rork.eduspark.data.remote.quiz.LessonQuizRemedialResponseDto
import com.rork.eduspark.data.remote.quiz.LessonQuizSubmitRequestDto
import com.rork.eduspark.data.remote.quiz.LessonQuizSubmitResponseDto
import com.rork.eduspark.data.remote.quiz.QuizAnalyticsOutDto
import com.rork.eduspark.data.remote.quiz.QuizAnswerOutDto
import com.rork.eduspark.data.remote.quiz.QuizAttemptOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionCreateDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionStudentOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionUpdateDto
import com.rork.eduspark.data.remote.quiz.QuizResultsOutDto
import com.rork.eduspark.data.remote.quiz.SaveAnswersRequestDto
import com.rork.eduspark.data.remote.quiz.StudentQuizListItemDto
import com.rork.eduspark.data.remote.quiz.StudentQuizTakeOutDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RemoteQuizRepositoryTest {

    @Test
    fun startSaveSubmitUsesServerPercentAndPendingEssay() = runBlocking {
        val api = FakeCourseQuizApi()
        val fixture = fixture(api)

        val quiz = assertIs<AppResult.Success<Quiz>>(fixture.repository.getQuiz("manual-5")).data
        assertEquals(QuizOrigin.TeacherManual, quiz.origin)
        assertEquals("5", quiz.lessonId)
        assertNotNull(api.lastStartedQuizId)

        fixture.repository.saveAnswer("manual-5", QuizAnswer("10", "0"))
        fixture.repository.saveAnswer("manual-5", QuizAnswer("11", "essay answer"))

        val result = assertIs<AppResult.Success<QuizResult>>(fixture.repository.submitQuiz("manual-5"))
        assertEquals(80, result.data.scorePercent)
        assertEquals(true, result.data.passed)
        assertTrue(result.data.hasPendingEssay)
        assertEquals(8f, result.data.earnedScore)
        assertEquals(10f, result.data.maxScore)
        assertTrue(result.data.attempt.isCompleted)
    }

    @Test
    fun completedAttemptCannotRestart() = runBlocking {
        val api = FakeCourseQuizApi(seedSubmitted = true)
        val fixture = fixture(api)

        assertIs<AppResult.Success<*>>(fixture.repository.getQuiz("12"))
        val attempt = fixture.repository.getAttempt("12")
        assertTrue(attempt.isCompleted)
        assertEquals(0, api.startCalls)

        val reset = fixture.repository.resetAttempt("12")
        assertTrue(reset.isCompleted)

        val result = assertIs<AppResult.Success<QuizResult>>(fixture.repository.getResult("12"))
        assertEquals(90, result.data.scorePercent)
        assertFalse(result.data.hasPendingEssay)
    }

    @Test
    fun remedialRejectedForManual() = runBlocking {
        val fixture = fixture(FakeCourseQuizApi())
        assertIs<AppResult.Success<*>>(fixture.repository.getQuiz("manual-5"))
        val remedial = assertIs<AppResult.Failure>(fixture.repository.buildRemedialQuiz("manual-5"))
        assertEquals(AppError.Domain("remedial_not_supported_for_manual"), remedial.error)
    }

    @Test
    fun listCourseQuizzesReturnsEachPublishedQuiz() = runBlocking {
        val api = FakeCourseQuizApi(extraQuiz = true)
        val fixture = fixture(api)
        val listed = assertIs<AppResult.Success<List<StudentCourseQuizSummary>>>(
            fixture.repository.listCourseQuizzes("5"),
        ).data
        assertEquals(2, listed.size)
        assertEquals(listOf("12", "99"), listed.map { it.id })
        assertEquals("كويز الوحدة", listed[0].title)
        assertEquals("كويز إضافي", listed[1].title)
    }

    @Test
    fun numericQuizIdOpensExactQuizNotFirstOnly() = runBlocking {
        val api = FakeCourseQuizApi(extraQuiz = true)
        val fixture = fixture(api)
        val quiz = assertIs<AppResult.Success<Quiz>>(fixture.repository.getQuiz("99")).data
        assertEquals("99", quiz.id)
        assertEquals(99, api.lastStartedQuizId)
    }

    @Test
    fun legacyManualCourseIdRejectedWhenMultipleQuizzes() = runBlocking {
        val fixture = fixture(FakeCourseQuizApi(extraQuiz = true))
        val failure = assertIs<AppResult.Failure>(fixture.repository.getQuiz("manual-5"))
        assertEquals(AppError.Domain("invalid_quiz_id"), failure.error)
    }

    @Test
    fun listCourseQuizzesEmptyIsSafe() = runBlocking {
        val fixture = fixture(FakeCourseQuizApi(emptyList = true))
        val listed = assertIs<AppResult.Success<List<StudentCourseQuizSummary>>>(
            fixture.repository.listCourseQuizzes("5"),
        ).data
        assertTrue(listed.isEmpty())
    }

    @Test
    fun aiLessonLoadSubmitUsesOptionIndexAndServerScore() = runBlocking {
        val lessonApi = FakeLessonQuizApi()
        val fixture = fixture(FakeCourseQuizApi(), lessonApi)

        val quiz = assertIs<AppResult.Success<Quiz>>(fixture.repository.getQuiz("lesson-88")).data
        assertEquals(QuizOrigin.AiLesson, quiz.origin)
        assertEquals("88", quiz.lessonId)
        assertEquals(2, quiz.questions.size)
        assertEquals("0", quiz.questions[0].options[0].id)
        assertNull(fixture.repository.getAttempt("lesson-88").attemptId)

        fixture.repository.saveAnswer("lesson-88", QuizAnswer("101", "1"))
        fixture.repository.saveAnswer("lesson-88", QuizAnswer("102", "0"))

        val result = assertIs<AppResult.Success<QuizResult>>(fixture.repository.submitQuiz("lesson-88"))
        assertEquals(mapOf("101" to 1, "102" to 0), lessonApi.lastSubmit?.answers)
        assertEquals(88, lessonApi.lastSubmit?.lessonId)
        assertEquals(50, result.data.scorePercent)
        assertEquals(1, result.data.correctCount)
        assertTrue(result.data.attempt.isCompleted)
        assertNull(result.data.attempt.attemptId)
    }

    @Test
    fun aiLessonEmptyQuizHandledSafely() = runBlocking {
        val lessonApi = FakeLessonQuizApi(empty = true)
        val fixture = fixture(FakeCourseQuizApi(), lessonApi)
        val failure = assertIs<AppResult.Failure>(fixture.repository.getQuiz("lesson-1"))
        assertEquals(AppError.Domain("quiz_not_ready"), failure.error)
    }

    @Test
    fun aiLessonRegenerateThenReload() = runBlocking {
        val lessonApi = FakeLessonQuizApi()
        val fixture = fixture(FakeCourseQuizApi(), lessonApi)
        assertIs<AppResult.Success<*>>(fixture.repository.getQuiz("lesson-88"))
        val regenerated = assertIs<AppResult.Success<Quiz>>(fixture.repository.regenerateQuiz("lesson-88"))
        assertEquals(1, lessonApi.regenerateCalls)
        assertEquals(QuizOrigin.AiLesson, regenerated.data.origin)
        assertEquals(2, regenerated.data.questions.size)
    }

    @Test
    fun aiLessonRemedialUsesBackendQuestions() = runBlocking {
        val lessonApi = FakeLessonQuizApi()
        val fixture = fixture(FakeCourseQuizApi(), lessonApi)
        assertIs<AppResult.Success<*>>(fixture.repository.getQuiz("lesson-88"))
        fixture.repository.saveAnswer("lesson-88", QuizAnswer("101", "0"))
        fixture.repository.saveAnswer("lesson-88", QuizAnswer("102", "1"))
        assertIs<AppResult.Success<*>>(fixture.repository.submitQuiz("lesson-88"))

        val remedial = assertIs<AppResult.Success<Quiz>>(fixture.repository.buildRemedialQuiz("lesson-88"))
        assertTrue(remedial.data.isRemedial)
        assertTrue(remedial.data.id.startsWith("remedial-"))
        assertEquals(1, remedial.data.questions.size)
        assertNotNull(lessonApi.lastRemedial)

        val remedialId = remedial.data.id
        val correct = remedial.data.questions[0].correctAnswer
        fixture.repository.saveAnswer(remedialId, QuizAnswer(remedial.data.questions[0].id, correct))
        val scored = assertIs<AppResult.Success<QuizResult>>(fixture.repository.submitQuiz(remedialId))
        assertEquals(100, scored.data.scorePercent)
        assertEquals(1, lessonApi.submitCalls) // remedial scored locally, not via /quiz/submit
    }

    @Test
    fun regenerateRejectedForManual() = runBlocking {
        val fixture = fixture(FakeCourseQuizApi())
        assertIs<AppResult.Success<*>>(fixture.repository.getQuiz("manual-5"))
        val failure = assertIs<AppResult.Failure>(fixture.repository.regenerateQuiz("manual-5"))
        assertEquals(AppError.Domain("regenerate_not_supported_for_manual"), failure.error)
    }

    private suspend fun fixture(
        api: FakeCourseQuizApi,
        lessonApi: LessonQuizApi = FakeLessonQuizApi(),
    ): Fixture {
        val auth = FakeQuizAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "42"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        return Fixture(
            repository = RemoteQuizRepository(
                api = api,
                lessonQuizApi = lessonApi,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
                ioScope = CoroutineScope(Dispatchers.Unconfined),
            ),
        )
    }

    private data class Fixture(val repository: RemoteQuizRepository)
}

private class FakeLessonQuizApi(
    private val empty: Boolean = false,
) : LessonQuizApi {
    var lastSubmit: LessonQuizSubmitRequestDto? = null
    var lastRemedial: LessonQuizRemedialRequestDto? = null
    var regenerateCalls = 0
    var submitCalls = 0

    private val questions = listOf(
        LessonQuizQuestionDto(id = 101, question = "Q1", options = listOf("A", "B"), hint = "h1"),
        LessonQuizQuestionDto(id = 102, question = "Q2", options = listOf("C", "D"), hint = "h2"),
    )

    override suspend fun getQuiz(accessToken: String, lessonId: Int): ApiCallResult<List<LessonQuizQuestionDto>> {
        if (empty) return ApiCallResult.HttpFailure(404, detail = "لا يوجد اختبار لهذا الدرس")
        return ApiCallResult.Success(questions)
    }

    override suspend fun submitQuiz(
        accessToken: String,
        body: LessonQuizSubmitRequestDto,
    ): ApiCallResult<LessonQuizSubmitResponseDto> {
        submitCalls++
        lastSubmit = body
        return ApiCallResult.Success(
            LessonQuizSubmitResponseDto(
                correctCount = 1,
                total = 2,
                scorePercent = 50,
                feedback = listOf(
                    LessonQuizFeedbackItemDto(questionId = 101, correct = body.answers["101"] == 1, message = "ok"),
                    LessonQuizFeedbackItemDto(questionId = 102, correct = body.answers["102"] == 1, hint = "راجع", message = "خطأ"),
                ),
            ),
        )
    }

    override suspend fun regenerateQuiz(
        accessToken: String,
        lessonId: Int,
    ): ApiCallResult<LessonQuizRegenerateResponseDto> {
        regenerateCalls++
        return ApiCallResult.Success(
            LessonQuizRegenerateResponseDto(
                quizQuestions = listOf(
                    LessonQuizGeneratedQuestionDto("1", "NQ1", listOf("A", "B"), correctIndex = 0),
                    LessonQuizGeneratedQuestionDto("2", "NQ2", listOf("C", "D"), correctIndex = 1),
                ),
            ),
        )
    }

    override suspend fun remedialQuiz(
        accessToken: String,
        lessonId: Int,
        body: LessonQuizRemedialRequestDto,
    ): ApiCallResult<LessonQuizRemedialResponseDto> {
        lastRemedial = body
        return ApiCallResult.Success(
            LessonQuizRemedialResponseDto(
                questions = listOf(
                    LessonQuizGeneratedQuestionDto(
                        id = "remedial-$lessonId-0",
                        question = "Fix this",
                        options = listOf("Right", "Wrong"),
                        correctIndex = 0,
                        hint = "think",
                    ),
                ),
            ),
        )
    }
}

private class FakeCourseQuizApi(
    seedSubmitted: Boolean = false,
    private val extraQuiz: Boolean = false,
    private val emptyList: Boolean = false,
) : CourseQuizApi {
    var lastStartedQuizId: Int? = null
    var startCalls = 0
    private var nextAttemptId = 100
    private val attempts = mutableMapOf<Int, QuizAttemptOutDto>()
    private val takes = mutableMapOf<Int, StudentQuizTakeOutDto>()

    init {
        val quiz = StudentQuizListItemDto(
            id = 12,
            courseId = 5,
            title = "كويز الوحدة",
            durationMinutes = 15,
            passingScorePercent = 60,
            questionCount = 2,
            totalPoints = 10,
            attemptStatus = if (seedSubmitted) "graded" else null,
            percent = if (seedSubmitted) 90f else null,
            passed = if (seedSubmitted) true else null,
            score = if (seedSubmitted) 9f else null,
            maxScore = if (seedSubmitted) 10f else null,
        )
        val questions = listOf(
            QuizQuestionStudentOutDto(
                id = 10,
                questionType = "multiple_choice",
                questionText = "MC?",
                options = listOf("A", "B"),
                points = 5,
                sortOrder = 0,
            ),
            QuizQuestionStudentOutDto(
                id = 11,
                questionType = "essay",
                questionText = "Explain",
                points = 5,
                sortOrder = 1,
                requiresManualGrading = true,
            ),
        )
        if (seedSubmitted) {
            val attemptId = 55
            takes[12] = StudentQuizTakeOutDto(
                quiz = quiz,
                questions = questions,
                attemptId = attemptId,
                answers = mapOf("10" to buildJsonObject { put("selected_index", 0) }),
                timeRemainingSeconds = null,
            )
            attempts[attemptId] = QuizAttemptOutDto(
                id = attemptId,
                quizId = 12,
                studentId = 42,
                studentName = "Ali",
                status = "graded",
                score = 9f,
                maxScore = 10f,
                percent = 90f,
                passed = true,
                answers = listOf(
                    QuizAnswerOutDto(
                        questionId = 10,
                        questionType = "multiple_choice",
                        answer = buildJsonObject { put("selected_index", 0) },
                        pointsEarned = 5f,
                        maxPoints = 5,
                        isCorrect = true,
                    ),
                    QuizAnswerOutDto(
                        questionId = 11,
                        questionType = "essay",
                        answer = JsonPrimitive("done"),
                        pointsEarned = 4f,
                        maxPoints = 5,
                        requiresManualGrading = true,
                        pendingGrading = false,
                    ),
                ),
            )
        } else {
            takes[12] = StudentQuizTakeOutDto(
                quiz = quiz,
                questions = questions,
                attemptId = null,
                answers = emptyMap(),
                timeRemainingSeconds = 600,
            )
        }
        if (extraQuiz) {
            val second = StudentQuizListItemDto(
                id = 99,
                courseId = 5,
                title = "كويز إضافي",
                durationMinutes = 10,
                passingScorePercent = 60,
                questionCount = 1,
                totalPoints = 5,
            )
            takes[99] = StudentQuizTakeOutDto(
                quiz = second,
                questions = listOf(
                    QuizQuestionStudentOutDto(
                        id = 20,
                        questionType = "multiple_choice",
                        questionText = "Extra?",
                        options = listOf("Yes", "No"),
                        points = 5,
                        sortOrder = 0,
                    ),
                ),
                attemptId = null,
                answers = emptyMap(),
                timeRemainingSeconds = 300,
            )
        }
    }

    override suspend fun listStudentQuizzes(accessToken: String, courseId: Int) =
        when {
            emptyList -> ApiCallResult.Success(emptyList())
            extraQuiz -> ApiCallResult.Success(
                listOf(
                    takes[12]!!.quiz.copy(courseId = courseId),
                    takes[99]!!.quiz.copy(courseId = courseId),
                ),
            )
            else -> ApiCallResult.Success(listOf(takes[12]!!.quiz.copy(courseId = courseId)))
        }

    override suspend fun getStudentTake(accessToken: String, quizId: Int) =
        ApiCallResult.Success(takes[quizId] ?: takes[12]!!)

    override suspend fun startAttempt(accessToken: String, quizId: Int): ApiCallResult<StudentQuizTakeOutDto> {
        startCalls++
        lastStartedQuizId = quizId
        val existing = takes[quizId] ?: takes[12]!!
        if (existing.attemptId != null) return ApiCallResult.Success(existing)
        val attemptId = nextAttemptId++
        val updated = existing.copy(attemptId = attemptId, quiz = existing.quiz.copy(attemptStatus = "in_progress"))
        takes[quizId] = updated
        if (quizId == 12) takes[12] = updated
        attempts[attemptId] = QuizAttemptOutDto(
            id = attemptId,
            quizId = quizId,
            studentId = 42,
            status = "in_progress",
            score = 0f,
            maxScore = existing.quiz.totalPoints.toFloat().coerceAtLeast(1f),
        )
        return ApiCallResult.Success(updated)
    }

    override suspend fun saveAnswers(
        accessToken: String,
        attemptId: Int,
        body: SaveAnswersRequestDto,
    ): ApiCallResult<Unit> = ApiCallResult.Success(Unit)

    override suspend fun submitAttempt(accessToken: String, attemptId: Int): ApiCallResult<QuizAttemptOutDto> {
        val out = QuizAttemptOutDto(
            id = attemptId,
            quizId = 12,
            studentId = 42,
            studentName = "Ali",
            status = "submitted",
            score = 8f,
            maxScore = 10f,
            percent = 80f,
            passed = true,
            answers = listOf(
                QuizAnswerOutDto(
                    questionId = 10,
                    questionType = "multiple_choice",
                    answer = buildJsonObject { put("index", 0); put("selected_index", 0) },
                    pointsEarned = 5f,
                    maxPoints = 5,
                    isCorrect = true,
                ),
                QuizAnswerOutDto(
                    questionId = 11,
                    questionType = "essay",
                    answer = JsonPrimitive("essay answer"),
                    pointsEarned = null,
                    maxPoints = 5,
                    requiresManualGrading = true,
                    pendingGrading = true,
                ),
            ),
        )
        attempts[attemptId] = out
        takes[12] = takes[12]!!.copy(
            attemptId = attemptId,
            quiz = takes[12]!!.quiz.copy(attemptStatus = "submitted", percent = 80f, passed = true),
        )
        return ApiCallResult.Success(out)
    }

    override suspend fun getStudentAttempt(accessToken: String, attemptId: Int) =
        attempts[attemptId]?.let { ApiCallResult.Success(it) } ?: ApiCallResult.HttpFailure(404)

    // Teacher methods unused in student tests
    override suspend fun listTeacherQuizzes(accessToken: String, courseId: Int): ApiCallResult<List<CourseQuizOutDto>> =
        ApiCallResult.HttpFailure(500)
    override suspend fun createQuiz(
        accessToken: String,
        courseId: Int,
        body: CourseQuizCreateDto,
    ): ApiCallResult<CourseQuizOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun getQuizDetail(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<CourseQuizDetailOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun updateQuiz(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: CourseQuizUpdateDto,
    ): ApiCallResult<CourseQuizOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun deleteQuiz(accessToken: String, courseId: Int, quizId: Int): ApiCallResult<Unit> =
        ApiCallResult.HttpFailure(500)
    override suspend fun addQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: QuizQuestionCreateDto,
    ): ApiCallResult<QuizQuestionOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun updateQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
        body: QuizQuestionUpdateDto,
    ): ApiCallResult<QuizQuestionOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun deleteQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
    ): ApiCallResult<Unit> = ApiCallResult.HttpFailure(500)
    override suspend fun getResults(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<QuizResultsOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun getTeacherAttempt(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
    ): ApiCallResult<QuizAttemptOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun gradeEssay(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
        questionId: Int,
        body: GradeEssayRequestDto,
    ): ApiCallResult<QuizAttemptOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun getQuizAnalytics(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<QuizAnalyticsOutDto> = ApiCallResult.HttpFailure(500)
    override suspend fun getCourseQuizAnalytics(
        accessToken: String,
        courseId: Int,
    ): ApiCallResult<CourseQuizAnalyticsOutDto> = ApiCallResult.HttpFailure(500)
}

private class FakeQuizAuthApi : AuthApi {
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
