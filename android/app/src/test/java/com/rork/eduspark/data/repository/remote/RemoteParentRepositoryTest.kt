package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentAiInsightsSnapshot
import com.rork.eduspark.data.model.ParentAlertPreferenceKey
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNotesFeed
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPlannerSnapshot
import com.rork.eduspark.data.model.ParentPlannerSessionStatus
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportExport
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.auth.AuthApi
import com.rork.eduspark.data.remote.auth.ForgotPasswordRequestDto
import com.rork.eduspark.data.remote.auth.LoginRequestDto
import com.rork.eduspark.data.remote.auth.LoginResponseDto
import com.rork.eduspark.data.remote.auth.LogoutRequestDto
import com.rork.eduspark.data.remote.auth.OkResponseDto
import com.rork.eduspark.data.remote.auth.RefreshTokenRequestDto
import com.rork.eduspark.data.remote.auth.RegisterRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorResponseDto
import com.rork.eduspark.data.remote.auth.ResetPasswordRequestDto
import com.rork.eduspark.data.remote.auth.TokenResponseDto
import com.rork.eduspark.data.remote.auth.UserDto
import com.rork.eduspark.data.remote.auth.VerifyEmailRequestDto
import com.rork.eduspark.data.remote.auth.VerifyTwoFactorRequestDto
import com.rork.eduspark.data.remote.parent.ParentAchievementDto
import com.rork.eduspark.data.remote.parent.ParentAcademicIntelligenceDto
import com.rork.eduspark.data.remote.parent.ParentActivityDto
import com.rork.eduspark.data.remote.parent.ParentActivitySessionDto
import com.rork.eduspark.data.remote.parent.ParentActivityTrackingSummaryDto
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.parent.ParentAttendanceAnalyticsDto
import com.rork.eduspark.data.remote.parent.ParentAttendanceSummaryDto
import com.rork.eduspark.data.remote.parent.ParentCourseLessonProgressDto
import com.rork.eduspark.data.remote.parent.ParentCourseProgressDto
import com.rork.eduspark.data.remote.parent.ParentDashboardDto
import com.rork.eduspark.data.remote.parent.ParentExecutiveSummaryDto
import com.rork.eduspark.data.remote.parent.ParentExecutiveWeeklySnapshotDto
import com.rork.eduspark.data.remote.parent.ParentGamificationDto
import com.rork.eduspark.data.remote.parent.ParentHistoricalReportDto
import com.rork.eduspark.data.remote.parent.ParentInsightDto
import com.rork.eduspark.data.remote.parent.ParentLessonDetailDto
import com.rork.eduspark.data.remote.parent.ParentLessonProgressDto
import com.rork.eduspark.data.remote.parent.ParentLessonProgressItemDto
import com.rork.eduspark.data.remote.parent.ParentLessonProgressSummaryDto
import com.rork.eduspark.data.remote.parent.ParentLoginHistoryRowDto
import com.rork.eduspark.data.remote.parent.ParentNotificationDto
import com.rork.eduspark.data.remote.parent.ParentNotificationListDto
import com.rork.eduspark.data.remote.parent.ParentNotificationSettingsDto
import com.rork.eduspark.data.remote.parent.ParentNotificationSettingsUpdateDto
import com.rork.eduspark.data.remote.parent.ParentPlannerTaskDto
import com.rork.eduspark.data.remote.parent.ParentPlannerVisibilityDto
import com.rork.eduspark.data.remote.parent.ParentQuizResultDto
import com.rork.eduspark.data.remote.parent.ParentQuizTrackingDto
import com.rork.eduspark.data.remote.parent.ParentReportExportDto
import com.rork.eduspark.data.remote.parent.ParentReportLessonHistoryDto
import com.rork.eduspark.data.remote.parent.ParentReportAttendanceHistoryDto
import com.rork.eduspark.data.remote.parent.ParentReportPlannerHistoryDto
import com.rork.eduspark.data.remote.parent.ParentReportTrendPointDto
import com.rork.eduspark.data.remote.parent.ParentRoutineSlotDto
import com.rork.eduspark.data.remote.parent.ParentRoutineVisibilityDto
import com.rork.eduspark.data.remote.parent.ParentStudyTimeAveragesDto
import com.rork.eduspark.data.remote.parent.ParentStudyTimeOverviewDto
import com.rork.eduspark.data.remote.parent.ParentWeeklyStudyAnalyticsDto
import com.rork.eduspark.data.remote.parent.ParentSubjectAcademicDto
import com.rork.eduspark.data.remote.parent.ParentSubjectCourseDto
import com.rork.eduspark.data.remote.parent.ParentSubjectsTeachersDto
import com.rork.eduspark.data.remote.parent.ParentLinkStudentRequestDto
import com.rork.eduspark.data.remote.parent.ParentLinkStudentResponseDto
import com.rork.eduspark.data.remote.parent.ParentLinkedStudentDto
import com.rork.eduspark.data.remote.parent.ParentNotesListDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyCreateDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyDto
import com.rork.eduspark.data.remote.parent.toDomain
import com.rork.eduspark.data.remote.parent.isParentCalendarToday
import com.rork.eduspark.data.model.ParentReportsSnapshot
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RemoteParentRepositoryTest {

    @Test
    fun linkedStudentsAndSelectionRemainFromA46a() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(1, "Ali"), studentDto(2, "Sara")),
        )
        val fixture = fixture(api)

        val students = assertIs<AppResult.Success<List<ParentLinkedStudent>>>(
            fixture.repository.getLinkedStudents(),
        )
        assertEquals(listOf("1", "2"), students.data.map { it.id })
        assertEquals("1", fixture.repository.selectedStudentId.first())

        assertIs<AppResult.Success<*>>(fixture.repository.selectStudent("2"))
        assertEquals("2", fixture.repository.selectedStudentId.first())
    }

    @Test
    fun childOverviewLoadsMetricsFromDashboard() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(5, "Omar")),
            dashboards = mapOf(
                5 to ParentDashboardDto(
                    child = studentDto(5, "Omar"),
                    stats = JsonObject(
                        mapOf(
                            "weekly_sessions" to JsonPrimitive(4),
                            "weekly_quizzes" to JsonPrimitive(2),
                            "average_score" to JsonPrimitive(88),
                            "subjects_tracked" to JsonPrimitive(3),
                        ),
                    ),
                    attendance = ParentAttendanceSummaryDto(
                        attendancePercentage = 95,
                        streakDays = 6,
                        completedSessions = 10,
                        missedSessions = 1,
                    ),
                    insights = listOf(ParentInsightDto(id = "i1", text = "deferred")),
                    activity = listOf(ParentActivityDto(1, "lesson", "stale dashboard activity")),
                    courseProgress = listOf(
                        ParentCourseProgressDto(99, "Stale course", completionPercentage = 10f),
                    ),
                ),
            ),
            courses = mapOf(5 to emptyList()),
            activities = mapOf(5 to emptyList()),
        )
        val fixture = fixture(api)
        fixture.repository.getLinkedStudents()

        val overview = assertIs<AppResult.Success<ParentDashboard>>(
            fixture.repository.getChildOverview("5"),
        )
        assertEquals("Omar", overview.data.child.name)
        assertEquals(4, overview.data.weeklySessions)
        assertEquals(88, overview.data.averageScore)
        assertEquals(95, overview.data.attendancePercentage)
        assertTrue(overview.data.insights.isEmpty())
        assertTrue(overview.data.courseProgress.isEmpty())
        assertTrue(overview.data.recentActivity.isEmpty())
    }

    @Test
    fun coursesAndActivityComeFromDedicatedApis() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(7, "Lina")),
            dashboards = mapOf(7 to ParentDashboardDto(child = studentDto(7, "Lina"))),
            courses = mapOf(
                7 to listOf(
                    ParentCourseProgressDto(
                        courseId = 11,
                        courseTitle = "رياضيات",
                        subjectName = "Math",
                        completionPercentage = 50f,
                        averageScore = 80f,
                    ),
                ),
            ),
            activities = mapOf(
                7 to listOf(
                    ParentActivityDto(
                        id = 21,
                        eventType = "lesson_completed",
                        title = "أنهى درساً",
                        description = "الجبر",
                        relativeTime = "منذ ساعة",
                    ),
                ),
            ),
        )
        val fixture = fixture(api)

        val courses = assertIs<AppResult.Success<List<ParentCourseProgress>>>(
            fixture.repository.getCourseProgress("7"),
        )
        assertEquals("11", courses.data.single().courseId)
        assertEquals(0.5f, courses.data.single().completionPercentage)

        val activity = assertIs<AppResult.Success<List<ParentActivity>>>(
            fixture.repository.getRecentActivity("7"),
        )
        assertEquals("أنهى درساً", activity.data.single().title)

        val overview = assertIs<AppResult.Success<ParentDashboard>>(
            fixture.repository.getChildOverview("7"),
        )
        assertEquals("رياضيات", overview.data.courseProgress.single().courseTitle)
        assertEquals("أنهى درساً", overview.data.recentActivity.single().title)
    }

    @Test
    fun switchingChildRefreshesOverviewCoursesAndActivity() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(1, "Ali"), studentDto(2, "Sara")),
            dashboards = mapOf(
                1 to ParentDashboardDto(
                    child = studentDto(1, "Ali"),
                    stats = JsonObject(mapOf("weekly_sessions" to JsonPrimitive(1))),
                ),
                2 to ParentDashboardDto(
                    child = studentDto(2, "Sara"),
                    stats = JsonObject(mapOf("weekly_sessions" to JsonPrimitive(9))),
                ),
            ),
            courses = mapOf(
                1 to listOf(ParentCourseProgressDto(1, "Ali Course", completionPercentage = 20f)),
                2 to listOf(ParentCourseProgressDto(2, "Sara Course", completionPercentage = 80f)),
            ),
            activities = mapOf(
                1 to listOf(ParentActivityDto(1, "quiz", "Ali activity")),
                2 to listOf(ParentActivityDto(2, "quiz", "Sara activity")),
            ),
        )
        val fixture = fixture(api)
        fixture.repository.getLinkedStudents()

        val first = assertIs<AppResult.Success<ParentDashboard>>(fixture.repository.getChildOverview("1"))
        assertEquals("Ali", first.data.child.name)
        assertEquals("Ali Course", first.data.courseProgress.single().courseTitle)
        assertEquals("Ali activity", first.data.recentActivity.single().title)

        fixture.repository.selectStudent("2")
        val second = assertIs<AppResult.Success<ParentDashboard>>(fixture.repository.getChildOverview("2"))
        assertEquals("Sara", second.data.child.name)
        assertEquals(9, second.data.weeklySessions)
        assertEquals("Sara Course", second.data.courseProgress.single().courseTitle)
        assertEquals("Sara activity", second.data.recentActivity.single().title)
        assertEquals(listOf(1, 2), api.dashboardCalls)
        assertEquals(listOf(1, 2), api.courseCalls)
        assertEquals(listOf(1, 2), api.activityCalls)
    }

    @Test
    fun emptyCoursesAndActivityAreSafe() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(3, "NoData")),
            dashboards = mapOf(3 to ParentDashboardDto(child = studentDto(3, "NoData"))),
            courses = mapOf(3 to emptyList()),
            activities = mapOf(3 to emptyList()),
        )
        val fixture = fixture(api)
        val overview = assertIs<AppResult.Success<ParentDashboard>>(
            fixture.repository.getChildOverview("3"),
        )
        assertTrue(overview.data.courseProgress.isEmpty())
        assertTrue(overview.data.recentActivity.isEmpty())
        assertTrue(overview.data.insights.isEmpty())
    }

    @Test
    fun softFailsCoursesOrActivityToEmptyWhileKeepingOverview() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(8, "Soft")),
            dashboards = mapOf(
                8 to ParentDashboardDto(
                    child = studentDto(8, "Soft"),
                    stats = JsonObject(mapOf("average_score" to JsonPrimitive(70))),
                ),
            ),
            failCoursesFor = setOf(8),
            failActivityFor = setOf(8),
        )
        val fixture = fixture(api)
        val overview = assertIs<AppResult.Success<ParentDashboard>>(
            fixture.repository.getChildOverview("8"),
        )
        assertEquals(70, overview.data.averageScore)
        assertTrue(overview.data.courseProgress.isEmpty())
        assertTrue(overview.data.recentActivity.isEmpty())
    }

    @Test
    fun mapsCourseCompletionPercentToFraction() {
        val mapped = ParentCourseProgressDto(
            courseId = 1,
            courseTitle = "Physics",
            completionPercentage = 75f,
        ).toDomain()
        assertEquals(0.75f, mapped.completionPercentage)
    }

    @Test
    fun notesLoadWithRepliesForSelectedChild() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(1, "Ali")),
            notesByStudent = mapOf(
                1 to mutableListOf(
                    viewerNote(
                        id = 10,
                        studentId = 1,
                        title = "Attendance",
                        description = "Please follow up",
                        replies = listOf(
                            ParentViewerNoteReplyDto(
                                id = 100,
                                noteId = 10,
                                authorId = 7,
                                authorName = "Teacher",
                                authorRole = "teacher",
                                body = "First reply",
                                createdAt = "2026-04-01T10:00:00Z",
                            ),
                        ),
                    ),
                ),
            ),
        )
        val fixture = fixture(api)
        val feed = assertIs<AppResult.Success<ParentNotesFeed>>(fixture.repository.getParentNotes("1")).data
        assertEquals(1, feed.notes.size)
        assertEquals("Attendance", feed.notes.single().title)
        assertEquals(listOf("First reply"), feed.notes.single().replies.map { it.body })
        assertEquals(1, feed.unreadCount)
    }

    @Test
    fun acknowledgeAndReplyPersistAndChildSwitchRefreshesNotes() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(1, "Ali"), studentDto(2, "Sara")),
            notesByStudent = mutableMapOf(
                1 to mutableListOf(viewerNote(id = 11, studentId = 1, title = "Ali note")),
                2 to mutableListOf(viewerNote(id = 22, studentId = 2, title = "Sara note")),
            ),
        )
        val fixture = fixture(api)

        val acknowledged = assertIs<AppResult.Success<ParentNote>>(
            fixture.repository.acknowledgeParentNote("11"),
        ).data
        assertTrue(acknowledged.isRead)

        val replied = assertIs<AppResult.Success<ParentNote>>(
            fixture.repository.replyToParentNote("11", "Thanks teacher"),
        ).data
        assertEquals("Thanks teacher", replied.replies.last().body)
        assertTrue(replied.isRead)

        val aliNotes = assertIs<AppResult.Success<ParentNotesFeed>>(fixture.repository.getParentNotes("1")).data
        assertEquals("Ali note", aliNotes.notes.single().title)
        assertEquals(1, aliNotes.notes.single().replies.size)

        fixture.repository.selectStudent("2")
        val saraNotes = assertIs<AppResult.Success<ParentNotesFeed>>(fixture.repository.getParentNotes("2")).data
        assertEquals("Sara note", saraNotes.notes.single().title)
        assertEquals(listOf(1, 2), api.notesCalls)
    }

    @Test
    fun emptyNotesFeedIsSafe() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(3, "Empty")),
            notesByStudent = mapOf(3 to mutableListOf()),
        )
        val fixture = fixture(api)
        val feed = assertIs<AppResult.Success<ParentNotesFeed>>(fixture.repository.getParentNotes("3")).data
        assertTrue(feed.notes.isEmpty())
        assertEquals(0, feed.unreadCount)
    }

    @Test
    fun executiveSummaryMapsWeeklyBulletsAndStrength() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            executiveSummaryByStudent = mapOf(
                4 to ParentExecutiveSummaryDto(
                    studentName = "Omar",
                    hasData = true,
                    summaryLines = listOf("أكمل 3 دروس هذا الأسبوع"),
                    weeklySnapshot = ParentExecutiveWeeklySnapshotDto(
                        lessonsCompleted = 3,
                        studyHours = 4.5f,
                        strongestSubject = "رياضيات",
                        weakestSubject = "فيزياء",
                    ),
                    studyTimeAverages = ParentStudyTimeAveragesDto(dailyHours = 1.2f),
                    riskAlerts = listOf(ParentInsightDto(id = "r1", text = "انخفاض في الفيزياء", severity = "warning")),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentAiInsightsSnapshot>>(
            fixture(api).repository.getAiInsightsSnapshot("4"),
        ).data
        assertTrue(snapshot.hasData)
        assertEquals("أكمل 3 دروس هذا الأسبوع", snapshot.summary)
        assertEquals(3, snapshot.weeklySnapshot.lessonsCompleted)
        assertEquals("رياضيات", snapshot.weeklySnapshot.strongestSubject)
        assertEquals("انخفاض في الفيزياء", snapshot.riskInsights.single().text)
        assertEquals(1.2f, snapshot.studyTimeAverages.dailyHours)
        assertEquals(listOf(4), api.executiveSummaryCalls)
    }

    @Test
    fun insightsMergeKeepsExecutiveSummaryAndAddsUniqueSources() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            executiveSummaryByStudent = mapOf(
                4 to ParentExecutiveSummaryDto(
                    studentName = "Omar",
                    hasData = true,
                    summaryLines = listOf("أكمل 3 دروس هذا الأسبوع"),
                    weeklySnapshot = ParentExecutiveWeeklySnapshotDto(
                        lessonsCompleted = 3,
                        studyHours = 4.5f,
                        strongestSubject = "رياضيات",
                        weakestSubject = "فيزياء",
                    ),
                    riskAlerts = listOf(ParentInsightDto(id = "r1", text = "انخفاض في الفيزياء", severity = "warning")),
                ),
            ),
            insightsByStudent = mapOf(
                4 to listOf(
                    ParentInsightDto(
                        id = "activity_drop",
                        text = "نشاط الدراسة انخفض مقارنة بالأسبوع الماضي بنسبة 40%",
                        severity = "warning",
                    ),
                    ParentInsightDto(id = "best_subject", text = "أفضل أداء كان في رياضيات (92%)", severity = "success"),
                    ParentInsightDto(id = "r1", text = "انخفاض في الفيزياء", severity = "warning"),
                    ParentInsightDto(id = "default", text = "تابع تقدم Omar", severity = "info"),
                ),
            ),
            academicIntelligenceByStudent = mapOf(
                4 to ParentAcademicIntelligenceDto(
                    hasData = true,
                    overallAverage = 81f,
                    performanceLabel = "جيد",
                    subjects = listOf(
                        ParentSubjectAcademicDto(subjectName = "رياضيات", courseId = 1, quizAverage = 92f, completionRate = 80f),
                        ParentSubjectAcademicDto(subjectName = "فيزياء", courseId = 2, quizAverage = 61f, completionRate = 40f),
                        ParentSubjectAcademicDto(subjectName = "عربي", courseId = 3, quizAverage = 74f, completionRate = 55f),
                    ),
                ),
            ),
            attendanceByStudent = mapOf(
                4 to ParentAttendanceSummaryDto(
                    completedSessions = 4,
                    totalStudyMinutesWeek = 120,
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentAiInsightsSnapshot>>(
            fixture(api).repository.getAiInsightsSnapshot("4"),
        ).data
        assertEquals("أكمل 3 دروس هذا الأسبوع", snapshot.summary)
        assertEquals(3, snapshot.weeklySnapshot.lessonsCompleted)
        assertEquals(listOf("رياضيات", "فيزياء", "عربي"), snapshot.subjectInsights.map { it.subjectName })
        assertEquals(92, snapshot.subjectInsights.first().quizAveragePercent)
        assertTrue(snapshot.insights.any { it.id == "activity_drop" })
        assertFalse(snapshot.insights.any { it.id == "best_subject" })
        assertFalse(snapshot.insights.any { it.id == "default" })
        assertEquals(1, snapshot.riskInsights.count { it.text == "انخفاض في الفيزياء" })
        assertEquals(30, snapshot.behavior?.averageSessionMinutes)
        assertEquals(listOf(4), api.executiveSummaryCalls)
        assertEquals(listOf(4), api.insightsCalls)
        assertEquals(listOf(4), api.academicCalls)
    }

    @Test
    fun plannerMergesTodayRoutineWithoutInventingSlots() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            plannerProgressByStudent = mapOf(
                4 to ParentPlannerVisibilityDto(
                    summary = "خطة نشطة",
                    todayPlan = listOf(
                        ParentPlannerTaskDto(
                            id = 11,
                            subject = "رياضيات",
                            taskName = "واجب الجبر",
                            status = "planned",
                            statusLabel = "مجدول",
                        ),
                    ),
                ),
            ),
            studentRoutineByStudent = mapOf(
                4 to ParentRoutineVisibilityDto(
                    todayLabel = "الأحد",
                    todaySlots = listOf(
                        ParentRoutineSlotDto(
                            start = "08:00",
                            end = "09:00",
                            title = "مراجعة",
                            subject = "فيزياء",
                            status = "completed",
                        ),
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentPlannerSnapshot>>(
            fixture(api).repository.getPlannerSnapshot("4"),
        ).data
        assertEquals("الأحد", snapshot.todayLabel)
        assertEquals(1, snapshot.todayRoutine.size)
        assertEquals("مراجعة", snapshot.todayRoutine.single().title)
        assertEquals("فيزياء", snapshot.todayRoutine.single().subject)
        assertEquals("08:00 – 09:00", snapshot.todayRoutine.single().timeLabel)
        assertEquals(60, snapshot.todayRoutine.single().durationMinutes)
        assertEquals(ParentPlannerSessionStatus.Completed, snapshot.todayRoutine.single().status)
        assertEquals("واجب الجبر", snapshot.sessions.single().taskName)
        assertEquals(listOf(4), api.studentRoutineCalls)
    }

    @Test
    fun performanceMapsRecentQuizzesXpAndNamedAchievements() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            academicIntelligenceByStudent = mapOf(
                4 to ParentAcademicIntelligenceDto(hasData = true, overallAverage = 80f, summary = "أداء جيد"),
            ),
            quizByStudent = mapOf(
                4 to ParentQuizTrackingDto(
                    averageScore = 80,
                    recent = listOf(
                        ParentQuizResultDto(
                            id = 21,
                            subject = "رياضيات",
                            lessonTitle = "اختبار الجبر",
                            score = 88,
                            date = "2026-09-16T10:00:00Z",
                            relative = "أمس",
                        ),
                        ParentQuizResultDto(
                            id = 20,
                            subject = "فيزياء",
                            lessonTitle = "اختبار الحركة",
                            score = 72,
                            date = "2026-09-10T10:00:00Z",
                            relative = "",
                        ),
                    ),
                ),
            ),
            dashboards = mapOf(
                4 to ParentDashboardDto(
                    child = studentDto(4, "Omar"),
                    gamification = ParentGamificationDto(
                        level = 4,
                        totalXp = 1250,
                        currentStreak = 6,
                        achievementCount = 2,
                        achievements = listOf(
                            ParentAchievementDto(
                                achievementKey = "first_quiz",
                                title = "أول اختبار",
                                description = "أكمل أول اختبار",
                                unlockedAt = "2026-09-01T08:00:00Z",
                            ),
                        ),
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentPerformanceSnapshot>>(
            fixture(api).repository.getPerformanceSnapshot("4"),
        ).data
        assertEquals(listOf("اختبار الجبر", "اختبار الحركة"), snapshot.recentQuizzes.map { it.title })
        assertEquals("رياضيات", snapshot.recentQuizzes.first().subject)
        assertEquals(88, snapshot.recentQuizzes.first().scorePercent)
        assertEquals("أمس", snapshot.recentQuizzes.first().dateLabel)
        assertEquals("2026-09-10 10:00", snapshot.recentQuizzes.last().dateLabel)
        assertEquals(1250, snapshot.achievements?.totalXp)
        assertEquals(4, snapshot.achievements?.level)
        assertEquals(6, snapshot.achievements?.streakDays)
        assertEquals(2, snapshot.achievements?.badgeCount)
        assertEquals("أول اختبار", snapshot.achievements?.namedAchievements?.single()?.title)
        assertTrue(snapshot.trend != null)
    }

    @Test
    fun dashboardSnapshotIncludesLatestTeacherNoteWhenPresent() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            dashboards = mapOf(4 to ParentDashboardDto(child = studentDto(4, "Omar"))),
            notesByStudent = mapOf(
                4 to mutableListOf(
                    viewerNote(
                        id = 9,
                        studentId = 4,
                        title = "متابعة الجبر",
                        description = "راجع الصفحة 12",
                    ).copy(categoryLabelAr = "رياضيات", statusLabelAr = "جديد"),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentDashboardSnapshot>>(
            fixture(api).repository.getDashboardSnapshot("4"),
        ).data
        assertEquals("متابعة الجبر", snapshot.latestTeacherNote?.title)
        assertEquals("راجع الصفحة 12", snapshot.latestTeacherNote?.description)
        assertEquals("رياضيات", snapshot.latestTeacherNote?.categoryLabel)
        assertEquals(listOf(4), api.notesCalls)
    }

    @Test
    fun dashboardSnapshotOmitsTeacherNoteWhenFeedEmpty() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            dashboards = mapOf(4 to ParentDashboardDto(child = studentDto(4, "Omar"))),
            notesByStudent = mapOf(4 to mutableListOf()),
        )
        val snapshot = assertIs<AppResult.Success<ParentDashboardSnapshot>>(
            fixture(api).repository.getDashboardSnapshot("4"),
        ).data
        assertNull(snapshot.latestTeacherNote)
    }

    @Test
    fun dashboardSnapshotUsesRealInsightForHomeTeaser() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            dashboards = mapOf(
                4 to ParentDashboardDto(
                    child = studentDto(4, "Omar"),
                    insights = listOf(
                        ParentInsightDto(id = "default", text = "تابع تقدم Omar"),
                        ParentInsightDto(
                            id = "activity_drop",
                            text = "نشاط الدراسة انخفض مقارنة بالأسبوع الماضي بنسبة 40%",
                        ),
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentDashboardSnapshot>>(
            fixture(api).repository.getDashboardSnapshot("4"),
        ).data
        assertEquals("نشاط الدراسة انخفض مقارنة بالأسبوع الماضي بنسبة 40%", snapshot.latestInsightText)
    }

    @Test
    fun dashboardSnapshotSkipsDefaultInsightPlaceholder() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            dashboards = mapOf(
                4 to ParentDashboardDto(
                    child = studentDto(4, "Omar"),
                    insights = listOf(ParentInsightDto(id = "default", text = "تابع تقدم Omar")),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentDashboardSnapshot>>(
            fixture(api).repository.getDashboardSnapshot("4"),
        ).data
        assertNull(snapshot.latestInsightText)
    }

    @Test
    fun dashboardSnapshotFallsBackToAcademicSummaryWhenInsightsEmpty() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            dashboards = mapOf(
                4 to ParentDashboardDto(
                    child = studentDto(4, "Omar"),
                    academicIntelligence = ParentAcademicIntelligenceDto(
                        hasData = true,
                        summary = "الأداء جيد في معظم المواد",
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentDashboardSnapshot>>(
            fixture(api).repository.getDashboardSnapshot("4"),
        ).data
        assertEquals("الأداء جيد في معظم المواد", snapshot.latestInsightText)
    }

    @Test
    fun attendanceMergesAnalyticsSessionsAndDoesNotInventAverages() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            attendanceByStudent = mapOf(
                4 to ParentAttendanceSummaryDto(
                    attendancePercentage = 80,
                    weeklyConsistency = 70,
                    monthlyOverview = listOf(
                        com.rork.eduspark.data.remote.parent.ParentAttendanceMonthWeekDto(
                            weekIndex = 1,
                            label = "أسبوع 1",
                            present = 3,
                            partial = 1,
                            absent = 1,
                        ),
                    ),
                    consistencyBars = listOf(
                        com.rork.eduspark.data.remote.parent.ParentAttendanceConsistencyWeekDto(
                            weekLabel = "هذا الأسبوع",
                            consistency = 80,
                            presentDays = 4,
                            totalDays = 7,
                        ),
                    ),
                    aiInsights = listOf("حضور منتظم هذا الأسبوع"),
                ),
            ),
            attendanceAnalyticsByStudent = mapOf(
                4 to ParentAttendanceAnalyticsDto(
                    overview = ParentStudyTimeOverviewDto(
                        weekMinutes = 180,
                        averages = ParentStudyTimeAveragesDto(dailyHours = 0.8f, weeklyHours = 3f),
                    ),
                    weeklyAnalytics = ParentWeeklyStudyAnalyticsDto(
                        periodLabel = "هذا الأسبوع",
                        comparisonPercent = 12f,
                        activeDaysCount = 4,
                    ),
                    loginHistory = listOf(
                        ParentLoginHistoryRowDto(
                            id = 11,
                            date = "2026-09-16",
                            dayLabel = "الثلاثاء",
                            loginAt = "2026-09-16T08:00:00Z",
                            logoutAt = "2026-09-16T09:10:00Z",
                            activeMinutes = 70,
                        ),
                    ),
                ),
            ),
            activitySessionsByStudent = mapOf(
                4 to listOf(
                    ParentActivitySessionDto(
                        id = 11,
                        loginAt = "2026-09-16T08:00:00Z",
                        logoutAt = "2026-09-16T09:10:00Z",
                        activeMinutes = 70,
                    ),
                    ParentActivitySessionDto(
                        id = 12,
                        loginAt = "2026-09-15T18:00:00Z",
                        activeMinutes = 20,
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentAttendanceStudyTimeSnapshot>>(
            fixture(api).repository.getAttendanceStudyTime("4"),
        ).data
        assertTrue(snapshot.hasData)
        assertEquals(80, snapshot.attendancePercent)
        assertEquals(3f, snapshot.studyHours)
        assertEquals(setOf("11", "12"), snapshot.loginSessions.map { it.id }.toSet())
        assertEquals(45, snapshot.averageSessionMinutes)
        assertEquals(3, snapshot.statusBreakdown.presentDays)
        assertEquals(1, snapshot.statusBreakdown.partialDays)
        assertEquals(1, snapshot.statusBreakdown.absentDays)
        assertEquals("حضور منتظم هذا الأسبوع", snapshot.aiInsights.single())
        assertEquals(0.8f, snapshot.studyTimeAverages.dailyHours)
        assertEquals(12f, snapshot.weeklyComparisonPercent)
        assertEquals(listOf(4), api.attendanceCalls)
        assertEquals(listOf(4), api.analyticsCalls)
        assertEquals(listOf(4), api.sessionCalls)
    }

    @Test
    fun emptyAttendanceAndAnalyticsStayEmpty() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        val snapshot = assertIs<AppResult.Success<ParentAttendanceStudyTimeSnapshot>>(
            fixture(api).repository.getAttendanceStudyTime("4"),
        ).data
        assertTrue(!snapshot.hasData)
        assertTrue(snapshot.loginSessions.isEmpty())
        assertEquals(0, snapshot.averageSessionMinutes)
        assertTrue(!snapshot.statusBreakdown.hasValues)
    }

    @Test
    fun weeklyCalendarTodayUsesIsoDateNotActiveFlag() {
        assertTrue(isParentCalendarToday(java.time.LocalDate.now().toString()))
        assertTrue(!isParentCalendarToday("2020-01-01"))
        assertTrue(!isParentCalendarToday(""))
        assertTrue(!isParentCalendarToday("present"))
    }

    @Test
    fun lessonProgressFlattensNestedCoursesAndUsesSummary() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            lessonProgressByStudent = mapOf(
                4 to ParentLessonProgressDto(
                    studentId = 4,
                    courses = listOf(
                        ParentCourseLessonProgressDto(
                            courseId = 1,
                            courseTitle = "Math",
                            lessons = listOf(
                                ParentLessonProgressItemDto(
                                    lessonId = 55,
                                    lessonTitle = "Algebra",
                                    courseTitle = "Math",
                                    status = "completed",
                                    statusLabel = "مكتمل",
                                    completionPercent = 100,
                                ),
                            ),
                        ),
                    ),
                    summary = ParentLessonProgressSummaryDto(completedLessons = 1, totalLessons = 3),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentLessonProgressSnapshot>>(
            fixture(api).repository.getLessonProgress("4"),
        ).data
        assertEquals("55", snapshot.lessons.single().id)
        assertEquals("Algebra", snapshot.lessons.single().title)
        assertTrue(snapshot.lessons.single().isCompleted)
        assertEquals(1, snapshot.completedLessons)
        assertEquals(3, snapshot.totalLessons)
    }

    @Test
    fun subjectsTeachersCombinesEnrolledAndAvailable() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            subjectsTeachersByStudent = mapOf(
                4 to ParentSubjectsTeachersDto(
                    studentId = 4,
                    enrolled = listOf(
                        ParentSubjectCourseDto(
                            courseId = 1,
                            subjectName = "رياضيات",
                            teacherName = "معلم 1",
                            enrolled = true,
                            subscriptionStatus = "active",
                            threadId = 31,
                        ),
                    ),
                    available = listOf(
                        ParentSubjectCourseDto(
                            courseId = 2,
                            subjectName = "علوم",
                            teacherName = "معلم 2",
                            enrolled = false,
                            subscriptionStatus = "pending",
                        ),
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentSubjectsTeachersSnapshot>>(
            fixture(api).repository.getSubjectsTeachers("4"),
        ).data
        assertEquals(listOf("رياضيات", "علوم"), snapshot.items.map { it.subjectName })
        assertEquals("31", snapshot.items.first().threadId)
        assertEquals(null, snapshot.items.last().threadId)
    }

    @Test
    fun alertsPassStudentIdAndMapBooleanPreferenceFlags() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            notificationsByStudent = mapOf(
                4 to ParentNotificationListDto(
                    items = listOf(
                        ParentNotificationDto(id = 9, title = "دخول", body = "سجل الطالب", isRead = false),
                    ),
                    unreadCount = 1,
                ),
            ),
            notificationSettingsByStudent = mapOf(
                4 to ParentNotificationSettingsDto(
                    studentId = 4,
                    loginAlerts = true,
                    logoutAlerts = false,
                    lessonAlerts = true,
                ),
            ),
        )
        val repository = fixture(api).repository
        val snapshot = assertIs<AppResult.Success<ParentAlertsSnapshot>>(
            repository.getAlertsSnapshot("4"),
        ).data
        assertEquals(4, api.lastNotificationSettingsStudentId)
        assertEquals(1, snapshot.unreadCount)
        assertEquals(1, repository.unreadAlertCount.first())
        assertEquals("دخول", snapshot.alerts.single().title)
        assertTrue(snapshot.preferences.first { it.key == ParentAlertPreferenceKey.Login }.enabled)
        assertTrue(!snapshot.preferences.first { it.key == ParentAlertPreferenceKey.Logout }.enabled)
    }

    @Test
    fun alertPreferenceUpdateSendsOnlyChangedFlagAndReloads() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            notificationsByStudent = mapOf(4 to ParentNotificationListDto(unreadCount = 0)),
            notificationSettingsByStudent = mapOf(4 to ParentNotificationSettingsDto(studentId = 4)),
        )
        val snapshot = assertIs<AppResult.Success<ParentAlertsSnapshot>>(
            fixture(api).repository.setParentAlertPreferenceEnabled(
                studentId = "4",
                key = ParentAlertPreferenceKey.Quiz,
                enabled = false,
            ),
        ).data
        assertEquals(ParentNotificationSettingsUpdateDto(quizAlerts = false), api.lastSettingsUpdate)
        assertTrue(!snapshot.preferences.first { it.key == ParentAlertPreferenceKey.Quiz }.enabled)
    }

    @Test
    fun markingAlertReadFlipsUnreadStateFromBackend() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            notificationsByStudent = mapOf(
                4 to ParentNotificationListDto(
                    items = listOf(ParentNotificationDto(id = 9, title = "دخول", isRead = false)),
                    unreadCount = 1,
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentAlertsSnapshot>>(
            fixture(api).repository.markParentAlertRead("4", "9"),
        ).data
        assertEquals(listOf(9), api.markedNotificationIds)
        assertEquals(0, snapshot.unreadCount)
        assertTrue(!snapshot.alerts.single().isUnread)
    }

    @Test
    fun parentHttpDetailIsNotHidden() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        api.lessonProgressFailure = ApiCallResult.HttpFailure(404, detail = "الطالب غير مرتبط")
        val result = fixture(api).repository.getLessonProgress("4")
        assertEquals(AppError.Domain("الطالب غير مرتبط"), assertIs<AppResult.Failure>(result).error)
    }

    @Test
    fun exportHistoricalReportSendsStudentPeriodAndPdfFormat() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        val exported = assertIs<AppResult.Success<ParentReportExport>>(
            fixture(api).repository.exportHistoricalReport(
                studentId = "4",
                period = ParentReportPeriod.ThisWeek,
                customDateRange = null,
            ),
        ).data
        assertEquals(
            FakeParentApi.ExportCall(
                studentId = 4,
                period = "this_week",
                startDate = null,
                endDate = null,
                format = "pdf",
            ),
            api.lastExportCall,
        )
        assertEquals("eduspark-report-Omar-this_week.pdf", exported.filename)
        assertEquals("application/pdf", exported.mimeType)
        assertTrue(exported.bytes.isNotEmpty())
    }

    @Test
    fun exportCustomRangeSendsStartAndEndDates() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        assertIs<AppResult.Success<ParentReportExport>>(
            fixture(api).repository.exportHistoricalReport(
                studentId = "4",
                period = ParentReportPeriod.Custom,
                customDateRange = ParentReportDateRange(
                    startDateMillis = 1_766_044_800_000L,
                    endDateMillis = 1_766_131_200_000L,
                ),
            ),
        )
        assertEquals("custom", api.lastExportCall?.period)
        assertEquals("pdf", api.lastExportCall?.format)
        assertTrue(!api.lastExportCall?.startDate.isNullOrBlank())
        assertTrue(!api.lastExportCall?.endDate.isNullOrBlank())
    }

    @Test
    fun exportHistoricalReportForwardsCsvAndXlsxFormats() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        assertIs<AppResult.Success<ParentReportExport>>(
            fixture(api).repository.exportHistoricalReport(
                studentId = "4",
                period = ParentReportPeriod.ThisMonth,
                customDateRange = null,
                format = "csv",
            ),
        )
        assertEquals("csv", api.lastExportCall?.format)
        assertIs<AppResult.Success<ParentReportExport>>(
            fixture(api).repository.exportHistoricalReport(
                studentId = "4",
                period = ParentReportPeriod.ThisMonth,
                customDateRange = null,
                format = "xlsx",
            ),
        )
        assertEquals("xlsx", api.lastExportCall?.format)
    }

    @Test
    fun historicalReportMapsLessonPlannerAndLoginHistory() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            historicalReportsByStudent = mapOf(
                4 to ParentHistoricalReportDto(
                    period = "this_week",
                    periodLabel = "هذا الأسبوع",
                    hasData = true,
                    lessonHistory = ParentReportLessonHistoryDto(
                        weekly = listOf(ParentReportTrendPointDto(label = "أ1", value = 2f)),
                        totalInPeriod = 2,
                    ),
                    attendanceHistory = ParentReportAttendanceHistoryDto(
                        loginSessions = listOf(
                            ParentLoginHistoryRowDto(
                                id = 9,
                                dayLabel = "الأحد",
                                loginAt = "2026-09-13T08:00:00Z",
                                logoutAt = "2026-09-13T09:00:00Z",
                                activeMinutes = 60,
                            ),
                        ),
                        dailyStudyTrend = listOf(ParentReportTrendPointDto(label = "أحد", value = 40f)),
                        totalStudyHours = 1f,
                    ),
                    plannerHistory = ParentReportPlannerHistoryDto(
                        adherenceTrend = listOf(ParentReportTrendPointDto(label = "أ1", value = 80f)),
                        missedTasksTrend = listOf(ParentReportTrendPointDto(label = "أ1", value = 1f)),
                        averageAdherence = 80f,
                        totalMissed = 1,
                    ),
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentReportsSnapshot>>(
            fixture(api).repository.getReportsSnapshot("4", ParentReportPeriod.ThisWeek, null),
        ).data
        assertTrue(snapshot.hasData)
        assertEquals(2, snapshot.completedLessons)
        assertEquals(1, snapshot.weeklyLessonHistory.size)
        assertEquals("9", snapshot.loginSessions.single().id)
        assertEquals(80f, snapshot.plannerAdherenceHistory.single().value)
        assertEquals(1f, snapshot.missedLateTaskHistory.single().value)
    }

    @Test
    fun exportDoesNotInventSevenOrThirtyDayPeriods() {
        val supported = ParentReportPeriod.entries.map { it.apiValue }
        assertEquals(
            listOf("this_week", "last_week", "this_month", "last_month", "custom"),
            supported,
        )
    }

    @Test
    fun linkStudentSendsTrimmedUppercaseLinkCodeAndSelectsNewChild() = runBlocking {
        val api = FakeParentApi(students = mutableListOf(studentDto(1, "Ali")))
        api.linkResult = ApiCallResult.Success(ParentLinkStudentResponseDto(ok = true, studentId = 12))
        api.onLinked = { api.studentList += studentDto(12, "Lina") }
        val fixture = fixture(api)

        fixture.repository.getLinkedStudents()
        val linked = assertIs<AppResult.Success<ParentLinkedStudent>>(
            fixture.repository.linkStudent("  ab12cd34  "),
        ).data

        assertEquals("AB12CD34", api.lastLinkRequest?.linkCode)
        assertEquals("12", linked.id)
        assertEquals("Lina", linked.name)
        assertEquals("12", fixture.repository.selectedStudentId.first())
        assertEquals(listOf("1", "12"), fixture.repository.linkedStudents.first().map { it.id })
    }

    @Test
    fun linkStudentRejectsUnknownCodeWithBackendDetail() = runBlocking {
        val api = FakeParentApi()
        api.linkResult = ApiCallResult.HttpFailure(404, detail = "رمز الربط غير صالح")
        val fixture = fixture(api)

        val result = fixture.repository.linkStudent("ZZZZZZZZ")
        assertIs<AppResult.Failure>(result)
        assertEquals(AppError.Domain("رمز الربط غير صالح"), result.error)
        assertEquals("ZZZZZZZZ", api.lastLinkRequest?.linkCode)
    }

    @Test
    fun alreadyLinkedCodeReturnsExistingStudent() = runBlocking {
        val api = FakeParentApi(students = mutableListOf(studentDto(7, "Omar")))
        api.linkResult = ApiCallResult.Success(ParentLinkStudentResponseDto(ok = true, studentId = 7))
        val fixture = fixture(api)

        val linked = assertIs<AppResult.Success<ParentLinkedStudent>>(
            fixture.repository.linkStudent("EXISTING1"),
        ).data
        assertEquals("7", linked.id)
        assertEquals("Omar", linked.name)
        assertEquals(1, api.studentList.size)
    }

    @Test
    fun shortCodeIsRejectedBeforeRequest() = runBlocking {
        val api = FakeParentApi()
        val fixture = fixture(api)
        val result = fixture.repository.linkStudent("AB")
        assertIs<AppResult.Failure>(result)
        assertEquals(AppError.Validation(mapOf("link_code" to "invalid_length")), result.error)
        assertEquals(null, api.lastLinkRequest)
    }

    @Test
    fun linkRequestJsonMatchesFastApiLinkCodeField() {
        val encoded = Json.encodeToString(
            ParentLinkStudentRequestDto.serializer(),
            ParentLinkStudentRequestDto(linkCode = "AB12CD34"),
        )
        assertEquals("""{"link_code":"AB12CD34"}""", encoded)
    }

    private suspend fun fixture(api: FakeParentApi): Fixture {
        val auth = FakeParentAuthApi()
        val store = InMemoryTokenStore().apply {
            write(StoredSession("access", "refresh", 7, "99"))
        }
        val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
        return Fixture(
            repository = RemoteParentRepository(
                api = api,
                tokenStore = store,
                refreshCoordinator = AuthRefreshCoordinator(auth, store),
                authRepository = authRepository,
            ),
        )
    }

    private data class Fixture(val repository: RemoteParentRepository)

    private fun studentDto(id: Int, name: String) = ParentLinkedStudentDto(
        id = id,
        name = name,
        email = "$name@example.com",
        gradeLabel = "Grade 10",
        academicStatusLabel = "active",
    )

    private fun viewerNote(
        id: Int,
        studentId: Int,
        title: String,
        description: String = title,
        isRead: Boolean = false,
        replies: List<ParentViewerNoteReplyDto> = emptyList(),
    ) = ParentViewerNoteDto(
        id = id,
        studentId = studentId,
        title = title,
        description = description,
        createdByName = "Teacher",
        createdAt = "2026-04-01T09:00:00Z",
        isReadByViewer = isRead,
        replyCount = replies.size,
        replies = replies,
        canReply = true,
        isClosed = false,
        status = if (isRead) "read" else "new",
    )
}

private class FakeParentApi(
    students: List<ParentLinkedStudentDto> = emptyList(),
    private val dashboards: Map<Int, ParentDashboardDto> = emptyMap(),
    private val courses: Map<Int, List<ParentCourseProgressDto>> = emptyMap(),
    private val activities: Map<Int, List<ParentActivityDto>> = emptyMap(),
    private val notesByStudent: Map<Int, MutableList<ParentViewerNoteDto>> = emptyMap(),
    private val failCoursesFor: Set<Int> = emptySet(),
    private val failActivityFor: Set<Int> = emptySet(),
    private val lessonProgressByStudent: Map<Int, ParentLessonProgressDto> = emptyMap(),
    private val insightsByStudent: Map<Int, List<ParentInsightDto>> = emptyMap(),
    private val academicIntelligenceByStudent: Map<Int, ParentAcademicIntelligenceDto> = emptyMap(),
    private val subjectsTeachersByStudent: Map<Int, ParentSubjectsTeachersDto> = emptyMap(),
    private val attendanceByStudent: Map<Int, ParentAttendanceSummaryDto> = emptyMap(),
    private val attendanceAnalyticsByStudent: Map<Int, ParentAttendanceAnalyticsDto> = emptyMap(),
    private val activitySessionsByStudent: Map<Int, List<ParentActivitySessionDto>> = emptyMap(),
    private val executiveSummaryByStudent: Map<Int, ParentExecutiveSummaryDto> = emptyMap(),
    private val historicalReportsByStudent: Map<Int, ParentHistoricalReportDto> = emptyMap(),
    private val plannerProgressByStudent: Map<Int, ParentPlannerVisibilityDto> = emptyMap(),
    private val studentRoutineByStudent: Map<Int, ParentRoutineVisibilityDto> = emptyMap(),
    private val quizByStudent: Map<Int, ParentQuizTrackingDto> = emptyMap(),
    notificationsByStudent: Map<Int, ParentNotificationListDto> = emptyMap(),
    notificationSettingsByStudent: Map<Int, ParentNotificationSettingsDto> = emptyMap(),
) : ParentApi {
    val studentList = students.toMutableList()
    data class ExportCall(
        val studentId: Int,
        val period: String,
        val startDate: String?,
        val endDate: String?,
        val format: String,
    )
    var lastLinkRequest: ParentLinkStudentRequestDto? = null
    var linkResult: ApiCallResult<ParentLinkStudentResponseDto> =
        ApiCallResult.HttpFailure(404, detail = "رمز الربط غير صالح")
    var onLinked: (() -> Unit)? = null
    val dashboardCalls = mutableListOf<Int>()
    val courseCalls = mutableListOf<Int>()
    val activityCalls = mutableListOf<Int>()
    val notesCalls = mutableListOf<Int>()
    val attendanceCalls = mutableListOf<Int>()
    val analyticsCalls = mutableListOf<Int>()
    val sessionCalls = mutableListOf<Int>()
    val executiveSummaryCalls = mutableListOf<Int>()
    val insightsCalls = mutableListOf<Int>()
    val academicCalls = mutableListOf<Int>()
    val studentRoutineCalls = mutableListOf<Int>()
    var lastNotificationSettingsStudentId: Int? = null
    var lessonProgressFailure: ApiCallResult.HttpFailure? = null
    var lastSettingsUpdate: ParentNotificationSettingsUpdateDto? = null
    var lastExportCall: ExportCall? = null
    var exportResult: ApiCallResult<ParentReportExportDto>? = null
    val markedNotificationIds = mutableListOf<Int>()
    private val notificationState = notificationsByStudent.mapValues { it.value }.toMutableMap()
    private val notificationSettingsState = notificationSettingsByStudent.toMutableMap()
    private var nextReplyId = 1000

    override suspend fun students(accessToken: String): ApiCallResult<List<ParentLinkedStudentDto>> =
        ApiCallResult.Success(studentList.toList())

    override suspend fun dashboard(accessToken: String, studentId: Int): ApiCallResult<ParentDashboardDto> {
        dashboardCalls += studentId
        return dashboards[studentId]?.let { ApiCallResult.Success(it) }
            ?: ApiCallResult.HttpFailure(404)
    }

    override suspend fun courseProgress(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<List<ParentCourseProgressDto>> {
        courseCalls += studentId
        if (studentId in failCoursesFor) return ApiCallResult.HttpFailure(500)
        return ApiCallResult.Success(courses[studentId].orEmpty())
    }

    override suspend fun activity(
        accessToken: String,
        studentId: Int,
        limit: Int,
    ): ApiCallResult<List<ParentActivityDto>> {
        activityCalls += studentId
        if (studentId in failActivityFor) return ApiCallResult.NetworkFailure
        return ApiCallResult.Success(activities[studentId].orEmpty().take(limit))
    }

    override suspend fun notes(
        accessToken: String,
        studentId: Int,
        limit: Int,
        sort: String,
    ): ApiCallResult<ParentNotesListDto> {
        notesCalls += studentId
        val notes = notesByStudent[studentId].orEmpty().take(limit)
        return ApiCallResult.Success(
            ParentNotesListDto(
                notes = notes,
                total = notes.size,
                unreadCount = notes.count { !it.isReadByViewer },
            ),
        )
    }

    override suspend fun markNoteRead(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto> =
        markReadInternal(noteId)

    override suspend fun acknowledgeNote(accessToken: String, noteId: Int): ApiCallResult<ParentViewerNoteDto> =
        markReadInternal(noteId)

    override suspend fun replyToNote(
        accessToken: String,
        noteId: Int,
        body: ParentViewerNoteReplyCreateDto,
    ): ApiCallResult<ParentViewerNoteDto> {
        val bucket = notesByStudent.values.firstOrNull { list -> list.any { it.id == noteId } }
            ?: return ApiCallResult.HttpFailure(404)
        val index = bucket.indexOfFirst { it.id == noteId }
        if (index < 0) return ApiCallResult.HttpFailure(404)
        val existing = bucket[index]
        if (existing.isClosed) return ApiCallResult.HttpFailure(400, detail = "closed")
        val reply = ParentViewerNoteReplyDto(
            id = nextReplyId++,
            noteId = noteId,
            authorId = 99,
            authorName = "Parent",
            authorRole = "parent",
            body = body.body,
            createdAt = "2026-04-02T12:00:00Z",
            updatedAt = "2026-04-02T12:00:00Z",
        )
        val updated = existing.copy(
            isReadByViewer = true,
            status = "replied",
            replies = existing.replies + reply,
            replyCount = existing.replyCount + 1,
        )
        bucket[index] = updated
        return ApiCallResult.Success(updated)
    }

    override suspend fun linkStudent(
        accessToken: String,
        body: ParentLinkStudentRequestDto,
    ): ApiCallResult<ParentLinkStudentResponseDto> {
        lastLinkRequest = body
        val result = linkResult
        if (result is ApiCallResult.Success) onLinked?.invoke()
        return result
    }

    override suspend fun lessonProgress(accessToken: String, studentId: Int): ApiCallResult<ParentLessonProgressDto> =
        lessonProgressFailure ?: ApiCallResult.Success(
            lessonProgressByStudent[studentId] ?: ParentLessonProgressDto(),
        )

    override suspend fun lessonDetails(
        accessToken: String,
        studentId: Int,
        lessonId: String,
    ): ApiCallResult<ParentLessonDetailDto> =
        ApiCallResult.Success(ParentLessonDetailDto(lessonId = lessonId.toIntOrNull() ?: 0))

    override suspend fun subjectsTeachers(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentSubjectsTeachersDto> =
        ApiCallResult.Success(subjectsTeachersByStudent[studentId] ?: ParentSubjectsTeachersDto())

    override suspend fun plannerVisibility(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentPlannerVisibilityDto> = ApiCallResult.Success(ParentPlannerVisibilityDto())

    override suspend fun plannerProgress(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentPlannerVisibilityDto> =
        ApiCallResult.Success(plannerProgressByStudent[studentId] ?: ParentPlannerVisibilityDto())

    override suspend fun studentRoutine(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentRoutineVisibilityDto> {
        studentRoutineCalls += studentId
        return ApiCallResult.Success(studentRoutineByStudent[studentId] ?: ParentRoutineVisibilityDto())
    }

    override suspend fun attendance(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentAttendanceSummaryDto> {
        attendanceCalls += studentId
        return ApiCallResult.Success(attendanceByStudent[studentId] ?: ParentAttendanceSummaryDto())
    }

    override suspend fun activityTrackingSummary(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentActivityTrackingSummaryDto> =
        ApiCallResult.Success(ParentActivityTrackingSummaryDto())

    override suspend fun activityTrackingAnalytics(
        accessToken: String,
        studentId: Int,
        weekOffset: Int,
        monthOffset: Int,
        sessionLimit: Int,
    ): ApiCallResult<ParentAttendanceAnalyticsDto> {
        analyticsCalls += studentId
        return ApiCallResult.Success(attendanceAnalyticsByStudent[studentId] ?: ParentAttendanceAnalyticsDto())
    }

    override suspend fun activityTrackingSessions(
        accessToken: String,
        studentId: Int,
        limit: Int,
    ): ApiCallResult<List<ParentActivitySessionDto>> {
        sessionCalls += studentId
        return ApiCallResult.Success(activitySessionsByStudent[studentId].orEmpty().take(limit))
    }

    override suspend fun insights(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<List<ParentInsightDto>> {
        insightsCalls += studentId
        return ApiCallResult.Success(insightsByStudent[studentId].orEmpty())
    }

    override suspend fun academicIntelligence(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentAcademicIntelligenceDto> {
        academicCalls += studentId
        return ApiCallResult.Success(academicIntelligenceByStudent[studentId] ?: ParentAcademicIntelligenceDto())
    }

    override suspend fun executiveSummary(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentExecutiveSummaryDto> {
        executiveSummaryCalls += studentId
        return ApiCallResult.Success(executiveSummaryByStudent[studentId] ?: ParentExecutiveSummaryDto())
    }

    override suspend fun quizTracking(accessToken: String, studentId: Int): ApiCallResult<ParentQuizTrackingDto> =
        ApiCallResult.Success(quizByStudent[studentId] ?: ParentQuizTrackingDto())

    override suspend fun historicalReport(
        accessToken: String,
        studentId: Int,
        period: String,
        startDate: String?,
        endDate: String?,
    ): ApiCallResult<ParentHistoricalReportDto> =
        ApiCallResult.Success(
            historicalReportsByStudent[studentId]?.copy(period = period)
                ?: ParentHistoricalReportDto(period = period),
        )

    override suspend fun exportHistoricalReport(
        accessToken: String,
        studentId: Int,
        period: String,
        startDate: String?,
        endDate: String?,
        format: String,
    ): ApiCallResult<ParentReportExportDto> {
        lastExportCall = ExportCall(studentId, period, startDate, endDate, format)
        return exportResult ?: ApiCallResult.Success(
            ParentReportExportDto(
                bytes = byteArrayOf(0x25, 0x50, 0x44, 0x46),
                filename = "eduspark-report-Omar-$period.$format",
                mimeType = when (format) {
                    "csv" -> "text/csv"
                    "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else -> "application/pdf"
                },
            ),
        )
    }

    override suspend fun notifications(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentNotificationListDto> =
        ApiCallResult.Success(notificationState[studentId] ?: ParentNotificationListDto())

    override suspend fun markNotificationRead(
        accessToken: String,
        studentId: Int,
        notificationId: Int,
    ): ApiCallResult<ParentNotificationDto> {
        markedNotificationIds += notificationId
        val current = notificationState[studentId] ?: return ApiCallResult.HttpFailure(404)
        val target = current.items.firstOrNull { it.id == notificationId }
            ?: return ApiCallResult.HttpFailure(404)
        val updated = target.copy(isRead = true)
        notificationState[studentId] = current.copy(
            items = current.items.map { if (it.id == notificationId) updated else it },
            unreadCount = current.items.count { !it.isRead && it.id != notificationId },
        )
        return ApiCallResult.Success(updated)
    }

    override suspend fun notificationSettings(
        accessToken: String,
        studentId: Int,
    ): ApiCallResult<ParentNotificationSettingsDto> {
        lastNotificationSettingsStudentId = studentId
        return ApiCallResult.Success(
            notificationSettingsState[studentId] ?: ParentNotificationSettingsDto(studentId = studentId),
        )
    }

    override suspend fun updateNotificationSettings(
        accessToken: String,
        studentId: Int,
        body: ParentNotificationSettingsUpdateDto,
    ): ApiCallResult<ParentNotificationSettingsDto> {
        lastSettingsUpdate = body
        val current = notificationSettingsState[studentId] ?: ParentNotificationSettingsDto(studentId = studentId)
        val updated = current.copy(
            loginAlerts = body.loginAlerts ?: current.loginAlerts,
            logoutAlerts = body.logoutAlerts ?: current.logoutAlerts,
            lessonAlerts = body.lessonAlerts ?: current.lessonAlerts,
            quizAlerts = body.quizAlerts ?: current.quizAlerts,
            lowScoreAlerts = body.lowScoreAlerts ?: current.lowScoreAlerts,
            inactivityAlerts = body.inactivityAlerts ?: current.inactivityAlerts,
            plannerAlerts = body.plannerAlerts ?: current.plannerAlerts,
        )
        notificationSettingsState[studentId] = updated
        return ApiCallResult.Success(updated)
    }

    private fun markReadInternal(noteId: Int): ApiCallResult<ParentViewerNoteDto> {
        val bucket = notesByStudent.values.firstOrNull { list -> list.any { it.id == noteId } }
            ?: return ApiCallResult.HttpFailure(404)
        val index = bucket.indexOfFirst { it.id == noteId }
        if (index < 0) return ApiCallResult.HttpFailure(404)
        val updated = bucket[index].copy(isReadByViewer = true, status = "read")
        bucket[index] = updated
        return ApiCallResult.Success(updated)
    }
}

private class FakeParentAuthApi : AuthApi {
    override suspend fun refresh(body: RefreshTokenRequestDto): ApiCallResult<TokenResponseDto> =
        ApiCallResult.InvalidResponse

    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) =
        ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(
        body: ResendTwoFactorRequestDto,
    ): ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) =
        ApiCallResult.Success(OkResponseDto())
}
