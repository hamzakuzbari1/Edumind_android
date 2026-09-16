package com.rork.eduspark.data.remote.learning

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
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

internal interface StudentLearningApi {
    suspend fun dashboard(accessToken: String): ApiCallResult<StudentDashboardDto>
    suspend fun course(accessToken: String, courseId: Int): ApiCallResult<StudentCourseDetailDto>
    suspend fun units(accessToken: String, courseId: Int): ApiCallResult<List<StudentCourseUnitDto>>
    suspend fun resume(accessToken: String, courseId: Int): ApiCallResult<StudentCourseResumeLessonDto?>
    suspend fun lesson(accessToken: String, lessonId: Int): ApiCallResult<CourseLessonDto>
    suspend fun lessonProgress(accessToken: String, lessonId: Int): ApiCallResult<LessonProgressDto>
    suspend fun updateLessonProgress(
        accessToken: String,
        lessonId: Int,
        body: LessonProgressUpdateDto,
    ): ApiCallResult<LessonProgressDto>
    suspend fun verifyCompletion(accessToken: String, lessonId: Int): ApiCallResult<VerifyCompletionDto>
    suspend fun subscriptionsCatalog(accessToken: String): ApiCallResult<SubscriptionsCatalogDto>
    suspend fun subscribeCourse(
        accessToken: String,
        body: SubscribeCourseRequestDto,
    ): ApiCallResult<SubscribeCourseOutDto>
}

internal class KtorStudentLearningApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : StudentLearningApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun dashboard(accessToken: String) =
        authenticatedGet<StudentDashboardDto>("/api/student/dashboard", accessToken)

    override suspend fun course(accessToken: String, courseId: Int) =
        authenticatedGet<StudentCourseDetailDto>("/api/student/courses/$courseId", accessToken)

    override suspend fun units(accessToken: String, courseId: Int) =
        authenticatedGet<List<StudentCourseUnitDto>>("/api/student/courses/$courseId/units", accessToken)

    override suspend fun resume(accessToken: String, courseId: Int) =
        authenticatedGet<StudentCourseResumeLessonDto?>("/api/student/courses/$courseId/resume", accessToken)

    override suspend fun lesson(accessToken: String, lessonId: Int) =
        authenticatedGet<CourseLessonDto>("/api/student/lessons/$lessonId", accessToken)

    override suspend fun lessonProgress(accessToken: String, lessonId: Int) =
        authenticatedGet<LessonProgressDto>("/api/student/lessons/$lessonId/progress", accessToken)

    override suspend fun updateLessonProgress(
        accessToken: String,
        lessonId: Int,
        body: LessonProgressUpdateDto,
    ) = execute<LessonProgressDto> {
        client.post(url("/api/student/lessons/$lessonId/progress")) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun verifyCompletion(accessToken: String, lessonId: Int) =
        execute<VerifyCompletionDto> {
            client.post(url("/api/student/lessons/$lessonId/verify-completion")) {
                bearerAuth(accessToken)
            }
        }

    override suspend fun subscriptionsCatalog(accessToken: String) =
        authenticatedGet<SubscriptionsCatalogDto>("/api/student/subscriptions", accessToken)

    override suspend fun subscribeCourse(
        accessToken: String,
        body: SubscribeCourseRequestDto,
    ) = execute<SubscribeCourseOutDto> {
        client.post(url("/api/student/subscriptions/subscribe")) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    private suspend inline fun <reified T> authenticatedGet(
        path: String,
        accessToken: String,
    ): ApiCallResult<T> = execute {
        client.get(url(path)) { bearerAuth(accessToken) }
    }

    private fun url(path: String): String = root + path

    private suspend inline fun <reified T> execute(
        request: suspend () -> io.ktor.client.statement.HttpResponse,
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

@kotlinx.serialization.Serializable
internal data class VerifyCompletionDto(
    val success: Boolean = false,
    val message: String = "",
    val progress: LessonProgressDto? = null,
)
