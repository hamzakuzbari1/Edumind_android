package com.rork.eduspark.data.remote.teacher

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class ParentNoteListDto(
    val notes: List<ParentNoteDto> = emptyList(),
    val total: Int = 0,
    @SerialName("unread_count") val unreadCount: Int = 0,
)

@Serializable
internal data class ParentNoteDto(
    val id: Int,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String? = null,
    val title: String = "",
    val description: String = "",
    val category: String = "academic",
    @SerialName("category_label_ar") val categoryLabelAr: String = "",
    val status: String = "new",
    @SerialName("status_label_ar") val statusLabelAr: String = "",
    val priority: String = "medium",
    @SerialName("priority_label_ar") val priorityLabelAr: String = "",
    @SerialName("created_by_name") val createdByName: String = "",
    @SerialName("created_by_teacher_profile_id") val createdByTeacherProfileId: Int = 0,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
    @SerialName("reply_count") val replyCount: Int = 0,
    val replies: List<ParentNoteReplyDto> = emptyList(),
    @SerialName("is_closed") val isClosed: Boolean = false,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("can_reply") val canReply: Boolean = true,
    @SerialName("can_close") val canClose: Boolean = false,
)

@Serializable
internal data class ParentNoteReplyDto(
    val id: Int,
    @SerialName("note_id") val noteId: Int,
    @SerialName("author_id") val authorId: Int,
    @SerialName("author_name") val authorName: String = "",
    @SerialName("author_role") val authorRole: String = "teacher",
    val body: String = "",
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
)

@Serializable
internal data class ParentNoteCreateDto(
    val title: String,
    val description: String,
    val category: String = "academic",
    val priority: String = "medium",
)

@Serializable
internal data class ParentNoteReplyCreateDto(
    val body: String,
)
