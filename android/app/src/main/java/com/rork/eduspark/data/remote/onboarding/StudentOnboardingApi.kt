package com.rork.eduspark.data.remote.onboarding

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
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

internal interface StudentOnboardingApi {
    suspend fun status(accessToken: String): ApiCallResult<OnboardingStatusDto>
    suspend fun subjects(accessToken: String, grade: Int): ApiCallResult<List<SubjectDto>>
    suspend fun saveGrade(accessToken: String, body: GradeUpdateDto): ApiCallResult<OnboardingStatusDto>
    suspend fun saveSubjects(accessToken: String, body: SubjectsUpdateDto): ApiCallResult<OnboardingStatusDto>
    suspend fun teachers(accessToken: String, subjectId: Int, grade: Int): ApiCallResult<List<TeacherDto>>
    suspend fun saveTeachers(accessToken: String, body: TeachersUpdateDto): ApiCallResult<OnboardingStatusDto>
    suspend fun complete(accessToken: String): ApiCallResult<OnboardingCompleteDto>
}

internal class KtorStudentOnboardingApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : StudentOnboardingApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun status(accessToken: String) =
        execute<OnboardingStatusDto> {
            client.get(url("/api/student/onboarding/status")) { bearerAuth(accessToken) }
        }

    override suspend fun subjects(accessToken: String, grade: Int) =
        execute<List<SubjectDto>> {
            client.get(url("/api/catalog/subjects")) {
                bearerAuth(accessToken)
                parameter("grade", grade)
            }
        }

    override suspend fun saveGrade(accessToken: String, body: GradeUpdateDto) =
        authenticatedPut<OnboardingStatusDto, GradeUpdateDto>(
            "/api/student/onboarding/grade",
            accessToken,
            body,
        )

    override suspend fun saveSubjects(accessToken: String, body: SubjectsUpdateDto) =
        authenticatedPut<OnboardingStatusDto, SubjectsUpdateDto>(
            "/api/student/onboarding/subjects",
            accessToken,
            body,
        )

    override suspend fun teachers(accessToken: String, subjectId: Int, grade: Int) =
        execute<List<TeacherDto>> {
            client.get(url("/api/catalog/teachers")) {
                bearerAuth(accessToken)
                parameter("subject_id", subjectId)
                parameter("grade", grade)
            }
        }

    override suspend fun saveTeachers(accessToken: String, body: TeachersUpdateDto) =
        authenticatedPut<OnboardingStatusDto, TeachersUpdateDto>(
            "/api/student/onboarding/teachers",
            accessToken,
            body,
        )

    override suspend fun complete(accessToken: String) = execute<OnboardingCompleteDto> {
        client.post(url("/api/student/onboarding/complete")) { bearerAuth(accessToken) }
    }

    private suspend inline fun <reified T, reified B> authenticatedPut(
        path: String,
        accessToken: String,
        body: B,
    ): ApiCallResult<T> = execute {
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
