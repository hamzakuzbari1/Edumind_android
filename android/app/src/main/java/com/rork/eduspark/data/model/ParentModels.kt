package com.rork.eduspark.data.model

data class ParentLinkedStudent(
    val id: String,
    val name: String,
    val email: String,
    val gradeLabel: String,
    val academicStatusLabel: String,
    val lastActivityLabel: String?,
) {
    val displayName: String get() = name
    val statusLabel: String get() = academicStatusLabel
    val avatarInitial: String get() = name.trim().firstOrNull()?.toString().orEmpty()
}

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

data class ParentLinkedStudentRequest(
    val code: String,
)

data class ParentMetric(
    val label: String,
    val value: String,
    val supporting: String = "",
)

data class ParentActionItem(
    val id: String,
    val title: String,
    val subtitle: String = "",
    val value: String = "",
    val status: String = "",
)

data class ParentFeatureSnapshot(
    val title: String,
    val subtitle: String,
    val metrics: List<ParentMetric> = emptyList(),
    val items: List<ParentActionItem> = emptyList(),
)

/**
 * PR-02 home summary. Every number is a backend value; [hasAttendanceData] and
 * [hasAcademicData] let the screen show an honest "no data yet" state instead of a zero.
 */
data class ParentDashboardSnapshot(
    val academicAveragePercent: Int,
    val lessonProgressPercent: Int,
    val studyHoursThisWeek: Float,
    val attendancePercent: Int,
    val plannerItemsDue: Int,
    val alertCount: Int,
    val hasAttendanceData: Boolean,
    val hasAcademicData: Boolean,
    val recentActivities: List<ParentActivity> = emptyList(),
    val latestTeacherNote: ParentNote? = null,
    val latestInsightText: String? = null,
)

data class ParentPerformanceSnapshot(
    val testAveragePercent: Int,
    val subjectProgressPercent: Int,
    val improvementPercent: Int,
    val hasImprovementData: Boolean,
    val summary: String,
    val periodLabel: String,
    val trend: ParentPerformanceTrend?,
    val subjects: List<ParentSubjectPerformance> = emptyList(),
    val recentQuizzes: List<ParentQuizResult> = emptyList(),
    val achievements: ParentAchievementSummary?,
)

data class ParentQuizResult(
    val id: String,
    val title: String,
    val subject: String,
    val scorePercent: Int,
    val dateLabel: String,
)

data class ParentPerformanceTrend(
    val currentScores: List<Int>,
    val previousScores: List<Int>,
)

data class ParentSubjectPerformance(
    val id: String,
    val subjectName: String,
    val percent: Int,
    val statusLabel: String,
    val isStrong: Boolean,
)

data class ParentAchievementSummary(
    val streakDays: Int,
    val badgeCount: Int,
    val level: Int,
    val totalXp: Int? = null,
    val namedAchievements: List<ParentNamedAchievement> = emptyList(),
)

data class ParentNamedAchievement(
    val key: String,
    val title: String,
    val description: String,
    val unlockedAtLabel: String,
)

data class ParentAttendanceStudyTimeSnapshot(
    val attendancePercent: Int,
    val studyHours: Float,
    val activeDays: Int,
    val averageSessionMinutes: Int,
    val consistencyPercent: Int,
    val hasData: Boolean,
    val hasStudyTimeAnalytics: Boolean,
    val dailyStudyMinutes: List<ParentDailyStudyTime> = emptyList(),
    val studyTimeAverages: ParentStudyTimeAverages = ParentStudyTimeAverages(),
    val weeklyPeriodLabel: String = "",
    val weeklyComparisonPercent: Float? = null,
    val monthlyPeriodLabel: String = "",
    val monthlyComparisonPercent: Float? = null,
    val monthlyStudyWeeks: List<ParentMonthlyStudyWeek> = emptyList(),
    val monthlyAttendance: List<ParentAttendanceMonthWeek> = emptyList(),
    val consistencyWeeks: List<ParentAttendanceConsistencyWeek> = emptyList(),
    val statusBreakdown: ParentAttendanceStatusBreakdown = ParentAttendanceStatusBreakdown(),
    val aiInsights: List<String> = emptyList(),
    val loginSessions: List<ParentLoginSession> = emptyList(),
)

data class ParentDailyStudyTime(
    val dayLabel: String,
    val minutes: Int,
    val isToday: Boolean,
)

data class ParentStudyTimeAverages(
    val dailyHours: Float = 0f,
    val weeklyHours: Float = 0f,
    val monthlyHours: Float = 0f,
    val dailyTrendPercent: Float? = null,
    val weeklyTrendPercent: Float? = null,
    val monthlyTrendPercent: Float? = null,
) {
    val hasValues: Boolean
        get() = dailyHours > 0f ||
            weeklyHours > 0f ||
            monthlyHours > 0f ||
            dailyTrendPercent != null ||
            weeklyTrendPercent != null ||
            monthlyTrendPercent != null
}

