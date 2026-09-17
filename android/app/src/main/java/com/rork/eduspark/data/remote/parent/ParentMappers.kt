package com.rork.eduspark.data.remote.parent

import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentInsight
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNoteReply
import com.rork.eduspark.data.model.ParentNotesFeed
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.floatOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

internal fun ParentLinkedStudentDto.toDomain() = ParentLinkedStudent(
    id = id.toString(),
    name = name,
    email = email,
    gradeLabel = gradeLabel.ifBlank { grade?.let { "Grade $it" }.orEmpty() },
    academicStatusLabel = academicStatusLabel.ifBlank { academicStatus },
    lastActivityLabel = lastActivityAt,
)

internal fun ParentDashboardDto.toDomain(
    courseProgressOverride: List<ParentCourseProgress>? = null,
    activityOverride: List<ParentActivity>? = null,
    includeInsights: Boolean = false,
) = ParentDashboard(
    child = child.toDomain(),
    weeklySessions = stats.int("weekly_sessions"),
    weeklyQuizzes = stats.int("weekly_quizzes"),
    averageScore = stats.int("average_score"),
    subjectsTracked = stats.int("subjects_tracked"),
    attendancePercentage = attendance.attendancePercentage,
    streakDays = attendance.streakDays,
    completedSessions = attendance.completedSessions,
    missedSessions = attendance.missedSessions,
    courseProgress = courseProgressOverride ?: courseProgress.map(ParentCourseProgressDto::toDomain),
    // Insights / reports / notes / notifications stay for later parent batches.
    insights = if (includeInsights) insights.map(ParentInsightDto::toDomain) else emptyList(),
    recentActivity = activityOverride ?: activity.map(ParentActivityDto::toDomain),
)

internal fun ParentCourseProgressDto.toDomain() = ParentCourseProgress(
    courseId = courseId.toString(),
    courseTitle = courseTitle,
    subjectName = subjectName,
    completionPercentage = ((completionPercentage ?: 0f) / 100f).coerceIn(0f, 1f),
    averageScore = averageScore,
)

internal fun ParentInsightDto.toDomain() = ParentInsight(
    id = id,
    text = text,
    severity = severity,
)

internal fun ParentActivityDto.toDomain() = ParentActivity(
    id = id.toString(),
    title = title,
    description = description,
    relativeTime = relativeTime.ifBlank {
        createdAt?.take(16)?.replace('T', ' ').orEmpty()
    },
)

internal fun ParentNotesListDto.toDomain() = ParentNotesFeed(
    notes = notes.map(ParentViewerNoteDto::toDomain),
    unreadCount = unreadCount,
)

internal fun ParentViewerNoteDto.toDomain() = ParentNote(
    id = id.toString(),
    studentId = studentId.toString(),
    title = title,
    description = description,
    categoryLabel = categoryLabelAr.ifBlank { category },
    statusLabel = statusLabelAr.ifBlank { status },
    priorityLabel = priorityLabelAr.ifBlank { priority },
    teacherName = createdByName,
    createdLabel = formatParentTimestamp(createdAt),
    isRead = isReadByViewer,
    isClosed = isClosed || status == "closed",
    canReply = canReply && !isClosed && status != "closed",
    replies = replies.sortedBy { it.createdAt }.map(ParentViewerNoteReplyDto::toDomain),
)

internal fun ParentViewerNoteReplyDto.toDomain() = ParentNoteReply(
    id = id.toString(),
    authorName = authorName,
    authorRole = authorRole,
    body = body,
    createdLabel = formatParentTimestamp(createdAt),
)

internal fun formatParentTimestamp(raw: String): String {
    val value = raw.trim()
    if (value.isEmpty()) return ""
    return value.take(16).replace('T', ' ')
}

private fun JsonObject.int(key: String): Int =
    get(key)?.jsonPrimitive?.intOrNull
        ?: get(key)?.jsonPrimitive?.floatOrNull?.toInt()
        ?: 0
