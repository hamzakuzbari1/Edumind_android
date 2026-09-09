package com.rork.eduspark.data.model

/**
 * Parent-only linked student summary. It mirrors the existing mock student persona without
 * changing the student-side [StudentProfile] ownership boundary.
 */
data class ParentLinkedStudent(
    val id: String,
    val displayName: String,
    val gradeLabel: String,
    val sectionLabel: String,
    val schoolName: String,
    val avatarInitial: String,
    val statusLabel: String,
    val linkCode: String,
)

data class ParentDashboardSnapshot(
    val academicAveragePercent: Int,
    val lessonProgressPercent: Int,
    val studyHoursThisWeek: Float,
    val attendancePercent: Int,
    val plannerItemsDue: Int,
    val alertCount: Int,
    val recentActivities: List<ParentRecentActivity>,
)

data class ParentRecentActivity(
    val id: String,
    val type: ParentRecentActivityType,
)

enum class ParentRecentActivityType {
    QuizCompleted,
    LessonCompleted,
    PlannerMissed,
}

data class ParentPerformanceSnapshot(
    val testAveragePercent: Int,
    val subjectProgressPercent: Int,
    val improvementPercent: Int,
    val trend: ParentPerformanceTrend,
    val subjects: List<ParentSubjectPerformance>,
    val achievementSummary: ParentAchievementSummary,
)

data class ParentPerformanceTrend(
    val currentScores: List<Int>,
    val previousScores: List<Int>,
)

data class ParentSubjectPerformance(
    val id: String,
    val subject: ParentSubjectKind,
    val percent: Int,
    val status: ParentSubjectPerformanceStatus,
)

enum class ParentSubjectKind {
    Mathematics,
    Science,
    Arabic,
}

enum class ParentSubjectPerformanceStatus {
    Strong,
    NeedsAttention,
}

data class ParentAchievementSummary(
    val streakDays: Int,
    val badgeCount: Int,
    val level: Int,
)
