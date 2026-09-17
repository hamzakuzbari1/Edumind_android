package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.auth.AuthApi
import com.rork.eduspark.data.remote.auth.ForgotPasswordRequestDto
import com.rork.eduspark.data.remote.auth.LoginRequestDto
import com.rork.eduspark.data.remote.auth.LoginResponseDto
import com.rork.eduspark.data.remote.auth.LogoutRequestDto
import com.rork.eduspark.data.remote.auth.OkResponseDto
import com.rork.eduspark.data.remote.auth.RefreshTokenRequestDto
import com.rork.eduspark.data.remote.auth.RegisterRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorResponseDto
import com.rork.eduspark.data.remote.auth.ResetPasswordRequestDto
import com.rork.eduspark.data.remote.auth.TokenResponseDto
import com.rork.eduspark.data.remote.auth.UserDto
import com.rork.eduspark.data.remote.auth.VerifyEmailRequestDto
import com.rork.eduspark.data.remote.auth.VerifyTwoFactorRequestDto
import com.rork.eduspark.data.remote.teacher.ParentNoteCreateDto
import com.rork.eduspark.data.remote.teacher.ParentNoteDto
import com.rork.eduspark.data.remote.teacher.ParentNoteListDto
import com.rork.eduspark.data.remote.teacher.ParentNoteReplyCreateDto
import com.rork.eduspark.data.remote.teacher.ParentNoteReplyDto
import com.rork.eduspark.data.remote.teacher.TeacherParentNotesApi
import com.rork.eduspark.data.remote.teacher.buildParentNoteCreateBody
import com.rork.eduspark.data.remote.teacher.parseTeacherStudentNumericId
import com.rork.eduspark.data.remote.teacher.toTeacherParentNotes
import com.rork.eduspark.data.repository.mock.MockTeacherRepository
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue

class TeacherRepositoryWithRemoteParentNotesTest {

    @Test
    fun parseTeacherStudentNumericIdAcceptsMockPrefixedIds() {
        assertEquals(1, parseTeacherStudentNumericId("s1"))
        assertEquals(42, parseTeacherStudentNumericId("42"))
        assertEquals(null, parseTeacherStudentNumericId("student"))
    }

    @Test
    fun buildParentNoteCreateBodyUsesFirstLineTitle() {
        val body = buildParentNoteCreateBody("Title line\nMore detail")
        assertEquals("Title line", body.title)
        assertEquals("Title line\nMore detail", body.description)
        assertEquals("academic", body.category)
        assertEquals("medium", body.priority)
    }

    @Test
    fun mapsListFlatteningRootAndRepliesChronologically() {
        val list = ParentNoteListDto(
            notes = listOf(
                ParentNoteDto(
                    id = 10,
                    studentId = 1,
                    description = "Root note",
                    createdAt = "2026-04-01T10:00:00Z",
                    replies = listOf(
                        ParentNoteReplyDto(
                            id = 2,
                            noteId = 10,
                            authorId = 7,
                            body = "Second reply",
                            createdAt = "2026-04-01T12:00:00Z",
                        ),
                        ParentNoteReplyDto(
                            id = 1,
                            noteId = 10,
                            authorId = 7,
                            body = "First reply",
                            createdAt = "2026-04-01T11:00:00Z",
                        ),
                    ),
                ),
            ),
        )
        val mapped = list.toTeacherParentNotes("s1")
        assertEquals(listOf("10", "reply-1", "reply-2"), mapped.map { it.id })
        assertEquals(listOf("Root note", "First reply", "Second reply"), mapped.map { it.message })
    }

    @Test
    fun emptyBackendListReturnsEmptyNotes() = runBlocking {
        val fixture = fixture(FakeParentNotesApi())
        val result = assertIs<AppResult.Success<List<TeacherParentNote>>>(
            fixture.repository.getParentNotes("s1"),
        )
        assertTrue(result.data.isEmpty())
    }

    @Test
    fun createPersistsWhenNoOpenNoteExists() = runBlocking {
        val api = FakeParentNotesApi()
        val fixture = fixture(api)

        val created = assertIs<AppResult.Success<TeacherParentNote>>(
            fixture.repository.sendParentNote("s1", "Hello parent"),
        )
        assertEquals("Hello parent", created.data.message)
        assertEquals(1, api.notes.size)
        assertEquals("Hello parent", api.notes.single().description)

        val listed = assertIs<AppResult.Success<List<TeacherParentNote>>>(
            fixture.repository.getParentNotes("s1"),
        )
        assertEquals(1, listed.data.size)
        assertEquals(created.data.id, listed.data.single().id)
    }

    @Test
    fun replyPersistsAgainstOpenNote() = runBlocking {
        val api = FakeParentNotesApi(
            seed = listOf(
                ParentNoteDto(
                    id = 5,
                    studentId = 1,
                    description = "Open thread",
                    createdAt = "2026-04-01T09:00:00Z",
                    canReply = true,
                    isClosed = false,
                    status = "open",
                ),
            ),
        )
        val fixture = fixture(api)

        val replied = assertIs<AppResult.Success<TeacherParentNote>>(
            fixture.repository.sendParentNote("s1", "Follow-up"),
        )
        assertTrue(replied.data.id.startsWith("reply-"))
        assertEquals("Follow-up", replied.data.message)
        assertEquals(1, api.notes.single().replies.size)

        val listed = assertIs<AppResult.Success<List<TeacherParentNote>>>(
            fixture.repository.getParentNotes("s1"),
        )
        assertEquals(2, listed.data.size)
        assertEquals("Follow-up", listed.data.last().message)
    }

