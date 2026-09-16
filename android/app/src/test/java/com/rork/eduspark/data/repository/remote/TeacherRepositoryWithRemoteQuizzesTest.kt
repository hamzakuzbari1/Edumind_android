package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherCourseQuizAnalytics
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAnalytics
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizStatus
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
import com.rork.eduspark.data.remote.quiz.QuizAnalyticsOutDto
import com.rork.eduspark.data.remote.quiz.QuizAnswerOutDto
import com.rork.eduspark.data.remote.quiz.QuizAttemptOutDto
import com.rork.eduspark.data.remote.quiz.QuizAttemptSummaryOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionCreateDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionStudentOutDto
import com.rork.eduspark.data.remote.quiz.QuizQuestionUpdateDto
import com.rork.eduspark.data.remote.quiz.QuizResultsOutDto
import com.rork.eduspark.data.remote.quiz.SaveAnswersRequestDto
import com.rork.eduspark.data.remote.quiz.StudentQuizListItemDto
import com.rork.eduspark.data.remote.quiz.StudentQuizTakeOutDto
import com.rork.eduspark.data.repository.mock.MockTeacherRepository
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue

class TeacherRepositoryWithRemoteQuizzesTest {

    @Test
    fun createPublishAndListQuizzes() = runBlocking {
        val api = FakeTeacherCourseQuizApi()
        val fixture = fixture(api)

        val created = assertIs<AppResult.Success<TeacherQuiz>>(fixture.repository.createQuiz("c1"))
        assertEquals("كويز جديد", created.data.title)
        assertEquals("c1", created.data.courseId)
        assertEquals(TeacherQuizStatus.Draft, created.data.status)

        val withQuestions = assertIs<AppResult.Success<TeacherQuiz>>(
            fixture.repository.saveQuizQuestions(
                created.data.id,
                listOf(
                    TeacherQuizQuestion(
                        question = QuizQuestion(
                            id = "new",
                            type = QuestionType.MultipleChoice,
                            prompt = "2+2?",
                            options = listOf(QuizOption("0", "3"), QuizOption("1", "4")),
                            correctAnswer = "1",
                            explanation = "",
                        ),
                        points = 2,
                    ),
                    TeacherQuizQuestion(
                        question = QuizQuestion(
                            id = "essay-new",
                            type = QuestionType.ShortAnswer,
                            prompt = "Explain gravity",
                            correctAnswer = "",
                            explanation = "",
                        ),
                        points = 5,
                    ),
                ),
            ),
        )
        assertEquals(2, withQuestions.data.questions.size)

        val published = assertIs<AppResult.Success<TeacherQuiz>>(
            fixture.repository.publishQuiz(created.data.id),
        )
        assertEquals(TeacherQuizStatus.Published, published.data.status)
        assertTrue(api.quizzes.values.single().isPublished)

        val listed = assertIs<AppResult.Success<List<TeacherQuiz>>>(fixture.repository.getQuizzes("t1"))
        assertEquals(1, listed.data.size)
        assertEquals(created.data.id, listed.data.single().id)
    }

    @Test
    fun essayGradeAndAnalytics() = runBlocking {
        val api = FakeTeacherCourseQuizApi()
        val fixture = fixture(api)
        val created = assertIs<AppResult.Success<TeacherQuiz>>(fixture.repository.createQuiz("c1")).data
        assertIs<AppResult.Success<*>>(
            fixture.repository.saveQuizQuestions(
                created.id,
                listOf(
                    TeacherQuizQuestion(
                        question = QuizQuestion(
                            id = "e1",
                            type = QuestionType.ShortAnswer,
                            prompt = "Essay",
                            correctAnswer = "",
                            explanation = "",
                        ),
                        points = 10,
                    ),
                ),
            ),
        )
        api.seedSubmittedAttempt(courseId = 1, quizId = created.id.toInt(), questionId = api.questions.keys.first())

        val attempts = assertIs<AppResult.Success<List<TeacherQuizAttempt>>>(
            fixture.repository.getQuizAttempts(created.id),
        )
        assertEquals(1, attempts.data.size)
        assertTrue(attempts.data.single().hasPendingEssay)

        val graded = assertIs<AppResult.Success<TeacherQuizAttempt>>(
            fixture.repository.saveEssayGrade(
                quizId = created.id,
                studentId = "7",
                questionId = api.questions.keys.first().toString(),
                assignedMark = 8,
                feedback = "Good",
            ),
        )
        assertFalse(graded.data.hasPendingEssay)
        assertEquals(8, graded.data.essayResponses.values.single().assignedMark)

        val analytics = assertIs<AppResult.Success<TeacherQuizAnalytics>>(
            fixture.repository.getQuizAnalytics(created.id),
        )
        assertEquals(72f, analytics.data.averageScore)
        assertEquals(88f, analytics.data.highestScore)

        val courseAnalytics = assertIs<AppResult.Success<TeacherCourseQuizAnalytics>>(
            fixture.repository.getCourseQuizAnalytics("c1"),
        )
        assertEquals(1, courseAnalytics.data.quizCount)
    }

