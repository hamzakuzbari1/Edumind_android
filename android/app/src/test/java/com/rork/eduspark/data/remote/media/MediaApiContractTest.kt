package com.rork.eduspark.data.remote.media

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
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class MediaApiContractTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun downloadUrlUsesCanonicalAuthenticatedPath() = runBlocking {
        var path = ""
        var authHeader: String? = null
        val engine = MockEngine { request ->
            path = request.url.encodedPath
            authHeader = request.headers[HttpHeaders.Authorization]
            respond(
                """{"media_id":12,"url":"https://signed.example/x","expires_in":90,"provider":"supabase","is_signed":true,"bucket":"edumind-private"}""",
                HttpStatusCode.OK,
                headersOf(HttpHeaders.ContentType, "application/json"),
            )
        }
        val api = KtorMediaApi(testClient(engine), "https://example.test")
        val result = assertIs<ApiCallResult.Success<*>>(api.downloadUrl("tok", 12))
        val dto = assertIs<MediaDownloadUrlDto>(result.value)
        assertEquals("/api/media/12/download-url", path)
        assertEquals("Bearer tok", authHeader)
        assertEquals(12, dto.mediaId)
        assertTrue(dto.isSigned)
        assertEquals(90, dto.expiresIn)
    }

    private fun testClient(engine: MockEngine) = HttpClient(engine) {
        install(ContentNegotiation) { json(json) }
    }
}
