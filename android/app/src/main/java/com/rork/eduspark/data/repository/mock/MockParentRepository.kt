package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentAchievementSummary
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPerformanceTrend
import com.rork.eduspark.data.model.ParentRecentActivity
import com.rork.eduspark.data.model.ParentRecentActivityType
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.data.model.ParentSubjectPerformance
import com.rork.eduspark.data.model.ParentSubjectPerformanceStatus
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

    private companion object {
        const val MOCK_DELAY_MS = 400L
    }
}
