package com.rork.eduspark.data.remote.teacher

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

class TeacherSetupContractTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun usesCanonicalTeacherSetupMethodsAndPaths() = runBlocking {
        val requests = mutableListOf<String>()
        val engine = MockEngine { request ->
            requests += "${request.method.value} ${request.url.encodedPath}"
            val body = when {
                request.url.encodedPath.endsWith("/subjects") ->
                    """[{"id":4,"name_ar":"Math","grade":12,"slug":"math"}]"""
                request.url.encodedPath.endsWith("/cv") -> cvJson
                request.url.encodedPath.endsWith("/portfolio") -> portfolioJson
                request.url.encodedPath.endsWith("/qualifications") ||
                    request.url.encodedPath.contains("/qualifications/") -> qualificationJson
                request.url.encodedPath.endsWith("/teaching-experiences") ||
                    request.url.encodedPath.contains("/teaching-experiences/") -> experienceJson
                request.url.encodedPath.endsWith("/portfolio/impact") -> impactJson
                request.url.encodedPath.endsWith("/why-study-points") ||
                    request.url.encodedPath.contains("/why-study-points/") -> whyJson
                request.url.encodedPath.endsWith("/complete") ->
                    """{"ok":true,"next_route":"/teacher/dashboard"}"""
                else -> statusJson
            }
            respond(body, HttpStatusCode.OK, jsonHeaders)
        }
        val api = KtorTeacherSetupApi(testClient(engine), "https://example.test")

        assertIs<ApiCallResult.Success<*>>(api.status("token"))
        assertIs<ApiCallResult.Success<*>>(
            api.updateProfile("token", TeacherProfileUpdateDto("Teacher", "Bio"))
        )
        assertIs<ApiCallResult.Success<*>>(api.subjects("token", 12))
        assertIs<ApiCallResult.Success<*>>(
            api.updateTeaching("token", TeacherTeachingUpdateDto(listOf(4), listOf(12)))
        )
        assertIs<ApiCallResult.Success<*>>(api.cv("token"))
        assertIs<ApiCallResult.Success<*>>(
            api.createQualification("token", TeacherQualificationWriteDto("Degree"))
        )
        assertIs<ApiCallResult.Success<*>>(
            api.updateQualification("token", 9, TeacherQualificationWriteDto("Degree"))
        )
        assertIs<ApiCallResult.Success<*>>(
            api.createExperience("token", TeacherTeachingExperienceWriteDto("Teacher"))
        )
        assertIs<ApiCallResult.Success<*>>(
            api.updateExperience("token", 8, TeacherTeachingExperienceWriteDto("Teacher"))
        )
        assertIs<ApiCallResult.Success<*>>(api.portfolio("token"))
        assertIs<ApiCallResult.Success<*>>(
            api.updateImpact("token", TeachingImpactUpdateDto(yearsTeachingSubject = 5))
        )
        assertIs<ApiCallResult.Success<*>>(
            api.createWhyStudyPoint("token", TeacherWhyStudyPointWriteDto("Why"))
        )
        assertIs<ApiCallResult.Success<*>>(
            api.updateWhyStudyPoint("token", 7, TeacherWhyStudyPointWriteDto("Why"))
        )
        assertIs<ApiCallResult.Success<*>>(api.complete("token"))

        assertEquals(
            listOf(
                "GET /api/teacher/setup/status",
                "PUT /api/teacher/setup/profile",
                "GET /api/teacher/setup/subjects",
                "PUT /api/teacher/setup/teaching",
                "GET /api/teacher/setup/cv",
                "POST /api/teacher/setup/qualifications",
                "PUT /api/teacher/setup/qualifications/9",
                "POST /api/teacher/setup/teaching-experiences",
                "PUT /api/teacher/setup/teaching-experiences/8",
                "GET /api/teacher/setup/portfolio",
                "PUT /api/teacher/setup/portfolio/impact",
                "POST /api/teacher/setup/why-study-points",
                "PUT /api/teacher/setup/why-study-points/7",
                "POST /api/teacher/setup/complete",
            ),
            requests,
        )
    }

    @Test
    fun uploadAvatarPostsMultipartToCanonicalPath() = runBlocking {
        val requests = mutableListOf<String>()
        var sawMultipart = false
        val engine = MockEngine { request ->
            requests += "${request.method.value} ${request.url.encodedPath}"
            val contentType = request.body.contentType?.toString().orEmpty()
            if (contentType.contains("multipart", ignoreCase = true)) {
                sawMultipart = true
            }
            respond(statusJson, HttpStatusCode.OK, jsonHeaders)
        }
        val api = KtorTeacherSetupApi(testClient(engine), "https://example.test")
        val result = api.uploadAvatar(
            accessToken = "token",
            bytes = ByteArray(64) { 1 },
            filename = "avatar.png",
            mimeType = "image/png",
        )
        assertIs<ApiCallResult.Success<*>>(result)
        assertEquals(listOf("POST /api/teacher/setup/avatar"), requests)
        assertTrue(sawMultipart)
    }

    @Test
    fun transportDtosKeepNumericIdsAndSnakeCase() {
        val teaching = json.encodeToString(TeacherTeachingUpdateDto(listOf(4), listOf(12)))
        val experience = json.encodeToString(
            TeacherTeachingExperienceWriteDto(
                title = "Teacher",
                yearFrom = 2020,
                yearTo = 2024,
                sortOrder = 1,
            )
        )
        val impact = json.encodeToString(TeachingImpactUpdateDto(yearsTeachingSubject = 5))

        assertTrue(teaching.contains("\"subject_ids\":[4]"))
        assertTrue(experience.contains("\"year_from\":2020"))
        assertTrue(experience.contains("\"year_to\":2024"))
        assertTrue(experience.contains("\"sort_order\":1"))
        assertTrue(impact.contains("\"years_teaching_subject\":5"))
    }

    private fun testClient(engine: MockEngine) = HttpClient(engine) {
        install(ContentNegotiation) { json(json) }
    }

    private companion object {
        val jsonHeaders = headersOf(HttpHeaders.ContentType, "application/json")
        const val statusJson =
            """{"setup_complete":false,"full_name":"Teacher","bio":"Bio","subject_ids":[4],"grades":[12]}"""
        const val cvJson =
            """{"qualifications":[],"teaching_experiences":[],"achievements":[]}"""
        const val portfolioJson =
            """{"teaching_impact":{"years_teaching_subject":5},"teaching_philosophy":{},"why_study_points":[],"professional_documents":[],"academic_statistics":{}}"""
        const val qualificationJson =
            """{"id":9,"title":"Degree","institution":null,"year":null,"description":null,"sort_order":0}"""
        const val experienceJson =
            """{"id":8,"title":"Teacher","organization":null,"year_from":null,"year_to":null,"description":null,"sort_order":0}"""
        const val impactJson = """{"years_teaching_subject":5,"highlights":[]}"""
        const val whyJson = """{"id":7,"title":"Why","description":null,"sort_order":0}"""
    }
}
