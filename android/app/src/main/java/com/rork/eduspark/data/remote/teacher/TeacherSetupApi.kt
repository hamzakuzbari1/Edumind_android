package com.rork.eduspark.data.remote.teacher

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.delete
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.formData
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import java.io.IOException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

internal interface TeacherSetupApi {
    suspend fun status(accessToken: String): ApiCallResult<TeacherSetupStatusDto>
    suspend fun updateProfile(accessToken: String, body: TeacherProfileUpdateDto): ApiCallResult<TeacherSetupStatusDto>
    suspend fun uploadAvatar(
        accessToken: String,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
    ): ApiCallResult<TeacherSetupStatusDto>
    suspend fun subjects(accessToken: String, grade: Int): ApiCallResult<List<TeacherSubjectDto>>
    suspend fun updateTeaching(accessToken: String, body: TeacherTeachingUpdateDto): ApiCallResult<TeacherSetupStatusDto>
    suspend fun cv(accessToken: String): ApiCallResult<TeacherProfileCvDto>
    suspend fun createQualification(accessToken: String, body: TeacherQualificationWriteDto): ApiCallResult<TeacherQualificationDto>
    suspend fun updateQualification(accessToken: String, id: Int, body: TeacherQualificationWriteDto): ApiCallResult<TeacherQualificationDto>
    suspend fun deleteQualification(accessToken: String, id: Int): ApiCallResult<Unit>
    suspend fun createExperience(accessToken: String, body: TeacherTeachingExperienceWriteDto): ApiCallResult<TeacherTeachingExperienceDto>
    suspend fun updateExperience(accessToken: String, id: Int, body: TeacherTeachingExperienceWriteDto): ApiCallResult<TeacherTeachingExperienceDto>
    suspend fun portfolio(accessToken: String): ApiCallResult<TeacherPortfolioDto>
    suspend fun updateImpact(accessToken: String, body: TeachingImpactUpdateDto): ApiCallResult<TeachingImpactDto>
    suspend fun createWhyStudyPoint(accessToken: String, body: TeacherWhyStudyPointWriteDto): ApiCallResult<TeacherWhyStudyPointDto>
    suspend fun updateWhyStudyPoint(accessToken: String, id: Int, body: TeacherWhyStudyPointWriteDto): ApiCallResult<TeacherWhyStudyPointDto>
    suspend fun complete(accessToken: String): ApiCallResult<TeacherSetupCompleteDto>
}

internal class KtorTeacherSetupApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : TeacherSetupApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun status(accessToken: String) = get<TeacherSetupStatusDto>("/api/teacher/setup/status", accessToken)

    override suspend fun updateProfile(accessToken: String, body: TeacherProfileUpdateDto) =
        put<TeacherSetupStatusDto, TeacherProfileUpdateDto>("/api/teacher/setup/profile", accessToken, body)

    override suspend fun uploadAvatar(
        accessToken: String,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
    ): ApiCallResult<TeacherSetupStatusDto> = execute {
        val safeName = filename.ifBlank { "avatar.jpg" }
        val contentType = runCatching { ContentType.parse(mimeType) }.getOrElse { ContentType.Image.JPEG }
        client.post(url("/api/teacher/setup/avatar")) {
            bearerAuth(accessToken)
            setBody(
                MultiPartFormDataContent(
                    formData {
                        append(
                            "file",
                            bytes,
                            Headers.build {
                                append(HttpHeaders.ContentType, contentType.toString())
                                append(
                                    HttpHeaders.ContentDisposition,
                                    "filename=\"$safeName\"",
                                )
                            },
                        )
                    },
                ),
            )
        }
    }

    override suspend fun subjects(accessToken: String, grade: Int) = execute<List<TeacherSubjectDto>> {
        client.get(url("/api/teacher/setup/subjects")) {
            bearerAuth(accessToken)
            parameter("grade", grade)
        }
    }

    override suspend fun updateTeaching(accessToken: String, body: TeacherTeachingUpdateDto) =
        put<TeacherSetupStatusDto, TeacherTeachingUpdateDto>("/api/teacher/setup/teaching", accessToken, body)

    override suspend fun cv(accessToken: String) = get<TeacherProfileCvDto>("/api/teacher/setup/cv", accessToken)

    override suspend fun createQualification(accessToken: String, body: TeacherQualificationWriteDto) =
        post<TeacherQualificationDto, TeacherQualificationWriteDto>("/api/teacher/setup/qualifications", accessToken, body)

    override suspend fun updateQualification(accessToken: String, id: Int, body: TeacherQualificationWriteDto) =
        put<TeacherQualificationDto, TeacherQualificationWriteDto>("/api/teacher/setup/qualifications/$id", accessToken, body)

    override suspend fun deleteQualification(accessToken: String, id: Int) = executeUnit {
        client.delete(url("/api/teacher/setup/qualifications/$id")) { bearerAuth(accessToken) }
    }

    override suspend fun createExperience(accessToken: String, body: TeacherTeachingExperienceWriteDto) =
        post<TeacherTeachingExperienceDto, TeacherTeachingExperienceWriteDto>(
            "/api/teacher/setup/teaching-experiences",
            accessToken,
            body,
        )

    override suspend fun updateExperience(accessToken: String, id: Int, body: TeacherTeachingExperienceWriteDto) =
        put<TeacherTeachingExperienceDto, TeacherTeachingExperienceWriteDto>(
            "/api/teacher/setup/teaching-experiences/$id",
            accessToken,
            body,
        )

    override suspend fun portfolio(accessToken: String) = get<TeacherPortfolioDto>("/api/teacher/setup/portfolio", accessToken)

    override suspend fun updateImpact(accessToken: String, body: TeachingImpactUpdateDto) =
        put<TeachingImpactDto, TeachingImpactUpdateDto>("/api/teacher/setup/portfolio/impact", accessToken, body)

    override suspend fun createWhyStudyPoint(accessToken: String, body: TeacherWhyStudyPointWriteDto) =
        post<TeacherWhyStudyPointDto, TeacherWhyStudyPointWriteDto>("/api/teacher/setup/why-study-points", accessToken, body)

    override suspend fun updateWhyStudyPoint(accessToken: String, id: Int, body: TeacherWhyStudyPointWriteDto) =
        put<TeacherWhyStudyPointDto, TeacherWhyStudyPointWriteDto>(
            "/api/teacher/setup/why-study-points/$id",
            accessToken,
            body,
        )

    override suspend fun complete(accessToken: String) = execute<TeacherSetupCompleteDto> {
        client.post(url("/api/teacher/setup/complete")) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T> get(path: String, accessToken: String) = execute<T> {
        client.get(url(path)) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T, reified B> post(path: String, accessToken: String, body: B) = execute<T> {
        client.post(url(path)) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
        }
    }

    private suspend inline fun <reified T, reified B> put(path: String, accessToken: String, body: B) = execute<T> {
        client.put(url(path)) {
            contentType(ContentType.Application.Json)
            bearerAuth(accessToken)
            setBody(body)
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

    private suspend fun executeUnit(
        request: suspend () -> io.ktor.client.statement.HttpResponse,
    ): ApiCallResult<Unit> = try {
        val response = request()
        if (response.status.value in 200..299) {
            ApiCallResult.Success(Unit)
        } else {
            parseFailure(response.status.value, response.bodyAsText())
        }
    } catch (_: IOException) {
        ApiCallResult.NetworkFailure
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
