package com.rork.eduspark.data.remote.media

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
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
internal data class MediaDownloadUrlDto(
    @SerialName("media_id") val mediaId: Int,
    val url: String,
    @SerialName("expires_in") val expiresIn: Int? = null,
    val provider: String,
    @SerialName("is_signed") val isSigned: Boolean = false,
    val bucket: String? = null,
)

internal interface MediaApi {
    suspend fun downloadUrl(
        accessToken: String,
        mediaId: Int,
        expiresIn: Int? = null,
    ): ApiCallResult<MediaDownloadUrlDto>
}

internal class KtorMediaApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : MediaApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun downloadUrl(
        accessToken: String,
        mediaId: Int,
        expiresIn: Int?,
    ): ApiCallResult<MediaDownloadUrlDto> = try {
        val response = client.get(url("/api/media/$mediaId/download-url")) {
            bearerAuth(accessToken)
            contentType(ContentType.Application.Json)
            if (expiresIn != null) parameter("expires_in", expiresIn)
        }
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

    private fun url(path: String): String = root + path

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
