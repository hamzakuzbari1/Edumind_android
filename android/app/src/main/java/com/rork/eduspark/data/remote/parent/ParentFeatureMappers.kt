package com.rork.eduspark.data.remote.parent

import com.rork.eduspark.data.model.ParentAchievementSummary
import com.rork.eduspark.data.model.ParentAiInsightsSnapshot
import com.rork.eduspark.data.model.ParentInsight
import com.rork.eduspark.data.model.ParentNamedAchievement
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentQuizResult
import com.rork.eduspark.data.model.ParentRoutineSlot
import com.rork.eduspark.data.model.ParentAlert
import com.rork.eduspark.data.model.ParentAlertPreference
import com.rork.eduspark.data.model.ParentAlertPreferenceKey
import com.rork.eduspark.data.model.ParentAlertSeverity
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentAttendanceConsistencyWeek
import com.rork.eduspark.data.model.ParentAttendanceMonthWeek
import com.rork.eduspark.data.model.ParentAttendanceStatusBreakdown
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDailyStudyTime
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentExecutiveComparisonMetric
import com.rork.eduspark.data.model.ParentExecutiveSubjectAnalysis
import com.rork.eduspark.data.model.ParentExecutiveWeeklySnapshot
import com.rork.eduspark.data.model.ParentLessonActivityEvent
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressItem
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLessonVerificationItem
import com.rork.eduspark.data.model.ParentLoginSession
import com.rork.eduspark.data.model.ParentMonthlyStudyWeek
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPerformanceTrend
import com.rork.eduspark.data.model.ParentPlannerSession
import com.rork.eduspark.data.model.ParentPlannerSessionStatus
import com.rork.eduspark.data.model.ParentPlannerSnapshot
import com.rork.eduspark.data.model.ParentPlannerSubjectCommitment
import com.rork.eduspark.data.model.ParentReportComparisonMetric
import com.rork.eduspark.data.model.ParentReportMetricKey
import com.rork.eduspark.data.model.ParentReportTrendPoint
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.data.model.ParentStudyTimeAverages
import com.rork.eduspark.data.model.ParentStudyBehaviorInsight
import com.rork.eduspark.data.model.ParentSubjectInsight
import com.rork.eduspark.data.model.ParentSubjectPerformance
import com.rork.eduspark.data.model.ParentSubjectTeacher
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import kotlin.math.roundToInt

private val STRONG_INDICATORS = setOf("excellent", "strong", "good", "high", "on_track", "above_average")

internal fun ParentDashboardDto.toDashboardSnapshot(
    alertCount: Int,
    latestTeacherNote: ParentNote? = null,
): ParentDashboardSnapshot {
    val academicAverage = academicIntelligence?.overallAverage?.roundToInt()
        ?: stats.intOrNull("average_score")
    val lessonCompletion = lessonProgress?.summary?.completionRate ?: 0
    return ParentDashboardSnapshot(
        academicAveragePercent = academicAverage ?: 0,
        lessonProgressPercent = lessonCompletion,
        studyHoursThisWeek = attendance.totalStudyMinutesWeek / 60f,
        attendancePercent = attendance.attendancePercentage,
        plannerItemsDue = planner.commitment.pendingCount + planner.commitment.overdueCount,
        alertCount = alertCount,
        hasAttendanceData = attendance.hasData,
        hasAcademicData = academicIntelligence?.hasData ?: (academicAverage != null && academicAverage > 0),
        recentActivities = activity.map(ParentActivityDto::toDomain),
        latestTeacherNote = latestTeacherNote,
        latestInsightText = homeAiTeaserText(),
    )
}

private fun ParentDashboardDto.homeAiTeaserText(): String? {
    val fromInsights = insights.firstOrNull { insight ->
        insight.id != "default" && insight.text.isNotBlank()
    }?.text?.trim()
    if (!fromInsights.isNullOrBlank()) return fromInsights
    return academicIntelligence?.summary?.trim()?.takeIf { it.isNotBlank() }
}