    private suspend fun fixture(api: FakeTeacherCourseQuizApi): Fixture {
        val auth = FakeTeacherQuizAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "42"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        return Fixture(
            repository = TeacherRepositoryWithRemoteQuizzes(
                delegate = MockTeacherRepository(),
                api = api,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
            ),
        )
    }

    private data class Fixture(val repository: TeacherRepositoryWithRemoteQuizzes)
}

private class FakeTeacherCourseQuizApi : CourseQuizApi {
    var nextQuizId = 1
    var nextQuestionId = 100
    val quizzes = mutableMapOf<Int, CourseQuizOutDto>()
    val questions = mutableMapOf<Int, QuizQuestionOutDto>()
    private val quizQuestions = mutableMapOf<Int, MutableList<Int>>()
    private var attempt: QuizAttemptOutDto? = null

    fun seedSubmittedAttempt(courseId: Int, quizId: Int, questionId: Int) {
        attempt = QuizAttemptOutDto(
            id = 501,
            quizId = quizId,
            studentId = 7,
            studentName = "Sara",
            status = "submitted",
            score = 0f,
            maxScore = 10f,
            percent = null,
            passed = null,
            submittedAt = "2026-04-01T12:00:00Z",
            answers = listOf(
                QuizAnswerOutDto(
                    questionId = questionId,
                    questionType = "essay",
                    questionText = "Essay",
                    answer = JsonPrimitive("student essay"),
                    pointsEarned = null,
                    maxPoints = 10,
                    requiresManualGrading = true,
                    pendingGrading = true,
                ),
            ),
        )
    }

    override suspend fun listTeacherQuizzes(accessToken: String, courseId: Int) =
        ApiCallResult.Success(quizzes.values.filter { it.courseId == courseId })

    override suspend fun createQuiz(
        accessToken: String,
        courseId: Int,
        body: CourseQuizCreateDto,
    ): ApiCallResult<CourseQuizOutDto> {
        val id = nextQuizId++
        val quiz = CourseQuizOutDto(
            id = id,
            courseId = courseId,
            title = body.title,
            description = body.description,
            durationMinutes = body.durationMinutes,
            passingScorePercent = body.passingScorePercent,
            isPublished = body.isPublished,
        )
        quizzes[id] = quiz
        quizQuestions[id] = mutableListOf()
        return ApiCallResult.Success(quiz)
    }

    override suspend fun getQuizDetail(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<CourseQuizDetailOutDto> {
        val quiz = quizzes[quizId] ?: return ApiCallResult.HttpFailure(404)
        val q = quizQuestions[quizId].orEmpty().mapNotNull { questions[it] }
        return ApiCallResult.Success(
            CourseQuizDetailOutDto(
                id = quiz.id,
                courseId = quiz.courseId,
                title = quiz.title,
                description = quiz.description,
                durationMinutes = quiz.durationMinutes,
                passingScorePercent = quiz.passingScorePercent,
                isPublished = quiz.isPublished,
                questionCount = q.size,
                totalPoints = q.sumOf { it.points },
                questions = q,
            ),
        )
    }

    override suspend fun updateQuiz(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: CourseQuizUpdateDto,
    ): ApiCallResult<CourseQuizOutDto> {
        val existing = quizzes[quizId] ?: return ApiCallResult.HttpFailure(404)
        val updated = existing.copy(
            title = body.title ?: existing.title,
            description = body.description ?: existing.description,
            durationMinutes = body.durationMinutes ?: existing.durationMinutes,
            passingScorePercent = body.passingScorePercent ?: existing.passingScorePercent,
            isPublished = body.isPublished ?: existing.isPublished,
        )
        quizzes[quizId] = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun addQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: QuizQuestionCreateDto,
    ): ApiCallResult<QuizQuestionOutDto> {
        val id = nextQuestionId++
        val q = QuizQuestionOutDto(
            id = id,
            questionType = body.questionType,
            questionText = body.questionText,
            options = body.options.orEmpty(),
            points = body.points,
            sortOrder = body.sortOrder,
            requiresManualGrading = body.questionType == "essay",
            correctAnswer = body.correctAnswer,
        )
        questions[id] = q
        quizQuestions.getOrPut(quizId) { mutableListOf() }.add(id)
        return ApiCallResult.Success(q)
    }

    override suspend fun updateQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
        body: QuizQuestionUpdateDto,
    ): ApiCallResult<QuizQuestionOutDto> {
        val existing = questions[questionId] ?: return ApiCallResult.HttpFailure(404)
        val updated = existing.copy(
            questionType = body.questionType ?: existing.questionType,
            questionText = body.questionText ?: existing.questionText,
            options = body.options ?: existing.options,
            points = body.points ?: existing.points,
            sortOrder = body.sortOrder ?: existing.sortOrder,
            correctAnswer = body.correctAnswer ?: existing.correctAnswer,
            requiresManualGrading = (body.questionType ?: existing.questionType) == "essay",
        )
        questions[questionId] = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun deleteQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
    ): ApiCallResult<Unit> {
        questions.remove(questionId)
        quizQuestions[quizId]?.remove(questionId)
        return ApiCallResult.Success(Unit)
    }

