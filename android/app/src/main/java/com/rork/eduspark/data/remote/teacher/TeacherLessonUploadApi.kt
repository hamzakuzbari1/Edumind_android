package com.rork.eduspark.data.remote.teacher

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.formData
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders
import java.io.IOException
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

internal enum class TeacherLessonUploadAssetType { Video, Pdf, Homework, Audio }

internal data class TeacherLessonUploadFilePart(
    val assetType: TeacherLessonUploadAssetType,
    val bytes: ByteArray,
    val filename: String,
    val mimeType: String,
)

@Serializable
internal data class TeacherLessonUploadResponseDto(
    val id: Int,
    val title: String,
    val description: String? = null,
    @SerialName("video_url") val videoUrl: String? = null,
    @SerialName("pdf_url") val pdfUrl: String? = null,
    @SerialName("homework_url") val homeworkUrl: String? = null,
    @SerialName("audio_url") val audioUrl: String? = null,
)

internal interface TeacherLessonUploadApi {
    suspend fun createLessonWithFile(
        accessToken: String,
        courseId: Int,
        title: String,
        order: Int,
        file: TeacherLessonUploadFilePart,
    ): ApiCallResult<TeacherLessonUploadResponseDto>
}

internal class KtorTeacherLessonUploadApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : TeacherLessonUploadApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun createLessonWithFile(
        accessToken: String,
        courseId: Int,
        title: String,
        order: Int,
        file: TeacherLessonUploadFilePart,
    ): ApiCallResult<TeacherLessonUploadResponseDto> = execute {
        val path = when (file.assetType) {
            TeacherLessonUploadAssetType.Homework -> "/api/teacher/courses/$courseId/lessons/homework"
            else -> "/api/teacher/courses/$courseId/lessons"
        }
        val fieldName = when (file.assetType) {
            TeacherLessonUploadAssetType.Video -> "video"
            TeacherLessonUploadAssetType.Pdf -> "pdf"
            TeacherLessonUploadAssetType.Homework -> "file"
            TeacherLessonUploadAssetType.Audio -> "audio"
        }
        val fallbackContentType = when (file.assetType) {
            TeacherLessonUploadAssetType.Video -> ContentType.Video.MP4
            TeacherLessonUploadAssetType.Pdf, TeacherLessonUploadAssetType.Homework -> ContentType.Application.Pdf
            TeacherLessonUploadAssetType.Audio -> ContentType.Audio.MPEG
        }
        val contentType = runCatching { ContentType.parse(file.mimeType) }.getOrElse { fallbackContentType }
        val safeName = file.filename.ifBlank { fallbackFileName(file.assetType) }

        client.post(root + path) {
            bearerAuth(accessToken)
            setBody(
                MultiPartFormDataContent(
                    formData {
                        append("title", title)
                        append("description", "")
                        append("sort_order", order.toString())
                        append(
                            fieldName,
                            file.bytes,
                            Headers.build {
                                append(HttpHeaders.ContentType, contentType.toString())
                                append(HttpHeaders.ContentDisposition, "filename=\"$safeName\"")
                            },
                        )
                    },
                ),
            )
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

private fun fallbackFileName(type: TeacherLessonUploadAssetType): String = when (type) {
    TeacherLessonUploadAssetType.Video -> "lesson-video.mp4"
    TeacherLessonUploadAssetType.Pdf -> "lesson.pdf"
    TeacherLessonUploadAssetType.Homework -> "homework.pdf"
    TeacherLessonUploadAssetType.Audio -> "lesson-audio.mp3"
}
