package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizAttempt
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.StudentCourseQuizSummary
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.quiz.CourseQuizApi
import com.rork.eduspark.data.remote.quiz.LessonQuizApi
import com.rork.eduspark.data.remote.quiz.LessonQuizIds
import com.rork.eduspark.data.remote.quiz.LessonQuizRemedialRequestDto
import com.rork.eduspark.data.remote.quiz.LessonQuizSubmitRequestDto
import com.rork.eduspark.data.remote.quiz.SaveAnswerItemDto
import com.rork.eduspark.data.remote.quiz.SaveAnswersRequestDto
import com.rork.eduspark.data.remote.quiz.StudentQuizTakeOutDto
import com.rork.eduspark.data.remote.quiz.clientScoreAiQuiz
import com.rork.eduspark.data.remote.quiz.isAttemptSubmittedStatus
import com.rork.eduspark.data.remote.quiz.packAnswerForApi
import com.rork.eduspark.data.remote.quiz.toDomainAnswers
import com.rork.eduspark.data.remote.quiz.toDomainQuiz
import com.rork.eduspark.data.remote.quiz.toLessonQuizAnswerIndices
import com.rork.eduspark.data.remote.quiz.toQuizResult
import com.rork.eduspark.data.remote.quiz.toRemedialDomainQuiz
import com.rork.eduspark.data.remote.quiz.toStudentCourseQuizSummary
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.QuizRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * Remote student quiz shell for both engines:
 * - Manual course quizzes (`manual-{courseId}` / numeric) — attempt_id lifecycle (A5.1)
 * - AI lesson quizzes (`lesson-{lessonId}` / `remedial-lesson-{lessonId}`) — lesson_id + index submit (A5.2)
 */