data class ParentMonthlyStudyWeek(
    val weekIndex: Int,
    val minutes: Int,
)

data class ParentAttendanceMonthWeek(
    val label: String,
    val consistencyPercent: Int,
    val presentDays: Int,
    val partialDays: Int,
    val absentDays: Int,
)

data class ParentAttendanceConsistencyWeek(
    val label: String,
    val consistencyPercent: Int,
    val presentDays: Int,
    val totalDays: Int,
)

data class ParentAttendanceStatusBreakdown(
    val presentDays: Int = 0,
    val partialDays: Int = 0,
    val absentDays: Int = 0,
) {
    val totalDays: Int get() = presentDays + partialDays + absentDays
    val hasValues: Boolean get() = totalDays > 0
}

data class ParentLoginSession(
    val id: String,
    val dateLabel: String,
    val loginLabel: String,
    val logoutLabel: String?,
    val durationMinutes: Int,
    val isOpen: Boolean,
    val logoutReason: String?,
)

data class ParentLessonProgressSnapshot(
    val completedLessons: Int,
    val totalLessons: Int,
    val lessons: List<ParentLessonProgressItem> = emptyList(),
)

data class ParentLessonProgressItem(
    val id: String,
    val title: String,
    val subjectName: String,
    val courseTitle: String,
    val statusLabel: String,
    val isCompleted: Boolean,
    val progressPercent: Int,
    val teacherName: String,
    val lastActivityLabel: String,
)

enum class ParentLessonProgressFilter { All, InProgress, Completed }

data class ParentLessonDetails(
    val lessonId: String,
    val title: String,
    val courseTitle: String,
    val subjectName: String,
    val teacherName: String,
    val statusLabel: String,
    val completionPercent: Int,
    val videoPercent: Int,
    val quizScorePercent: Int,
    val pagesViewed: Int,
    val totalPages: Int,
    val requirementsCompleted: Int,
    val requirementsTotal: Int,
    val missingRequirements: Int,
    val checklist: List<ParentLessonVerificationItem> = emptyList(),
    val timeline: List<ParentLessonActivityEvent> = emptyList(),
)

data class ParentLessonVerificationItem(
    val id: String,
    val label: String,
    val isComplete: Boolean,
)

data class ParentLessonActivityEvent(
    val id: String,
    val label: String,
    val timeLabel: String,
)

data class ParentSubjectsTeachersSnapshot(
    val items: List<ParentSubjectTeacher> = emptyList(),
)

data class ParentSubjectTeacher(
    val id: String,
    val courseId: String,
    val subjectName: String,
    val courseTitle: String,
    val teacherName: String,
    val progressPercent: Int,
    val statusLabel: String,
    val isOnTrack: Boolean,
    val lessonCount: Int,
    val completedLessonCount: Int,
    val enrolled: Boolean,
    val threadId: String?,
    val unreadCount: Int,
) {
    val teacherInitial: String get() = teacherName.trim().firstOrNull()?.toString().orEmpty()
}

data class ParentPlannerSnapshot(
    val commitmentPercent: Int,
    val completedSessions: Int,
    val totalSessions: Int,
    val postponedSessions: Int,
    val summary: String,
    val consistencyLabel: String,
    val sessions: List<ParentPlannerSession> = emptyList(),
    val subjectBreakdown: List<ParentPlannerSubjectCommitment> = emptyList(),
    val todayLabel: String = "",
    val todayRoutine: List<ParentRoutineSlot> = emptyList(),
)

data class ParentRoutineSlot(
    val start: String,
    val end: String,
    val title: String,
    val subject: String?,
    val statusLabel: String,
    val status: ParentPlannerSessionStatus,
    val durationMinutes: Int? = null,
) {
    val timeLabel: String
        get() = listOf(start, end).map { it.trim() }.filter { it.isNotBlank() }.distinct().let { parts ->
            when {
                parts.size >= 2 -> "${parts[0]} – ${parts[1]}"
                parts.size == 1 -> parts[0]
                else -> ""
            }
        }
}

data class ParentPlannerSession(
    val id: String,
    val subjectName: String,
    val taskName: String,
    val timeLabel: String,
    val statusLabel: String,
    val status: ParentPlannerSessionStatus,
)

enum class ParentPlannerSessionStatus { Completed, Planned, Missed }

data class ParentPlannerSubjectCommitment(
    val subjectName: String,
    val adherencePercent: Int,
    val completedCount: Int,
    val totalCount: Int,
)

data class ParentAlertsSnapshot(
    val unreadCount: Int,
    val alerts: List<ParentAlert> = emptyList(),
    val preferences: List<ParentAlertPreference> = emptyList(),
)

data class ParentAlert(
    val id: String,
    val title: String,
    val body: String,
    val categoryLabel: String,
    val timeLabel: String,
    val severity: ParentAlertSeverity,
    val isUnread: Boolean,
)

enum class ParentAlertSeverity { Important, Success, Info }

/** The seven alert switches the backend actually stores on `/api/parent/notification-settings`. */
enum class ParentAlertPreferenceKey { Login, Logout, Lesson, Quiz, LowScore, Inactivity, Planner }

