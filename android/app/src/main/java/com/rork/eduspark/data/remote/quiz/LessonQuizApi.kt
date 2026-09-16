package com.rork.eduspark.data.remote.quiz

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.post
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

internal interface LessonQuizApi {
    suspend fun getQuiz(accessToken: String, lessonId: Int): ApiCallResult<List<LessonQuizQuestionDto>>
    suspend fun submitQuiz(
        accessToken: String,
        body: LessonQuizSubmitRequestDto,
    ): ApiCallResult<LessonQuizSubmitResponseDto>
    suspend fun regenerateQuiz(
        accessToken: String,
        lessonId: Int,
    ): ApiCallResult<LessonQuizRegenerateResponseDto>
    suspend fun remedialQuiz(
        accessToken: String,
        lessonId: Int,
        body: LessonQuizRemedialRequestDto,
    ): ApiCallResult<LessonQuizRemedialResponseDto>
}

internal class KtorLessonQuizApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : LessonQuizApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun getQuiz(accessToken: String, lessonId: Int) =
        authenticatedGet<List<LessonQuizQuestionDto>>("/api/student/quiz/$lessonId", accessToken)

    override suspend fun submitQuiz(accessToken: String, body: LessonQuizSubmitRequestDto) =
        authenticatedPost<LessonQuizSubmitResponseDto>("/api/student/quiz/submit", accessToken, body)

    override suspend fun regenerateQuiz(accessToken: String, lessonId: Int) =
        authenticatedPost<LessonQuizRegenerateResponseDto>(
            "/api/student/lesson/$lessonId/quiz/regenerate",
            accessToken,
        )

    override suspend fun remedialQuiz(
        accessToken: String,
        lessonId: Int,
        body: LessonQuizRemedialRequestDto,
    ) = authenticatedPost<LessonQuizRemedialResponseDto>(
        "/api/student/lesson/$lessonId/quiz/remedial",
        accessToken,
        body,
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
