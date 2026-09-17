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
    val attendance: ParentAttendanceSummaryDto = ParentAttendanceSummaryDto(),
    @SerialName("course_progress") val courseProgress: List<ParentCourseProgressDto> = emptyList(),
    val planner: ParentPlannerVisibilityDto = ParentPlannerVisibilityDto(),
    val gamification: ParentGamificationDto? = null,
    @SerialName("academic_intelligence") val academicIntelligence: ParentAcademicIntelligenceDto? = null,
    @SerialName("lesson_progress") val lessonProgress: ParentLessonProgressDto? = null,
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

@Serializable
internal data class ParentLinkStudentRequestDto(
    @SerialName("link_code") val linkCode: String,
)

@Serializable
internal data class ParentLinkStudentResponseDto(
    val ok: Boolean = true,
    @SerialName("student_id") val studentId: Int,
)

// ── Typed payloads for the read-only parent monitoring endpoints ──────────

@Serializable
internal data class ParentAttendanceDayDto(
    val date: String = "",
    @SerialName("day_label") val dayLabel: String = "",
    val status: String = "",
    @SerialName("study_minutes") val studyMinutes: Int = 0,
    @SerialName("consistency_score") val consistencyScore: Int = 0,
    val active: Boolean = false,
)

@Serializable
internal data class ParentAttendanceMonthWeekDto(
    @SerialName("week_index") val weekIndex: Int = 0,
    val label: String = "",
    val consistency: Int = 0,
    val present: Int = 0,
    val absent: Int = 0,
    val partial: Int = 0,
)

@Serializable
internal data class ParentAttendanceConsistencyWeekDto(
    @SerialName("week_label") val weekLabel: String = "",
    val consistency: Int = 0,
    @SerialName("present_days") val presentDays: Int = 0,
    @SerialName("total_days") val totalDays: Int = 7,
)

@Serializable
internal data class ParentAttendanceAlertDto(
    val type: String = "",
    val text: String = "",
)

