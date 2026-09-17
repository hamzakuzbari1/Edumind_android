package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.MessageAttachment
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.messaging.ConversationCreateDto
import com.rork.eduspark.data.remote.messaging.ConversationDetailDto
import com.rork.eduspark.data.remote.messaging.ConversationDto
import com.rork.eduspark.data.remote.messaging.ConversationMessageDto
import com.rork.eduspark.data.remote.messaging.ConversationParticipantDto
import com.rork.eduspark.data.remote.messaging.CourseTeacherChatOpenDto
import com.rork.eduspark.data.remote.messaging.MessageCreateDto
import com.rork.eduspark.data.remote.messaging.MessagingApi
import com.rork.eduspark.data.remote.messaging.ParentTeacherChatOpenDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import java.io.File
import java.time.OffsetDateTime
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first

internal class RemoteMessagingRepository(
    private val api: MessagingApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : MessagingRepository {

    private val _threads = MutableStateFlow<List<MessageThread>>(emptyList())
    override val threads: Flow<List<MessageThread>> = _threads.asStateFlow()

    override suspend fun getThreads(): AppResult<List<MessageThread>> =
        when (val response = authorizedRequest(api::listConversations)) {
            is ApiCallResult.Success -> {
                val viewerId = currentViewerId()
                val mapped = response.value.conversations.map { it.toDomain(viewerId) }
                _threads.value = mapped
                AppResult.Success(mapped)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun getThread(threadId: String): AppResult<MessageThread> {
        val numericThreadId = threadId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.NotFound)
        return when (val response = authorizedRequest { api.getConversation(it, numericThreadId, markRead = true) }) {
            is ApiCallResult.Success -> {
                val thread = response.value.toDomain(currentViewerId())
                replaceThread(thread)
                AppResult.Success(thread)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getPermittedContacts(
        viewerId: String,
        viewerRole: MessageParticipantRole,
    ): AppResult<List<MessageParticipant>> =
        when (viewerRole) {
            MessageParticipantRole.Teacher -> teacherContacts()
            MessageParticipantRole.Parent -> parentContacts()
            MessageParticipantRole.Student -> studentContactsFromExistingThreads(viewerId)
        }

    override suspend fun openOrCreateThread(
        viewerId: String,
        viewerRole: MessageParticipantRole,
        contactId: String,
    ): AppResult<MessageThread> = when (viewerRole) {
        MessageParticipantRole.Teacher -> openTeacherThread(contactId)
        MessageParticipantRole.Parent -> openParentThread(contactId)
        MessageParticipantRole.Student -> openStudentThread(contactId)
    }

    override suspend fun openCourseTeacherThread(courseId: String, includeParent: Boolean): AppResult<MessageThread> {
        val numericCourseId = courseId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.NotFound)
        val opened = authorizedRequest {
            api.openCourseTeacherChat(it, numericCourseId, CourseTeacherChatOpenDto(includeParent = includeParent))
        }
        val threadId = when (opened) {
            is ApiCallResult.Success -> opened.value.threadId
            else -> return AppResult.Failure(handleFailure(opened))
        }
        return getThread(threadId.toString())
    }

    override suspend fun getParentThreadForStudent(teacherId: String, studentId: String): AppResult<MessageThread> {
        val parentContact = when (val contacts = teacherContacts()) {
            is AppResult.Success -> contacts.data.firstOrNull {
                it.role == MessageParticipantRole.Parent && it.relatedStudentId == studentId
            }
            is AppResult.Failure -> return contacts
        } ?: return AppResult.Failure(AppError.NotFound)
        return openTeacherThread(parentContact.id)
    }

    override suspend fun sendMessage(
        threadId: String,
        senderId: String,
        body: String,
        attachment: MessageAttachment?,
    ): AppResult<MessagingChatMessage> {
        val numericThreadId = threadId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.NotFound)
        val response = if (attachment == null) {
            authorizedRequest {
                api.sendMessage(it, numericThreadId, MessageCreateDto(body = body))
            }
        } else {
            val upload = attachment.toUploadPayload()
                ?: return AppResult.Failure(AppError.Domain("attachment_file_unavailable"))
            authorizedRequest {
                api.sendAttachment(
                    accessToken = it,
                    threadId = numericThreadId,
                    bytes = upload.bytes,
                    filename = upload.filename,
                    mimeType = upload.mimeType,
                    caption = body,
                    voiceDurationMs = attachment.durationSeconds?.let { seconds -> seconds * 1000 },
                )
            }
        }
        return when (response) {
            is ApiCallResult.Success -> {
                val thread = response.value.toDomain(currentViewerId())
                replaceThread(thread)
                val message = thread.messages.lastOrNull { it.senderId == senderId } ?: thread.messages.last()
                AppResult.Success(message)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun markThreadRead(threadId: String, viewerId: String): AppResult<Unit> {
        val numericThreadId = threadId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.NotFound)
        return when (val response = authorizedRequest { api.markRead(it, numericThreadId) }) {
            is ApiCallResult.Success -> {
                getThread(threadId)
                AppResult.Success(Unit)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private suspend fun teacherContacts(): AppResult<List<MessageParticipant>> =
        when (val response = authorizedRequest(api::teacherContacts)) {
            is ApiCallResult.Success -> {
                val students = response.value.students.map {
                    MessageParticipant(
                        id = it.userId.toString(),
                        displayName = it.name,
                        role = MessageParticipantRole.Student,
                        avatarInitial = it.name.avatarInitial(),
                        contextLabel = it.studentName ?: "",
                    )
                }
                val parents = response.value.parents.map {
                    MessageParticipant(
                        id = parentContactId(parentId = it.userId, studentId = it.studentId ?: 0),
                        displayName = it.name,
                        role = MessageParticipantRole.Parent,
                        avatarInitial = it.name.avatarInitial(),
                        contextLabel = it.studentName?.let { name -> "ولي أمر $name" }.orEmpty(),
                        relatedStudentId = it.studentId?.toString(),
                    )
                }
                AppResult.Success(students + parents)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    private suspend fun parentContacts(): AppResult<List<MessageParticipant>> =
        when (val response = authorizedRequest(api::parentTeachers)) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.teachers.map {
                    MessageParticipant(
                        id = parentTeacherContactId(it.teacherUserId, it.studentId, it.courseId),
                        displayName = it.teacherName,
                        role = MessageParticipantRole.Teacher,
                        avatarInitial = it.teacherName.avatarInitial(),
                        contextLabel = "${it.subjectName} — ${it.studentName}",
                        relatedStudentId = it.studentId.toString(),
                    )
                },
            )
            else -> AppResult.Failure(handleFailure(response))
        }

    private suspend fun studentContactsFromExistingThreads(viewerId: String): AppResult<List<MessageParticipant>> {
        val current = when (val loaded = getThreads()) {
            is AppResult.Success -> loaded.data
            is AppResult.Failure -> return loaded
        }
        return AppResult.Success(
            current
                .filter { it.involves(viewerId) }
                .map { it.teacherParticipant }
                .distinctBy { it.id },
        )
    }

    private suspend fun openTeacherThread(contactId: String): AppResult<MessageThread> {
        val parentParts = parseParentContactId(contactId)
        val body = if (parentParts != null) {
            ConversationCreateDto(
                studentId = parentParts.studentId,
                parentIds = listOf(parentParts.parentId),
                includeStudent = false,
            )
        } else {
            ConversationCreateDto(
                studentId = contactId.toRemoteIdOrNull() ?: return AppResult.Failure(AppError.NotFound),
                includeStudent = true,
            )
        }
        return when (val response = authorizedRequest { api.createConversation(it, body) }) {
            is ApiCallResult.Success -> {
                val thread = response.value.toDomain(currentViewerId())
                replaceThread(thread)
                AppResult.Success(thread)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private suspend fun openParentThread(contactId: String): AppResult<MessageThread> {
        val parts = parseParentTeacherContactId(contactId) ?: return AppResult.Failure(AppError.NotFound)
        val opened = authorizedRequest {
            api.openParentTeacherChat(
                it,
                parts.teacherId,
                ParentTeacherChatOpenDto(studentId = parts.studentId, courseId = parts.courseId),
            )
        }
        val threadId = when (opened) {
            is ApiCallResult.Success -> opened.value.threadId
            else -> return AppResult.Failure(handleFailure(opened))
        }
        return getThread(threadId.toString())
    }

    private suspend fun openStudentThread(contactId: String): AppResult<MessageThread> =
        if (contactId.startsWith(COURSE_CONTACT_PREFIX)) {
            openCourseTeacherThread(contactId.removePrefix(COURSE_CONTACT_PREFIX))
        } else {
            AppResult.Failure(AppError.NotFound)
        }

    private suspend fun <T> authorizedRequest(
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = tokenStore.read() ?: return ApiCallResult.HttpFailure(401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> call(refreshed.data.accessToken)
            is AppResult.Failure -> ApiCallResult.HttpFailure(401)
        }
    }

    private suspend fun handleFailure(response: ApiCallResult<*>): AppError {
        val error = when (response) {
            ApiCallResult.NetworkFailure -> AppError.Network
            ApiCallResult.InvalidResponse -> AppError.Unknown
            is ApiCallResult.Success -> AppError.Unknown
            is ApiCallResult.HttpFailure -> when (response.statusCode) {
                401 -> AppError.SessionExpired
                403 -> AppError.Forbidden
                404, 410 -> AppError.NotFound
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "messaging_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }

    private suspend fun currentViewerId(): String = authRepository.session.first()?.id.orEmpty()

    private fun replaceThread(thread: MessageThread) {
        _threads.value = (_threads.value.filterNot { it.id == thread.id } + thread)
            .sortedByDescending { it.lastMessage?.sentAtMillis ?: 0L }
    }
}

private data class ParentContactParts(val parentId: Int, val studentId: Int)
private data class ParentTeacherContactParts(val teacherId: Int, val studentId: Int, val courseId: Int)
private data class AttachmentUploadPayload(val bytes: ByteArray, val filename: String, val mimeType: String)

private const val PARENT_CONTACT_PREFIX = "parent:"
private const val PARENT_TEACHER_CONTACT_PREFIX = "parent-teacher:"
private const val COURSE_CONTACT_PREFIX = "course:"

private fun parentContactId(parentId: Int, studentId: Int): String = "$PARENT_CONTACT_PREFIX$parentId:student:$studentId"

private fun parentTeacherContactId(teacherId: Int, studentId: Int, courseId: Int): String =
    "$PARENT_TEACHER_CONTACT_PREFIX$teacherId:student:$studentId:course:$courseId"

private fun parseParentContactId(value: String): ParentContactParts? {
    val parts = value.split(":")
    return if (parts.size == 4 && parts[0] == "parent" && parts[2] == "student") {
        ParentContactParts(parentId = parts[1].toIntOrNull() ?: return null, studentId = parts[3].toIntOrNull() ?: return null)
    } else {
        null
    }
}

private fun parseParentTeacherContactId(value: String): ParentTeacherContactParts? {
    val parts = value.split(":")
    return if (parts.size == 6 && parts[0] == "parent-teacher" && parts[2] == "student" && parts[4] == "course") {
        ParentTeacherContactParts(
            teacherId = parts[1].toIntOrNull() ?: return null,
            studentId = parts[3].toIntOrNull() ?: return null,
            courseId = parts[5].toIntOrNull() ?: return null,
        )
    } else {
        null
    }
}

private fun ConversationDto.toDomain(viewerId: String): MessageThread =
    toDetailDto(messages = previewMessages()).toDomain(viewerId)

private fun ConversationDetailDto.toDomain(viewerId: String): MessageThread {
    val teacher = participants.firstOrNull { it.role == "teacher" }
        ?: otherParticipants.firstOrNull { it.role == "teacher" }
        ?: participants.firstOrNull()
        ?: fallbackParticipant("teacher", title)
    val counterpart = chooseCounterpart(viewerId)
    val teacherParticipant = teacher.toDomain(roleOverride = MessageParticipantRole.Teacher, context = courseContextLabel.orEmpty())
    val studentParticipant = counterpart.toDomain(context = courseContextLabel ?: studentName.orEmpty())
    val mappedMessages = messages.map { it.toDomain() }.ifEmpty { previewMessages() }
    return MessageThread(
        id = id.toString(),
        teacherParticipant = teacherParticipant,
        studentParticipant = studentParticipant,
        messages = mappedMessages,
    )
}

private fun ConversationDetailDto.chooseCounterpart(viewerId: String): ConversationParticipantDto {
    val all = participants.ifEmpty { otherParticipants }
    val current = all.firstOrNull { it.userId.toString() == viewerId }
    if (current?.role == "parent") return current
    if (current?.role == "student") return current
    if (threadType == "teacher_parent") {
        all.firstOrNull { it.role == "parent" }?.let { return it }
    }
    return all.firstOrNull { it.role == "student" }
        ?: all.firstOrNull { it.role == "parent" }
        ?: all.firstOrNull { it.userId.toString() != viewerId }
        ?: fallbackParticipant("student", studentName ?: title)
}

private fun ConversationDto.toDetailDto(messages: List<MessagingChatMessage>): ConversationDetailDto =
    ConversationDetailDto(
        id = id,
        title = title,
        threadType = threadType,
        studentId = studentId,
        studentName = studentName,
        courseId = courseId,
        courseContextLabel = courseContextLabel,
        courseSubjectName = courseSubjectName,
        includeParent = includeParent,
        participants = participants,
        otherParticipants = otherParticipants,
        lastMessagePreview = lastMessagePreview,
        lastMessageAt = lastMessageAt,
        unreadCount = unreadCount,
        isPinned = isPinned,
        isArchived = isArchived,
        createdAt = createdAt,
        messages = emptyList(),
    )

private fun ConversationDto.previewMessages(): List<MessagingChatMessage> =
    lastMessagePreview?.takeIf { it.isNotBlank() }?.let {
        listOf(
            MessagingChatMessage(
                id = "$id-preview",
                senderId = "",
                body = it,
                sentAtLabel = lastMessageAt?.toRelativeLabel().orEmpty(),
                sentAtMillis = lastMessageAt.toMillisOrNow(),
                isRead = unreadCount == 0,
            ),
        )
    }.orEmpty()

private fun ConversationDetailDto.previewMessages(): List<MessagingChatMessage> =
    lastMessagePreview?.takeIf { it.isNotBlank() }?.let {
        listOf(
            MessagingChatMessage(
                id = "$id-preview",
                senderId = "",
                body = it,
                sentAtLabel = lastMessageAt?.toRelativeLabel().orEmpty(),
                sentAtMillis = lastMessageAt.toMillisOrNow(),
                isRead = unreadCount == 0,
            ),
        )
    }.orEmpty()

private fun ConversationParticipantDto.toDomain(
    roleOverride: MessageParticipantRole? = null,
    context: String = "",
): MessageParticipant {
    val label = displayName.ifBlank { name }
    val mappedRole = roleOverride ?: role.toParticipantRole()
    return MessageParticipant(
        id = userId.toString(),
        displayName = label,
        role = mappedRole,
        avatarInitial = label.avatarInitial(),
        contextLabel = context,
    )
}

private fun ConversationMessageDto.toDomain(): MessagingChatMessage =
    MessagingChatMessage(
        id = id.toString(),
        senderId = senderId.toString(),
        body = body,
        sentAtLabel = createdAt.toRelativeLabel(),
        sentAtMillis = createdAt.toMillisOrNow(),
        isRead = isMine || status == "read",
        attachment = toAttachment(),
    )

private fun ConversationMessageDto.toAttachment(): MessageAttachment? {
    val ref = attachmentUrl?.takeIf { it.isNotBlank() } ?: return null
    val type = when (messageKind) {
        "image" -> MessageAttachmentType.Image
        "voice" -> MessageAttachmentType.Voice
        else -> MessageAttachmentType.File
    }
    return MessageAttachment(
        type = type,
        label = attachmentName?.takeIf { it.isNotBlank() } ?: ref.substringAfterLast('/'),
        durationSeconds = voiceDurationMs?.let { (it / 1000).coerceAtLeast(0) },
        mediaRef = ref,
        mimeType = attachmentMime,
    )
}

private fun MessageAttachment.toUploadPayload(): AttachmentUploadPayload? {
    uploadBytes?.let {
        return AttachmentUploadPayload(
            bytes = it,
            filename = label.ifBlank { defaultUploadFilename() },
            mimeType = mimeType ?: defaultMimeType(),
        )
    }
    if (type == MessageAttachmentType.Voice) {
        val file = File(label)
        if (!file.exists() || !file.isFile) return null
        return AttachmentUploadPayload(
            bytes = file.readBytes(),
            filename = file.name.ifBlank { defaultUploadFilename() },
            mimeType = mimeType ?: "audio/mp4",
        )
    }
    return null
}

private fun MessageAttachment.defaultUploadFilename(): String = when (type) {
    MessageAttachmentType.Image -> "message-image.jpg"
    MessageAttachmentType.File -> "message-file.bin"
    MessageAttachmentType.Link -> "message-link.txt"
    MessageAttachmentType.Voice -> "voice-note.m4a"
}

private fun MessageAttachment.defaultMimeType(): String = when (type) {
    MessageAttachmentType.Image -> "image/jpeg"
    MessageAttachmentType.File -> "application/octet-stream"
    MessageAttachmentType.Link -> "text/plain"
    MessageAttachmentType.Voice -> "audio/mp4"
}

private fun String.toParticipantRole(): MessageParticipantRole = when (this) {
    "teacher" -> MessageParticipantRole.Teacher
    "parent" -> MessageParticipantRole.Parent
    else -> MessageParticipantRole.Student
}

private fun fallbackParticipant(role: String, name: String): ConversationParticipantDto =
    ConversationParticipantDto(userId = -1, name = name.ifBlank { "—" }, role = role)

private fun String?.toMillisOrNow(): Long =
    this?.let { raw -> runCatching { OffsetDateTime.parse(raw).toInstant().toEpochMilli() }.getOrNull() }
        ?: System.currentTimeMillis()

private fun String.toRelativeLabel(): String = if (isBlank()) "" else "الآن"

private fun String.avatarInitial(): String = trim().firstOrNull()?.toString().orEmpty().ifBlank { "؟" }

private fun String.toRemoteIdOrNull(): Int? =
    toIntOrNull()
        ?: substringAfter("course-", missingDelimiterValue = "").toIntOrNull()
