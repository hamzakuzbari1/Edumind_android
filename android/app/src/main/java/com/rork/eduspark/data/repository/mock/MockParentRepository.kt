package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
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
import com.rork.eduspark.data.model.ParentRecentActivity
import com.rork.eduspark.data.model.ParentRecentActivityType
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.data.model.ParentSubjectPerformance
import com.rork.eduspark.data.model.ParentSubjectPerformanceStatus
import com.rork.eduspark.data.model.ParentStudyDay
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
