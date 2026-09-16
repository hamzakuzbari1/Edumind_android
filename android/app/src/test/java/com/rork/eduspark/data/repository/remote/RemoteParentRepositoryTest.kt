package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentFeatureSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentNotificationSnapshot
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
import com.rork.eduspark.data.remote.parent.ParentActivityDto
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.parent.ParentCourseProgressDto
import com.rork.eduspark.data.remote.parent.ParentDashboardDto
import com.rork.eduspark.data.remote.parent.ParentInsightDto
import com.rork.eduspark.data.remote.parent.ParentLinkStudentRequestDto
import com.rork.eduspark.data.remote.parent.ParentLinkStudentResponseDto
import com.rork.eduspark.data.remote.parent.ParentLinkedStudentDto
import com.rork.eduspark.data.remote.parent.ParentNotesListDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyCreateDto
import com.rork.eduspark.data.remote.parent.ParentViewerNoteReplyDto
import com.rork.eduspark.data.remote.parent.toDomain
import com.rork.eduspark.data.model.ParentNotesFeed
import com.rork.eduspark.data.model.ParentNote
import kotlinx.serialization.json.JsonElement
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
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
                    attendance = JsonObject(
                        mapOf(
                            "attendance_percentage" to JsonPrimitive(95),
                            "streak_days" to JsonPrimitive(6),
                            "completed_sessions" to JsonPrimitive(10),
                            "missed_sessions" to JsonPrimitive(1),
                        ),
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
    fun insightsArrayAndAcademicIntelligenceMerge() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            insightsByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """[{"id":"i1","text":"تحسّن في الرياضيات","severity":"info"}]""",
                ),
            ),
            academicIntelligenceByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """{"overall_average":82.5,"performance_label":"جيد","summary":"أداء مستقر","subjects":[{"subject_name":"رياضيات","course_id":9,"composite_score":88}]}""",
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentFeatureSnapshot>>(
            fixture(api).repository.getInsightsSnapshot("4"),
        ).data
        assertEquals("82.5", snapshot.metrics.first { it.label == "المعدل" }.value)
        assertEquals("تحسّن في الرياضيات", snapshot.items.first().title)
        assertEquals("رياضيات", snapshot.items.last().title)
    }

    @Test
    fun lessonProgressFlattensNestedCoursesAndUsesSummary() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            lessonProgressByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """{"student_id":4,"courses":[{"course_id":1,"course_title":"Math","lessons":[{"lesson_id":55,"lesson_title":"Algebra","course_title":"Math","status":"completed","status_label":"مكتمل","completion_percent":100}]}],"summary":{"completed_lessons":1,"total_lessons":3}}""",
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentLessonProgressSnapshot>>(
            fixture(api).repository.getLessonProgress("4"),
        ).data
        assertEquals("55", snapshot.lessons.single().id)
        assertEquals("Algebra", snapshot.lessons.single().title)
        assertEquals(1, snapshot.completedLessons)
        assertEquals(3, snapshot.totalLessons)
    }

    @Test
    fun subjectsTeachersCombinesEnrolledAndAvailable() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            subjectsTeachersByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """{"student_id":4,"enrolled":[{"course_id":1,"subject_name":"رياضيات","teacher_name":"معلم 1","enrolled":true,"subscription_status":"active"}],"available":[{"course_id":2,"subject_name":"علوم","teacher_name":"معلم 2","enrolled":false,"subscription_status":"pending"}]}""",
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentSubjectsTeachersSnapshot>>(
            fixture(api).repository.getSubjectsTeachers("4"),
        ).data
        assertEquals(listOf("رياضيات", "علوم"), snapshot.items.map { it.title })
    }

    @Test
    fun notificationSettingsPassStudentIdAndMapBooleanFlags() = runBlocking {
        val api = FakeParentApi(
            students = listOf(studentDto(4, "Omar")),
            notificationsByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """{"items":[{"id":9,"title":"دخول","body":"سجل الطالب","is_read":false}],"unread_count":1}""",
                ),
            ),
            notificationSettingsByStudent = mapOf(
                4 to Json.parseToJsonElement(
                    """{"student_id":4,"login_alerts":true,"logout_alerts":false,"lesson_alerts":true}""",
                ),
            ),
        )
        val snapshot = assertIs<AppResult.Success<ParentNotificationSnapshot>>(
            fixture(api).repository.getNotificationsSnapshot("4"),
        ).data
        assertEquals(4, api.lastNotificationSettingsStudentId)
        assertEquals(1, snapshot.unreadCount)
        assertEquals("دخول", snapshot.notifications.single().title)
        assertEquals("مفعل", snapshot.preferences.first { it.id == "login_alerts" }.status)
        assertEquals("متوقف", snapshot.preferences.first { it.id == "logout_alerts" }.status)
    }

    @Test
    fun parentHttpDetailIsNotHidden() = runBlocking {
        val api = FakeParentApi(students = listOf(studentDto(4, "Omar")))
        api.lessonProgressFailure = ApiCallResult.HttpFailure(404, detail = "الطالب غير مرتبط")
        val result = fixture(api).repository.getLessonProgress("4")
        assertEquals(AppError.Domain("الطالب غير مرتبط"), assertIs<AppResult.Failure>(result).error)
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
    private val lessonProgressByStudent: Map<Int, JsonElement> = emptyMap(),
    private val insightsByStudent: Map<Int, JsonElement> = emptyMap(),
    private val academicIntelligenceByStudent: Map<Int, JsonElement> = emptyMap(),
    private val subjectsTeachersByStudent: Map<Int, JsonElement> = emptyMap(),
    private val notificationsByStudent: Map<Int, JsonElement> = emptyMap(),
    private val notificationSettingsByStudent: Map<Int, JsonElement> = emptyMap(),
) : ParentApi {
    val studentList = students.toMutableList()
    var lastLinkRequest: ParentLinkStudentRequestDto? = null
    var linkResult: ApiCallResult<ParentLinkStudentResponseDto> =
        ApiCallResult.HttpFailure(404, detail = "رمز الربط غير صالح")
    var onLinked: (() -> Unit)? = null
    val dashboardCalls = mutableListOf<Int>()
    val courseCalls = mutableListOf<Int>()
    val activityCalls = mutableListOf<Int>()
    val notesCalls = mutableListOf<Int>()
    var lastNotificationSettingsStudentId: Int? = null
    var lessonProgressFailure: ApiCallResult.HttpFailure? = null
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

    override suspend fun lessonProgress(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        lessonProgressFailure ?: ApiCallResult.Success(
            lessonProgressByStudent[studentId] ?: JsonObject(emptyMap()),
        )

    override suspend fun lessonDetails(
        accessToken: String,
        studentId: Int,
        lessonId: String,
    ): ApiCallResult<JsonElement> = ApiCallResult.Success(JsonObject(mapOf("lesson_id" to JsonPrimitive(lessonId))))

    override suspend fun subjectsTeachers(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(subjectsTeachersByStudent[studentId] ?: JsonObject(emptyMap()))

    override suspend fun plannerVisibility(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun plannerProgress(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun studentRoutine(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun attendance(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun activityTrackingSummary(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun insights(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(insightsByStudent[studentId] ?: JsonObject(emptyMap()))

    override suspend fun academicIntelligence(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(academicIntelligenceByStudent[studentId] ?: JsonObject(emptyMap()))

    override suspend fun executiveSummary(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun historicalReport(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(JsonObject(emptyMap()))

    override suspend fun notifications(accessToken: String, studentId: Int): ApiCallResult<JsonElement> =
        ApiCallResult.Success(notificationsByStudent[studentId] ?: JsonObject(emptyMap()))

    override suspend fun notificationSettings(accessToken: String, studentId: Int): ApiCallResult<JsonElement> {
        lastNotificationSettingsStudentId = studentId
        return ApiCallResult.Success(notificationSettingsByStudent[studentId] ?: JsonObject(emptyMap()))
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