internal fun buildPerformanceSnapshot(
    academic: ParentAcademicIntelligenceDto?,
    quiz: ParentQuizTrackingDto?,
    report: ParentHistoricalReportDto?,
    lessonProgress: ParentLessonProgressDto?,
    gamification: ParentGamificationDto?,
): ParentPerformanceSnapshot {
    val subjects = academic?.subjects.orEmpty().mapIndexed { index, subject ->
        ParentSubjectPerformance(
            id = subject.courseId.takeIf { it != 0 }?.toString() ?: "subject-$index",
            subjectName = subject.subjectName,
            percent = subject.displayPercent,
            statusLabel = subject.performanceLabel,
            isStrong = subject.isStrong,
        )
    }
    val quizScores = quiz?.recent.orEmpty().reversed().map { it.score }
    val gradeChange = report?.comparison?.grades?.changePercent
    return ParentPerformanceSnapshot(
        testAveragePercent = academic?.overallAverage?.roundToInt() ?: quiz?.averageScore ?: 0,
        subjectProgressPercent = lessonProgress?.summary?.completionRate
            ?: subjects.map { it.percent }.averageOrZero(),
        improvementPercent = gradeChange?.roundToInt() ?: 0,
        hasImprovementData = gradeChange != null,
        summary = academic?.summary.orEmpty(),
        periodLabel = report?.periodLabel.orEmpty(),
        trend = if (quizScores.size >= 2) {
            ParentPerformanceTrend(currentScores = quizScores, previousScores = emptyList())
        } else {
            null
        },
        subjects = subjects,
        recentQuizzes = quiz?.recent.orEmpty().map(ParentQuizResultDto::toDomain),
        achievements = gamification?.toAchievementSummary(),
    )
}

internal fun buildAttendanceSnapshot(
    attendance: ParentAttendanceSummaryDto,
    analytics: ParentAttendanceAnalyticsDto?,
    activitySessions: List<ParentActivitySessionDto>,
): ParentAttendanceStudyTimeSnapshot {
    val analyticsDays = analytics?.dailyBreakdown.orEmpty()
    val dailyRows = if (analyticsDays.isNotEmpty()) {
        analyticsDays.map { day ->
            ParentDailyStudyTime(
                dayLabel = day.dayLabel.ifBlank { day.date },
                minutes = day.studyMinutes,
                isToday = isParentCalendarToday(day.date),
            )
        }
    } else {
        attendance.weeklyCalendar.map { day ->
            ParentDailyStudyTime(
                dayLabel = day.dayLabel.ifBlank { day.date },
                minutes = day.studyMinutes,
                isToday = isParentCalendarToday(day.date),
            )
        }
    }
    val analyticsHistory = analytics?.loginHistory.orEmpty().map(ParentLoginHistoryRowDto::toLoginSession)
    val sessionHistory = activitySessions.map(ParentActivitySessionDto::toLoginSession)
    val loginSessions = (analyticsHistory + sessionHistory).distinctBy { it.id }
    val sessionDurations = loginSessions.map { it.durationMinutes }.filter { it > 0 }
    val averageSession = if (sessionDurations.isNotEmpty()) {
        sessionDurations.average().roundToInt()
    } else {
        0
    }
    val attendanceBreakdown = attendance.statusBreakdown()
    val hasStudyTimeAnalytics = analytics?.let {
        it.overview.todayMinutes > 0 ||
            it.overview.weekMinutes > 0 ||
            it.overview.monthMinutes > 0 ||
            it.dailyBreakdown.any { day -> day.studyMinutes > 0 } ||
            it.monthlyAnalytics.weeks.any { week -> week.studyMinutes > 0 }
    } ?: false
    return ParentAttendanceStudyTimeSnapshot(
        attendancePercent = attendance.attendancePercentage,
        studyHours = (analytics?.overview?.weekMinutes ?: attendance.totalStudyMinutesWeek) / 60f,
        activeDays = analytics?.weeklyAnalytics?.activeDaysCount
            ?: attendance.weeklyCalendar.count { it.studyMinutes > 0 || it.active },
        averageSessionMinutes = averageSession,
        consistencyPercent = attendance.weeklyConsistency,
        hasData = attendance.hasData || hasStudyTimeAnalytics || loginSessions.isNotEmpty(),
        hasStudyTimeAnalytics = hasStudyTimeAnalytics,
        dailyStudyMinutes = dailyRows,
        studyTimeAverages = analytics?.overview?.averages?.toDomain() ?: ParentStudyTimeAverages(),
        weeklyPeriodLabel = analytics?.weeklyAnalytics?.periodLabel.orEmpty(),
        weeklyComparisonPercent = analytics?.weeklyAnalytics?.comparisonPercent,
        monthlyPeriodLabel = analytics?.monthlyAnalytics?.periodLabel.orEmpty(),
        monthlyComparisonPercent = analytics?.monthlyAnalytics?.comparisonPercent,
        monthlyStudyWeeks = analytics?.monthlyAnalytics?.weeks.orEmpty().map { week ->
            ParentMonthlyStudyWeek(weekIndex = week.weekIndex, minutes = week.studyMinutes)
        },
        monthlyAttendance = attendance.monthlyOverview.map { week ->
            ParentAttendanceMonthWeek(
                label = week.label,
                consistencyPercent = week.consistency,
                presentDays = week.present,
                partialDays = week.partial,
                absentDays = week.absent,
            )
        },
        consistencyWeeks = attendance.consistencyBars.map { week ->
            ParentAttendanceConsistencyWeek(
                label = week.weekLabel,
                consistencyPercent = week.consistency,
                presentDays = week.presentDays,
                totalDays = week.totalDays,
            )
        },
        statusBreakdown = attendanceBreakdown,
        aiInsights = attendance.aiInsights.filter { it.isNotBlank() },
        loginSessions = loginSessions,
    )
}

