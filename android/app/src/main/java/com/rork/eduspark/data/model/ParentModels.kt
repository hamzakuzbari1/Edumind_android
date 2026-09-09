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

data class ParentAttendanceStudyTimeSnapshot(
    val period: ParentAttendancePeriod,
    val attendancePercent: Int,
    val studyHours: Float,
    val activeDays: Int,
    val averageSessionMinutes: Int,
    val dailyStudyMinutes: List<ParentDailyStudyTime>,
)

enum class ParentAttendancePeriod {
    ThisWeek,
    PreviousWeek,
    ThisMonth,
}

data class ParentDailyStudyTime(
    val day: ParentStudyDay,
    val minutes: Int,
    val isToday: Boolean,
)

enum class ParentStudyDay {
    Saturday,
    Sunday,
    Monday,
    Tuesday,
    Wednesday,
    Thursday,
    Friday,
}

data class ParentLessonProgressSnapshot(
    val completedLessons: Int,
    val totalLessons: Int,
    val lessons: List<ParentLessonProgressItem>,
)

data class ParentLessonProgressItem(
    val id: String,
    val topic: ParentLessonTopic,
    val subject: ParentSubjectKind,
    val status: ParentLessonProgressStatus,
    val progressPercent: Int,
    val completedActivities: Int,
    val totalActivities: Int,
)

enum class ParentLessonTopic {
    DecimalFractions,
    RespiratorySystem,
    ObjectPronoun,
}

enum class ParentLessonProgressStatus {
    Completed,
    InProgress,
}

enum class ParentLessonProgressFilter {
    All,
    InProgress,
    Completed,
}
