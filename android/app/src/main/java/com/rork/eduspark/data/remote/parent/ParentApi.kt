package com.rork.eduspark.data.remote.parent

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.timeout
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.client.statement.readRawBytes
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import java.io.IOException
import java.net.URLDecoder
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
    suspend fun lessonProgress(accessToken: String, studentId: Int): ApiCallResult<ParentLessonProgressDto>
    suspend fun lessonDetails(accessToken: String, studentId: Int, lessonId: String): ApiCallResult<ParentLessonDetailDto>
    suspend fun subjectsTeachers(accessToken: String, studentId: Int): ApiCallResult<ParentSubjectsTeachersDto>
    suspend fun plannerVisibility(accessToken: String, studentId: Int): ApiCallResult<ParentPlannerVisibilityDto>
    suspend fun plannerProgress(accessToken: String, studentId: Int): ApiCallResult<ParentPlannerVisibilityDto>
    suspend fun studentRoutine(accessToken: String, studentId: Int): ApiCallResult<ParentRoutineVisibilityDto>
    suspend fun attendance(accessToken: String, studentId: Int): ApiCallResult<ParentAttendanceSummaryDto>
    suspend fun activityTrackingSummary(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentActivityTrackingSummaryDto>
    suspend fun activityTrackingAnalytics(
        accessToken: String,
        studentId: Int,
        weekOffset: Int = 0,
        monthOffset: Int = 0,
        sessionLimit: Int = 30,
    ): ApiCallResult<ParentAttendanceAnalyticsDto>
    suspend fun activityTrackingSessions(
        accessToken: String,
        studentId: Int,
        limit: Int = 30,
    ): ApiCallResult<List<ParentActivitySessionDto>>
    suspend fun insights(accessToken: String, studentId: Int): ApiCallResult<List<ParentInsightDto>>
    suspend fun academicIntelligence(accessToken: String, studentId: Int): ApiCallResult<ParentAcademicIntelligenceDto>
    suspend fun executiveSummary(accessToken: String, studentId: Int): ApiCallResult<ParentExecutiveSummaryDto>
    suspend fun quizTracking(accessToken: String, studentId: Int): ApiCallResult<ParentQuizTrackingDto>

    suspend fun historicalReport(
        accessToken: String,
        studentId: Int,
        period: String = "this_week",
        startDate: String? = null,
        endDate: String? = null,
    ): ApiCallResult<ParentHistoricalReportDto>

    suspend fun exportHistoricalReport(
        accessToken: String,
        studentId: Int,
        period: String = "this_week",
        startDate: String? = null,
        endDate: String? = null,
        format: String = "pdf",
    ): ApiCallResult<ParentReportExportDto>

    suspend fun notifications(accessToken: String, studentId: Int): ApiCallResult<ParentNotificationListDto>
    suspend fun markNotificationRead(
        accessToken: String,
        studentId: Int,
        notificationId: Int,
    ): ApiCallResult<ParentNotificationDto>

    suspend fun notificationSettings(accessToken: String, studentId: Int): ApiCallResult<ParentNotificationSettingsDto>
    suspend fun updateNotificationSettings(
        accessToken: String,
        studentId: Int,
        body: ParentNotificationSettingsUpdateDto,
    ): ApiCallResult<ParentNotificationSettingsDto>
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
        authenticatedGet<ParentLessonProgressDto>("/api/parent/lesson-progress", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun lessonDetails(accessToken: String, studentId: Int, lessonId: String) =
        authenticatedGet<ParentLessonDetailDto>("/api/parent/lesson-progress/$lessonId", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun subjectsTeachers(accessToken: String, studentId: Int) =
        authenticatedGet<ParentSubjectsTeachersDto>("/api/parent/subjects-teachers", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun plannerVisibility(accessToken: String, studentId: Int) =
        authenticatedGet<ParentPlannerVisibilityDto>("/api/parent/planner-visibility", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun plannerProgress(accessToken: String, studentId: Int) =
        authenticatedGet<ParentPlannerVisibilityDto>("/api/parent/planner-progress", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun studentRoutine(accessToken: String, studentId: Int) =
        authenticatedGet<ParentRoutineVisibilityDto>("/api/parent/student-routine", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun attendance(accessToken: String, studentId: Int) =
        authenticatedGet<ParentAttendanceSummaryDto>("/api/parent/attendance", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun activityTrackingSummary(accessToken: String, studentId: Int) =
        authenticatedGet<ParentActivityTrackingSummaryDto>("/api/parent/activity-tracking/summary", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun activityTrackingAnalytics(
        accessToken: String,
        studentId: Int,
        weekOffset: Int,
        monthOffset: Int,
        sessionLimit: Int,
    ) = authenticatedGet<ParentAttendanceAnalyticsDto>("/api/parent/activity-tracking/analytics", accessToken) {
        parameter("student_id", studentId)
        parameter("week_offset", weekOffset)
        parameter("month_offset", monthOffset)
        parameter("session_limit", sessionLimit)
    }

    override suspend fun activityTrackingSessions(
        accessToken: String,
        studentId: Int,
        limit: Int,
    ) = authenticatedGet<List<ParentActivitySessionDto>>("/api/parent/activity-tracking/sessions", accessToken) {
        parameter("student_id", studentId)
        parameter("limit", limit)
    }

    override suspend fun insights(accessToken: String, studentId: Int) =
        authenticatedGet<List<ParentInsightDto>>("/api/parent/insights", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun academicIntelligence(accessToken: String, studentId: Int) =
        authenticatedGet<ParentAcademicIntelligenceDto>("/api/parent/academic-intelligence", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun executiveSummary(accessToken: String, studentId: Int) =
        authenticatedGet<ParentExecutiveSummaryDto>("/api/parent/executive-summary", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun quizTracking(accessToken: String, studentId: Int) =
        authenticatedGet<ParentQuizTrackingDto>("/api/parent/quiz", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun historicalReport(
        accessToken: String,
        studentId: Int,
        period: String,
        startDate: String?,
        endDate: String?,
    ) = authenticatedGet<ParentHistoricalReportDto>("/api/parent/historical-report", accessToken) {
        parameter("student_id", studentId)
        parameter("period", period)
        startDate?.let { parameter("start_date", it) }
        endDate?.let { parameter("end_date", it) }
    }

    override suspend fun exportHistoricalReport(
        accessToken: String,
        studentId: Int,
        period: String,
        startDate: String?,
        endDate: String?,
        format: String,
    ): ApiCallResult<ParentReportExportDto> = executeBinary(
        fallbackFilename = "eduspark-report.$format",
        fallbackMime = mimeForExportFormat(format),
    ) {
        client.get("$root/api/parent/historical-report/export") {
            bearerAuth(accessToken)
            timeout {
                requestTimeoutMillis = EXPORT_TIMEOUT_MS
                socketTimeoutMillis = EXPORT_TIMEOUT_MS
            }
            parameter("student_id", studentId)
            parameter("period", period)
            parameter("format", format)
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }
    }

    override suspend fun notifications(accessToken: String, studentId: Int) =
        authenticatedGet<ParentNotificationListDto>("/api/parent/notifications", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun markNotificationRead(
        accessToken: String,
        studentId: Int,
        notificationId: Int,
    ) = authenticatedPost<ParentNotificationDto>(
        path = "/api/parent/notifications/$notificationId/read",
        accessToken = accessToken,
    ) {
        parameter("student_id", studentId)
    }

    override suspend fun notificationSettings(accessToken: String, studentId: Int) =
        authenticatedGet<ParentNotificationSettingsDto>("/api/parent/notification-settings", accessToken) {
            parameter("student_id", studentId)
        }

    override suspend fun updateNotificationSettings(
        accessToken: String,
        studentId: Int,
        body: ParentNotificationSettingsUpdateDto,
    ) = authenticatedPut<ParentNotificationSettingsDto>(
        path = "/api/parent/notification-settings",
        accessToken = accessToken,
        body = body,
    ) {
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
        crossinline configure: io.ktor.client.request.HttpRequestBuilder.() -> Unit = {},
    ): ApiCallResult<T> = execute {
        client.post(root + path) {
            bearerAuth(accessToken)
            if (body != null) {
                contentType(ContentType.Application.Json)
                setBody(body)
            }
            configure()
        }
    }

    private suspend inline fun <reified T> authenticatedPut(
        path: String,
        accessToken: String,
        body: Any,
        crossinline configure: io.ktor.client.request.HttpRequestBuilder.() -> Unit = {},
    ): ApiCallResult<T> = execute {
        client.put(root + path) {
            bearerAuth(accessToken)
            contentType(ContentType.Application.Json)
            setBody(body)
            configure()
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

    private suspend fun executeBinary(
        fallbackFilename: String,
        fallbackMime: String,
        request: suspend () -> HttpResponse,
    ): ApiCallResult<ParentReportExportDto> = try {
        val response = request()
        if (response.status.value in 200..299) {
            ApiCallResult.Success(
                ParentReportExportDto(
                    bytes = response.readRawBytes(),
                    filename = parseAttachmentFilename(response.headers[HttpHeaders.ContentDisposition])
                        ?: fallbackFilename,
                    mimeType = response.headers[HttpHeaders.ContentType]
                        ?.substringBefore(';')
                        ?.trim()
                        ?.ifBlank { null }
                        ?: fallbackMime,
                ),
            )
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

    private companion object {
        const val EXPORT_TIMEOUT_MS = 120_000L
    }
}

internal fun parseAttachmentFilename(header: String?): String? {
    if (header.isNullOrBlank()) return null
    val encoded = Regex("filename\\*=(?:UTF-8''|utf-8'')([^;]+)", RegexOption.IGNORE_CASE)
        .find(header)
        ?.groupValues
        ?.get(1)
        ?.trim()
    if (!encoded.isNullOrBlank()) {
        return runCatching { URLDecoder.decode(encoded, Charsets.UTF_8.name()) }
            .getOrNull()
            ?.sanitizeExportFilename()
    }
    val quoted = Regex("filename=\"([^\"]+)\"").find(header)?.groupValues?.get(1)
    val plain = Regex("filename=([^;]+)").find(header)?.groupValues?.get(1)?.trim()?.trim('"')
    return (quoted ?: plain)?.sanitizeExportFilename()
}

private fun String.sanitizeExportFilename(): String? =
    substringAfterLast('/')
        .substringAfterLast('\\')
        .trim()
        .takeIf { it.isNotBlank() }

private fun mimeForExportFormat(format: String): String = when (format) {
    "csv" -> "text/csv"
    "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else -> "application/pdf"
}
