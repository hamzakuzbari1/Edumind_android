package com.rork.eduspark.data.remote.messaging

import com.rork.eduspark.data.remote.auth.ApiCallResult
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.formData
import io.ktor.client.request.bearerAuth
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders
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
internal data class ConversationParticipantDto(
    @SerialName("user_id") val userId: Int,
    val name: String,
    val role: String,
    @SerialName("display_name") val displayName: String = "",
    @SerialName("role_label") val roleLabel: String = "",
    @SerialName("avatar_url") val avatarUrl: String? = null,
)

@Serializable
internal data class ConversationMessageDto(
    val id: Int,
    @SerialName("thread_id") val threadId: Int,
    @SerialName("sender_id") val senderId: Int,
    @SerialName("sender_name") val senderName: String,
    val body: String,
    @SerialName("message_kind") val messageKind: String = "text",
    @SerialName("attachment_media_id") val attachmentMediaId: Int? = null,
    @SerialName("attachment_url") val attachmentUrl: String? = null,
    @SerialName("attachment_name") val attachmentName: String? = null,
    @SerialName("attachment_mime") val attachmentMime: String? = null,
    @SerialName("voice_duration_ms") val voiceDurationMs: Int? = null,
    val status: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("is_mine") val isMine: Boolean = false,
)

