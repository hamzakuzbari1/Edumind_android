package com.rork.eduspark.data.remote.teacher

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
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

internal interface TeacherParentNotesApi {
    suspend fun list(accessToken: String, studentId: Int, limit: Int = 50): ApiCallResult<ParentNoteListDto>
    suspend fun create(
        accessToken: String,
        studentId: Int,
        body: ParentNoteCreateDto,
    ): ApiCallResult<ParentNoteDto>
    suspend fun reply(
        accessToken: String,
        studentId: Int,
        noteId: Int,
        body: ParentNoteReplyCreateDto,
    ): ApiCallResult<ParentNoteDto>
    suspend fun close(accessToken: String, studentId: Int, noteId: Int): ApiCallResult<ParentNoteDto>
}

internal class KtorTeacherParentNotesApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : TeacherParentNotesApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun list(accessToken: String, studentId: Int, limit: Int): ApiCallResult<ParentNoteListDto> =
        execute {
            client.get(url("/api/teacher/students/$studentId/parent-notes")) {
                bearerAuth(accessToken)
                parameter("limit", limit)
            }
        }

    override suspend fun create(
        accessToken: String,
        studentId: Int,
        body: ParentNoteCreateDto,
    ): ApiCallResult<ParentNoteDto> = execute {
        client.post(url("/api/teacher/students/$studentId/parent-notes")) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun reply(
        accessToken: String,
        studentId: Int,
        noteId: Int,
        body: ParentNoteReplyCreateDto,
    ): ApiCallResult<ParentNoteDto> = execute {
        client.post(url("/api/teacher/students/$studentId/parent-notes/$noteId/reply")) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun close(
        accessToken: String,
        studentId: Int,
        noteId: Int,
    ): ApiCallResult<ParentNoteDto> = execute {
        client.post(url("/api/teacher/students/$studentId/parent-notes/$noteId/close")) {
            bearerAuth(accessToken)
        }
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
