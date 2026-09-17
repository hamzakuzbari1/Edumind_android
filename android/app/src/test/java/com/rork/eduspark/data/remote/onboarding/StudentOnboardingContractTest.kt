package com.rork.eduspark.data.remote.onboarding

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class StudentOnboardingContractTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun usesCanonicalMethodsPathsAndCatalogQueries() = runBlocking {
        val requests = mutableListOf<RecordedRequest>()
        val engine = MockEngine { request ->
            requests += RecordedRequest(
                method = request.method.value,
                path = request.url.encodedPath,
                grade = request.url.parameters["grade"],
                subjectId = request.url.parameters["subject_id"],
            )
            val body = when (request.url.encodedPath) {
                "/api/catalog/subjects" ->
                    """[{"id":4,"name_ar":"الرياضيات","slug":"math","grade":12}]"""
                "/api/catalog/teachers" ->
                    """[{"id":2,"full_name":"DEV Teacher","rating":4.5,"student_count":3,"subject_id":4,"subject_name":"الرياضيات"}]"""
                "/api/student/onboarding/complete" ->
                    """{"ok":true,"next_route":"/student/payment","checkout_preview":[]}"""
                else ->
                    """{"step":"subjects","grade":12,"onboarding_complete":false,"selected_subject_ids":[4],"teacher_choices":[]}"""
            }
            respond(body, HttpStatusCode.OK, jsonHeaders)
        }
        val api = KtorStudentOnboardingApi(testClient(engine), "https://example.test")

        assertIs<ApiCallResult.Success<*>>(api.status("token"))
        assertIs<ApiCallResult.Success<*>>(api.saveGrade("token", GradeUpdateDto(12)))
        assertIs<ApiCallResult.Success<*>>(api.subjects("token", 12))
        assertIs<ApiCallResult.Success<*>>(api.saveSubjects("token", SubjectsUpdateDto(listOf(4))))
        assertIs<ApiCallResult.Success<*>>(api.teachers("token", 4, 12))
        assertIs<ApiCallResult.Success<*>>(
            api.saveTeachers("token", TeachersUpdateDto(listOf(TeacherChoiceDto(4, 2))))
        )
        assertIs<ApiCallResult.Success<*>>(api.complete("token"))

        assertEquals(
            listOf(
                "GET /api/student/onboarding/status",
                "PUT /api/student/onboarding/grade",
                "GET /api/catalog/subjects",
                "PUT /api/student/onboarding/subjects",
                "GET /api/catalog/teachers",
                "PUT /api/student/onboarding/teachers",
                "POST /api/student/onboarding/complete",
            ),
            requests.map { "${it.method} ${it.path}" },
        )
        assertEquals("12", requests[2].grade)
        assertEquals("12", requests[4].grade)
        assertEquals("4", requests[4].subjectId)
    }

    @Test
    fun numericIdsAndSnakeCaseBodiesMatchFastApiDtos() {
        val subjects = json.encodeToString(SubjectsUpdateDto(listOf(4, 7)))
        val teachers = json.encodeToString(
            TeachersUpdateDto(listOf(TeacherChoiceDto(subjectId = 4, teacherProfileId = 2)))
        )

        assertTrue(subjects.contains("\"subject_ids\":[4,7]"))
        assertTrue(teachers.contains("\"subject_id\":4"))
        assertTrue(teachers.contains("\"teacher_profile_id\":2"))
    }

    private fun testClient(engine: MockEngine) = HttpClient(engine) {
        install(ContentNegotiation) { json(json) }
    }

    private data class RecordedRequest(
        val method: String,
        val path: String,
        val grade: String?,
        val subjectId: String?,
    )

    private companion object {
        val jsonHeaders = headersOf(HttpHeaders.ContentType, "application/json")
    }
}
