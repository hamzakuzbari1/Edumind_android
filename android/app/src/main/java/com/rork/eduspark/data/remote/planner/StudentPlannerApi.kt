package com.rork.eduspark.data.remote.planner

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

internal interface StudentPlannerApi {
    suspend fun planner(accessToken: String): ApiCallResult<PlannerStateDto>
    suspend fun summary(accessToken: String): ApiCallResult<PlannerStateDto>
    suspend fun generate(accessToken: String): ApiCallResult<PlannerStateDto>
    suspend fun optimize(accessToken: String): ApiCallResult<PlannerStateDto>
    suspend fun chat(
        accessToken: String,
        body: PlannerChatRequestDto,
    ): ApiCallResult<PlannerChatResponseDto>
    suspend fun completeSession(
        accessToken: String,
        body: PlannerCompleteSessionRequestDto,
    ): ApiCallResult<PlannerStateDto>
}

internal class KtorStudentPlannerApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : StudentPlannerApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun planner(accessToken: String) =
        authenticatedGet<PlannerStateDto>("/api/student/planner", accessToken)

    override suspend fun summary(accessToken: String) =
        authenticatedGet<PlannerStateDto>("/api/student/planner/summary", accessToken)

    override suspend fun generate(accessToken: String) =
        authenticatedPostWithoutBody<PlannerStateDto>("/api/student/planner/generate", accessToken)

    override suspend fun optimize(accessToken: String) =
        authenticatedPostWithoutBody<PlannerStateDto>("/api/student/planner/optimize", accessToken)

    override suspend fun chat(
        accessToken: String,
        body: PlannerChatRequestDto,
    ) = authenticatedPost<PlannerChatResponseDto, PlannerChatRequestDto>(
        "/api/student/planner/chat",
        accessToken,
        body,
    )

    override suspend fun completeSession(
        accessToken: String,
        body: PlannerCompleteSessionRequestDto,
    ) = authenticatedPost<PlannerStateDto, PlannerCompleteSessionRequestDto>(
        "/api/student/planner/sessions/complete",
        accessToken,
        body,
    )

    private suspend inline fun <reified T> authenticatedGet(
        path: String,
        accessToken: String,
    ): ApiCallResult<T> = execute {
        client.get(url(path)) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T> authenticatedPostWithoutBody(
        path: String,
        accessToken: String,
    ): ApiCallResult<T> = execute {
        client.post(url(path)) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T, reified B> authenticatedPost(
        path: String,
        accessToken: String,
        body: B,
    ): ApiCallResult<T> = execute {
        client.post(url(path)) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    private fun url(path: String): String = root + path

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