internal fun ParentAttendanceSummaryDto.toAttendanceSnapshot(
    analytics: ParentAttendanceAnalyticsDto? = null,
    activitySessions: List<ParentActivitySessionDto> = emptyList(),
): ParentAttendanceStudyTimeSnapshot = buildAttendanceSnapshot(
    attendance = this,
    analytics = analytics,
    activitySessions = activitySessions,
)

internal val ParentAttendanceSummaryDto.hasData: Boolean
    get() = totalStudyMinutesWeek > 0 ||
        completedSessions > 0 ||
        missedSessions > 0 ||
        partialDays > 0 ||
        weeklyCalendar.any { it.studyMinutes > 0 } ||
        monthlyOverview.isNotEmpty() ||
        consistencyBars.isNotEmpty() ||
        recentRecords.isNotEmpty()

private fun ParentAttendanceSummaryDto.statusBreakdown(): ParentAttendanceStatusBreakdown {
    val fromMonth = monthlyOverview.takeIf { it.isNotEmpty() }?.let { weeks ->
        ParentAttendanceStatusBreakdown(
            presentDays = weeks.sumOf { it.present },
            partialDays = weeks.sumOf { it.partial },
            absentDays = weeks.sumOf { it.absent },
        )
    }
    if (fromMonth != null && fromMonth.hasValues) return fromMonth
    if (recentRecords.isNotEmpty()) {
        return ParentAttendanceStatusBreakdown(
            presentDays = recentRecords.count { it.status.equals("present", ignoreCase = true) },
            partialDays = recentRecords.count { it.status.equals("partial", ignoreCase = true) },
            absentDays = recentRecords.count { it.status.equals("absent", ignoreCase = true) },
        )
    }
    if (weeklyCalendar.any { it.status.isNotBlank() }) {
        return ParentAttendanceStatusBreakdown(
            presentDays = weeklyCalendar.count { it.status.equals("present", ignoreCase = true) },
            partialDays = weeklyCalendar.count { it.status.equals("partial", ignoreCase = true) },
            absentDays = weeklyCalendar.count { it.status.equals("absent", ignoreCase = true) },
        )
    }
    return ParentAttendanceStatusBreakdown()
}

private fun ParentStudyTimeAveragesDto.toDomain() = ParentStudyTimeAverages(
    dailyHours = dailyHours,
    weeklyHours = weeklyHours,
    monthlyHours = monthlyHours,
    dailyTrendPercent = dailyTrendPercent,
    weeklyTrendPercent = weeklyTrendPercent,
    monthlyTrendPercent = monthlyTrendPercent,
)

private fun ParentLoginHistoryRowDto.toLoginSession() = ParentLoginSession(
    id = id.toString(),
    dateLabel = dayLabel?.takeIf { it.isNotBlank() } ?: date.orEmpty(),
    loginLabel = formatParentTimestamp(loginAt.orEmpty()),
    logoutLabel = logoutAt?.let(::formatParentTimestamp)?.takeIf { it.isNotBlank() },
    durationMinutes = activeMinutes,
    isOpen = isOpen || logoutAt == null,
    logoutReason = logoutReason,
)

private fun ParentActivitySessionDto.toLoginSession() = ParentLoginSession(
    id = id.toString(),
    dateLabel = loginAt?.take(10).orEmpty(),
    loginLabel = formatParentTimestamp(loginAt.orEmpty()),
    logoutLabel = logoutAt?.let(::formatParentTimestamp)?.takeIf { it.isNotBlank() },
    durationMinutes = activeMinutes,
    isOpen = logoutAt == null,
    logoutReason = logoutReason,
)

