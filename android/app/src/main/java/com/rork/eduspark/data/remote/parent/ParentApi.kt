package com.rork.eduspark.data.remote.parent

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import java.io.IOException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

internal interface ParentApi {
    suspend fun students(accessToken: String): ApiCallResult<List<ParentLinkedStudentDto>>
    suspend fun dashboard(accessToken: String, studentId: Int): ApiCallResult<ParentDashboardDto>
    suspend fun courseProgress(accessToken: String, studentId: Int): ApiCallResult<List<ParentCourseProgressDto>>
    suspend fun activity(
        accessToken: String,
        studentId: Int,
        limit: Int = 30,
    ): ApiCallResult<List<ParentActivityDto>>

    suspend fun notes(
        accessToken: String,
        studentId: Int,
        limit: Int = 30,
        sort: String = "newest",
    ): ApiCallResult<ParentNotesListDto>

    suspend fun markNoteRead(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto>
    suspend fun acknowledgeNote(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto>
    suspend fun replyToNote(
        accessToken: String,
        noteId: Int,
        body: ParentViewerNoteReplyCreateDto,
    ): ApiCallResult<ParentViewerNoteDto>

    suspend fun linkStudent(accessToken: String, body: ParentLinkStudentRequestDto): ApiCallResult<ParentLinkStudentResponseDto>
    suspend fun lessonProgress(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun lessonDetails(accessToken: String, studentId: Int, lessonId: String): ApiCallResult<JsonElement>
    suspend fun subjectsTeachers(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun plannerVisibility(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun plannerProgress(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun studentRoutine(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun attendance(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun activityTrackingSummary(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun insights(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun academicIntelligence(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun executiveSummary(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun historicalReport(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun notifications(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
    suspend fun notificationSettings(accessToken: String, studentId: Int): ApiCallResult<JsonElement>
}

internal class KtorParentApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : ParentApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun students(accessToken: String) =
        authenticatedGet<List<ParentLinkedStudentDto>>("/api/parent/students", accessToken)

    override suspend fun dashboard(accessToken: String, studentId: Int) =
        authenticatedGet<ParentDashboardDto>("/api/parent/dashboard", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun courseProgress(accessToken: String, studentId: Int) =
        authenticatedGet<List<ParentCourseProgressDto>>("/api/parent/course-progress", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun activity(accessToken: String, studentId: Int, limit: Int) =
        authenticatedGet<List<ParentActivityDto>>("/api/parent/activity", accessToken) {
            parameter("student_id", studentId)
            parameter("limit", limit)
        }

    override suspend fun notes(
        accessToken: String,
        studentId: Int,
        limit: Int,
        sort: String,
    ): ApiCallResult<ParentNotesListDto> =
        authenticatedGet("/api/parent/notes", accessToken) {
            parameter("student_id", studentId)
            parameter("limit", limit)
            parameter("sort", sort)
        }

    override suspend fun markNoteRead(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto> =
        authenticatedPost("/api/parent/notes/$noteId/read", accessToken)

    override suspend fun acknowledgeNote(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto> =
        authenticatedPost("/api/parent/notes/$noteId/acknowledge", accessToken)

    override suspend fun replyToNote(
        accessToken: String,
        noteId: Int,
        body: ParentViewerNoteReplyCreateDto,
    ): ApiCallResult<ParentViewerNoteDto> =
        authenticatedPost("/api/parent/notes/$noteId/reply", accessToken, body)

    override suspend fun linkStudent(accessToken: String, body: ParentLinkStudentRequestDto): ApiCallResult<ParentLinkStudentResponseDto> =
        authenticatedPost("/api/parent/link", accessToken, body)

    override suspend fun lessonProgress(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/lesson-progress", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun lessonDetails(accessToken: String, studentId: Int, lessonId: String) =
        authenticatedGet<JsonElement>("/api/parent/lesson-progress/$lessonId", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun subjectsTeachers(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/subjects-teachers", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun plannerVisibility(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/planner-visibility", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun plannerProgress(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/planner-progress", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun studentRoutine(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/student-routine", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun attendance(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/attendance", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun activityTrackingSummary(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/activity-tracking/summary", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun insights(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/insights", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun academicIntelligence(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/academic-intelligence", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun executiveSummary(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/executive-summary", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun historicalReport(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/historical-report", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun notifications(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/notifications", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun notificationSettings(accessToken: String, studentId: Int) =
        authenticatedGet<JsonElement>("/api/parent/notification-settings", accessToken) {
            parameter("student_id", studentId)
        }

    private suspend inline fun <reified T> authenticatedGet(
        path: String,
        accessToken: String,
        crossinline configure: io.ktor.client.request.HttpRequestBuilder.() -> Unit = {},
    ): ApiCallResult<T> = execute {
        client.get(root + path) {
            bearerAuth(accessToken)
            configure()
        }
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
