package com.rork.eduspark.data.remote.routine

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
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

internal interface StudentRoutineApi {
    suspend fun profile(accessToken: String): ApiCallResult<RoutineProfileDto>
    suspend fun saveOnboarding(accessToken: String, body: RoutineOnboardingRequestDto): ApiCallResult<RoutineOnboardingResponseDto>
    suspend fun updateProfile(accessToken: String, body: RoutineOnboardingRequestDto): ApiCallResult<RoutineOkResponseDto>
    suspend fun resetProfile(accessToken: String): ApiCallResult<RoutineOkResponseDto>
    suspend fun chat(accessToken: String, body: RoutineChatRequestDto): ApiCallResult<RoutineChatResponseDto>
    suspend fun confirm(accessToken: String, body: RoutineConfirmRequestDto): ApiCallResult<RoutineConfirmResponseDto>
    suspend fun week(accessToken: String): ApiCallResult<RoutineWeekResponseDto>
    suspend fun regenerate(accessToken: String): ApiCallResult<RoutineRegenerateResponseDto>
    suspend fun renewWeek(accessToken: String): ApiCallResult<RoutineRegenerateResponseDto>
    suspend fun completeSlot(accessToken: String, slotId: Int): ApiCallResult<RoutineSlotStatusResponseDto>
    suspend fun missSlot(accessToken: String, slotId: Int): ApiCallResult<RoutineSlotStatusResponseDto>
    suspend fun undoSlot(accessToken: String, slotId: Int): ApiCallResult<RoutineSlotStatusResponseDto>
    suspend fun review(accessToken: String): ApiCallResult<RoutineReviewResponseDto>
}

internal class KtorStudentRoutineApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : StudentRoutineApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun profile(accessToken: String) =
        authenticatedGet<RoutineProfileDto>("/api/student/routine/profile", accessToken)

    override suspend fun saveOnboarding(
        accessToken: String,
        body: RoutineOnboardingRequestDto,
    ) = authenticatedPost<RoutineOnboardingResponseDto, RoutineOnboardingRequestDto>(
        "/api/student/routine/onboarding",
        accessToken,
        body,
    )

    override suspend fun updateProfile(
        accessToken: String,
        body: RoutineOnboardingRequestDto,
    ) = authenticatedPatch<RoutineOkResponseDto, RoutineOnboardingRequestDto>(
        "/api/student/routine/profile",
        accessToken,
        body,
    )

    override suspend fun resetProfile(accessToken: String) =
        execute<RoutineOkResponseDto> {
            client.delete(url("/api/student/routine/profile")) { bearerAuth(accessToken) }
        }

    override suspend fun chat(
        accessToken: String,
        body: RoutineChatRequestDto,
    ) = authenticatedPost<RoutineChatResponseDto, RoutineChatRequestDto>(
        "/api/student/routine/chat",
        accessToken,
        body,
    )

    override suspend fun confirm(
        accessToken: String,
        body: RoutineConfirmRequestDto,
    ) = authenticatedPost<RoutineConfirmResponseDto, RoutineConfirmRequestDto>(
        "/api/student/routine/confirm",
        accessToken,
        body,
    )

    override suspend fun week(accessToken: String) =
        authenticatedGet<RoutineWeekResponseDto>("/api/student/routine/week", accessToken)

    override suspend fun regenerate(accessToken: String) =
        authenticatedPostWithoutBody<RoutineRegenerateResponseDto>("/api/student/routine/regenerate", accessToken)

    override suspend fun renewWeek(accessToken: String) =
        authenticatedPostWithoutBody<RoutineRegenerateResponseDto>("/api/student/routine/renew-week", accessToken)

    override suspend fun completeSlot(accessToken: String, slotId: Int) =
        authenticatedPostWithoutBody<RoutineSlotStatusResponseDto>("/api/student/routine/slots/$slotId/complete", accessToken)

    override suspend fun missSlot(accessToken: String, slotId: Int) =
        authenticatedPostWithoutBody<RoutineSlotStatusResponseDto>("/api/student/routine/slots/$slotId/miss", accessToken)

    override suspend fun undoSlot(accessToken: String, slotId: Int) =
        authenticatedPostWithoutBody<RoutineSlotStatusResponseDto>("/api/student/routine/slots/$slotId/undo", accessToken)

    override suspend fun review(accessToken: String) =
        authenticatedPostWithoutBody<RoutineReviewResponseDto>("/api/student/routine/review", accessToken)

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

    private suspend inline fun <reified T, reified B> authenticatedPatch(
        path: String,
        accessToken: String,
        body: B,
    ): ApiCallResult<T> = execute {
        client.patch(url(path)) {
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
