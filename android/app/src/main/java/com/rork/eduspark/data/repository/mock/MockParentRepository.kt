package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ParentAlert
import com.rork.eduspark.data.model.ParentAlertPreference
import com.rork.eduspark.data.model.ParentAlertPreferenceCategory
import com.rork.eduspark.data.model.ParentAlertSeverity
import com.rork.eduspark.data.model.ParentAlertTime
import com.rork.eduspark.data.model.ParentAlertType
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentAiInsightsSnapshot
import com.rork.eduspark.data.model.ParentAiSummary
import com.rork.eduspark.data.model.ParentAiSummaryType
import com.rork.eduspark.data.model.ParentAttendancePeriod
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentAchievementSummary
import com.rork.eduspark.data.model.ParentDailyStudyTime
import com.rork.eduspark.data.model.ParentLessonActivityEvent
import com.rork.eduspark.data.model.ParentLessonActivityTime
import com.rork.eduspark.data.model.ParentLessonActivityType
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentLessonProgressItem
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLessonProgressStatus
import com.rork.eduspark.data.model.ParentLessonTopic
import com.rork.eduspark.data.model.ParentLessonUnit
import com.rork.eduspark.data.model.ParentLessonVerificationItem
import com.rork.eduspark.data.model.ParentLessonVerificationStatus
import com.rork.eduspark.data.model.ParentLessonVerificationType
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPerformanceTrend
import com.rork.eduspark.data.model.ParentPlannerPattern
import com.rork.eduspark.data.model.ParentPlannerSession
import com.rork.eduspark.data.model.ParentPlannerSessionStatus
import com.rork.eduspark.data.model.ParentPlannerSessionTime
import com.rork.eduspark.data.model.ParentPlannerSnapshot
import com.rork.eduspark.data.model.ParentRecentActivity
import com.rork.eduspark.data.model.ParentRecentActivityType
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportStatus
import com.rork.eduspark.data.model.ParentReportSummary
import com.rork.eduspark.data.model.ParentReportSummaryType
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.data.model.ParentSubjectPerformance
import com.rork.eduspark.data.model.ParentSubjectPerformanceStatus
import com.rork.eduspark.data.model.ParentSubjectTeacher
import com.rork.eduspark.data.model.ParentSubjectTeacherStatus
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.model.ParentStudyDay
import com.rork.eduspark.data.model.ParentStudyBehaviorBestTime
import com.rork.eduspark.data.model.ParentStudyBehaviorInsight
import com.rork.eduspark.data.model.ParentStudyBehaviorInterruptions
import com.rork.eduspark.data.model.ParentTeacherAvailability
import com.rork.eduspark.data.model.ParentTeacherName
import com.rork.eduspark.data.model.ParentTeacherProfile
import com.rork.eduspark.data.model.ParentTeacherResponseTime
import com.rork.eduspark.data.model.ParentTeacherRole
import com.rork.eduspark.data.model.ParentSubjectInsight
import com.rork.eduspark.data.model.ParentSubjectInsightObservation
import com.rork.eduspark.data.model.ParentSubjectInsightStatus
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlin.math.absoluteValue

/**
 * PR-01/PR-13 mock parent linking. Relationship state lives in [MockParentStudentLinkStore]
 * so the Parent and Student repository contracts stay synchronized.
 */