data class ParentAlertPreference(
    val key: ParentAlertPreferenceKey,
    val enabled: Boolean,
)

data class ParentAiInsightsSnapshot(
    val summary: String,
    val performanceLabel: String,
    val overallAveragePercent: Int?,
    val hasData: Boolean = false,
    val summaryLines: List<String> = emptyList(),
    val weeklySnapshot: ParentExecutiveWeeklySnapshot = ParentExecutiveWeeklySnapshot(),
    val periodLabel: String = "",
    val periodComparison: List<ParentExecutiveComparisonMetric> = emptyList(),
    val studyTimeAverages: ParentStudyTimeAverages = ParentStudyTimeAverages(),
    val insights: List<ParentInsight> = emptyList(),
    val subjectInsights: List<ParentSubjectInsight> = emptyList(),
    val strengthAnalysis: ParentExecutiveSubjectAnalysis? = null,
    val weaknessAnalysis: ParentExecutiveSubjectAnalysis? = null,
    val riskInsights: List<ParentInsight> = emptyList(),
    val recommendations: List<ParentInsight> = emptyList(),
    val behavior: ParentStudyBehaviorInsight?,
)

data class ParentExecutiveWeeklySnapshot(
    val lessonsCompleted: Int = 0,
    val studyHours: Float = 0f,
    val averageQuizScore: Int? = null,
    val plannerAdherencePercent: Int? = null,
    val missedPlannerTasks: Int = 0,
    val strongestSubject: String? = null,
    val weakestSubject: String? = null,
)

data class ParentExecutiveComparisonMetric(
    val label: String,
    val currentValue: Float,
    val previousValue: Float,
    val changePercent: Float?,
    val unit: String,
)

data class ParentExecutiveSubjectAnalysis(
    val subjectName: String,
    val reasons: List<String> = emptyList(),
    val averageScorePercent: Int? = null,
    val studyMinutes: Int = 0,
)

data class ParentSubjectInsight(
    val id: String,
    val subjectName: String,
    val statusLabel: String,
    val isStrength: Boolean,
    val quizAveragePercent: Int?,
    val completionPercent: Int?,
)

data class ParentStudyBehaviorInsight(
    val averageSessionMinutes: Int?,
    val consistencyDays: Int,
    val consistencyTotalDays: Int,
    val studyHours: Float,
    val averageDailyStudyHours: Float = 0f,
    val preferredStudyHoursLabel: String? = null,
    val consistencyLabel: String = "",
)

data class ParentReportsSnapshot(
    val periodLabel: String,
    val startDate: String,
    val endDate: String,
    val academicAveragePercent: Int,
    val completedLessons: Int,
    val studyHours: Float,
    val hasData: Boolean,
    val trend: List<ParentReportTrendPoint> = emptyList(),
    val comparison: List<ParentReportComparisonMetric> = emptyList(),
    val weeklyLessonHistory: List<ParentReportTrendPoint> = emptyList(),
    val monthlyLessonHistory: List<ParentReportTrendPoint> = emptyList(),
    val loginSessions: List<ParentLoginSession> = emptyList(),
    val plannerAdherenceHistory: List<ParentReportTrendPoint> = emptyList(),
    val missedLateTaskHistory: List<ParentReportTrendPoint> = emptyList(),
    val averagePlannerAdherence: Float = 0f,
    val totalMissedLateTasks: Int = 0,
)

data class ParentReportTrendPoint(
    val label: String,
    val value: Float,
)

data class ParentReportComparisonMetric(
    val key: ParentReportMetricKey,
    val currentValue: Float,
    val previousValue: Float,
    val changePercent: Float?,
)

enum class ParentReportMetricKey { StudyTime, Grades, LessonCompletion, PlannerAdherence }

/** Mirrors the `period` values `/api/parent/historical-report` accepts. */
enum class ParentReportPeriod(val apiValue: String) {
    ThisWeek("this_week"),
    LastWeek("last_week"),
    ThisMonth("this_month"),
    LastMonth("last_month"),
    Custom("custom"),
}

/** Formats accepted by `GET /api/parent/historical-report/export`. */
enum class ParentReportExportFormat(val apiValue: String, val mimeType: String) {
    Pdf("pdf", "application/pdf"),
    Csv("csv", "text/csv"),
    Xlsx("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}

data class ParentReportDateRange(
    val startDateMillis: Long,
    val endDateMillis: Long,
)

/** Binary payload from `GET /api/parent/historical-report/export`. */
data class ParentReportExport(
    val bytes: ByteArray,
    val filename: String,
    val mimeType: String,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ParentReportExport) return false
        return filename == other.filename && mimeType == other.mimeType && bytes.contentEquals(other.bytes)
    }

    override fun hashCode(): Int {
        var result = bytes.contentHashCode()
        result = 31 * result + filename.hashCode()
        result = 31 * result + mimeType.hashCode()
        return result
    }
}
