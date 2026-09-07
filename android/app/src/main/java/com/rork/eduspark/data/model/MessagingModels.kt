package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-01 · Messages List / X-02 · Conversation Thread / X-03 · New Conversation — Phase 6.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One canonical MOCK messaging model, shared by Student and Teacher sessions alike — never a
 * per-screen fixture. [MessageParticipant] is a lightweight reference to an identity that
 * already exists elsewhere (the Teacher persona's own display name, a
 * [TeacherStudentSummary] roster row), never a second, duplicate person record.
 *
 * A thread has exactly two sides, always stored together — [teacherParticipant] and
 * [studentParticipant] (the non-teacher counterpart: a Student or a Parent). [otherParticipant]
 * derives the other side for whichever viewer is looking. Parent threads reuse this same
 * shape; [MessageParticipant.relatedStudentId] names the linked student when the counterpart
 * is a Parent.
 */
enum class MessageParticipantRole { Student, Teacher, Parent }

data class MessageParticipant(
    val id: String,
    val displayName: String,
    val role: MessageParticipantRole,
    val avatarInitial: String,
    val contextLabel: String = "",
    /** Set on Parent participants — the linked student id (e.g. ريم = `s1`). */
    val relatedStudentId: String? = null,
)

enum class MessageAttachmentType { Image, File, Link, Voice }

/**
 * [label] holds a filename/URL for Image/File/Link, and the local recording's file path/URI
 * for [MessageAttachmentType.Voice] — same field, no second "voice URI" property, since only
 * one of the two meanings is ever relevant for a given [type]. [durationSeconds] is Voice-only
 * and stays null for every other type — purely additive, so no existing Image/File/Link call
 * site needs to change.
 */
data class MessageAttachment(
    val type: MessageAttachmentType,
    val label: String,
    val durationSeconds: Int? = null,
)

data class MessagingChatMessage(
    val id: String,
    val senderId: String,
    val body: String,
    val sentAtLabel: String,
    val sentAtMillis: Long,
    val isRead: Boolean = false,
    val attachment: MessageAttachment? = null,
)

data class MessageThread(
    val id: String,
    val teacherParticipant: MessageParticipant,
    val studentParticipant: MessageParticipant,
    val messages: List<MessagingChatMessage> = emptyList(),
) {
    val lastMessage: MessagingChatMessage? get() = messages.maxByOrNull { it.sentAtMillis }

    fun involves(participantId: String): Boolean =
        teacherParticipant.id == participantId || studentParticipant.id == participantId

    fun otherParticipant(viewerId: String): MessageParticipant =
        if (teacherParticipant.id == viewerId) studentParticipant else teacherParticipant

    fun unreadCountFor(viewerId: String): Int =
        messages.count { !it.isRead && it.senderId != viewerId }

    val isParentThread: Boolean get() = studentParticipant.role == MessageParticipantRole.Parent
}

/**
 * The app has exactly one signed-in Student fixture persona ("mock-student" — see
 * [com.rork.eduspark.data.repository.mock.MockAuthRepository]), and that persona already
 * reuses "ريم الحلبي" / avatar initial "ر" verbatim as its profile
 * (see [com.rork.eduspark.data.repository.mock.MockProfileRepository]) — the exact same
 * name/avatar as Teacher roster entry `"s1"`. There is no id-level link between the two
 * fixture spaces anywhere else in the codebase (Student Core and Teacher Core were built as
 * separate phases), so Messaging resolves the current Student session onto this existing,
 * evidence-based identity match rather than inventing a new one or leaving them unlinked.
 */
const val CURRENT_STUDENT_MESSAGING_ID = "s1"