    @Test
    fun closePersistsAndBlocksFurtherReplies() = runBlocking {
        val api = FakeParentNotesApi(
            seed = listOf(
                ParentNoteDto(
                    id = 9,
                    studentId = 1,
                    description = "Closeable",
                    createdAt = "2026-04-01T09:00:00Z",
                    canReply = true,
                    canClose = true,
                    isClosed = false,
                    status = "open",
                ),
            ),
        )
        val fixture = fixture(api)

        val closed = assertIs<AppResult.Success<TeacherParentNote>>(
            fixture.repository.closeParentNote("s1", "9"),
        )
        assertEquals("9", closed.data.id)
        assertTrue(api.notes.single().isClosed)
        assertEquals("closed", api.notes.single().status)
        assertFalse(api.notes.single().canReply)

        // Next send creates a new note instead of replying to the closed one.
        assertIs<AppResult.Success<TeacherParentNote>>(
            fixture.repository.sendParentNote("s1", "New thread"),
        )
        assertEquals(2, api.notes.size)
    }

    @Test
    fun reloadRestoresServerStateAfterCreateReplyClose() = runBlocking {
        val api = FakeParentNotesApi()
        val fixture = fixture(api)

        assertIs<AppResult.Success<*>>(fixture.repository.sendParentNote("s1", "Create"))
        assertIs<AppResult.Success<*>>(fixture.repository.sendParentNote("s1", "Reply"))
        val noteId = api.notes.single().id.toString()
        assertIs<AppResult.Success<*>>(fixture.repository.closeParentNote("s1", noteId))

        val listed = assertIs<AppResult.Success<List<TeacherParentNote>>>(
            fixture.repository.getParentNotes("s1"),
        )
        assertEquals(2, listed.data.size)
        assertEquals("Create", listed.data.first().message)
        assertEquals("Reply", listed.data.last().message)
        assertTrue(api.notes.single().isClosed)
    }

    private suspend fun fixture(api: FakeParentNotesApi): Fixture {
        val auth = FakeParentNotesAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "42"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        val delegate = MockTeacherRepository()
        return Fixture(
            repository = TeacherRepositoryWithRemoteParentNotes(
                delegate = delegate,
                api = api,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
            ),
        )
    }

    private data class Fixture(val repository: TeacherRepositoryWithRemoteParentNotes)
}

private class FakeParentNotesApi(
    seed: List<ParentNoteDto> = emptyList(),
) : TeacherParentNotesApi {
    val notes = seed.map { it.copy(replies = it.replies.toList()) }.toMutableList()
    private var nextNoteId = (seed.maxOfOrNull { it.id } ?: 0) + 1
    private var nextReplyId = (seed.flatMap { it.replies }.maxOfOrNull { it.id } ?: 0) + 1

    override suspend fun list(
        accessToken: String,
        studentId: Int,
        limit: Int,
    ): ApiCallResult<ParentNoteListDto> =
        ApiCallResult.Success(
            ParentNoteListDto(
                notes = notes.filter { it.studentId == studentId }.take(limit),
                total = notes.count { it.studentId == studentId },
            ),
        )

    override suspend fun create(
        accessToken: String,
        studentId: Int,
        body: ParentNoteCreateDto,
    ): ApiCallResult<ParentNoteDto> {
        val note = ParentNoteDto(
            id = nextNoteId++,
            studentId = studentId,
            title = body.title,
            description = body.description,
            category = body.category,
            priority = body.priority,
            createdAt = "2026-04-02T10:00:00Z",
            updatedAt = "2026-04-02T10:00:00Z",
            status = "open",
            canReply = true,
            canClose = true,
            isClosed = false,
        )
        notes += note
        return ApiCallResult.Success(note)
    }

    override suspend fun reply(
        accessToken: String,
        studentId: Int,
        noteId: Int,
        body: ParentNoteReplyCreateDto,
    ): ApiCallResult<ParentNoteDto> {
        val index = notes.indexOfFirst { it.id == noteId && it.studentId == studentId }
        if (index < 0) return ApiCallResult.HttpFailure(404)
        val existing = notes[index]
        if (existing.isClosed || !existing.canReply) return ApiCallResult.HttpFailure(409)
        val reply = ParentNoteReplyDto(
            id = nextReplyId++,
            noteId = noteId,
            authorId = 7,
            authorName = "Teacher",
            authorRole = "teacher",
            body = body.body,
            createdAt = "2026-04-02T11:00:00Z",
            updatedAt = "2026-04-02T11:00:00Z",
        )
        val updated = existing.copy(
            replies = existing.replies + reply,
            replyCount = existing.replyCount + 1,
            updatedAt = reply.createdAt,
        )
        notes[index] = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun close(
        accessToken: String,
        studentId: Int,
        noteId: Int,
    ): ApiCallResult<ParentNoteDto> {
        val index = notes.indexOfFirst { it.id == noteId && it.studentId == studentId }
        if (index < 0) return ApiCallResult.HttpFailure(404)
        val updated = notes[index].copy(
            isClosed = true,
            canReply = false,
            status = "closed",
            closedAt = "2026-04-02T12:00:00Z",
            canClose = false,
        )
        notes[index] = updated
        return ApiCallResult.Success(updated)
    }
}

private class FakeParentNotesAuthApi : AuthApi {
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.InvalidResponse

    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) =
        ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(
        body: ResendTwoFactorRequestDto,
    ): ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
}