@Serializable
internal data class ConversationDto(
    val id: Int,
    val title: String,
    @SerialName("thread_type") val threadType: String,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String? = null,
    @SerialName("course_id") val courseId: Int? = null,
    @SerialName("course_context_label") val courseContextLabel: String? = null,
    @SerialName("course_subject_name") val courseSubjectName: String? = null,
    @SerialName("include_parent") val includeParent: Boolean = false,
    val participants: List<ConversationParticipantDto> = emptyList(),
    @SerialName("other_participants") val otherParticipants: List<ConversationParticipantDto> = emptyList(),
    @SerialName("last_message_preview") val lastMessagePreview: String? = null,
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("unread_count") val unreadCount: Int = 0,
    @SerialName("is_pinned") val isPinned: Boolean = false,
    @SerialName("is_archived") val isArchived: Boolean = false,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
internal data class ConversationDetailDto(
    val id: Int,
    val title: String,
    @SerialName("thread_type") val threadType: String,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String? = null,
    @SerialName("course_id") val courseId: Int? = null,
    @SerialName("course_context_label") val courseContextLabel: String? = null,
    @SerialName("course_subject_name") val courseSubjectName: String? = null,
    @SerialName("include_parent") val includeParent: Boolean = false,
    val participants: List<ConversationParticipantDto> = emptyList(),
    @SerialName("other_participants") val otherParticipants: List<ConversationParticipantDto> = emptyList(),
    @SerialName("last_message_preview") val lastMessagePreview: String? = null,
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("unread_count") val unreadCount: Int = 0,
    @SerialName("is_pinned") val isPinned: Boolean = false,
    @SerialName("is_archived") val isArchived: Boolean = false,
    @SerialName("created_at") val createdAt: String,
    val messages: List<ConversationMessageDto> = emptyList(),
)

@Serializable
internal data class ConversationListDto(
    val conversations: List<ConversationDto> = emptyList(),
    @SerialName("total_unread") val totalUnread: Int = 0,
)

@Serializable
internal data class MessagingContactDto(
    @SerialName("user_id") val userId: Int,
    val name: String,
    val role: String,
    @SerialName("student_id") val studentId: Int? = null,
    @SerialName("student_name") val studentName: String? = null,
)

@Serializable
internal data class MessagingContactsDto(
    val students: List<MessagingContactDto> = emptyList(),
    val parents: List<MessagingContactDto> = emptyList(),
)

@Serializable
internal data class MessageCreateDto(val body: String)

@Serializable
internal data class ConversationCreateDto(
    @SerialName("student_id") val studentId: Int,
    @SerialName("parent_ids") val parentIds: List<Int> = emptyList(),
    @SerialName("include_student") val includeStudent: Boolean = true,
    val title: String? = null,
)

@Serializable
internal data class CourseTeacherChatOpenDto(
    @SerialName("include_parent") val includeParent: Boolean = false,
)

@Serializable
internal data class CourseTeacherChatDto(
    @SerialName("thread_id") val threadId: Int,
    val created: Boolean = false,
    @SerialName("course_context_label") val courseContextLabel: String,
)

@Serializable
internal data class ParentTeacherContactDto(
    @SerialName("teacher_user_id") val teacherUserId: Int,
    @SerialName("teacher_name") val teacherName: String,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("course_id") val courseId: Int,
    @SerialName("course_title") val courseTitle: String,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String,
    @SerialName("thread_id") val threadId: Int? = null,
    @SerialName("last_message_preview") val lastMessagePreview: String? = null,
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("unread_count") val unreadCount: Int = 0,
)

@Serializable
internal data class ParentTeachersListDto(
    val teachers: List<ParentTeacherContactDto> = emptyList(),
    @SerialName("total_unread") val totalUnread: Int = 0,
)

@Serializable
internal data class ParentTeacherChatOpenDto(
    @SerialName("student_id") val studentId: Int,
    @SerialName("course_id") val courseId: Int,
)

@Serializable
internal data class ParentTeacherChatDto(
    @SerialName("thread_id") val threadId: Int,
    val created: Boolean = false,
    @SerialName("teacher_name") val teacherName: String,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("student_name") val studentName: String,
    @SerialName("context_label") val contextLabel: String,
)

internal interface MessagingApi {
    suspend fun listConversations(accessToken: String): ApiCallResult<ConversationListDto>
    suspend fun getConversation(accessToken: String, threadId: Int, markRead: Boolean): ApiCallResult<ConversationDetailDto>
    suspend fun sendMessage(accessToken: String, threadId: Int, body: MessageCreateDto): ApiCallResult<ConversationDetailDto>
    suspend fun sendAttachment(
        accessToken: String,
        threadId: Int,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
        caption: String,
        voiceDurationMs: Int?,
    ): ApiCallResult<ConversationDetailDto>
    suspend fun markRead(accessToken: String, threadId: Int): ApiCallResult<Unit>
    suspend fun createConversation(accessToken: String, body: ConversationCreateDto): ApiCallResult<ConversationDetailDto>
    suspend fun teacherContacts(accessToken: String): ApiCallResult<MessagingContactsDto>
    suspend fun openCourseTeacherChat(accessToken: String, courseId: Int, body: CourseTeacherChatOpenDto): ApiCallResult<CourseTeacherChatDto>
    suspend fun parentTeachers(accessToken: String): ApiCallResult<ParentTeachersListDto>
    suspend fun openParentTeacherChat(accessToken: String, teacherId: Int, body: ParentTeacherChatOpenDto): ApiCallResult<ParentTeacherChatDto>
}

internal class KtorMessagingApi(
    private val client: HttpClient,
    baseUrl: String,
    private val json: Json = Json { ignoreUnknownKeys = true },
) : MessagingApi {
    private val root = baseUrl.trimEnd('/')

    override suspend fun listConversations(accessToken: String) =
        get<ConversationListDto>("/api/messages/conversations", accessToken)

    override suspend fun getConversation(accessToken: String, threadId: Int, markRead: Boolean) =
        execute<ConversationDetailDto> {
            client.get(url("/api/messages/conversations/$threadId")) {
                bearerAuth(accessToken)
                parameter("mark_read", markRead)
            }
        }

    override suspend fun sendMessage(accessToken: String, threadId: Int, body: MessageCreateDto) =
        post<ConversationDetailDto, MessageCreateDto>("/api/messages/conversations/$threadId/messages", accessToken, body)

    override suspend fun sendAttachment(
        accessToken: String,
        threadId: Int,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
        caption: String,
        voiceDurationMs: Int?,
    ) = execute<ConversationDetailDto> {
        client.post(url("/api/messages/conversations/$threadId/messages/attachment")) {
            bearerAuth(accessToken)
            setBody(
                MultiPartFormDataContent(
                    formData {
                        append("caption", caption)
                        voiceDurationMs?.let { append("voice_duration_ms", it.toString()) }
                        append(
                            key = "file",
                            value = bytes,
                            headers = Headers.build {
                                append(HttpHeaders.ContentType, mimeType)
                                append(HttpHeaders.ContentDisposition, "filename=\"${filename.sanitizeHeaderValue()}\"")
                            },
                        )
                    },
                ),
            )
        }
    }

    override suspend fun markRead(accessToken: String, threadId: Int) =
        executeUnit { client.post(url("/api/messages/conversations/$threadId/read")) { bearerAuth(accessToken) } }

    override suspend fun createConversation(accessToken: String, body: ConversationCreateDto) =
        post<ConversationDetailDto, ConversationCreateDto>("/api/messages/conversations", accessToken, body)

    override suspend fun teacherContacts(accessToken: String) =
        get<MessagingContactsDto>("/api/messages/contacts", accessToken)

    override suspend fun openCourseTeacherChat(accessToken: String, courseId: Int, body: CourseTeacherChatOpenDto) =
        post<CourseTeacherChatDto, CourseTeacherChatOpenDto>("/api/student/courses/$courseId/open-teacher-chat", accessToken, body)

    override suspend fun parentTeachers(accessToken: String) =
        get<ParentTeachersListDto>("/api/parent/messaging/teachers", accessToken)

    override suspend fun openParentTeacherChat(accessToken: String, teacherId: Int, body: ParentTeacherChatOpenDto) =
        post<ParentTeacherChatDto, ParentTeacherChatOpenDto>("/api/parent/messaging/teachers/$teacherId/open-chat", accessToken, body)

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

private fun String.sanitizeHeaderValue(): String =
    replace("\"", "_").replace("\r", "_").replace("\n", "_").ifBlank { "attachment.bin" }
