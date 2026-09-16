package com.rork.eduspark.data.remote.teacher

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import java.io.IOException
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Serializable
internal data class TeacherCourseDto(
    val id: Int,
    val title: String,
    val description: String? = null,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("subject_id") val subjectId: Int,
    val grade: Int,
    val price: Float = 0f,
    val currency: String = "SYP",
    @SerialName("thumbnail_url") val thumbnailUrl: String? = null,
    @SerialName("banner_url") val bannerUrl: String? = null,
    @SerialName("is_published") val isPublished: Boolean = true,
    @SerialName("lesson_count") val lessonCount: Int = 0,
)

@Serializable
internal data class TeacherCourseSubjectOptionDto(
    val id: Int,
    @SerialName("name_ar") val nameAr: String,
    val grade: Int,
)

@Serializable
internal data class TeacherCourseFormContextDto(
    val grades: List<Int> = emptyList(),
    val subjects: List<TeacherCourseSubjectOptionDto> = emptyList(),
)

@Serializable
internal data class TeacherCourseCreateRequestDto(
    val title: String,
    val description: String? = null,
    @SerialName("subject_id") val subjectId: Int,
    val grade: Int,
    val price: Float,
    val currency: String,
    @SerialName("is_published") val isPublished: Boolean,
)

@Serializable
internal data class TeacherCourseUpdateRequestDto(
    val title: String? = null,
    val description: String? = null,
    @SerialName("subject_id") val subjectId: Int? = null,
    val price: Float? = null,
    @SerialName("is_published") val isPublished: Boolean? = null,
)

@Serializable
internal data class TeacherCourseLessonDto(
    val id: Int,
    val title: String,
    val description: String? = null,
    @SerialName("video_url") val videoUrl: String? = null,
    @SerialName("pdf_url") val pdfUrl: String? = null,
    @SerialName("homework_url") val homeworkUrl: String? = null,
    @SerialName("audio_url") val audioUrl: String? = null,
    @SerialName("has_video") val hasVideo: Boolean = false,
    @SerialName("has_pdf") val hasPdf: Boolean = false,
    @SerialName("has_audio") val hasAudio: Boolean = false,
    @SerialName("sort_order") val sortOrder: Int = 0,
    val status: String,
    @SerialName("is_visible") val isVisible: Boolean = true,
)

@Serializable
internal data class TeacherLessonVisibilityUpdateDto(
    @SerialName("is_visible") val isVisible: Boolean,
)

internal interface TeacherCoursesApi {
    suspend fun listCourses(accessToken: String): ApiCallResult<List<TeacherCourseDto>>
    suspend fun getFormContext(accessToken: String, grade: Int): ApiCallResult<TeacherCourseFormContextDto>
    suspend fun createCourse(
        accessToken: String,
        body: TeacherCourseCreateRequestDto,
    ): ApiCallResult<TeacherCourseDto>
    suspend fun updateCourse(
        accessToken: String,
        courseId: Int,
        body: TeacherCourseUpdateRequestDto,
    ): ApiCallResult<TeacherCourseDto>
    suspend fun listLessons(accessToken: String, courseId: Int): ApiCallResult<List<TeacherCourseLessonDto>>
    suspend fun updateLessonVisibility(
        accessToken: String,
        courseId: Int,
        lessonId: Int,
        visible: Boolean,
    ): ApiCallResult<TeacherCourseLessonDto>
}

internal class KtorTeacherCoursesApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : TeacherCoursesApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun listCourses(accessToken: String): ApiCallResult<List<TeacherCourseDto>> = execute {
        client.get("$root/api/teacher/courses") { bearerAuth(accessToken) }
    }

    override suspend fun getFormContext(
        accessToken: String,
        grade: Int,
    ): ApiCallResult<TeacherCourseFormContextDto> = execute {
        client.get("$root/api/teacher/courses/form-context") {
            bearerAuth(accessToken)
            parameter("grade", grade)
        }
    }

    override suspend fun createCourse(
        accessToken: String,
        body: TeacherCourseCreateRequestDto,
    ): ApiCallResult<TeacherCourseDto> = execute {
        client.post("$root/api/teacher/courses") {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun updateCourse(
        accessToken: String,
        courseId: Int,
        body: TeacherCourseUpdateRequestDto,
    ): ApiCallResult<TeacherCourseDto> = execute {
        client.put("$root/api/teacher/courses/$courseId") {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun listLessons(
        accessToken: String,
        courseId: Int,
    ): ApiCallResult<List<TeacherCourseLessonDto>> = execute {
        client.get("$root/api/teacher/courses/$courseId/lessons") { bearerAuth(accessToken) }
    }

    override suspend fun updateLessonVisibility(
        accessToken: String,
        courseId: Int,
        lessonId: Int,
        visible: Boolean,
    ): ApiCallResult<TeacherCourseLessonDto> = execute {
        client.patch("$root/api/teacher/courses/$courseId/lessons/$lessonId") {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(TeacherLessonVisibilityUpdateDto(isVisible = visible))
        }
    }

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
