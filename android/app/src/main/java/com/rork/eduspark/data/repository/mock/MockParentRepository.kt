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

/**
 * PR-01/PR-13 mock parent linking. Relationship state lives in [MockParentStudentLinkStore]
 * so the Parent and Student repository contracts stay synchronized.
 */
class MockParentRepository(
    private val linkStore: MockParentStudentLinkStore,
) : ParentRepository {

    override val linkedStudents: Flow<List<ParentLinkedStudent>> = linkStore.linkedStudents

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
        return AppResult.Success(
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
        )
    }

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

    private companion object {
        const val MOCK_DELAY_MS = 400L
    }
}
