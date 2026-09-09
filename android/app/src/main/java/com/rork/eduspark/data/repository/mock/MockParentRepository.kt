package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ParentAttendancePeriod
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentAchievementSummary
import com.rork.eduspark.data.model.ParentDailyStudyTime
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentLessonProgressItem
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLessonProgressStatus
import com.rork.eduspark.data.model.ParentLessonTopic
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
                lessons = listOf(
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
                ),
            )
        )
    }

    private companion object {
        const val MOCK_DELAY_MS = 400L
    }
}
