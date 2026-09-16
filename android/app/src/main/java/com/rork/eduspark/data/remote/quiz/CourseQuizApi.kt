package com.rork.eduspark.data.remote.quiz

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import java.io.IOException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

internal interface CourseQuizApi {
    // —— Student ——
    suspend fun listStudentQuizzes(accessToken: String, courseId: Int): ApiCallResult<List<StudentQuizListItemDto>>
    suspend fun getStudentTake(accessToken: String, quizId: Int): ApiCallResult<StudentQuizTakeOutDto>
    suspend fun startAttempt(accessToken: String, quizId: Int): ApiCallResult<StudentQuizTakeOutDto>
    suspend fun saveAnswers(
        accessToken: String,
        attemptId: Int,
        body: SaveAnswersRequestDto,
    ): ApiCallResult<Unit>
    suspend fun submitAttempt(accessToken: String, attemptId: Int): ApiCallResult<QuizAttemptOutDto>
    suspend fun getStudentAttempt(accessToken: String, attemptId: Int): ApiCallResult<QuizAttemptOutDto>

    // —— Teacher ——
    suspend fun listTeacherQuizzes(accessToken: String, courseId: Int): ApiCallResult<List<CourseQuizOutDto>>
    suspend fun createQuiz(
        accessToken: String,
        courseId: Int,
        body: CourseQuizCreateDto,
    ): ApiCallResult<CourseQuizOutDto>
    suspend fun getQuizDetail(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<CourseQuizDetailOutDto>
    suspend fun updateQuiz(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: CourseQuizUpdateDto,
    ): ApiCallResult<CourseQuizOutDto>
    suspend fun deleteQuiz(accessToken: String, courseId: Int, quizId: Int): ApiCallResult<Unit>
    suspend fun addQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: QuizQuestionCreateDto,
    ): ApiCallResult<QuizQuestionOutDto>
    suspend fun updateQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
        body: QuizQuestionUpdateDto,
    ): ApiCallResult<QuizQuestionOutDto>
    suspend fun deleteQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
    ): ApiCallResult<Unit>
    suspend fun getResults(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<QuizResultsOutDto>
    suspend fun getTeacherAttempt(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
    ): ApiCallResult<QuizAttemptOutDto>
    suspend fun gradeEssay(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
        questionId: Int,
        body: GradeEssayRequestDto,
    ): ApiCallResult<QuizAttemptOutDto>
    suspend fun getQuizAnalytics(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ): ApiCallResult<QuizAnalyticsOutDto>
    suspend fun getCourseQuizAnalytics(
        accessToken: String,
        courseId: Int,
    ): ApiCallResult<CourseQuizAnalyticsOutDto>
}