internal fun ParentLessonProgressDto.toLessonProgressSnapshot(): ParentLessonProgressSnapshot {
    val lessons = courses.flatMap { course ->
        course.lessons.map { lesson ->
            ParentLessonProgressItem(
                id = lesson.lessonId.toString(),
                title = lesson.lessonTitle,
                subjectName = lesson.subjectName.ifBlank { course.subjectName },
                courseTitle = lesson.courseTitle.ifBlank { course.courseTitle },
                statusLabel = lesson.statusLabel.ifBlank { lesson.status },
                isCompleted = lesson.status.equals("completed", ignoreCase = true) || lesson.isVerified,
                progressPercent = lesson.completionPercent,
                teacherName = lesson.teacherName.orEmpty(),
                lastActivityLabel = formatParentTimestamp(
                    lesson.lastActivityAt ?: lesson.completedAt.orEmpty(),
                ),
            )
        }
    }
    return ParentLessonProgressSnapshot(
        completedLessons = summary.completedLessons,
        totalLessons = summary.totalLessons.takeIf { it > 0 } ?: lessons.size,
        lessons = lessons,
    )
}

internal fun ParentLessonDetailDto.toLessonDetails(): ParentLessonDetails {
    val required = checklist.filter { it.required }
    return ParentLessonDetails(
        lessonId = lessonId.toString(),
        title = lessonTitle,
        courseTitle = courseTitle,
        subjectName = subjectName,
        teacherName = teacherName,
        statusLabel = verificationStatusLabel.ifBlank { completionStatus },
        completionPercent = completionPercent,
        videoPercent = videoProgressPercent.roundToInt(),
        quizScorePercent = quizScorePercent.roundToInt(),
        pagesViewed = pdfPagesViewed ?: 0,
        totalPages = pdfTotalPages ?: 0,
        requirementsCompleted = required.count { it.met },
        requirementsTotal = required.size,
        missingRequirements = missingRequirements.size,
        checklist = checklist.map { item ->
            ParentLessonVerificationItem(
                id = item.key,
                label = item.label,
                isComplete = item.met,
            )
        },
        timeline = timeline.mapIndexed { index, event ->
            ParentLessonActivityEvent(
                id = "${event.date}-$index",
                label = event.label,
                timeLabel = formatParentTimestamp(event.datetime ?: event.date),
            )
        },
    )
}

internal fun ParentSubjectsTeachersDto.toSubjectsTeachersSnapshot(): ParentSubjectsTeachersSnapshot =
    ParentSubjectsTeachersSnapshot(
        items = (enrolled + available).map { course ->
            ParentSubjectTeacher(
                id = "${course.courseId}",
                courseId = course.courseId.toString(),
                subjectName = course.subjectName,
                courseTitle = course.courseTitle,
                teacherName = course.teacherName,
                progressPercent = course.progressPercent,
                statusLabel = course.subscriptionStatus,
                isOnTrack = course.progressPercent >= 60,
                lessonCount = course.lessonCount,
                completedLessonCount = course.completedLessonCount,
                enrolled = course.enrolled,
                threadId = course.threadId?.toString(),
                unreadCount = course.unreadCount,
            )
        },
    )

internal fun ParentPlannerVisibilityDto.toPlannerSnapshot(
    routine: ParentRoutineVisibilityDto? = null,
): ParentPlannerSnapshot {
    val tasks = (todayPlan + upcomingTasks + overdueTasks + missedTasks + completedTasks)
        .distinctBy { it.id }
    return ParentPlannerSnapshot(
        commitmentPercent = commitment.adherenceRate,
        completedSessions = commitment.completedCount,
        totalSessions = commitment.totalDueCount,
        postponedSessions = commitment.missedCount + commitment.overdueCount,
        summary = summary,
        consistencyLabel = weeklyConsistency.label,
        sessions = tasks.map { task ->
            ParentPlannerSession(
                id = task.id.toString(),
                subjectName = task.subject,
                taskName = task.taskName,
                timeLabel = formatParentTimestamp(task.completedAt ?: task.plannedAt.orEmpty()),
                statusLabel = task.statusLabel.ifBlank { task.status },
                status = task.plannerStatus,
            )
        },
        subjectBreakdown = subjectBreakdown.map { subject ->
            ParentPlannerSubjectCommitment(
                subjectName = subject.subjectName,
                adherencePercent = subject.adherencePercent,
                completedCount = subject.completedCount,
                totalCount = subject.totalCount,
            )
        },
        todayLabel = routine?.todayLabel.orEmpty(),
        todayRoutine = routine?.todaySlots.orEmpty().map(ParentRoutineSlotDto::toDomain),
    )
}