@Serializable
internal data class ParentAttendanceRecordDto(
    val id: Int = 0,
    @SerialName("student_id") val studentId: Int = 0,
    val date: String = "",
    val status: String = "",
    @SerialName("study_minutes") val studyMinutes: Int = 0,
    @SerialName("consistency_score") val consistencyScore: Int = 0,
    val notes: String? = null,
    @SerialName("day_label") val dayLabel: String = "",
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
internal data class ParentAttendanceSummaryDto(
    @SerialName("attendance_percentage") val attendancePercentage: Int = 0,
    @SerialName("weekly_consistency") val weeklyConsistency: Int = 0,
    @SerialName("streak_days") val streakDays: Int = 0,
    @SerialName("inactive_days") val inactiveDays: Int = 0,
    @SerialName("completed_sessions") val completedSessions: Int = 0,
    @SerialName("missed_sessions") val missedSessions: Int = 0,
    @SerialName("partial_days") val partialDays: Int = 0,
    @SerialName("total_study_minutes_week") val totalStudyMinutesWeek: Int = 0,
    @SerialName("weekly_calendar") val weeklyCalendar: List<ParentAttendanceDayDto> = emptyList(),
    @SerialName("monthly_overview") val monthlyOverview: List<ParentAttendanceMonthWeekDto> = emptyList(),
    @SerialName("consistency_bars") val consistencyBars: List<ParentAttendanceConsistencyWeekDto> = emptyList(),
    val alerts: List<ParentAttendanceAlertDto> = emptyList(),
    @SerialName("ai_insights") val aiInsights: List<String> = emptyList(),
    @SerialName("recent_records") val recentRecords: List<ParentAttendanceRecordDto> = emptyList(),
)

@Serializable
internal data class ParentStudyTimeAveragesDto(
    @SerialName("daily_hours") val dailyHours: Float = 0f,
    @SerialName("weekly_hours") val weeklyHours: Float = 0f,
    @SerialName("monthly_hours") val monthlyHours: Float = 0f,
    @SerialName("daily_trend_percent") val dailyTrendPercent: Float? = null,
    @SerialName("weekly_trend_percent") val weeklyTrendPercent: Float? = null,
    @SerialName("monthly_trend_percent") val monthlyTrendPercent: Float? = null,
)

@Serializable
internal data class ParentStudyTimeOverviewDto(
    @SerialName("today_minutes") val todayMinutes: Int = 0,
    @SerialName("week_minutes") val weekMinutes: Int = 0,
    @SerialName("month_minutes") val monthMinutes: Int = 0,
    @SerialName("last_activity_at") val lastActivityAt: String? = null,
    @SerialName("week_comparison_percent") val weekComparisonPercent: Float? = null,
    @SerialName("month_comparison_percent") val monthComparisonPercent: Float? = null,
    val averages: ParentStudyTimeAveragesDto = ParentStudyTimeAveragesDto(),
)

@Serializable
internal data class ParentDailyStudyDto(
    val date: String = "",
    @SerialName("day_label") val dayLabel: String = "",
    @SerialName("study_minutes") val studyMinutes: Int = 0,
)

@Serializable
internal data class ParentWeeklyStudyAnalyticsDto(
    @SerialName("period_label") val periodLabel: String = "",
    @SerialName("total_minutes") val totalMinutes: Int = 0,
    @SerialName("daily_average_minutes") val dailyAverageMinutes: Float = 0f,
    @SerialName("most_active_day") val mostActiveDay: ParentDailyStudyDto? = null,
    @SerialName("least_active_day") val leastActiveDay: ParentDailyStudyDto? = null,
    @SerialName("comparison_percent") val comparisonPercent: Float? = null,
    @SerialName("active_days_count") val activeDaysCount: Int = 0,
)

@Serializable
internal data class ParentMonthlyStudyWeekDto(
    @SerialName("week_index") val weekIndex: Int = 0,
    @SerialName("study_minutes") val studyMinutes: Int = 0,
)

@Serializable
internal data class ParentMonthlyStudyAnalyticsDto(
    @SerialName("period_label") val periodLabel: String = "",
    @SerialName("total_minutes") val totalMinutes: Int = 0,
    @SerialName("weekly_average_minutes") val weeklyAverageMinutes: Float = 0f,
    @SerialName("comparison_percent") val comparisonPercent: Float? = null,
    val trend: String = "flat",
    val weeks: List<ParentMonthlyStudyWeekDto> = emptyList(),
    @SerialName("daily_breakdown") val dailyBreakdown: List<ParentDailyStudyDto> = emptyList(),
)

@Serializable
internal data class ParentLoginHistoryRowDto(
    val id: Int = 0,
    val date: String? = null,
    @SerialName("day_label") val dayLabel: String? = null,
    @SerialName("login_at") val loginAt: String? = null,
    @SerialName("logout_at") val logoutAt: String? = null,
    @SerialName("logout_reason") val logoutReason: String? = null,
    @SerialName("active_minutes") val activeMinutes: Int = 0,
    @SerialName("is_open") val isOpen: Boolean = false,
)

@Serializable
internal data class ParentAttendanceAnalyticsDto(
    val overview: ParentStudyTimeOverviewDto = ParentStudyTimeOverviewDto(),
    @SerialName("week_offset") val weekOffset: Int = 0,
    @SerialName("month_offset") val monthOffset: Int = 0,
    @SerialName("daily_breakdown") val dailyBreakdown: List<ParentDailyStudyDto> = emptyList(),
    @SerialName("weekly_analytics") val weeklyAnalytics: ParentWeeklyStudyAnalyticsDto =
        ParentWeeklyStudyAnalyticsDto(),
    @SerialName("monthly_analytics") val monthlyAnalytics: ParentMonthlyStudyAnalyticsDto =
        ParentMonthlyStudyAnalyticsDto(),
    @SerialName("login_history") val loginHistory: List<ParentLoginHistoryRowDto> = emptyList(),
)

@Serializable
internal data class ParentActivitySessionDto(
    val id: Int = 0,
    @SerialName("login_at") val loginAt: String? = null,
    @SerialName("logout_at") val logoutAt: String? = null,
    @SerialName("logout_reason") val logoutReason: String? = null,
    @SerialName("active_minutes") val activeMinutes: Int = 0,
    @SerialName("auth_session_id") val authSessionId: Int? = null,
)

@Serializable
internal data class ParentActivityTrackingSummaryDto(
    @SerialName("last_activity_at") val lastActivityAt: String? = null,
    @SerialName("active_session_id") val activeSessionId: Int? = null,
    @SerialName("session_login_at") val sessionLoginAt: String? = null,
    @SerialName("session_active_minutes") val sessionActiveMinutes: Int = 0,
    @SerialName("today_active_minutes") val todayActiveMinutes: Int = 0,
    @SerialName("week_active_minutes") val weekActiveMinutes: Int = 0,
    @SerialName("inactivity_threshold_minutes") val inactivityThresholdMinutes: Int = 15,
)

@Serializable
internal data class ParentPlannerTaskDto(
    val id: Int = 0,
    val subject: String = "",
    @SerialName("task_name") val taskName: String = "",
    @SerialName("planned_at") val plannedAt: String? = null,
    @SerialName("completed_at") val completedAt: String? = null,
    val status: String = "planned",
    @SerialName("status_label") val statusLabel: String = "",
    @SerialName("duration_minutes") val durationMinutes: Int = 0,
    @SerialName("is_overdue") val isOverdue: Boolean = false,
)

@Serializable
internal data class ParentPlannerCommitmentDto(
    @SerialName("adherence_rate") val adherenceRate: Int = 0,
    @SerialName("completed_count") val completedCount: Int = 0,
    @SerialName("total_due_count") val totalDueCount: Int = 0,
    @SerialName("missed_count") val missedCount: Int = 0,
    @SerialName("pending_count") val pendingCount: Int = 0,
    @SerialName("overdue_count") val overdueCount: Int = 0,
)

@Serializable
internal data class ParentPlannerSubjectCommitmentDto(
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("adherence_percent") val adherencePercent: Int = 0,
    @SerialName("completed_count") val completedCount: Int = 0,
    @SerialName("total_count") val totalCount: Int = 0,
)

@Serializable
internal data class ParentPlannerConsistencyDto(
    @SerialName("active_days") val activeDays: Int = 0,
    @SerialName("total_days") val totalDays: Int = 7,
    val label: String = "",
)

@Serializable
internal data class ParentPlannerVisibilityDto(
    val summary: String = "",
    @SerialName("plan_active") val planActive: Boolean = false,
    @SerialName("today_plan") val todayPlan: List<ParentPlannerTaskDto> = emptyList(),
    @SerialName("upcoming_tasks") val upcomingTasks: List<ParentPlannerTaskDto> = emptyList(),
    @SerialName("completed_tasks") val completedTasks: List<ParentPlannerTaskDto> = emptyList(),
    @SerialName("missed_tasks") val missedTasks: List<ParentPlannerTaskDto> = emptyList(),
    @SerialName("overdue_tasks") val overdueTasks: List<ParentPlannerTaskDto> = emptyList(),
    val commitment: ParentPlannerCommitmentDto = ParentPlannerCommitmentDto(),
    @SerialName("subject_breakdown") val subjectBreakdown: List<ParentPlannerSubjectCommitmentDto> = emptyList(),
    @SerialName("weekly_consistency") val weeklyConsistency: ParentPlannerConsistencyDto = ParentPlannerConsistencyDto(),
)

@Serializable
internal data class ParentLessonProgressItemDto(
    @SerialName("lesson_id") val lessonId: Int,
    @SerialName("lesson_title") val lessonTitle: String = "",
    @SerialName("course_id") val courseId: Int = 0,
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("subject_name") val subjectName: String = "",
    val status: String = "",
    @SerialName("status_label") val statusLabel: String = "",
    @SerialName("completion_percent") val completionPercent: Int = 0,
    @SerialName("is_verified") val isVerified: Boolean = false,
    @SerialName("completed_at") val completedAt: String? = null,
    @SerialName("last_activity_at") val lastActivityAt: String? = null,
    @SerialName("teacher_name") val teacherName: String? = null,
)

@Serializable
internal data class ParentCourseLessonProgressDto(
    @SerialName("course_id") val courseId: Int = 0,
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("progress_percent") val progressPercent: Int = 0,
    val lessons: List<ParentLessonProgressItemDto> = emptyList(),
)

@Serializable
internal data class ParentLessonProgressSummaryDto(
    @SerialName("completed_lessons") val completedLessons: Int = 0,
    @SerialName("in_progress_lessons") val inProgressLessons: Int = 0,
    @SerialName("pending_lessons") val pendingLessons: Int = 0,
    @SerialName("total_lessons") val totalLessons: Int = 0,
    @SerialName("completion_rate") val completionRate: Int = 0,
)

@Serializable
internal data class ParentLessonProgressDto(
    @SerialName("student_id") val studentId: Int = 0,
    val courses: List<ParentCourseLessonProgressDto> = emptyList(),
    val summary: ParentLessonProgressSummaryDto = ParentLessonProgressSummaryDto(),
)

@Serializable
internal data class ParentChecklistItemDto(
    val key: String = "",
    val label: String = "",
    val met: Boolean = false,
    val required: Boolean = true,
)

@Serializable
internal data class ParentLessonTimelineItemDto(
    val date: String = "",
    val datetime: String? = null,
    val label: String = "",
)

@Serializable
internal data class ParentLessonDetailDto(
    @SerialName("lesson_id") val lessonId: Int,
    @SerialName("lesson_title") val lessonTitle: String = "",
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("teacher_name") val teacherName: String = "",
    @SerialName("video_progress_percent") val videoProgressPercent: Float = 0f,
    @SerialName("pdf_progress_percent") val pdfProgressPercent: Float = 0f,
    @SerialName("pdf_total_pages") val pdfTotalPages: Int? = null,
    @SerialName("pdf_pages_viewed") val pdfPagesViewed: Int? = null,
    @SerialName("quiz_score_percent") val quizScorePercent: Float = 0f,
    @SerialName("completion_status") val completionStatus: String = "",
    @SerialName("verification_status_label") val verificationStatusLabel: String = "",
    @SerialName("completion_percent") val completionPercent: Int = 0,
    val checklist: List<ParentChecklistItemDto> = emptyList(),
    @SerialName("missing_requirements") val missingRequirements: List<String> = emptyList(),
    val timeline: List<ParentLessonTimelineItemDto> = emptyList(),
)

@Serializable
internal data class ParentSubjectCourseDto(
    @SerialName("subject_id") val subjectId: Int = 0,
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("course_id") val courseId: Int = 0,
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("teacher_name") val teacherName: String = "",
    val enrolled: Boolean = false,
    @SerialName("subscription_status") val subscriptionStatus: String = "pending",
    @SerialName("progress_percent") val progressPercent: Int = 0,
    @SerialName("lesson_count") val lessonCount: Int = 0,
    @SerialName("completed_lesson_count") val completedLessonCount: Int = 0,
    @SerialName("thread_id") val threadId: Int? = null,
    @SerialName("unread_count") val unreadCount: Int = 0,
)

@Serializable
internal data class ParentSubjectsTeachersDto(
    @SerialName("student_id") val studentId: Int = 0,
    val enrolled: List<ParentSubjectCourseDto> = emptyList(),
    val available: List<ParentSubjectCourseDto> = emptyList(),
)

@Serializable
internal data class ParentNotificationDto(
    val id: Int,
    val type: String = "",
    val category: String = "",
    @SerialName("category_label") val categoryLabel: String = "",
    val title: String = "",
    val body: String = "",
    @SerialName("is_read") val isRead: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
internal data class ParentNotificationListDto(
    val items: List<ParentNotificationDto> = emptyList(),
    @SerialName("unread_count") val unreadCount: Int = 0,
)

@Serializable
internal data class ParentNotificationSettingsDto(
    @SerialName("student_id") val studentId: Int = 0,
    @SerialName("login_alerts") val loginAlerts: Boolean = true,
    @SerialName("logout_alerts") val logoutAlerts: Boolean = true,
    @SerialName("lesson_alerts") val lessonAlerts: Boolean = true,
    @SerialName("quiz_alerts") val quizAlerts: Boolean = true,
    @SerialName("low_score_alerts") val lowScoreAlerts: Boolean = true,
    @SerialName("inactivity_alerts") val inactivityAlerts: Boolean = true,
    @SerialName("planner_alerts") val plannerAlerts: Boolean = true,
)

@Serializable
internal data class ParentNotificationSettingsUpdateDto(
    @SerialName("login_alerts") val loginAlerts: Boolean? = null,
    @SerialName("logout_alerts") val logoutAlerts: Boolean? = null,
    @SerialName("lesson_alerts") val lessonAlerts: Boolean? = null,
    @SerialName("quiz_alerts") val quizAlerts: Boolean? = null,
    @SerialName("low_score_alerts") val lowScoreAlerts: Boolean? = null,
    @SerialName("inactivity_alerts") val inactivityAlerts: Boolean? = null,
    @SerialName("planner_alerts") val plannerAlerts: Boolean? = null,
)

@Serializable
internal data class ParentSubjectAcademicDto(
    @SerialName("subject_name") val subjectName: String = "",
    @SerialName("course_id") val courseId: Int = 0,
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("quiz_average") val quizAverage: Float? = null,
    @SerialName("completion_rate") val completionRate: Float? = null,
    @SerialName("composite_score") val compositeScore: Float? = null,
    @SerialName("performance_indicator") val performanceIndicator: String? = null,
    @SerialName("performance_label") val performanceLabel: String = "",
)

@Serializable
internal data class ParentAcademicIntelligenceDto(
    @SerialName("overall_average") val overallAverage: Float? = null,
    @SerialName("performance_indicator") val performanceIndicator: String? = null,
    @SerialName("performance_label") val performanceLabel: String = "",
    val subjects: List<ParentSubjectAcademicDto> = emptyList(),
    @SerialName("has_data") val hasData: Boolean = false,
    val summary: String = "",
)

@Serializable
internal data class ParentReportMetricComparisonDto(
    val label: String = "",
    @SerialName("current_value") val currentValue: Float = 0f,
    @SerialName("previous_value") val previousValue: Float = 0f,
    @SerialName("change_percent") val changePercent: Float? = null,
    val unit: String = "",
)

@Serializable
internal data class ParentReportPeriodComparisonDto(
    @SerialName("period_label") val periodLabel: String = "",
    @SerialName("previous_period_label") val previousPeriodLabel: String = "",
    @SerialName("study_time") val studyTime: ParentReportMetricComparisonDto? = null,
    val grades: ParentReportMetricComparisonDto? = null,
    @SerialName("lesson_completion") val lessonCompletion: ParentReportMetricComparisonDto? = null,
    @SerialName("planner_adherence") val plannerAdherence: ParentReportMetricComparisonDto? = null,
)

@Serializable
internal data class ParentReportTrendPointDto(
    val label: String = "",
    val date: String? = null,
    val value: Float = 0f,
    @SerialName("secondary_value") val secondaryValue: Float? = null,
)

@Serializable
internal data class ParentReportLessonHistoryDto(
    val weekly: List<ParentReportTrendPointDto> = emptyList(),
    val monthly: List<ParentReportTrendPointDto> = emptyList(),
    @SerialName("total_in_period") val totalInPeriod: Int = 0,
)

@Serializable
internal data class ParentReportAttendanceHistoryDto(
    @SerialName("login_sessions") val loginSessions: List<ParentLoginHistoryRowDto> = emptyList(),
    @SerialName("daily_study_trend") val dailyStudyTrend: List<ParentReportTrendPointDto> = emptyList(),
    @SerialName("total_study_hours") val totalStudyHours: Float = 0f,
    @SerialName("total_sessions") val totalSessions: Int = 0,
)

@Serializable
internal data class ParentReportPlannerHistoryDto(
    @SerialName("adherence_trend") val adherenceTrend: List<ParentReportTrendPointDto> = emptyList(),
    @SerialName("missed_tasks_trend") val missedTasksTrend: List<ParentReportTrendPointDto> = emptyList(),
    @SerialName("average_adherence") val averageAdherence: Float = 0f,
    @SerialName("total_missed") val totalMissed: Int = 0,
)

@Serializable
internal data class ParentHistoricalReportDto(
    @SerialName("student_name") val studentName: String = "",
    val period: String = "this_week",
    @SerialName("period_label") val periodLabel: String = "",
    @SerialName("start_date") val startDate: String = "",
    @SerialName("end_date") val endDate: String = "",
    val comparison: ParentReportPeriodComparisonDto = ParentReportPeriodComparisonDto(),
    @SerialName("lesson_history") val lessonHistory: ParentReportLessonHistoryDto = ParentReportLessonHistoryDto(),
    @SerialName("attendance_history") val attendanceHistory: ParentReportAttendanceHistoryDto = ParentReportAttendanceHistoryDto(),
    @SerialName("planner_history") val plannerHistory: ParentReportPlannerHistoryDto = ParentReportPlannerHistoryDto(),
    @SerialName("has_data") val hasData: Boolean = false,
)

@Serializable
internal data class ParentExecutiveWeeklySnapshotDto(
    @SerialName("lessons_completed") val lessonsCompleted: Int = 0,
    @SerialName("study_hours") val studyHours: Float = 0f,
    @SerialName("average_quiz_score") val averageQuizScore: Int? = null,
    @SerialName("planner_adherence_percent") val plannerAdherencePercent: Int? = null,
    @SerialName("missed_planner_tasks") val missedPlannerTasks: Int = 0,
    @SerialName("most_active_subject") val mostActiveSubject: String? = null,
    @SerialName("weakest_subject") val weakestSubject: String? = null,
    @SerialName("strongest_subject") val strongestSubject: String? = null,
)

@Serializable
internal data class ParentExecutiveComparisonMetricDto(
    val label: String = "",
    @SerialName("current_value") val currentValue: Float = 0f,
    @SerialName("previous_value") val previousValue: Float = 0f,
    @SerialName("change_percent") val changePercent: Float? = null,
    val unit: String = "",
)

@Serializable
internal data class ParentExecutivePeriodComparisonDto(
    @SerialName("period_label") val periodLabel: String = "",
    @SerialName("study_time") val studyTime: ParentExecutiveComparisonMetricDto? = null,
    @SerialName("lesson_completion") val lessonCompletion: ParentExecutiveComparisonMetricDto? = null,
    @SerialName("quiz_performance") val quizPerformance: ParentExecutiveComparisonMetricDto? = null,
    @SerialName("planner_adherence") val plannerAdherence: ParentExecutiveComparisonMetricDto? = null,
)

@Serializable
internal data class ParentExecutiveSubjectAnalysisDto(
    val subject: String = "",
    val reasons: List<String> = emptyList(),
    @SerialName("average_score") val averageScore: Int? = null,
    @SerialName("study_minutes") val studyMinutes: Int = 0,
    @SerialName("engagement_rank") val engagementRank: Int? = null,
)

@Serializable
internal data class ParentExecutiveStudyBehaviorDto(
    @SerialName("average_daily_study_hours") val averageDailyStudyHours: Float = 0f,
    @SerialName("preferred_study_hours_label") val preferredStudyHoursLabel: String? = null,
    @SerialName("preferred_study_hours_start") val preferredStudyHoursStart: Int? = null,
    @SerialName("preferred_study_hours_end") val preferredStudyHoursEnd: Int? = null,
    @SerialName("consistency_level") val consistencyLevel: String = "unknown",
    @SerialName("consistency_label") val consistencyLabel: String = "",
    @SerialName("active_days_this_week") val activeDaysThisWeek: Int = 0,
    @SerialName("total_days_this_week") val totalDaysThisWeek: Int = 7,
)

@Serializable
internal data class ParentExecutiveNotificationSignalsDto(
    @SerialName("recent_alerts_count") val recentAlertsCount: Int = 0,
    @SerialName("unread_count") val unreadCount: Int = 0,
    @SerialName("has_inactivity_alert") val hasInactivityAlert: Boolean = false,
    @SerialName("has_low_score_alert") val hasLowScoreAlert: Boolean = false,
    @SerialName("has_planner_alert") val hasPlannerAlert: Boolean = false,
)

@Serializable
internal data class ParentExecutiveSummaryDto(
    @SerialName("student_name") val studentName: String = "",
    @SerialName("grade_label") val gradeLabel: String = "",
    @SerialName("academic_status_label") val academicStatusLabel: String = "",
    @SerialName("weekly_snapshot") val weeklySnapshot: ParentExecutiveWeeklySnapshotDto =
        ParentExecutiveWeeklySnapshotDto(),
    @SerialName("period_comparison") val periodComparison: ParentExecutivePeriodComparisonDto =
        ParentExecutivePeriodComparisonDto(),
    @SerialName("study_time_averages") val studyTimeAverages: ParentStudyTimeAveragesDto =
        ParentStudyTimeAveragesDto(),
    @SerialName("study_behavior") val studyBehavior: ParentExecutiveStudyBehaviorDto =
        ParentExecutiveStudyBehaviorDto(),
    @SerialName("strength_analysis") val strengthAnalysis: ParentExecutiveSubjectAnalysisDto? = null,
    @SerialName("weakness_analysis") val weaknessAnalysis: ParentExecutiveSubjectAnalysisDto? = null,
    @SerialName("risk_alerts") val riskAlerts: List<ParentInsightDto> = emptyList(),
    val recommendations: List<ParentInsightDto> = emptyList(),
    @SerialName("summary_lines") val summaryLines: List<String> = emptyList(),
    @SerialName("notification_signals") val notificationSignals: ParentExecutiveNotificationSignalsDto =
        ParentExecutiveNotificationSignalsDto(),
    @SerialName("latest_insight") val latestInsight: ParentInsightDto? = null,
    @SerialName("has_data") val hasData: Boolean = false,
)

@Serializable
internal data class ParentQuizResultDto(
    val id: Int? = null,
    val subject: String = "",
    @SerialName("lesson_title") val lessonTitle: String = "",
    val score: Int = 0,
    val date: String? = null,
    val relative: String = "",
)

@Serializable
internal data class ParentQuizTrackingDto(
    val recent: List<ParentQuizResultDto> = emptyList(),
    @SerialName("average_score") val averageScore: Int = 0,
)

@Serializable
internal data class ParentGamificationDto(
    val level: Int = 1,
    @SerialName("total_xp") val totalXp: Int = 0,
    @SerialName("current_streak") val currentStreak: Int = 0,
    val achievements: List<ParentAchievementDto> = emptyList(),
    @SerialName("achievement_count") val achievementCount: Int = 0,
    val badges: List<ParentBadgeDto> = emptyList(),
)

@Serializable
internal data class ParentAchievementDto(
    @SerialName("achievement_key") val achievementKey: String = "",
    val title: String = "",
    val description: String = "",
    @SerialName("unlocked_at") val unlockedAt: String? = null,
)

@Serializable
internal data class ParentBadgeDto(
    @SerialName("achievement_key") val achievementKey: String = "",
    val title: String = "",
    val description: String = "",
    val unlocked: Boolean = false,
    @SerialName("unlocked_at") val unlockedAt: String? = null,
)

@Serializable
internal data class ParentRoutineSlotDto(
    val start: String = "",
    val end: String = "",
    val title: String = "",
    val subject: String? = null,
    val status: String = "planned",
)

@Serializable
internal data class ParentRoutineVisibilityDto(
    @SerialName("onboarding_complete") val onboardingComplete: Boolean = false,
    @SerialName("weekly_commitment_percent") val weeklyCommitmentPercent: Int = 0,
    @SerialName("today_label") val todayLabel: String = "",
    @SerialName("today_slots") val todaySlots: List<ParentRoutineSlotDto> = emptyList(),
)

internal data class ParentReportExportDto(
    val bytes: ByteArray,
    val filename: String,
    val mimeType: String,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ParentReportExportDto) return false
        return filename == other.filename && mimeType == other.mimeType && bytes.contentEquals(other.bytes)
    }

    override fun hashCode(): Int {
        var result = bytes.contentHashCode()
        result = 31 * result + filename.hashCode()
        result = 31 * result + mimeType.hashCode()
        return result
    }
}
