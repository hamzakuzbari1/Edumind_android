package com.rork.eduspark.data.model

data class ParentLinkedStudent(
    val id: String,
    val name: String,
    val email: String,
    val gradeLabel: String,
    val academicStatusLabel: String,
    val lastActivityLabel: String?,
)

data class ParentDashboard(
    val child: ParentLinkedStudent,
    val weeklySessions: Int,
    val weeklyQuizzes: Int,
    val averageScore: Int,
    val subjectsTracked: Int,
    val attendancePercentage: Int,
    val streakDays: Int,
    val completedSessions: Int,
    val missedSessions: Int,
    val courseProgress: List<ParentCourseProgress>,
    val insights: List<ParentInsight>,
    val recentActivity: List<ParentActivity>,
)

data class ParentCourseProgress(
    val courseId: String,
    val courseTitle: String,
    val subjectName: String,
    val completionPercentage: Float,
    val averageScore: Float?,
)

data class ParentInsight(
    val id: String,
    val text: String,
    val severity: String,
)

data class ParentActivity(
    val id: String,
    val title: String,
    val description: String?,
    val relativeTime: String,
)

data class ParentNoteReply(
    val id: String,
    val authorName: String,
    val authorRole: String,
    val body: String,
    val createdLabel: String,
)

data class ParentNote(
    val id: String,
    val studentId: String,
    val title: String,
    val description: String,
    val categoryLabel: String,
    val statusLabel: String,
    val priorityLabel: String,
    val teacherName: String,
    val createdLabel: String,
    val isRead: Boolean,
    val isClosed: Boolean,
    val canReply: Boolean,
    val replies: List<ParentNoteReply>,
)

data class ParentNotesFeed(
    val notes: List<ParentNote> = emptyList(),
    val unreadCount: Int = 0,
)