internal fun buildAlertsSnapshot(
    notifications: ParentNotificationListDto,
    settings: ParentNotificationSettingsDto?,
): ParentAlertsSnapshot = ParentAlertsSnapshot(
    unreadCount = notifications.unreadCount,
    alerts = notifications.items.map { item ->
        ParentAlert(
            id = item.id.toString(),
            title = item.title,
            body = item.body,
            categoryLabel = item.categoryLabel.ifBlank { item.category },
            timeLabel = formatParentTimestamp(item.createdAt.orEmpty()),
            severity = item.severity,
            isUnread = !item.isRead,
        )
    },
    preferences = settings?.toPreferences().orEmpty(),
)

internal fun ParentNotificationSettingsDto.toPreferences(): List<ParentAlertPreference> = listOf(
    ParentAlertPreference(ParentAlertPreferenceKey.Login, loginAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.Logout, logoutAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.Lesson, lessonAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.Quiz, quizAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.LowScore, lowScoreAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.Inactivity, inactivityAlerts),
    ParentAlertPreference(ParentAlertPreferenceKey.Planner, plannerAlerts),
)

internal fun ParentAlertPreferenceKey.toUpdateDto(enabled: Boolean): ParentNotificationSettingsUpdateDto =
    when (this) {
        ParentAlertPreferenceKey.Login -> ParentNotificationSettingsUpdateDto(loginAlerts = enabled)
        ParentAlertPreferenceKey.Logout -> ParentNotificationSettingsUpdateDto(logoutAlerts = enabled)
        ParentAlertPreferenceKey.Lesson -> ParentNotificationSettingsUpdateDto(lessonAlerts = enabled)
        ParentAlertPreferenceKey.Quiz -> ParentNotificationSettingsUpdateDto(quizAlerts = enabled)
        ParentAlertPreferenceKey.LowScore -> ParentNotificationSettingsUpdateDto(lowScoreAlerts = enabled)
        ParentAlertPreferenceKey.Inactivity -> ParentNotificationSettingsUpdateDto(inactivityAlerts = enabled)
        ParentAlertPreferenceKey.Planner -> ParentNotificationSettingsUpdateDto(plannerAlerts = enabled)
    }

internal fun buildAiInsightsSnapshot(
    insights: List<ParentInsightDto>,
    academic: ParentAcademicIntelligenceDto?,
    attendance: ParentAttendanceSummaryDto?,
): ParentAiInsightsSnapshot = ParentAiInsightsSnapshot(
    summary = academic?.summary.orEmpty(),
    performanceLabel = academic?.performanceLabel.orEmpty(),
    overallAveragePercent = academic?.overallAverage?.roundToInt(),
    hasData = academic?.hasData == true || insights.isNotEmpty() || attendance?.hasData == true,
    insights = insights.map(ParentInsightDto::toDomain),
    subjectInsights = academic?.subjects.orEmpty().mapIndexed { index, subject ->
        ParentSubjectInsight(
            id = subject.courseId.takeIf { it != 0 }?.toString() ?: "insight-$index",
            subjectName = subject.subjectName,
            statusLabel = subject.performanceLabel,
            isStrength = subject.isStrong,
            quizAveragePercent = subject.quizAverage?.roundToInt(),
            completionPercent = subject.completionRate?.roundToInt(),
        )
    },
    behavior = attendance?.takeIf { it.hasData }?.let { summary ->
        ParentStudyBehaviorInsight(
            averageSessionMinutes = if (summary.completedSessions > 0) {
                summary.totalStudyMinutesWeek / summary.completedSessions
            } else {
                null
            },
            consistencyDays = summary.weeklyCalendar.count { it.studyMinutes > 0 },
            consistencyTotalDays = summary.weeklyCalendar.size.takeIf { it > 0 } ?: 7,
            studyHours = summary.totalStudyMinutesWeek / 60f,
        )
    },
)