internal class RemoteQuizRepository(
    private val api: CourseQuizApi,
    private val lessonQuizApi: LessonQuizApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
    private val ioScope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
) : QuizRepository {

    private enum class Engine { Manual, AiLesson }

    private data class Session(
        val engine: Engine,
        var quiz: Quiz,
        val numericQuizId: Int?,
        val courseId: Int?,
        val lessonId: Int?,
        val attemptId: Int?,
        val answers: MutableMap<String, QuizAnswer>,
        var currentIndex: Int,
        val timeRemainingSeconds: Int?,
        val questionBackendTypes: Map<String, String>,
        var completed: Boolean,
    )

    private val sessions = mutableMapOf<String, Session>()
    private val results = mutableMapOf<String, QuizResult>()
    private val mutex = Mutex()

    override suspend fun getQuiz(quizId: String): AppResult<Quiz> {
        if (LessonQuizIds.isAiLessonClientId(quizId)) {
            return getAiLessonQuiz(quizId)
        }
        return getManualQuiz(quizId)
    }

    private suspend fun getAiLessonQuiz(quizId: String): AppResult<Quiz> {
        if (LessonQuizIds.isRemedialClientId(quizId)) {
            val existing = mutex.withLock { sessions[quizId]?.quiz }
            return if (existing != null && existing.isRemedial) {
                AppResult.Success(existing)
            } else {
                AppResult.Failure(AppError.NotFound)
            }
        }
        val lessonId = LessonQuizIds.parseLessonId(quizId)
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_quiz_id"))

        return when (val loaded = authorizedRequest { lessonQuizApi.getQuiz(it, lessonId) }) {
            is ApiCallResult.Success -> {
                if (loaded.value.isEmpty()) {
                    return AppResult.Failure(AppError.Domain("quiz_not_ready"))
                }
                val quiz = loaded.value.toDomainQuiz(clientQuizId = quizId, lessonId = lessonId)
                mutex.withLock {
                    sessions[quizId] = Session(
                        engine = Engine.AiLesson,
                        quiz = quiz,
                        numericQuizId = null,
                        courseId = null,
                        lessonId = lessonId,
                        attemptId = null,
                        answers = mutableMapOf(),
                        currentIndex = 0,
                        timeRemainingSeconds = null,
                        questionBackendTypes = emptyMap(),
                        completed = false,
                    )
                    results.remove(quizId)
                }
                AppResult.Success(quiz)
            }
            is ApiCallResult.HttpFailure -> when (loaded.statusCode) {
                404, 410 -> AppResult.Failure(AppError.Domain("quiz_not_ready"))
                else -> AppResult.Failure(handleFailure(loaded))
            }
            else -> AppResult.Failure(handleFailure(loaded))
        }
    }

    private suspend fun getManualQuiz(quizId: String): AppResult<Quiz> {
        val resolved = resolveNumericQuizId(quizId)
            ?: return AppResult.Failure(AppError.Domain("invalid_quiz_id"))
        val (numericId, courseHint) = resolved

        val takeResult = authorizedRequest { api.getStudentTake(it, numericId) }
        val take = when (takeResult) {
            is ApiCallResult.Success -> takeResult.value
            else -> return AppResult.Failure(handleFailure(takeResult))
        }

        val alreadySubmitted = isAttemptSubmittedStatus(take.quiz.attemptStatus)
        val activeTake: StudentQuizTakeOutDto = when {
            take.attemptId != null || alreadySubmitted -> take
            else -> when (val started = authorizedRequest { api.startAttempt(it, numericId) }) {
                is ApiCallResult.Success -> started.value
                else -> return AppResult.Failure(handleFailure(started))
            }
        }

        val quiz = activeTake.toDomainQuiz(clientQuizId = quizId)
        val answers = activeTake.toDomainAnswers().toMutableMap()
        val backendTypes = activeTake.questions.associate { it.id.toString() to it.questionType }
        val completed = isAttemptSubmittedStatus(activeTake.quiz.attemptStatus)

        mutex.withLock {
            sessions[quizId] = Session(
                engine = Engine.Manual,
                quiz = quiz,
                numericQuizId = activeTake.quiz.id,
                courseId = courseHint ?: activeTake.quiz.courseId,
                lessonId = null,
                attemptId = activeTake.attemptId,
                answers = answers,
                currentIndex = 0,
                timeRemainingSeconds = activeTake.timeRemainingSeconds,
                questionBackendTypes = backendTypes,
                completed = completed,
            )
        }

        if (completed && activeTake.attemptId != null) {
            when (val attempt = authorizedRequest { api.getStudentAttempt(it, activeTake.attemptId) }) {
                is ApiCallResult.Success -> {
                    val result = attempt.value.toQuizResult(quiz)
                    results[quizId] = result
                }
                else -> Unit
            }
        }

        return AppResult.Success(quiz)
    }

    override fun getAttempt(quizId: String): QuizAttempt {
        val session = sessions[quizId]
        return if (session != null) {
            QuizAttempt(
                quizId = quizId,
                currentQuestionIndex = session.currentIndex,
                answers = session.answers.toMap(),
                isCompleted = session.completed,
                attemptId = session.attemptId?.toString(),
            )
        } else {
            QuizAttempt(quizId = quizId)
        }
    }

    override fun saveAnswer(quizId: String, answer: QuizAnswer): QuizAttempt {
        val session = sessions[quizId] ?: return QuizAttempt(quizId = quizId)
        if (session.completed) {
            return getAttempt(quizId)
        }
        session.answers[answer.questionId] = answer
        if (session.engine == Engine.Manual) {
            val attemptId = session.attemptId
            val question = session.quiz.questions.firstOrNull { it.id == answer.questionId }
            val backendType = session.questionBackendTypes[answer.questionId]
            val questionNumericId = answer.questionId.toIntOrNull()
            if (attemptId != null && question != null && questionNumericId != null) {
                val packed = packAnswerForApi(question.type, answer.response, backendType)
                ioScope.launch {
                    authorizedRequest {
                        api.saveAnswers(
                            it,
                            attemptId,
                            SaveAnswersRequestDto(
                                answers = listOf(
                                    SaveAnswerItemDto(
                                        questionId = questionNumericId,
                                        answer = packed,
                                    ),
                                ),
                            ),
                        )
                    }
                }
            }
        }
        return getAttempt(quizId)
    }

    override fun goToQuestion(quizId: String, index: Int): QuizAttempt {
        val session = sessions[quizId] ?: return QuizAttempt(quizId = quizId)
        session.currentIndex = index.coerceIn(0, (session.quiz.questions.size - 1).coerceAtLeast(0))
        return getAttempt(quizId)
    }

    override fun resetAttempt(quizId: String): QuizAttempt {
        val session = sessions[quizId]
        if (session != null && session.engine == Engine.Manual && session.completed) {
            return getAttempt(quizId)
        }
        if (session != null) {
            session.answers.clear()
            session.currentIndex = 0
            session.completed = false
            results.remove(quizId)
        }
        return getAttempt(quizId)
    }

    override suspend fun submitQuiz(quizId: String): AppResult<QuizResult> {
        val session = mutex.withLock { sessions[quizId] }
            ?: return AppResult.Failure(AppError.NotFound)
        if (session.completed) {
            return results[quizId]?.let { AppResult.Success(it) }
                ?: AppResult.Failure(AppError.Domain("attempt_locked"))
        }
        return when (session.engine) {
            Engine.Manual -> submitManualQuiz(quizId, session)
            Engine.AiLesson -> submitAiLessonQuiz(quizId, session)
        }
    }

    private suspend fun submitManualQuiz(quizId: String, session: Session): AppResult<QuizResult> {
        val attemptId = session.attemptId
            ?: return AppResult.Failure(AppError.Domain("attempt_not_started"))

        if (session.answers.isNotEmpty()) {
            val items = session.answers.mapNotNull { (qid, answer) ->
                val question = session.quiz.questions.firstOrNull { it.id == qid } ?: return@mapNotNull null
                val questionId = qid.toIntOrNull() ?: return@mapNotNull null
                SaveAnswerItemDto(
                    questionId = questionId,
                    answer = packAnswerForApi(
                        question.type,
                        answer.response,
                        session.questionBackendTypes[qid],
                    ),
                )
            }
            if (items.isNotEmpty()) {
                when (
                    val flush = authorizedRequest {
                        api.saveAnswers(it, attemptId, SaveAnswersRequestDto(answers = items))
                    }
                ) {
                    is ApiCallResult.Success -> Unit
                    else -> return AppResult.Failure(handleFailure(flush))
                }
            }
        }

        return when (val submitted = authorizedRequest { api.submitAttempt(it, attemptId) }) {
            is ApiCallResult.Success -> {
                val result = submitted.value.toQuizResult(session.quiz)
                mutex.withLock {
                    session.completed = true
                    results[quizId] = result
                }
                AppResult.Success(result)
            }
            else -> AppResult.Failure(handleFailure(submitted))
        }
    }

    private suspend fun submitAiLessonQuiz(quizId: String, session: Session): AppResult<QuizResult> {
        if (session.quiz.isRemedial) {
            val result = clientScoreAiQuiz(session.quiz, session.answers.toMap())
            mutex.withLock {
                session.completed = true
                results[quizId] = result
            }
            return AppResult.Success(result)
        }
        val lessonId = session.lessonId
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_quiz_id"))
        val packed = session.answers.toLessonQuizAnswerIndices(session.quiz.questions)
        return when (
            val submitted = authorizedRequest {
                lessonQuizApi.submitQuiz(
                    it,
                    LessonQuizSubmitRequestDto(lessonId = lessonId, answers = packed),
                )
            }
        ) {
            is ApiCallResult.Success -> {
                val result = submitted.value.toQuizResult(session.quiz, session.answers.toMap())
                mutex.withLock {
                    session.quiz = result.quiz
                    session.completed = true
                    results[quizId] = result
                }
                AppResult.Success(result)
            }
            else -> AppResult.Failure(handleFailure(submitted))
        }
    }

    override suspend fun getResult(quizId: String): AppResult<QuizResult> {
        results[quizId]?.let { return AppResult.Success(it) }
        val session = sessions[quizId] ?: return AppResult.Failure(AppError.NotFound)
        if (session.engine == Engine.AiLesson) {
            return AppResult.Failure(AppError.NotFound)
        }
        val attemptId = session.attemptId ?: return AppResult.Failure(AppError.NotFound)
        return when (val attempt = authorizedRequest { api.getStudentAttempt(it, attemptId) }) {
            is ApiCallResult.Success -> {
                val result = attempt.value.toQuizResult(session.quiz)
                results[quizId] = result
                AppResult.Success(result)
            }
            else -> AppResult.Failure(handleFailure(attempt))
        }
    }

    override suspend fun buildRemedialQuiz(sourceQuizId: String): AppResult<Quiz> {
        val session = sessions[sourceQuizId]
        if (session?.engine == Engine.Manual ||
            sourceQuizId.startsWith("manual-") ||
            session?.quiz?.origin == QuizOrigin.TeacherManual
        ) {
            return AppResult.Failure(AppError.Domain("remedial_not_supported_for_manual"))
        }
        val lessonId = session?.lessonId
            ?: LessonQuizIds.parseLessonId(sourceQuizId)
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_quiz_id"))
        val sourceQuiz = session?.quiz ?: return AppResult.Failure(AppError.NotFound)
        val answers = session.answers.toLessonQuizAnswerIndices(sourceQuiz.questions)
        if (answers.isEmpty()) {
            return AppResult.Failure(AppError.Domain("no_wrong_answers"))
        }
        return when (
            val remedial = authorizedRequest {
                lessonQuizApi.remedialQuiz(
                    it,
                    lessonId,
                    LessonQuizRemedialRequestDto(answers = answers),
                )
            }
        ) {
            is ApiCallResult.Success -> {
                if (remedial.value.questions.isEmpty()) {
                    return AppResult.Failure(AppError.Domain("no_wrong_answers"))
                }
                val remedialId = LessonQuizIds.remedialQuizId(lessonId)
                val quiz = remedial.value.questions.toRemedialDomainQuiz(
                    clientQuizId = remedialId,
                    lessonId = lessonId,
                    lessonTitle = sourceQuiz.lessonTitle,
                    teacherName = sourceQuiz.teacherName,
                )
                mutex.withLock {
                    sessions[remedialId] = Session(
                        engine = Engine.AiLesson,
                        quiz = quiz,
                        numericQuizId = null,
                        courseId = null,
                        lessonId = lessonId,
                        attemptId = null,
                        answers = mutableMapOf(),
                        currentIndex = 0,
                        timeRemainingSeconds = null,
                        questionBackendTypes = emptyMap(),
                        completed = false,
                    )
                    results.remove(remedialId)
                }
                AppResult.Success(quiz)
            }
            is ApiCallResult.HttpFailure -> when (remedial.statusCode) {
                400 -> AppResult.Failure(AppError.Domain(remedial.detail ?: "no_wrong_answers"))
                else -> AppResult.Failure(handleFailure(remedial))
            }
            else -> AppResult.Failure(handleFailure(remedial))
        }
    }

    override suspend fun regenerateQuiz(quizId: String): AppResult<Quiz> {
        if (!LessonQuizIds.isAiLessonClientId(quizId) || LessonQuizIds.isRemedialClientId(quizId)) {
            return AppResult.Failure(AppError.Domain("regenerate_not_supported_for_manual"))
        }
        val lessonId = LessonQuizIds.parseLessonId(quizId)
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_quiz_id"))
        return when (val regenerated = authorizedRequest { lessonQuizApi.regenerateQuiz(it, lessonId) }) {
            is ApiCallResult.Success -> {
                if (regenerated.value.quizQuestions.isEmpty()) {
                    return getAiLessonQuiz(LessonQuizIds.lessonQuizId(lessonId))
                }
                // Prefer authoritative GET (no key leakage) after regenerate succeeds.
                getAiLessonQuiz(LessonQuizIds.lessonQuizId(lessonId))
            }
            else -> AppResult.Failure(handleFailure(regenerated))
        }
    }

    override suspend fun listCourseQuizzes(courseId: String): AppResult<List<StudentCourseQuizSummary>> {
        val numericCourseId = courseId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return when (val listed = authorizedRequest { api.listStudentQuizzes(it, numericCourseId) }) {
            is ApiCallResult.Success -> AppResult.Success(
                listed.value.map { it.toStudentCourseQuizSummary() },
            )
            else -> AppResult.Failure(handleFailure(listed))
        }
    }

    /**
     * @return numeric quiz id and optional course id hint.
     * Prefer numeric quiz ids from [listCourseQuizzes]. Legacy `manual-{courseId}` resolves
     * only when the course has exactly one published quiz (avoids silently opening the first).
     */
    private suspend fun resolveNumericQuizId(quizId: String): Pair<Int, Int?>? {
        if (quizId.startsWith("manual-")) {
            val courseId = quizId.removePrefix("manual-").toIntOrNull()?.takeIf { it > 0 }
                ?: return null
            return when (val listed = authorizedRequest { api.listStudentQuizzes(it, courseId) }) {
                is ApiCallResult.Success -> {
                    val only = listed.value.singleOrNull() ?: return null
                    only.id to courseId
                }
                else -> null
            }
        }
        val numeric = quizId.toIntOrNull()?.takeIf { it > 0 } ?: return null
        return numeric to null
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
                else -> AppError.Domain(response.detail ?: "quiz_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}