internal class KtorCourseQuizApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : CourseQuizApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun listStudentQuizzes(accessToken: String, courseId: Int) =
        authenticatedGet<List<StudentQuizListItemDto>>(
            "/api/student/courses/$courseId/manual-quizzes",
            accessToken,
        )

    override suspend fun getStudentTake(accessToken: String, quizId: Int) =
        authenticatedGet<StudentQuizTakeOutDto>("/api/student/manual-quizzes/$quizId", accessToken)

    override suspend fun startAttempt(accessToken: String, quizId: Int) =
        authenticatedPost<StudentQuizTakeOutDto>("/api/student/manual-quizzes/$quizId/start", accessToken)

    override suspend fun saveAnswers(
        accessToken: String,
        attemptId: Int,
        body: SaveAnswersRequestDto,
    ): ApiCallResult<Unit> = authenticatedPatchUnit(
        "/api/student/manual-quiz-attempts/$attemptId/answers",
        accessToken,
        body,
    )

    override suspend fun submitAttempt(accessToken: String, attemptId: Int) =
        authenticatedPost<QuizAttemptOutDto>(
            "/api/student/manual-quiz-attempts/$attemptId/submit",
            accessToken,
        )

    override suspend fun getStudentAttempt(accessToken: String, attemptId: Int) =
        authenticatedGet<QuizAttemptOutDto>("/api/student/manual-quiz-attempts/$attemptId", accessToken)

    override suspend fun listTeacherQuizzes(accessToken: String, courseId: Int) =
        authenticatedGet<List<CourseQuizOutDto>>(
            "/api/teacher/courses/$courseId/manual-quizzes",
            accessToken,
        )

    override suspend fun createQuiz(
        accessToken: String,
        courseId: Int,
        body: CourseQuizCreateDto,
    ) = authenticatedPost<CourseQuizOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes",
        accessToken,
        body,
    )

    override suspend fun getQuizDetail(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ) = authenticatedGet<CourseQuizDetailOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId",
        accessToken,
    )

    override suspend fun updateQuiz(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: CourseQuizUpdateDto,
    ) = authenticatedPut<CourseQuizOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId",
        accessToken,
        body,
    )

    override suspend fun deleteQuiz(accessToken: String, courseId: Int, quizId: Int) =
        authenticatedDeleteUnit("/api/teacher/courses/$courseId/manual-quizzes/$quizId", accessToken)

    override suspend fun addQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        body: QuizQuestionCreateDto,
    ) = authenticatedPost<QuizQuestionOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/questions",
        accessToken,
        body,
    )

    override suspend fun updateQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
        body: QuizQuestionUpdateDto,
    ) = authenticatedPut<QuizQuestionOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/questions/$questionId",
        accessToken,
        body,
    )

    override suspend fun deleteQuestion(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        questionId: Int,
    ) = authenticatedDeleteUnit(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/questions/$questionId",
        accessToken,
    )

    override suspend fun getResults(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ) = authenticatedGet<QuizResultsOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/results",
        accessToken,
    )

    override suspend fun getTeacherAttempt(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
    ) = authenticatedGet<QuizAttemptOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/attempts/$attemptId",
        accessToken,
    )

    override suspend fun gradeEssay(
        accessToken: String,
        courseId: Int,
        quizId: Int,
        attemptId: Int,
        questionId: Int,
        body: GradeEssayRequestDto,
    ) = authenticatedPost<QuizAttemptOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/attempts/$attemptId/questions/$questionId/grade",
        accessToken,
        body,
    )

    override suspend fun getQuizAnalytics(
        accessToken: String,
        courseId: Int,
        quizId: Int,
    ) = authenticatedGet<QuizAnalyticsOutDto>(
        "/api/teacher/courses/$courseId/manual-quizzes/$quizId/analytics",
        accessToken,
    )

    override suspend fun getCourseQuizAnalytics(
        accessToken: String,
        courseId: Int,
    ) = authenticatedGet<CourseQuizAnalyticsOutDto>(
        "/api/teacher/courses/$courseId/manual-quiz-analytics",
        accessToken,
    )

    private suspend inline fun <reified T> authenticatedGet(
        path: String,
        accessToken: String,
    ): ApiCallResult<T> = execute {
        client.get(root + path) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T> authenticatedPost(
        path: String,
        accessToken: String,
        body: Any? = null,
    ): ApiCallResult<T> = execute {
        client.post(root + path) {
            bearerAuth(accessToken)
            if (body != null) {
                contentType(ContentType.Application.Json)
                setBody(body)
            }
        }
    }

    private suspend inline fun <reified T> authenticatedPut(
        path: String,
        accessToken: String,
        body: Any,
    ): ApiCallResult<T> = execute {
        client.put(root + path) {
            bearerAuth(accessToken)
            contentType(ContentType.Application.Json)
            setBody(body)
        }
    }

    private suspend fun authenticatedPatchUnit(
        path: String,
        accessToken: String,
        body: Any,
    ): ApiCallResult<Unit> = executeUnit {
        client.patch(root + path) {
            bearerAuth(accessToken)
            contentType(ContentType.Application.Json)
            setBody(body)
        }
    }

    private suspend fun authenticatedDeleteUnit(
        path: String,
        accessToken: String,
    ): ApiCallResult<Unit> = executeUnit {
        client.delete(root + path) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T> execute(
        request: suspend () -> HttpResponse,
    ): ApiCallResult<T> = try {
        val response = request()
        if (response.status.value in 200..299) {
            ApiCallResult.Success(response.body())
        } else {
            parseFailure(response.status.value, response.bodyAsText())
        }
    } catch (_: IOException) {
        ApiCallResult.NetworkFailure
    } catch (_: SerializationException) {
        ApiCallResult.InvalidResponse
    } catch (_: IllegalStateException) {
        ApiCallResult.InvalidResponse
    }

    private suspend fun executeUnit(
        request: suspend () -> HttpResponse,
    ): ApiCallResult<Unit> = try {
        val response = request()
        if (response.status.value in 200..299) {
            ApiCallResult.Success(Unit)
        } else {
            parseFailure(response.status.value, response.bodyAsText())
        }
    } catch (_: IOException) {
        ApiCallResult.NetworkFailure
    } catch (_: IllegalStateException) {
        ApiCallResult.InvalidResponse
    }

    private fun parseFailure(statusCode: Int, body: String): ApiCallResult.HttpFailure {
        val rootObject = runCatching { json.parseToJsonElement(body).jsonObject }.getOrNull()
            ?: return ApiCallResult.HttpFailure(statusCode)
        val detail = rootObject["detail"] ?: return ApiCallResult.HttpFailure(statusCode)
        runCatching { detail.jsonPrimitive.contentOrNull }.getOrNull()?.let {
            return ApiCallResult.HttpFailure(statusCode = statusCode, detail = it)
        }
        val fieldErrors = runCatching {
            detail.jsonArray.mapNotNull { item ->
                val itemObject = item.jsonObject
                val field = itemObject["loc"]?.jsonArray?.lastOrNull()?.jsonPrimitive?.contentOrNull
                val message = itemObject["msg"]?.jsonPrimitive?.contentOrNull
                if (field != null && message != null) field to message else null
            }.toMap()
        }.getOrDefault(emptyMap())
        return ApiCallResult.HttpFailure(statusCode, fieldErrors = fieldErrors)
    }
}