internal fun ParentExecutiveSummaryDto.toAiInsightsSnapshot(
    extraInsights: List<ParentInsightDto> = emptyList(),
    academic: ParentAcademicIntelligenceDto? = null,
    attendance: ParentAttendanceSummaryDto? = null,
): ParentAiInsightsSnapshot {
    val strength = strengthAnalysis?.toDomain()
    val weakness = weaknessAnalysis?.toDomain()
    val bullets = summaryLines.filter { it.isNotBlank() }
    val executiveRisks = riskAlerts.map(ParentInsightDto::toDomain)
    val executiveRecommendations = recommendations.map(ParentInsightDto::toDomain)
    val uniqueExtras = uniqueSupplementaryInsights(
        extras = extraInsights,
        existing = bullets +
            listOfNotNull(latestInsight?.text) +
            executiveRisks.map(ParentInsight::text) +
            executiveRecommendations.map(ParentInsight::text),
        strongestSubject = weeklySnapshot.strongestSubject,
        weakestSubject = weeklySnapshot.weakestSubject,
        hasOtherContent = hasData || bullets.isNotEmpty() || executiveRisks.isNotEmpty() ||
            executiveRecommendations.isNotEmpty() || academic?.hasData == true,
    )
    val extraRisks = uniqueExtras.filter { it.severity.equals("warning", ignoreCase = true) }
    val extraRecommendations = uniqueExtras.filter { it.severity.equals("success", ignoreCase = true) }
    val academicSubjects = academic?.subjects.orEmpty().mapIndexed { index, subject ->
        ParentSubjectInsight(
            id = subject.courseId.takeIf { it != 0 }?.toString() ?: "insight-$index",
            subjectName = subject.subjectName,
            statusLabel = subject.performanceLabel,
            isStrength = subject.isStrong,
            quizAveragePercent = subject.quizAverage?.roundToInt(),
            completionPercent = subject.completionRate?.roundToInt(),
        )
    }
    val executiveSubjects = listOfNotNull(
        strengthAnalysis?.toSubjectInsight(isStrength = true, id = "strength"),
        weaknessAnalysis?.toSubjectInsight(isStrength = false, id = "weakness"),
    )
    val attendanceMinutes = attendance?.takeIf { it.hasData && it.completedSessions > 0 }?.let {
        it.totalStudyMinutesWeek / it.completedSessions
    }
    val executiveBehavior = studyBehavior.takeIf {
        hasData || it.activeDaysThisWeek > 0 || !it.preferredStudyHoursLabel.isNullOrBlank()
    }?.let {
        ParentStudyBehaviorInsight(
            averageSessionMinutes = attendanceMinutes,
            consistencyDays = it.activeDaysThisWeek,
            consistencyTotalDays = it.totalDaysThisWeek,
            studyHours = weeklySnapshot.studyHours,
            averageDailyStudyHours = it.averageDailyStudyHours,
            preferredStudyHoursLabel = it.preferredStudyHoursLabel,
            consistencyLabel = it.consistencyLabel,
        )
    }
    val attendanceBehavior = attendance?.takeIf { it.hasData }?.let { summary ->
        ParentStudyBehaviorInsight(
            averageSessionMinutes = attendanceMinutes,
            consistencyDays = summary.weeklyCalendar.count { it.studyMinutes > 0 },
            consistencyTotalDays = summary.weeklyCalendar.size.takeIf { it > 0 } ?: 7,
            studyHours = summary.totalStudyMinutesWeek / 60f,
        )
    }
    return ParentAiInsightsSnapshot(
        summary = bullets.joinToString(" · ").ifBlank { latestInsight?.text.orEmpty() },
        performanceLabel = academicStatusLabel.ifBlank { academic?.performanceLabel.orEmpty() },
        overallAveragePercent = weeklySnapshot.averageQuizScore ?: academic?.overallAverage?.roundToInt(),
        hasData = hasData || academic?.hasData == true || uniqueExtras.isNotEmpty() || academicSubjects.isNotEmpty(),
        summaryLines = bullets,
        weeklySnapshot = ParentExecutiveWeeklySnapshot(
            lessonsCompleted = weeklySnapshot.lessonsCompleted,
            studyHours = weeklySnapshot.studyHours,
            averageQuizScore = weeklySnapshot.averageQuizScore,
            plannerAdherencePercent = weeklySnapshot.plannerAdherencePercent,
            missedPlannerTasks = weeklySnapshot.missedPlannerTasks,
            strongestSubject = weeklySnapshot.strongestSubject,
            weakestSubject = weeklySnapshot.weakestSubject,
        ),
        periodLabel = periodComparison.periodLabel,
        periodComparison = listOfNotNull(
            periodComparison.studyTime?.toDomain(),
            periodComparison.lessonCompletion?.toDomain(),
            periodComparison.quizPerformance?.toDomain(),
            periodComparison.plannerAdherence?.toDomain(),
        ),
        studyTimeAverages = studyTimeAverages.toDomain(),
        insights = (executiveRisks + executiveRecommendations + uniqueExtras).distinctBy { insightKey(it) },
        subjectInsights = academicSubjects.ifEmpty { executiveSubjects },
        strengthAnalysis = strength,
        weaknessAnalysis = weakness,
        riskInsights = (executiveRisks + extraRisks).distinctBy { insightKey(it) },
        recommendations = (executiveRecommendations + extraRecommendations).distinctBy { insightKey(it) },
        behavior = executiveBehavior ?: attendanceBehavior,
    )
}