    override suspend fun getResults(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<QuizResultsOutDto> {
        val quiz = quizzes[quizId] ?: return ApiCallResult.HttpFailure(404)
        val att = attempt
        val summaries = if (att != null && att.quizId == quizId) {
            listOf(
                QuizAttemptSummaryOutDto(
                    id = att.id,
                    studentId = att.studentId,
                    studentName = att.studentName.orEmpty(),
                    status = att.status,
                    score = att.score,
                    maxScore = att.maxScore,
                    percent = att.percent,
                    passed = att.passed,
                    submittedAt = att.submittedAt,
                    pendingEssayCount = att.answers.count { it.pendingGrading },
                ),
            )
        } else {
            emptyList()
        }
        return ApiCallResult.Success(QuizResultsOutDto(quiz = quiz, attempts = summaries))
    }

    override suspend fun getTeacherAttempt(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
    ): ApiCallResult<QuizAttemptOutDto> =
        attempt?.takeIf { it.id == attemptId }?.let { ApiCallResult.Success(it) }
            ?: ApiCallResult.HttpFailure(404)

    override suspend fun gradeEssay(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
        questionId: Int,
        body: GradeEssayRequestDto,
    ): ApiCallResult<QuizAttemptOutDto> {
        val current = attempt ?: return ApiCallResult.HttpFailure(404)
        val updatedAnswers = current.answers.map {
            if (it.questionId == questionId) {
                it.copy(
                    pointsEarned = body.pointsEarned,
                    teacherFeedback = body.teacherFeedback,
                    pendingGrading = false,
                    isCorrect = body.pointsEarned > 0,
                )
            } else {
                it
            }
        }
        val updated = current.copy(
            status = "graded",
            score = body.pointsEarned,
            percent = (body.pointsEarned / current.maxScore) * 100f,
            passed = true,
            answers = updatedAnswers,
        )
        attempt = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun getQuizAnalytics(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ) = ApiCallResult.Success(
        QuizAnalyticsOutDto(
            quizId = quizId,
            quizTitle = quizzes[quizId]?.title.orEmpty(),
            enrolledStudents = 10,
            attemptedCount = 5,
            completionRate = 0.5f,
            averageScore = 72f,
            highestScore = 88f,
            lowestScore = 40f,
        ),
    )

    override suspend fun getCourseQuizAnalytics(accessToken: String, courseId: Int) =
        ApiCallResult.Success(
            CourseQuizAnalyticsOutDto(
                courseId = courseId,
                courseTitle = "Physics",
                quizCount = quizzes.values.count { it.courseId == courseId },
                enrolledStudents = 10,
                totalAttempts = 5,
                averageScore = 70f,
                completionRate = 0.4f,
                quizzes = emptyList(),
            ),
        )

    override suspend fun deleteQuiz(accessToken: String, courseId: Int, quizId: Int): ApiCallResult<Unit> {
        quizzes.remove(quizId)
        return ApiCallResult.Success(Unit)
    }

    // Student stubs
    override suspend fun listStudentQuizzes(
        accessToken: String,
        courseId: Int,
    ): ApiCallResult<List<StudentQuizListItemDto>> = ApiCallResult.HttpFailure(500)
    override suspend fun getStudentTake(accessToken: String, quizId: Int): ApiCallResult<StudentQuizTakeOutDto> =
        ApiCallResult.HttpFailure(500)
    override suspend fun startAttempt(accessToken: String, quizId: Int): ApiCallResult<StudentQuizTakeOutDto> =
        ApiCallResult.HttpFailure(500)
    override suspend fun saveAnswers(
        accessToken: String,
        attemptId: Int,
        body: SaveAnswersRequestDto,
    ): ApiCallResult<Unit> = ApiCallResult.HttpFailure(500)
    override suspend fun submitAttempt(accessToken: String, attemptId: Int): ApiCallResult<QuizAttemptOutDto> =
        ApiCallResult.HttpFailure(500)
    override suspend fun getStudentAttempt(accessToken: String, attemptId: Int): ApiCallResult<QuizAttemptOutDto> =
        ApiCallResult.HttpFailure(500)
}

private class FakeTeacherQuizAuthApi : AuthApi {
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
