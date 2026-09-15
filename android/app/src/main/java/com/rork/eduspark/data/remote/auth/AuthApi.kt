package com.rork.eduspark.data.remote.auth

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

internal sealed interface ApiCallResult<out T> {
    data class Success<T>(val value: T) : ApiCallResult<T>
    data class HttpFailure(
        val statusCode: Int,
        val detail: String? = null,
        val fieldErrors: Map<String, String> = emptyMap(),
    ) : ApiCallResult<Nothing>
    data object NetworkFailure : ApiCallResult<Nothing>
    data object InvalidResponse : ApiCallResult<Nothing>
}

internal interface AuthApi {
    suspend fun register(body: RegisterRequestDto): ApiCallResult<TokenResponseDto>
    suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto>
    suspend fun me(accessToken: String): ApiCallResult<UserDto>
    suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto>
    suspend fun logout(accessToken: String, body: LogoutRequestDto): ApiCallResult<OkResponseDto>
    suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto): ApiCallResult<LoginResponseDto>
    suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto): ApiCallResult<ResendTwoFactorResponseDto>
    suspend fun verifyEmail(body: VerifyEmailRequestDto): ApiCallResult<OkResponseDto>
    suspend fun resendVerification(accessToken: String): ApiCallResult<OkResponseDto>
    suspend fun forgotPassword(body: ForgotPasswordRequestDto): ApiCallResult<OkResponseDto>
    suspend fun resetPassword(body: ResetPasswordRequestDto): ApiCallResult<OkResponseDto>
    suspend fun completeStudentOnboarding(accessToken: String): ApiCallResult<OkResponseDto>
    suspend fun completeTeacherSetup(accessToken: String): ApiCallResult<OkResponseDto>
}

internal class KtorAuthApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : AuthApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun register(body: RegisterRequestDto) =
        post<TokenResponseDto, RegisterRequestDto>("/api/auth/register", body)

    override suspend fun login(body: LoginRequestDto) =
        post<LoginResponseDto, LoginRequestDto>("/api/auth/login", body)

    override suspend fun me(accessToken: String) =
        execute<UserDto> { client.get(url("/api/auth/me")) { bearerAuth(accessToken) } }

    override suspend fun refresh(body: RefreshTokenRequestDto) =
        post<TokenResponseDto, RefreshTokenRequestDto>("/api/auth/refresh", body)

    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        execute<OkResponseDto> {
            client.post(url("/api/auth/logout")) {
                contentType(ContentType.Application.Json)
                bearerAuth(accessToken)
                setBody(body)
            }
        }

    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) =
        post<LoginResponseDto, VerifyTwoFactorRequestDto>("/api/auth/verify-2fa", body)

    override suspend fun resendTwoFactor(body: ResendTwoFactorRequestDto) =
        post<ResendTwoFactorResponseDto, ResendTwoFactorRequestDto>("/api/auth/resend-2fa", body)

    override suspend fun verifyEmail(body: VerifyEmailRequestDto) =
        post<OkResponseDto, VerifyEmailRequestDto>("/api/auth/verify-email", body)

    override suspend fun resendVerification(accessToken: String) =
        execute<OkResponseDto> {
            client.post(url("/api/auth/resend-verification")) {
                bearerAuth(accessToken)
            }
        }

    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) =
        post<OkResponseDto, ForgotPasswordRequestDto>("/api/auth/forgot-password", body)

    override suspend fun resetPassword(body: ResetPasswordRequestDto) =
        post<OkResponseDto, ResetPasswordRequestDto>("/api/auth/reset-password", body)

    override suspend fun completeStudentOnboarding(accessToken: String) =
        authenticatedPost<OkResponseDto>("/api/student/onboarding/complete", accessToken)

    override suspend fun completeTeacherSetup(accessToken: String) =
        authenticatedPost<OkResponseDto>("/api/teacher/setup/complete", accessToken)

    private suspend inline fun <reified T, reified B> post(path: String, body: B): ApiCallResult<T> =
        execute {
            client.post(url(path)) {
                contentType(ContentType.Application.Json)
                setBody(body)
            }
        }

    private suspend inline fun <reified T> authenticatedPost(
        path: String,
        accessToken: String,
    ): ApiCallResult<T> = execute {
        client.post(url(path)) { bearerAuth(accessToken) }
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
        detail.jsonPrimitiveOrNull()?.contentOrNull?.let {
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
        return ApiCallResult.HttpFailure(statusCode = statusCode, fieldErrors = fieldErrors)
    }
}

private fun kotlinx.serialization.json.JsonElement.jsonPrimitiveOrNull() =
    runCatching { jsonPrimitive }.getOrNull()