private fun ParentExecutiveComparisonMetricDto.toDomain() = ParentExecutiveComparisonMetric(
    label = label,
    currentValue = currentValue,
    previousValue = previousValue,
    changePercent = changePercent,
    unit = unit,
)

private fun ParentExecutiveSubjectAnalysisDto.toDomain() = ParentExecutiveSubjectAnalysis(
    subjectName = subject,
    reasons = reasons.filter { it.isNotBlank() },
    averageScorePercent = averageScore,
    studyMinutes = studyMinutes,
)

private fun ParentExecutiveSubjectAnalysisDto.toSubjectInsight(
    isStrength: Boolean,
    id: String,
) = ParentSubjectInsight(
    id = id,
    subjectName = subject,
    statusLabel = reasons.firstOrNull().orEmpty(),
    isStrength = isStrength,
    quizAveragePercent = averageScore,
    completionPercent = null,
)

internal fun ParentHistoricalReportDto.toReportsSnapshot(): ParentReportsSnapshot = ParentReportsSnapshot(
    periodLabel = periodLabel.ifBlank { period },
    startDate = startDate,
    endDate = endDate,
    academicAveragePercent = comparison.grades?.currentValue?.roundToInt() ?: 0,
    completedLessons = lessonHistory.totalInPeriod,
    studyHours = attendanceHistory.totalStudyHours,
    hasData = hasData,
    trend = attendanceHistory.dailyStudyTrend.map { point ->
        ParentReportTrendPoint(label = point.label, value = point.value)
    },
    comparison = listOfNotNull(
        comparison.studyTime?.toMetric(ParentReportMetricKey.StudyTime),
        comparison.grades?.toMetric(ParentReportMetricKey.Grades),
        comparison.lessonCompletion?.toMetric(ParentReportMetricKey.LessonCompletion),
        comparison.plannerAdherence?.toMetric(ParentReportMetricKey.PlannerAdherence),
    ),
    weeklyLessonHistory = lessonHistory.weekly.map(ParentReportTrendPointDto::toDomain),
    monthlyLessonHistory = lessonHistory.monthly.map(ParentReportTrendPointDto::toDomain),
    loginSessions = attendanceHistory.loginSessions.map(ParentLoginHistoryRowDto::toLoginSession),
    plannerAdherenceHistory = plannerHistory.adherenceTrend.map(ParentReportTrendPointDto::toDomain),
    missedLateTaskHistory = plannerHistory.missedTasksTrend.map(ParentReportTrendPointDto::toDomain),
    averagePlannerAdherence = plannerHistory.averageAdherence,
    totalMissedLateTasks = plannerHistory.totalMissed,
)

private fun ParentReportTrendPointDto.toDomain() = ParentReportTrendPoint(
    label = label.ifBlank { date.orEmpty() },
    value = value,
)

private fun ParentReportMetricComparisonDto.toMetric(key: ParentReportMetricKey) =
    ParentReportComparisonMetric(
        key = key,
        currentValue = currentValue,
        previousValue = previousValue,
        changePercent = changePercent,
    )

private val ParentNotificationDto.severity: ParentAlertSeverity
    get() = when {
        type.contains("low_score") || type.contains("inactiv") || type.contains("missed") ->
            ParentAlertSeverity.Important

        type.contains("completed") || type.contains("quiz") -> ParentAlertSeverity.Success
        else -> ParentAlertSeverity.Info
    }

private val ParentPlannerTaskDto.plannerStatus: ParentPlannerSessionStatus
    get() = when {
        status.equals("completed", ignoreCase = true) -> ParentPlannerSessionStatus.Completed
        isOverdue || status.equals("missed", ignoreCase = true) -> ParentPlannerSessionStatus.Missed
        else -> ParentPlannerSessionStatus.Planned
    }

private fun ParentQuizResultDto.toDomain() = ParentQuizResult(
    id = id?.toString().orEmpty().ifBlank { listOf(subject, lessonTitle, date.orEmpty()).joinToString("|") },
    title = lessonTitle,
    subject = subject,
    scorePercent = score,
    dateLabel = relative.trim().ifBlank { formatParentTimestamp(date.orEmpty()) },
)

