package com.rork.eduspark.data.remote.auth

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
import com.rork.eduspark.data.model.StudentOnboardingStep

class AuthContractTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun loginAndRegisterDtosUseBackendSnakeCase() {
        val login = json.encodeToString(
            LoginRequestDto("student@example.com", "password", "student", "Pixel 7")
        )
        val register = json.encodeToString(
            RegisterRequestDto("Student", "student@example.com", "password", "student", "Pixel 7")
        )

        assertTrue(login.contains("\"viewer_mode\""))
        assertTrue(login.contains("\"device_name\""))
        assertTrue(register.contains("\"device_name\""))
        assertTrue(register.contains("\"role\":\"student\""))
    }

    @Test
    fun backendIdsAndRolesMapToExistingDomain() {
        val roles = listOf("student", "teacher", "parent")
        val mapped = roles.map { role ->
            UserDto(
                id = 42,
                name = "Name",
                email = "$role@example.com",
                role = role,
                onboardingComplete = true,
                teacherSetupComplete = true,
            ).toDomain()
        }

        assertTrue(mapped.all { it.id == "42" })
        assertEquals(listOf("Student", "Teacher", "Parent"), mapped.map { it.role.name })
    }

    @Test
    fun meIdentityAndOnboardingStateMapWithoutMockFallback() {
        val user = UserDto(
            id = 42,
            name = "Abeer Abdullah",
            email = "abeer@example.com",
            role = "student",
            onboardingComplete = false,
            onboardingStep = "subjects",
            grade = 12,
        ).toDomain()

        assertEquals("Abeer Abdullah", user.displayName)
        assertEquals("abeer@example.com", user.email)
        assertEquals(StudentOnboardingStep.Subjects, user.onboardingStep)
        assertEquals(12, user.grade)
    }

    @Test
    fun unknownRoleFailsSafely() {
        assertIs<UnknownRoleException>(
            runCatching {
                UserDto(1, "Name", "x@example.com", "admin").toDomain()
            }.exceptionOrNull()
        )
    }

    @Test
    fun fastApiValidationArrayIsPreserved() = runBlocking {
        val api = apiReturning(
            status = HttpStatusCode.UnprocessableEntity,
            body = """{"detail":[{"loc":["body","email"],"msg":"invalid email","type":"value_error"}]}""",
        )

        val result = api.login(LoginRequestDto("bad", "password"))

        val failure = assertIs<ApiCallResult.HttpFailure>(result)
        assertEquals("invalid email", failure.fieldErrors["email"])
    }

    @Test
    fun twoFactorResendUsesCanonicalRouteAndParsesMetadata() = runBlocking {
        var requestedPath = ""
        val engine = MockEngine { request ->
            requestedPath = request.url.encodedPath
            respond(
                content = """{"ok":true,"expires_in_seconds":300,"resend_available_in_seconds":30}""",
                status = HttpStatusCode.OK,
                headers = jsonHeaders,
            )
        }
        val api = KtorAuthApi(testClient(engine), "https://example.test")

        val result = api.resendTwoFactor(ResendTwoFactorRequestDto("private-challenge"))

        assertEquals("/api/auth/resend-2fa", requestedPath)
        val value = assertIs<ApiCallResult.Success<ResendTwoFactorResponseDto>>(result).value
        assertEquals(300, value.expiresInSeconds)
        assertEquals(30, value.resendAvailableInSeconds)
    }

    private fun apiReturning(status: HttpStatusCode, body: String): KtorAuthApi {
        val engine = MockEngine {
            respond(content = body, status = status, headers = jsonHeaders)
        }
        return KtorAuthApi(testClient(engine), "https://example.test")
    }

    private fun testClient(engine: MockEngine) = HttpClient(engine) {
        install(ContentNegotiation) { json(json) }
    }

    private companion object {
        val jsonHeaders = headersOf(HttpHeaders.ContentType, "application/json")
    }
}
