package com.rork.eduspark.data.remote.profile

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.put
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

internal interface StudentProfileApi {
    suspend fun profile(accessToken: String): ApiCallResult<StudentProfileDto>
    suspend fun updateProfile(
        accessToken: String,
        body: StudentProfileUpdateDto,
    ): ApiCallResult<StudentProfileDto>
    suspend fun linkedParents(accessToken: String): ApiCallResult<LinkedParentsDto>
    suspend fun parentLinkCode(accessToken: String): ApiCallResult<ParentLinkCodeDto>
}

internal class KtorStudentProfileApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : StudentProfileApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun profile(accessToken: String) =
        authenticatedGet<StudentProfileDto>("/api/student/profile", accessToken)

    override suspend fun updateProfile(
        accessToken: String,
        body: StudentProfileUpdateDto,
    ) = execute<StudentProfileDto> {
        client.put(url("/api/student/profile")) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    override suspend fun linkedParents(accessToken: String) =
        authenticatedGet<LinkedParentsDto>("/api/student/linked-parents", accessToken)

    override suspend fun parentLinkCode(accessToken: String) =
        authenticatedGet<ParentLinkCodeDto>("/api/parent/link-code", accessToken)

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