private fun ParentGamificationDto.toAchievementSummary(): ParentAchievementSummary {
    val named = achievements.mapNotNull { item ->
        item.title.trim().takeIf { it.isNotBlank() }?.let { title ->
            ParentNamedAchievement(
                key = item.achievementKey,
                title = title,
                description = item.description.trim(),
                unlockedAtLabel = formatParentTimestamp(item.unlockedAt.orEmpty()),
            )
        }
    }.ifEmpty {
        badges.mapNotNull { badge ->
            if (!badge.unlocked) return@mapNotNull null
            badge.title.trim().takeIf { it.isNotBlank() }?.let { title ->
                ParentNamedAchievement(
                    key = badge.achievementKey,
                    title = title,
                    description = badge.description.trim(),
                    unlockedAtLabel = formatParentTimestamp(badge.unlockedAt.orEmpty()),
                )
            }
        }
    }
    return ParentAchievementSummary(
        streakDays = currentStreak,
        badgeCount = achievementCount,
        level = level,
        totalXp = totalXp,
        namedAchievements = named,
    )
}

private fun ParentRoutineSlotDto.toDomain() = ParentRoutineSlot(
    start = start,
    end = end,
    title = title,
    subject = subject?.takeIf { it.isNotBlank() },
    statusLabel = status,
    status = routineStatus,
    durationMinutes = routineDurationMinutes(start, end),
)

private val ParentRoutineSlotDto.routineStatus: ParentPlannerSessionStatus
    get() = when (status.lowercase()) {
        "completed" -> ParentPlannerSessionStatus.Completed
        "missed" -> ParentPlannerSessionStatus.Missed
        else -> ParentPlannerSessionStatus.Planned
    }

private fun uniqueSupplementaryInsights(
    extras: List<ParentInsightDto>,
    existing: List<String>,
    strongestSubject: String?,
    weakestSubject: String?,
    hasOtherContent: Boolean,
): List<ParentInsight> {
    val seen = existing.map(::normalizeInsightText).filter { it.isNotBlank() }.toMutableSet()
    return extras.mapNotNull { extra ->
        val text = extra.text.trim()
        if (text.isBlank()) return@mapNotNull null
        if (extra.id == "default" && hasOtherContent) return@mapNotNull null
        if (extra.id == "best_subject" && !strongestSubject.isNullOrBlank()) return@mapNotNull null
        if (extra.id == "weak_subject" && !weakestSubject.isNullOrBlank()) return@mapNotNull null
        val normalized = normalizeInsightText(text)
        if (normalized.isBlank() || seen.any { existingText -> textsOverlap(existingText, normalized) }) {
            return@mapNotNull null
        }
        seen += normalized
        extra.toDomain()
    }
}

private fun insightKey(insight: ParentInsight): String =
    insight.id.ifBlank { normalizeInsightText(insight.text) }

private fun normalizeInsightText(value: String): String =
    value.trim().lowercase().replace(Regex("\\s+"), " ")

private fun textsOverlap(left: String, right: String): Boolean {
    if (left == right) return true
    if (left.length >= 12 && right.contains(left)) return true
    if (right.length >= 12 && left.contains(right)) return true
    return false
}

private fun routineDurationMinutes(start: String, end: String): Int? {
    val startMinutes = parseHourMinute(start) ?: return null
    val endMinutes = parseHourMinute(end) ?: return null
    val delta = endMinutes - startMinutes
    return delta.takeIf { it > 0 }
}

private fun parseHourMinute(raw: String): Int? {
    val parts = raw.trim().split(':')
    if (parts.size < 2) return null
    val hour = parts[0].toIntOrNull() ?: return null
    val minute = parts[1].take(2).toIntOrNull() ?: return null
    if (hour !in 0..23 || minute !in 0..59) return null
    return hour * 60 + minute
}

private val ParentSubjectAcademicDto.isStrong: Boolean
    get() = performanceIndicator?.lowercase() in STRONG_INDICATORS || displayPercent >= 75

private val ParentSubjectAcademicDto.displayPercent: Int
    get() = (compositeScore ?: quizAverage ?: completionRate ?: 0f).roundToInt()

private fun List<Int>.averageOrZero(): Int = if (isEmpty()) 0 else (sum().toFloat() / size).roundToInt()

internal fun isParentCalendarToday(date: String): Boolean {
    val isoDate = date.trim().take(10)
    if (isoDate.length != 10) return false
    return isoDate == java.time.LocalDate.now().toString()
}

private fun kotlinx.serialization.json.JsonObject.intOrNull(key: String): Int? {
    val primitive = get(key) as? kotlinx.serialization.json.JsonPrimitive ?: return null
    return primitive.content.toIntOrNull() ?: primitive.content.toFloatOrNull()?.roundToInt()
}