class MockParentRepository(
    private val linkStore: MockParentStudentLinkStore,
) : ParentRepository {

    override val linkedStudents: Flow<List<ParentLinkedStudent>> = linkStore.linkedStudents
    private val alertSnapshots = MutableStateFlow<Map<String, ParentAlertsSnapshot>>(emptyMap())

    override suspend fun getLinkedStudents(): AppResult<List<ParentLinkedStudent>> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(linkStore.linkedStudents.value)
    }

    override suspend fun linkStudent(code: String): AppResult<ParentLinkedStudent> {
        delay(MOCK_DELAY_MS)
        return linkStore.linkStudent(code)
    }

    override suspend fun getDashboardSnapshot(studentId: String): AppResult<ParentDashboardSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentDashboardSnapshot(
                academicAveragePercent = 91,
                lessonProgressPercent = 82,
                studyHoursThisWeek = 6.4f,
                attendancePercent = 96,
                plannerItemsDue = 2,
                alertCount = 1,
                recentActivities = listOf(
                    ParentRecentActivity(
                        id = "$studentId-quiz-completed",
                        type = ParentRecentActivityType.QuizCompleted,
                    ),
                    ParentRecentActivity(
                        id = "$studentId-lesson-completed",
                        type = ParentRecentActivityType.LessonCompleted,
                    ),
                    ParentRecentActivity(
                        id = "$studentId-planner-missed",
                        type = ParentRecentActivityType.PlannerMissed,
                    ),
                ),
            )
        )
    }

    override suspend fun getPerformanceSnapshot(studentId: String): AppResult<ParentPerformanceSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentPerformanceSnapshot(
                testAveragePercent = 91,
                subjectProgressPercent = 82,
                improvementPercent = 6,
                trend = ParentPerformanceTrend(
                    currentScores = listOf(72, 78, 76, 88, 84, 94, 97),
                    previousScores = listOf(64, 69, 71, 72, 78, 79, 84),
                ),
                subjects = listOf(
                    ParentSubjectPerformance(
                        id = "$studentId-math",
                        subject = ParentSubjectKind.Mathematics,
                        percent = 76,
                        status = ParentSubjectPerformanceStatus.NeedsAttention,
                    ),
                    ParentSubjectPerformance(
                        id = "$studentId-science",
                        subject = ParentSubjectKind.Science,
                        percent = 92,
                        status = ParentSubjectPerformanceStatus.Strong,
                    ),
                    ParentSubjectPerformance(
                        id = "$studentId-arabic",
                        subject = ParentSubjectKind.Arabic,
                        percent = 88,
                        status = ParentSubjectPerformanceStatus.Strong,
                    ),
                ),
                achievementSummary = ParentAchievementSummary(
                    streakDays = 7,
                    badgeCount = 3,
                    level = 5,
                ),
            )
        )
    }

    override suspend fun getAttendanceStudyTime(
        studentId: String,
        period: ParentAttendancePeriod,
    ): AppResult<ParentAttendanceStudyTimeSnapshot> {
        delay(MOCK_DELAY_MS)
        val minutes = when (period) {
            ParentAttendancePeriod.ThisWeek -> listOf(42, 68, 54, 80, 64, 34, 42)
            ParentAttendancePeriod.PreviousWeek -> listOf(24, 42, 38, 55, 46, 18, 26)
            ParentAttendancePeriod.ThisMonth -> listOf(44, 50, 48, 56, 52, 34, 40)
        }
        val attendancePercent = when (period) {
            ParentAttendancePeriod.ThisWeek -> 96
            ParentAttendancePeriod.PreviousWeek -> 91
            ParentAttendancePeriod.ThisMonth -> 94
        }
        val activeDays = when (period) {
            ParentAttendancePeriod.ThisWeek -> 5
            ParentAttendancePeriod.PreviousWeek -> 4
            ParentAttendancePeriod.ThisMonth -> 21
        }
        val averageSessionMinutes = when (period) {
            ParentAttendancePeriod.ThisWeek -> 48
            ParentAttendancePeriod.PreviousWeek -> 42
            ParentAttendancePeriod.ThisMonth -> 45
        }

        return AppResult.Success(
            ParentAttendanceStudyTimeSnapshot(
                period = period,
                attendancePercent = attendancePercent,
                studyHours = minutes.sum() / 60f,
                activeDays = activeDays,
                averageSessionMinutes = averageSessionMinutes,
                dailyStudyMinutes = ParentStudyDay.entries.mapIndexed { index, day ->
                    ParentDailyStudyTime(
                        day = day,
                        minutes = minutes[index],
                        isToday = period == ParentAttendancePeriod.ThisWeek && index == 3,
                    )
                },
            )
        )
    }

    override suspend fun getLessonProgress(studentId: String): AppResult<ParentLessonProgressSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentLessonProgressSnapshot(
                completedLessons = 18,
                totalLessons = 24,
                lessons = lessonProgressItems(studentId),
            )
        )
    }

    override suspend fun getLessonDetails(lessonId: String): AppResult<ParentLessonDetails> {
        delay(MOCK_DELAY_MS)
        val student = linkStore.linkedStudents.value.firstOrNull { lessonId.startsWith("${it.id}-") }
            ?: return AppResult.Failure(AppError.NotFound)
        val lesson = lessonProgressItems(student.id).firstOrNull { it.id == lessonId }
            ?: return AppResult.Failure(AppError.NotFound)

        val (pagesViewed, totalPages, learningMinutes) = when (lesson.topic) {
            ParentLessonTopic.DecimalFractions -> Triple(12, 12, 28)
            ParentLessonTopic.RespiratorySystem -> Triple(8, 12, 32)
            ParentLessonTopic.ObjectPronoun -> Triple(5, 10, 21)
        }
        val missingRequirements = (lesson.totalActivities - lesson.completedActivities).coerceAtLeast(0)
        return AppResult.Success(
            ParentLessonDetails(
                lesson = lesson,
                unit = ParentLessonUnit.UnitThree,
                pagesViewed = pagesViewed,
                totalPages = totalPages,
                learningMinutes = learningMinutes,
                requirementsCompleted = lesson.completedActivities,
                requirementsTotal = lesson.totalActivities,
                checklist = lessonVerificationChecklist(lesson),
                missingRequirements = missingRequirements,
                timeline = lessonActivityTimeline(lesson.id),
            )
        )
    }

    override suspend fun getSubjectsTeachers(studentId: String): AppResult<ParentSubjectsTeachersSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentSubjectsTeachersSnapshot(
                items = listOf(
                    ParentSubjectTeacher(
                        id = "$studentId-math-teacher",
                        subject = ParentSubjectKind.Mathematics,
                        teacher = ParentTeacherProfile(
                            id = "teacher-rami-al-hassan",
                            name = ParentTeacherName.RamiAlHassan,
                            role = ParentTeacherRole.MathematicsTeacher,
                            avatarInitial = "ر",
                            availability = ParentTeacherAvailability.SundayTuesday,
                            responseTime = ParentTeacherResponseTime.SameDay,
                        ),
                        progressPercent = 76,
                        status = ParentSubjectTeacherStatus.NeedsFollowUp,
                        weeklySessions = 3,
                    ),
                    ParentSubjectTeacher(
                        id = "$studentId-science-teacher",
                        subject = ParentSubjectKind.Science,
                        teacher = ParentTeacherProfile(
                            id = "teacher-sara-al-khatib",
                            name = ParentTeacherName.SaraAlKhatib,
                            role = ParentTeacherRole.ScienceTeacher,
                            avatarInitial = "س",
                            availability = ParentTeacherAvailability.MondayWednesday,
                            responseTime = ParentTeacherResponseTime.OneSchoolDay,
                        ),
                        progressPercent = 92,
                        status = ParentSubjectTeacherStatus.OnTrack,
                        weeklySessions = 2,
                    ),
                    ParentSubjectTeacher(
                        id = "$studentId-arabic-teacher",
                        subject = ParentSubjectKind.Arabic,
                        teacher = ParentTeacherProfile(
                            id = "teacher-mona-nassar",
                            name = ParentTeacherName.MonaNassar,
                            role = ParentTeacherRole.ArabicTeacher,
                            avatarInitial = "م",
                            availability = ParentTeacherAvailability.SaturdayMonday,
                            responseTime = ParentTeacherResponseTime.SameDay,
                        ),
                        progressPercent = 88,
                        status = ParentSubjectTeacherStatus.OnTrack,
                        weeklySessions = 3,
                    ),
                ),
            )
        )
    }

    override suspend fun getPlannerSnapshot(studentId: String): AppResult<ParentPlannerSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentPlannerSnapshot(
                commitmentPercent = 84,
                completedSessions = 1,
                totalSessions = 3,
                postponedSessions = 1,
                sessions = listOf(
                    ParentPlannerSession(
                        id = "$studentId-planner-math",
                        subject = ParentSubjectKind.Mathematics,
                        time = ParentPlannerSessionTime.MathToday1600,
                        status = ParentPlannerSessionStatus.Completed,
                    ),
                    ParentPlannerSession(
                        id = "$studentId-planner-science",
                        subject = ParentSubjectKind.Science,
                        time = ParentPlannerSessionTime.ScienceToday1700,
                        status = ParentPlannerSessionStatus.Today,
                    ),
                    ParentPlannerSession(
                        id = "$studentId-planner-arabic",
                        subject = ParentSubjectKind.Arabic,
                        time = ParentPlannerSessionTime.ArabicTomorrow,
                        status = ParentPlannerSessionStatus.Postponed,
                    ),
                ),
                pattern = ParentPlannerPattern.AfterSchool,
            )
        )
    }

    override suspend fun getAlertsSnapshot(studentId: String): AppResult<ParentAlertsSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(alertSnapshotFor(studentId))
    }

    override suspend fun markParentAlertRead(studentId: String, alertId: String): AppResult<ParentAlertsSnapshot> {
        delay(MOCK_DELAY_MS)
        val snapshot = alertSnapshotFor(studentId)
        if (snapshot.alerts.none { it.id == alertId }) {
            return AppResult.Failure(AppError.NotFound)
        }
        val updated = snapshot.copy(
            alerts = snapshot.alerts.map { alert ->
                if (alert.id == alertId) alert.copy(isUnread = false) else alert
            },
        )
        alertSnapshots.update { it + (studentId to updated) }
        return AppResult.Success(updated)
    }

    override suspend fun markAllParentAlertsRead(studentId: String): AppResult<ParentAlertsSnapshot> {
        delay(MOCK_DELAY_MS)
        val snapshot = alertSnapshotFor(studentId)
        val updated = snapshot.copy(alerts = snapshot.alerts.map { it.copy(isUnread = false) })
        alertSnapshots.update { it + (studentId to updated) }
        return AppResult.Success(updated)
    }

    override suspend fun setParentAlertPreferenceEnabled(
        studentId: String,
        category: ParentAlertPreferenceCategory,
        enabled: Boolean,
    ): AppResult<ParentAlertsSnapshot> {
        delay(MOCK_DELAY_MS)
        val snapshot = alertSnapshotFor(studentId)
        if (snapshot.preferences.none { it.category == category }) {
            return AppResult.Failure(AppError.NotFound)
        }
        val updated = snapshot.copy(
            preferences = snapshot.preferences.map { preference ->
                if (preference.category == category) {
                    preference.copy(enabled = enabled)
                } else {
                    preference
                }
            },
        )
        alertSnapshots.update { it + (studentId to updated) }
        return AppResult.Success(updated)
    }

    private fun alertSnapshotFor(studentId: String): ParentAlertsSnapshot {
        val existing = alertSnapshots.value[studentId]
        if (existing != null) return existing

        val seeded = seededAlertSnapshot(studentId)
        alertSnapshots.update { it + (studentId to seeded) }
        return seeded
    }

    private fun seededAlertSnapshot(studentId: String): ParentAlertsSnapshot =
        ParentAlertsSnapshot(
            alerts = listOf(
                ParentAlert(
                    id = "$studentId-alert-math-performance",
                    type = ParentAlertType.MathPerformanceDrop,
                    time = ParentAlertTime.Minutes35Ago,
                    severity = ParentAlertSeverity.Important,
                    isUnread = true,
                ),
                ParentAlert(
                    id = "$studentId-alert-science-lesson",
                    type = ParentAlertType.ScienceLessonCompleted,
                    time = ParentAlertTime.TwoHoursAgo,
                    severity = ParentAlertSeverity.Success,
                    isUnread = true,
                ),
                ParentAlert(
                    id = "$studentId-alert-teacher-note",
                    type = ParentAlertType.TeacherNote,
                    time = ParentAlertTime.Yesterday,
                    severity = ParentAlertSeverity.Info,
                    isUnread = true,
                ),
            ),
            preferences = listOf(
                ParentAlertPreference(
                    category = ParentAlertPreferenceCategory.Performance,
                    enabled = true,
                ),
                ParentAlertPreference(
                    category = ParentAlertPreferenceCategory.LessonProgress,
                    enabled = true,
                ),
                ParentAlertPreference(
                    category = ParentAlertPreferenceCategory.TeacherNotes,
                    enabled = true,
                ),
            ),
        )

    override suspend fun getAiInsightsSnapshot(studentId: String): AppResult<ParentAiInsightsSnapshot> {
        delay(MOCK_DELAY_MS)
        return AppResult.Success(
            ParentAiInsightsSnapshot(
                summary = ParentAiSummary(type = ParentAiSummaryType.StableWithAlgebraSupport),
                subjectInsights = listOf(
                    ParentSubjectInsight(
                        id = "$studentId-ai-science",
                        subject = ParentSubjectKind.Science,
                        status = ParentSubjectInsightStatus.Strength,
                        observation = ParentSubjectInsightObservation.PositiveStableTrend,
                    ),
                    ParentSubjectInsight(
                        id = "$studentId-ai-math",
                        subject = ParentSubjectKind.Mathematics,
                        status = ParentSubjectInsightStatus.FollowUp,
                        observation = ParentSubjectInsightObservation.RepeatedAlgebraMistakes,
                    ),
                ),
                behavior = ParentStudyBehaviorInsight(
                    bestTime = ParentStudyBehaviorBestTime.Afternoon,
                    averageSessionMinutes = 48,
                    consistencyDays = 5,
                    consistencyTotalDays = 7,
                    interruptions = ParentStudyBehaviorInterruptions.Low,
                ),
            )
        )
    }

    override suspend fun getReportsSnapshot(
        studentId: String,
        period: ParentReportPeriod,
        dateRange: ParentReportDateRange?,
    ): AppResult<ParentReportsSnapshot> {
        delay(MOCK_DELAY_MS)
        val metrics = when (period) {
            ParentReportPeriod.Last7Days -> ParentReportMockMetrics(
                average = 89,
                completedLessons = 18,
                studyHours = 6.4f,
                trend = listOf(62, 68, 66, 76, 78, 82, 89),
            )
            ParentReportPeriod.Last30Days -> ParentReportMockMetrics(
                average = 91,
                completedLessons = 24,
                studyHours = 24.8f,
                trend = listOf(70, 72, 75, 78, 82, 84, 91),
            )
            ParentReportPeriod.Term -> ParentReportMockMetrics(
                average = 88,
                completedLessons = 64,
                studyHours = 72.5f,
                trend = listOf(64, 68, 73, 76, 81, 84, 88),
            )
            ParentReportPeriod.Custom -> ParentReportMockMetrics(
                average = 90,
                completedLessons = 12,
                studyHours = 8.6f,
                trend = listOf(74, 76, 78, 77, 82, 86, 90),
            )
        }.let { canned ->
            if (period == ParentReportPeriod.Custom && dateRange != null) {
                customReportMetrics(studentId = studentId, dateRange = dateRange)
            } else {
                canned
            }
        }
        return AppResult.Success(
            ParentReportsSnapshot(
                period = period,
                academicAveragePercent = metrics.average,
                completedLessons = metrics.completedLessons,
                studyHours = metrics.studyHours,
                trendScores = metrics.trend,
                summary = ParentReportSummary(
                    status = ParentReportStatus.Ready,
                    type = ParentReportSummaryType.ImprovedAverageAndLessons,
                ),
                dateRange = dateRange.takeIf { period == ParentReportPeriod.Custom },
            )
        )
    }

    private fun customReportMetrics(
        studentId: String,
        dateRange: ParentReportDateRange,
    ): ParentReportMockMetrics {
        val startDay = dateRange.startDateMillis / MILLIS_PER_DAY
        val endDay = dateRange.endDateMillis / MILLIS_PER_DAY
        val days = (endDay - startDay + 1).coerceAtLeast(1)
        val seed = (studentId.hashCode() + startDay + endDay).toInt().absoluteValue
        val average = 82 + seed % 12
        val completedLessons = (days / 2 + seed % 4).toInt().coerceAtLeast(1)
        val studyHours = (days * 70 + seed % 50) / 60f
        val trend = List(REPORT_TREND_POINT_COUNT) { index ->
            (
                average -
                    (REPORT_TREND_POINT_COUNT - index - 1) * (1 + seed % 2) +
                    (seed + index) % 3
                ).coerceIn(45, 99)
        }
        return ParentReportMockMetrics(
            average = average,
            completedLessons = completedLessons,
            studyHours = studyHours,
            trend = trend,
        )
    }

    private fun lessonProgressItems(studentId: String): List<ParentLessonProgressItem> = listOf(
        ParentLessonProgressItem(
            id = "$studentId-decimal-fractions",
            topic = ParentLessonTopic.DecimalFractions,
            subject = ParentSubjectKind.Mathematics,
            status = ParentLessonProgressStatus.Completed,
            progressPercent = 100,
            completedActivities = 6,
            totalActivities = 6,
        ),
        ParentLessonProgressItem(
            id = "$studentId-respiratory-system",
            topic = ParentLessonTopic.RespiratorySystem,
            subject = ParentSubjectKind.Science,
            status = ParentLessonProgressStatus.InProgress,
            progressPercent = 67,
            completedActivities = 4,
            totalActivities = 6,
        ),
        ParentLessonProgressItem(
            id = "$studentId-object-pronoun",
            topic = ParentLessonTopic.ObjectPronoun,
            subject = ParentSubjectKind.Arabic,
            status = ParentLessonProgressStatus.InProgress,
            progressPercent = 40,
            completedActivities = 2,
            totalActivities = 5,
        ),
    )

    private fun lessonVerificationChecklist(
        lesson: ParentLessonProgressItem,
    ): List<ParentLessonVerificationItem> = listOf(
        ParentLessonVerificationItem(
            id = "${lesson.id}-opened",
            type = ParentLessonVerificationType.OpenedLessonFile,
            status = ParentLessonVerificationStatus.Complete,
        ),
        ParentLessonVerificationItem(
            id = "${lesson.id}-read",
            type = ParentLessonVerificationType.ReadRequiredPages,
            status = ParentLessonVerificationStatus.Complete,
        ),
        ParentLessonVerificationItem(
            id = "${lesson.id}-activity",
            type = ParentLessonVerificationType.CompletedVerificationActivity,
            status = if (lesson.status == ParentLessonProgressStatus.Completed) {
                ParentLessonVerificationStatus.Complete
            } else {
                ParentLessonVerificationStatus.Missing
            },
        ),
    )

    private fun lessonActivityTimeline(lessonId: String): List<ParentLessonActivityEvent> = listOf(
        ParentLessonActivityEvent(
            id = "$lessonId-terms",
            type = ParentLessonActivityType.CompletedTermsActivity,
            time = ParentLessonActivityTime.Today1640,
        ),
        ParentLessonActivityEvent(
            id = "$lessonId-pages",
            type = ParentLessonActivityType.OpenedPages,
            time = ParentLessonActivityTime.Today1615,
        ),
        ParentLessonActivityEvent(
            id = "$lessonId-started",
            type = ParentLessonActivityType.StartedLesson,
            time = ParentLessonActivityTime.Today1600,
        ),
    )

    private data class ParentReportMockMetrics(
        val average: Int,
        val completedLessons: Int,
        val studyHours: Float,
        val trend: List<Int>,
    )

    private companion object {
        const val MOCK_DELAY_MS = 400L
        const val MILLIS_PER_DAY = 86_400_000L
        const val REPORT_TREND_POINT_COUNT = 7
    }
}
