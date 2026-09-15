package com.rork.eduspark.data.remote.parent

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
internal data class ParentLinkedStudentDto(
    val id: Int,
    val name: String,
    val email: String,
    val grade: Int? = null,
    @SerialName("grade_label") val gradeLabel: String = "",
    @SerialName("academic_status") val academicStatus: String = "inactive",
    @SerialName("academic_status_label") val academicStatusLabel: String = "",
    @SerialName("last_activity_at") val lastActivityAt: String? = null,
)

@Serializable
internal data class ParentDashboardDto(
    val child: ParentLinkedStudentDto,
    val activity: List<ParentActivityDto> = emptyList(),
    val insights: List<ParentInsightDto> = emptyList(),
    val stats: JsonObject = JsonObject(emptyMap()),
    val attendance: JsonObject = JsonObject(emptyMap()),
    @SerialName("course_progress") val courseProgress: List<ParentCourseProgressDto> = emptyList(),
)

@Serializable
internal data class ParentCourseProgressDto(
    @SerialName("course_id") val courseId: Int,
    @SerialName("course_title") val courseTitle: String,
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("average_score") val averageScore: Float? = null,
    @SerialName("attendance_percentage") val attendancePercentage: Float? = null,
    @SerialName("completion_percentage") val completionPercentage: Float? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
internal data class ParentInsightDto(
    val id: String,
    val text: String,
    val severity: String = "info",
)

@Serializable
internal data class ParentActivityDto(
    val id: Int,
    @SerialName("event_type") val eventType: String,
    val title: String,
    val description: String? = null,
    @SerialName("relative_time") val relativeTime: String = "",
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
internal data class ParentNotesListDto(
    val notes: List<ParentViewerNoteDto> = emptyList(),
    val total: Int = 0,
    @SerialName("unread_count") val unreadCount: Int = 0,
)

@Serializable
internal data class ParentViewerNoteDto(
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
    @SerialName("is_read_by_viewer") val isReadByViewer: Boolean = false,
    @SerialName("read_at_by_viewer") val readAtByViewer: String? = null,
    @SerialName("reply_count") val replyCount: Int = 0,
    val replies: List<ParentViewerNoteReplyDto> = emptyList(),
    @SerialName("is_closed") val isClosed: Boolean = false,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("can_reply") val canReply: Boolean = true,
)

@Serializable
internal data class ParentViewerNoteReplyDto(
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
internal data class ParentViewerNoteReplyCreateDto(
    val body: String,
)
