package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.AchievementKind
import com.rork.eduspark.data.model.AiPreReviewAvailability
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.AnalyticsPeriod
import com.rork.eduspark.data.model.AtRiskReason
import com.rork.eduspark.data.model.AtRiskStudent
import com.rork.eduspark.data.model.AttendanceRecord
import com.rork.eduspark.data.model.AttendanceStatus
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.model.CURRENT_STUDENT_MESSAGING_ID
import com.rork.eduspark.data.model.MessageAttachment
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.model.StudentNotification
import com.rork.eduspark.data.model.StudentNotificationType
import com.rork.eduspark.data.model.EngagementPoint
import com.rork.eduspark.data.model.FunnelStage
import com.rork.eduspark.data.model.FunnelStageKind
import com.rork.eduspark.data.model.GradePublicationStatus
import com.rork.eduspark.data.model.AchievementProgress
import com.rork.eduspark.data.model.AchievementStatus
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.data.model.ContinueLearningItem
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.LearningStep
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonDetail
import com.rork.eduspark.data.model.LessonMediaType
import com.rork.eduspark.data.model.LessonProcessingOverallStatus
import com.rork.eduspark.data.model.LessonProcessingStage
import com.rork.eduspark.data.model.LessonProcessingStageState
import com.rork.eduspark.data.model.LessonProcessingStageStatus
import com.rork.eduspark.data.model.LessonStatus
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.model.LearningGoal
import com.rork.eduspark.data.model.ExplanationLength
import com.rork.eduspark.data.model.LearningInterest
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.LockedReason
import com.rork.eduspark.data.model.ExamEntry
import com.rork.eduspark.data.model.ExamSchedule
import com.rork.eduspark.data.model.OcrConfidence
import com.rork.eduspark.data.model.Money
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.data.model.PaymentRequest
import com.rork.eduspark.data.model.PaymentStatus
import com.rork.eduspark.data.model.PeerReview
import com.rork.eduspark.data.model.PeerReviewDraft
import com.rork.eduspark.data.model.PeerSubmissionPreview
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.model.PlannerChangeProposal
import com.rork.eduspark.data.model.PlannerChatMessage
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.PlannerItem
import com.rork.eduspark.data.model.PlannerPriority
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.PlannerSession
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectDifficulty
import com.rork.eduspark.data.model.ProjectMaterial
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.ProjectMilestone
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.model.ProjectReflection
import com.rork.eduspark.data.model.ProjectReview
import com.rork.eduspark.data.model.ProjectShowcaseSample
import com.rork.eduspark.data.model.ProjectSubmission
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.ProjectTaskStatus
import com.rork.eduspark.data.model.ProjectSafetyNote
import com.rork.eduspark.data.model.ProjectTeam
import com.rork.eduspark.data.model.RubricCriterion
import com.rork.eduspark.data.model.RubricResult
import com.rork.eduspark.data.model.RoutineBuildMessage
import com.rork.eduspark.data.model.RoutineDayDraft
import com.rork.eduspark.data.model.RoutineDraft
import com.rork.eduspark.data.model.SafetySeverity
import com.rork.eduspark.data.model.SharedDeliverable
import com.rork.eduspark.data.model.SubmissionAttachment
import com.rork.eduspark.data.model.SubmissionDraft
import com.rork.eduspark.data.model.SubmissionType
import com.rork.eduspark.data.model.TaskHint
import com.rork.eduspark.data.model.TaskWorkflowStatus
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherDashboardSummary
import com.rork.eduspark.data.model.TeacherDocumentKind
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.LessonInsightKind
import com.rork.eduspark.data.model.TeacherGeneratedQuestion
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonChunk
import com.rork.eduspark.data.model.TeacherLessonEditorState
import com.rork.eduspark.data.model.TeacherLessonInsight
import com.rork.eduspark.data.model.TeacherLessonProcessingState
import com.rork.eduspark.data.model.TeacherLessonStatus
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.StudentFlag
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherActivityItem
import com.rork.eduspark.data.model.TeacherActivityKind
import com.rork.eduspark.data.model.TeacherAnalyticsSnapshot
import com.rork.eduspark.data.model.TeacherCriterionReview
import com.rork.eduspark.data.model.TeacherGradeEntry
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.data.model.TeacherPrivateNote
import com.rork.eduspark.data.model.TeacherProject
import com.rork.eduspark.data.model.TeacherProjectMaterial
import com.rork.eduspark.data.model.TeacherProjectMediaItem
import com.rork.eduspark.data.model.TeacherProjectMediaKind
import com.rork.eduspark.data.model.TeacherProjectMilestone
import com.rork.eduspark.data.model.TeacherProjectRubricCriterion
import com.rork.eduspark.data.model.TeacherProjectSafetyNote
import com.rork.eduspark.data.model.TeacherProjectStatus
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.data.model.TeacherProjectTask
import com.rork.eduspark.data.model.ProjectReviewStatus
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherEssayResponse
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.data.model.TeacherStudentAttendance
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherSetupStepId
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceProfile
import com.rork.eduspark.data.model.TeacherVoiceProfileSample
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.model.VoiceProfileStatus
import com.rork.eduspark.data.model.VoiceSampleQualityStatus
import com.rork.eduspark.data.model.VoiceSampleSourceType
import com.rork.eduspark.data.model.TeacherWorkItem
import com.rork.eduspark.data.model.TeacherWorkItemKind
import com.rork.eduspark.data.model.TeacherWorkItemUrgency
import com.rork.eduspark.data.model.TeamMember
import com.rork.eduspark.data.model.TeamMessage
import com.rork.eduspark.data.model.TeamRole
import com.rork.eduspark.data.model.TeamTaskAssignment
import com.rork.eduspark.data.model.VoiceSampleState
import com.rork.eduspark.data.model.isFullyCompleted
import com.rork.eduspark.data.model.ProposalStatus
import com.rork.eduspark.data.model.PurchaseAccess
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizAttempt
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.RedeemedVoucher
import com.rork.eduspark.data.model.FeedbackMode
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.SecuritySettings
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.model.SubjectProgress
import com.rork.eduspark.data.model.CommitmentSchedule
import com.rork.eduspark.data.model.RoutineBuilderAnswers
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.RoutineSlotType
import com.rork.eduspark.data.model.SimpleDate
import com.rork.eduspark.data.model.SubscriptionStatus
import com.rork.eduspark.data.model.TutorReply
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.model.VoucherStatus
import com.rork.eduspark.data.model.VoucherValidationResult
import com.rork.eduspark.data.model.WeekPlan
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.data.model.SessionStatus
import com.rork.eduspark.data.model.matchesQuizAnswer
import com.rork.eduspark.data.repository.AchievementRepository
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.CertificateRepository
import com.rork.eduspark.data.repository.ExamRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.MessagingRepository
import com.rork.eduspark.data.repository.NotificationRepository
import com.rork.eduspark.data.repository.OnboardingRepository
import com.rork.eduspark.data.repository.PaymentRepository
import com.rork.eduspark.data.repository.PlannerRepository
import com.rork.eduspark.data.repository.ProfileRepository
import com.rork.eduspark.data.repository.ProjectRepository
import com.rork.eduspark.data.repository.QuizRepository
import com.rork.eduspark.data.repository.RoutineRepository
import com.rork.eduspark.data.repository.SecurityRepository
import com.rork.eduspark.data.repository.SignInOutcome
import com.rork.eduspark.data.repository.SubscriptionRepository
import com.rork.eduspark.data.repository.TeacherRepository
import com.rork.eduspark.data.repository.VoucherRepository
import com.rork.eduspark.data.repository.TutorRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.update

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ISOLATED MOCK REPOSITORIES — development only.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * These exist so screens can be built and reviewed before the FastAPI client is wired.
 * They are intentionally quarantined in this package so that deleting the package is a
 * complete removal — no mock data leaks into models, ViewModels or composables.
 *
 * They deliberately reproduce the platform's *real* behaviours rather than a happy path:
 *  • latency you can feel (the AI tutor genuinely takes 5–30s and does not stream),
 *  • the branching login outcomes (unverified email, email-OTP 2FA),
 *  • failure cases, so error and offline states are exercised during development.
 *
 * They do NOT invent endpoints, field names or response envelopes.
 */

/** Deterministic latencies so the four states are visible while building screens. */
private object MockLatency {
    const val FAST_MS = 400L
    const val LIST_MS = 700L

    /** Deliberately the longest mock latency in the app — a felt echo of the tutor's real
     *  5–30+ second, non-streaming reply, without actually making a reviewer wait that long. */
    const val TUTOR_MS = 2200L
}

class MockStudentEntitlements(initialCourseIds: Set<String> = emptySet()) {
    private val _activatedCourseIds = MutableStateFlow(initialCourseIds)
    val activatedCourseIds: Flow<Set<String>> = _activatedCourseIds.asStateFlow()

    fun isActivated(courseId: String): Boolean = courseId in _activatedCourseIds.value

    fun activate(courseId: String) {
        _activatedCourseIds.update { it + courseId }
    }
}

/** XP per correct answer — same order of magnitude as a lesson's own XP reward (see math-1…3 fixtures). */
private const val QUIZ_XP_PER_CORRECT = 15

/** 14 days, most recent last — the trailing 7 are all true, matching the fixture's streakDays = 7. */
private val MOCK_STREAK_HISTORY = listOf(
    true, false, true, false, true, true, false,
    true, true, true, true, true, true, true,
)

class MockAuthRepository(
    private val tokenStore: SecureTokenStore,
) : AuthRepository {

    private val _session = MutableStateFlow<SessionUser?>(null)
    override val session: Flow<SessionUser?> = _session.asStateFlow()

    /**
     * Fixture accounts. The local part of the address selects the outcome, so every
     * branch of A-04 Login can be walked by hand on a device without a backend:
     *   student@… / teacher@… / parent@…  → straight in
     *   newteacher@…                      → straight in, Teacher role, setup incomplete —
     *                                        the deterministic TC-01 QA persona (Teacher A);
     *                                        [MockTeacherRepository] seeds a partially-saved
     *                                        wizard for this exact id, so TC-01 resumes at
     *                                        its first genuinely incomplete step
     *   unverified@…                      → A-08 Verify Email
     *   twofactor@…                       → A-09 Two-Factor Verify
     *   locked@…                          → forbidden
     *   offline@…                         → offline error
     */
    override suspend fun signIn(email: String, password: String): AppResult<SignInOutcome> {
        delay(MockLatency.FAST_MS)

        if (password.isBlank()) {
            return AppResult.Failure(AppError.Validation(mapOf("password" to "required")))
        }

        val local = email.substringBefore('@').lowercase()
        return when {
            local.startsWith("offline") -> AppResult.Failure(AppError.Offline)
            local.startsWith("locked") -> AppResult.Failure(AppError.Forbidden)
            local.startsWith("unverified") ->
                AppResult.Success(SignInOutcome.EmailVerificationRequired(email))

            local.startsWith("twofactor") ->
                AppResult.Success(SignInOutcome.TwoFactorRequired(email))

            password.length < 6 ->
                AppResult.Failure(AppError.Domain("invalid_credentials"))

            else -> {
                val user = fixtureUser(email, roleFor(local))
                persist(user)
                AppResult.Success(SignInOutcome.Authenticated(user))
            }
        }
    }

    /**
     * A fresh registration always gets an id of its own — never [fixtureUser]'s fixed
     * "mock-teacher"/"mock-\<role\>" ids, which are reserved for the deterministic QA sign-in
     * personas ([signIn] only). Reusing one of those here would make a brand-new Teacher
     * silently inherit the seeded COMPLETE persona's [TeacherSetupState][com.rork.eduspark.data.model.TeacherSetupState]
     * in [MockTeacherRepository] and skip TC-01 entirely.
     */
    override suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<SessionUser> {
        delay(MockLatency.FAST_MS)
        if (email.contains("taken")) {
            return AppResult.Failure(AppError.Validation(mapOf("email" to "already_registered")))
        }
        val base = fixtureUser(email, role)
        val user = base.copy(
            id = if (role == UserRole.Teacher) "mock-teacher-${System.currentTimeMillis()}" else base.id,
            displayName = name,
            isEmailVerified = false,
            hasCompletedOnboarding = false,
        )
        persist(user)
        return AppResult.Success(user)
    }

    override suspend fun verifyEmail(code: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (code != VALID_CODE) return AppResult.Failure(AppError.Domain("invalid_code"))
        _session.value = _session.value?.copy(isEmailVerified = true)
        return AppResult.Success(Unit)
    }

    override suspend fun resendEmailCode(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    override suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): AppResult<SessionUser> {
        delay(MockLatency.FAST_MS)
        if (code != VALID_CODE) return AppResult.Failure(AppError.Domain("invalid_code"))
        val user = fixtureUser("student@edumind.sy", UserRole.Student)
        persist(user)
        return AppResult.Success(user)
    }

    /**
     * A-10. Same fixture-prefix convention as [signIn], so offline and server failure are
     * reachable by hand: offline@… / servererror@… trigger those branches, everything else
     * succeeds — including an address with no account, because the platform never confirms
     * whether one exists (Source Audit-consistent: this is a security choice, not an oversight).
     */
    override suspend fun requestPasswordReset(email: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        val local = email.substringBefore('@').lowercase()
        return when {
            local.startsWith("offline") -> AppResult.Failure(AppError.Offline)
            local.startsWith("servererror") -> AppResult.Failure(AppError.Server)
            else -> AppResult.Success(Unit)
        }
    }

    /** A-11. A blank token or the literal "expired" fixture both exercise A-11's expired state. */
    override suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (token.isBlank() || token == "expired") {
            return AppResult.Failure(AppError.Domain("expired_link"))
        }
        return AppResult.Success(Unit)
    }

    /** SO-05. In-memory only — matches every other mutation this mock makes to `_session`. */
    override suspend fun completeOnboarding(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _session.value = _session.value?.copy(hasCompletedOnboarding = true)
        return AppResult.Success(Unit)
    }

    override suspend fun signOut() {
        tokenStore.clear()
        _session.value = null
    }

    private suspend fun persist(user: SessionUser) {
        tokenStore.write(
            StoredSession(
                accessToken = "mock-access-token",
                sessionId = "mock-session",
                userId = user.id,
            )
        )
        _session.value = user
    }

    private fun roleFor(localPart: String): UserRole = when {
        localPart.contains("teacher") -> UserRole.Teacher
        localPart.startsWith("parent") -> UserRole.Parent
        else -> UserRole.Student
    }

    /**
     * [TEACHER_INCOMPLETE_ID] is the one id [MockTeacherRepository] recognises as "setup not
     * finished"; everything else resolves to the ordinary "mock-teacher" id, which
     * [MockTeacherRepository] treats as already complete. This function backs both [signIn]
     * (where those fixed ids are the intended, deterministic QA personas) and [register] (which
     * overrides the id it returns for Teacher role — see [register]'s own doc comment — so a
     * fresh registration never actually keeps this "mock-teacher" id).
     */
    private fun fixtureUser(email: String, role: UserRole): SessionUser {
        val local = email.substringBefore('@').lowercase()
        val isIncompleteTeacher = role == UserRole.Teacher && local.startsWith("newteacher")
        return SessionUser(
            id = if (isIncompleteTeacher) TEACHER_INCOMPLETE_ID else "mock-${role.name.lowercase()}",
            displayName = email.substringBefore('@'),
            email = email,
            role = role,
            isEmailVerified = true,
            requiresTwoFactor = false,
            hasCompletedOnboarding = !isIncompleteTeacher,
        )
    }

    private companion object {
        const val VALID_CODE = "123456"
        const val TEACHER_INCOMPLETE_ID = "mock-teacher-new"
    }
}

/**
 * TC-01/TC-02/TC-03 fixtures. Two deterministic personas, both reachable through
 * [MockAuthRepository]'s own email-prefix convention (extended, not duplicated, for this
 * slice):
 *   "mock-teacher"     (teacher@…)    — setup already complete; TC-02/TC-03 data seeded.
 *   "mock-teacher-new" (newteacher@…) — setup partially saved: Identity and Subjects & Grades
 *                                        are done, Qualifications is the first genuinely
 *                                        incomplete step, so TC-01 resumes there with the
 *                                        earlier steps' values intact.
 * Any other id (e.g. a fresh Teacher registration through A-05/06/07, which never goes
 * through the newteacher@ branch) falls back to a genuinely blank [TeacherSetupState] —
 * never someone else's persona data.
 */
class MockTeacherRepository : TeacherRepository {

    private val setupStates = MutableStateFlow(
        mapOf(
            COMPLETE_TEACHER_ID to completeSetupState(),
            INCOMPLETE_TEACHER_ID to incompleteSetupState(),
        )
    )

    // TC-04/05/06 — one canonical lesson list per course, one in-flight upload draft per
    // course, one processing record per lesson. All three screens read/write these same maps;
    // none of them keeps a private copy.
    private val lessons = MutableStateFlow(seedLessons())
    private val uploadDrafts = MutableStateFlow<Map<String, TeacherLessonUploadDraft>>(emptyMap())
    private val processingStates = MutableStateFlow(seedProcessingStates())

    // TC-07/TC-08 — one editorial record per lesson. TC-09 — one voice profile per teacher,
    // kept in sync with TeacherSetupState.voiceSample by saveVoiceSample() below rather than
    // drifting into a second, disconnected voice store.
    private val editorStates = MutableStateFlow(seedEditorStates())
    private val voiceProfiles = MutableStateFlow(seedVoiceProfiles())

    // TC-10/11 — one canonical quiz map (create/edit/publish/grade all mutate this). Attempts
    // are the same [TeacherQuizAttempt] list TC-11 already reads — essay grades write into it.
    private val quizzes = MutableStateFlow(seedQuizzes())
    private val quizAttempts = MutableStateFlow(seedQuizAttempts())

    // TC-13 — private notes and sent parent notes, keyed by their own id; both empty until a
    // teacher actually writes one, never pre-seeded, so TC-13 shows genuine empty states on
    // first open. TC-14 — one gradebook entry per (studentId, courseId), created blank on
    // first read by getGradebook() below rather than pre-seeded here, same "seed a blank
    // record on first read" convention getLessonEditorState() already uses.
    private val privateNotes = MutableStateFlow<List<TeacherPrivateNote>>(emptyList())
    private val parentNotes = MutableStateFlow<List<TeacherParentNote>>(emptyList())
    private val gradeEntries = MutableStateFlow<Map<String, TeacherGradeEntry>>(seedGradeEntries())

    // TC-17 — one canonical teacher-authored project map (create/edit/reorder/publish all
    // mutate this). TC-18 — one canonical submission map; AI-suggested content is seeded once
    // and never mutated, only the teacher-confirmed fields on top of it.
    private val teacherProjects = MutableStateFlow(seedTeacherProjects())
    private val reviewQueue = MutableStateFlow(seedReviewQueue())

    override suspend fun getSetupState(teacherId: String): AppResult<TeacherSetupState> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(setupStates.value[teacherId] ?: TeacherSetupState(teacherId = teacherId))
    }

    override suspend fun saveIdentity(teacherId: String, identity: TeacherIdentityInfo): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(identity = identity, completedStepIds = it.completedStepIds + TeacherSetupStepId.Identity) }

    override suspend fun saveSubjectsGrades(teacherId: String, subjectsGrades: TeacherSubjectsGrades): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(subjectsGrades = subjectsGrades, completedStepIds = it.completedStepIds + TeacherSetupStepId.SubjectsGrades) }

    override suspend fun saveQualifications(teacherId: String, qualifications: List<TeacherQualification>): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(qualifications = qualifications, completedStepIds = it.completedStepIds + TeacherSetupStepId.Qualifications) }

    override suspend fun saveExperience(teacherId: String, experience: TeacherExperienceInfo): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(experience = experience, completedStepIds = it.completedStepIds + TeacherSetupStepId.Experience) }

    override suspend fun saveDocuments(teacherId: String, documents: List<TeacherSetupDocument>): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(documents = documents, completedStepIds = it.completedStepIds + TeacherSetupStepId.Documents) }

    override suspend fun savePricing(teacherId: String, pricing: TeacherPricingInfo): AppResult<TeacherSetupState> =
        updateState(teacherId) { it.copy(pricing = pricing, completedStepIds = it.completedStepIds + TeacherSetupStepId.Pricing) }

    /**
     * TC-01's own save call — unchanged contract, unchanged return type. The one addition is a
     * side effect: [syncVoiceProfileFromSetup] keeps TC-09's [TeacherVoiceProfile] in step with
     * whatever TC-01 just recorded, so the two screens never disagree about it. Nothing about
     * TC-01's own flow (its draft, its steps, [TeacherSetupState.completedStepIds]) changes.
     */
    override suspend fun saveVoiceSample(teacherId: String, voiceSample: TeacherVoiceSample): AppResult<TeacherSetupState> {
        val result = updateState(teacherId) { it.copy(voiceSample = voiceSample, completedStepIds = it.completedStepIds + TeacherSetupStepId.VoiceSample) }
        syncVoiceProfileFromSetup(teacherId, voiceSample)
        return result
    }

    /** Never silently completes a skipped required step — see [TeacherRepository.finishSetup]'s own doc comment. */
    override suspend fun finishSetup(teacherId: String): AppResult<TeacherSetupState> {
        delay(MockLatency.FAST_MS)
        val state = setupStates.value[teacherId] ?: TeacherSetupState(teacherId = teacherId)
        val identityValid = state.identity.displayName.isNotBlank()
        val subjectsGradesValid = state.subjectsGrades.subjectIds.isNotEmpty() && state.subjectsGrades.grades.isNotEmpty()
        if (!identityValid || !subjectsGradesValid) {
            return AppResult.Failure(AppError.Validation(mapOf("setup" to "required_steps_incomplete")))
        }
        return AppResult.Success(state)
    }

    override suspend fun getDashboard(teacherId: String): AppResult<TeacherDashboardSummary> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(DASHBOARD_SUMMARY)
    }

    override suspend fun getCourses(teacherId: String): AppResult<List<TeacherCourseSummary>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(COURSES)
    }

    override suspend fun getCourse(courseId: String): AppResult<TeacherCourseSummary> {
        delay(MockLatency.FAST_MS)
        val course = COURSES.firstOrNull { it.id == courseId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(course)
    }

    override suspend fun getLessons(courseId: String): AppResult<List<TeacherLesson>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(lessons.value[courseId].orEmpty().sortedBy { it.order })
    }

    override suspend fun getLesson(courseId: String, lessonId: String): AppResult<TeacherLesson> {
        delay(MockLatency.FAST_MS)
        val lesson = lessons.value[courseId]?.firstOrNull { it.id == lessonId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(lesson)
    }

    override suspend fun reorderLessons(courseId: String, orderedLessonIds: List<String>): AppResult<List<TeacherLesson>> {
        val byId = lessons.value[courseId].orEmpty().associateBy { it.id }
        val reordered = orderedLessonIds.mapIndexedNotNull { index, id -> byId[id]?.copy(order = index + 1) }
        lessons.value = lessons.value + (courseId to reordered)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(reordered)
    }

    override suspend fun getUploadDraft(courseId: String): AppResult<TeacherLessonUploadDraft?> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(uploadDrafts.value[courseId])
    }

    override suspend fun startLessonUpload(
        courseId: String,
        contentType: LessonContentType,
        mockFileName: String,
        mockTotalBytes: Long,
        title: String,
        order: Int,
        generateQuiz: Boolean,
        generateNarration: Boolean,
        indexForTutor: Boolean,
    ): AppResult<TeacherLessonUploadDraft> {
        val draft = TeacherLessonUploadDraft(
            courseId = courseId,
            contentType = contentType,
            mockFileName = mockFileName,
            mockTotalBytes = mockTotalBytes,
            title = title,
            order = order,
            generateQuiz = generateQuiz,
            generateNarration = generateNarration,
            indexForTutor = indexForTutor,
        )
        uploadDrafts.value = uploadDrafts.value + (courseId to draft)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(draft)
    }

    override suspend fun advanceLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft> {
        val current = uploadDrafts.value[courseId] ?: return AppResult.Failure(AppError.NotFound)
        if (current.stage == LessonUploadStage.Completed || current.stage == LessonUploadStage.Paused) {
            return AppResult.Success(current)
        }
        val chunk = (current.mockTotalBytes / UPLOAD_TICKS).coerceAtLeast(1L)
        val nextBytes = (current.uploadedBytes + chunk).coerceAtMost(current.mockTotalBytes)
        val isDone = nextBytes >= current.mockTotalBytes
        var updated = current.copy(
            uploadedBytes = nextBytes,
            stage = if (isDone) LessonUploadStage.Completed else LessonUploadStage.Uploading,
        )
        if (isDone) {
            updated = updated.copy(createdLessonId = createLessonFromUpload(updated))
        }
        uploadDrafts.value = uploadDrafts.value + (courseId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    override suspend fun pauseLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft> {
        val current = uploadDrafts.value[courseId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(stage = LessonUploadStage.Paused)
        uploadDrafts.value = uploadDrafts.value + (courseId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    override suspend fun resumeLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft> {
        val current = uploadDrafts.value[courseId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(stage = LessonUploadStage.Uploading)
        uploadDrafts.value = uploadDrafts.value + (courseId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    override suspend fun cancelLessonUpload(courseId: String): AppResult<Unit> {
        uploadDrafts.value = uploadDrafts.value - courseId
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    override suspend fun getLessonProcessingState(lessonId: String): AppResult<TeacherLessonProcessingState> {
        delay(MockLatency.FAST_MS)
        val state = processingStates.value[lessonId] ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(state)
    }

    override suspend fun advanceLessonProcessing(lessonId: String): AppResult<TeacherLessonProcessingState> {
        val current = processingStates.value[lessonId] ?: return AppResult.Failure(AppError.NotFound)
        val activeIndex = current.stages.indexOfFirst { it.status == LessonProcessingStageStatus.Running }
        if (current.overallStatus != LessonProcessingOverallStatus.Running || activeIndex == -1) {
            delay(MockLatency.FAST_MS)
            return AppResult.Success(current)
        }
        val active = current.stages[activeIndex]
        val shouldFail = active.stage == LessonProcessingStage.Index && lessonId == FAILING_LESSON_ID && !current.hasRetried
        val stages = current.stages.toMutableList()
        val updated = if (shouldFail) {
            stages[activeIndex] = active.copy(status = LessonProcessingStageStatus.Failed, errorLabel = PROCESSING_FAILURE_MESSAGE)
            current.copy(stages = stages)
        } else {
            stages[activeIndex] = active.copy(status = LessonProcessingStageStatus.Complete, errorLabel = null)
            val nextIndex = stages.indexOfFirst { it.status == LessonProcessingStageStatus.Pending }
            if (nextIndex != -1) stages[nextIndex] = stages[nextIndex].copy(status = LessonProcessingStageStatus.Running)
            current.copy(stages = stages)
        }
        processingStates.value = processingStates.value + (lessonId to updated)
        if (updated.overallStatus == LessonProcessingOverallStatus.Completed) {
            publishLesson(updated.courseId, lessonId)
        }
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    /** Only meaningful while the pipeline is [LessonProcessingOverallStatus.Failed] — resets the failed stage to run again, this time unconditionally toward success. */
    override suspend fun retryLessonProcessing(lessonId: String): AppResult<TeacherLessonProcessingState> {
        val current = processingStates.value[lessonId] ?: return AppResult.Failure(AppError.NotFound)
        val failedIndex = current.stages.indexOfFirst { it.status == LessonProcessingStageStatus.Failed }
        if (failedIndex == -1) {
            delay(MockLatency.FAST_MS)
            return AppResult.Success(current)
        }
        val stages = current.stages.toMutableList()
        stages[failedIndex] = stages[failedIndex].copy(status = LessonProcessingStageStatus.Running, errorLabel = null)
        val updated = current.copy(stages = stages, hasRetried = true)
        processingStates.value = processingStates.value + (lessonId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    // ── TC-07 · Lesson Editor / TC-08 · Lesson Preview ──────────────────────────────────────

    override suspend fun getLessonEditorState(courseId: String, lessonId: String): AppResult<TeacherLessonEditorState> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(editorStates.value[lessonId] ?: TeacherLessonEditorState(lessonId = lessonId, courseId = courseId))
    }

    override suspend fun saveExtractedText(courseId: String, lessonId: String, text: String): AppResult<TeacherLessonEditorState> =
        updateEditorState(courseId, lessonId) { it.copy(extractedText = text) }

    override suspend fun saveChunks(courseId: String, lessonId: String, chunks: List<TeacherLessonChunk>): AppResult<TeacherLessonEditorState> =
        updateEditorState(courseId, lessonId) { it.copy(chunks = chunks.mapIndexed { index, chunk -> chunk.copy(order = index + 1) }) }

    override suspend fun saveGeneratedQuestionEdit(
        courseId: String,
        lessonId: String,
        questionId: String,
        edited: QuizQuestion,
    ): AppResult<TeacherLessonEditorState> = updateEditorState(courseId, lessonId) { state ->
        state.copy(
            generatedQuestions = state.generatedQuestions.map {
                if (it.question.id == questionId) it.copy(question = edited) else it
            }
        )
    }

    override suspend fun reviewGeneratedQuestion(
        courseId: String,
        lessonId: String,
        questionId: String,
        status: AiReviewStatus,
    ): AppResult<TeacherLessonEditorState> = updateEditorState(courseId, lessonId) { state ->
        state.copy(
            generatedQuestions = state.generatedQuestions.map {
                if (it.question.id == questionId) it.copy(reviewStatus = status) else it
            }
        )
    }

    override suspend fun reviewInsight(courseId: String, lessonId: String, insightId: String, status: AiReviewStatus): AppResult<TeacherLessonEditorState> =
        updateEditorState(courseId, lessonId) { state ->
            state.copy(insights = state.insights.map { if (it.id == insightId) it.copy(reviewStatus = status) else it })
        }

    /** Never trusts the client's own gate check alone — see [TeacherRepository.submitLessonForPublish]'s own doc comment. */
    override suspend fun submitLessonForPublish(courseId: String, lessonId: String): AppResult<TeacherLesson> {
        delay(MockLatency.FAST_MS)
        val editor = editorStates.value[lessonId] ?: TeacherLessonEditorState(lessonId = lessonId, courseId = courseId)
        val contentSaved = editor.extractedText.isNotBlank()
        val hasApprovedChunk = editor.chunks.any { it.text.isNotBlank() }
        val questionsReviewed = editor.generatedQuestions.all { it.reviewStatus != AiReviewStatus.Unreviewed }
        val insightsReviewed = editor.insights.all { it.reviewStatus != AiReviewStatus.Unreviewed }
        if (!contentSaved || !hasApprovedChunk || !questionsReviewed || !insightsReviewed) {
            return AppResult.Failure(AppError.Validation(mapOf("publish" to "review_incomplete")))
        }
        publishLesson(courseId, lessonId)
        val lesson = lessons.value[courseId].orEmpty().firstOrNull { it.id == lessonId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(lesson)
    }

    private suspend fun updateEditorState(
        courseId: String,
        lessonId: String,
        transform: (TeacherLessonEditorState) -> TeacherLessonEditorState,
    ): AppResult<TeacherLessonEditorState> {
        val current = editorStates.value[lessonId] ?: TeacherLessonEditorState(lessonId = lessonId, courseId = courseId)
        val updated = transform(current)
        editorStates.value = editorStates.value + (lessonId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    // ── TC-09 · Voice Profile ────────────────────────────────────────────────────────────────

    override suspend fun getVoiceProfile(teacherId: String): AppResult<TeacherVoiceProfile> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(voiceProfiles.value[teacherId] ?: TeacherVoiceProfile(teacherId = teacherId))
    }

    override suspend fun setVoiceConsent(teacherId: String, granted: Boolean): AppResult<TeacherVoiceProfile> =
        updateVoiceProfile(teacherId) { it.copy(consentGranted = granted) }

    override suspend fun addVoiceSample(teacherId: String, sourceType: VoiceSampleSourceType): AppResult<TeacherVoiceProfile> =
        updateVoiceProfile(teacherId) { profile ->
            val isGood = profile.samples.size % 2 == 0
            val sample = TeacherVoiceProfileSample(
                id = "sample-${System.currentTimeMillis()}",
                sourceType = sourceType,
                fileName = if (sourceType == VoiceSampleSourceType.Uploaded) "voice_sample_${profile.samples.size + 1}.m4a" else null,
                durationLabel = if (sourceType == VoiceSampleSourceType.Recorded) "٠٠:٣٠" else "٠٠:٤٢",
                qualityStatus = if (isGood) VoiceSampleQualityStatus.Good else VoiceSampleQualityStatus.NeedsImprovement,
                qualityFeedback = if (isGood) GOOD_SAMPLE_FEEDBACK else NEEDS_IMPROVEMENT_SAMPLE_FEEDBACK,
            )
            profile.copy(samples = profile.samples + sample)
        }

    override suspend fun removeVoiceSample(teacherId: String, sampleId: String): AppResult<TeacherVoiceProfile> =
        updateVoiceProfile(teacherId) { it.copy(samples = it.samples.filterNot { sample -> sample.id == sampleId }) }

    /** Deterministically fails the first time a profile is generated for this teacher, then always succeeds — never a real cloning pipeline. */
    override suspend fun generateVoiceProfile(teacherId: String): AppResult<TeacherVoiceProfile> {
        val current = voiceProfiles.value[teacherId] ?: TeacherVoiceProfile(teacherId = teacherId)
        if (!current.consentGranted || current.samples.isEmpty()) {
            return AppResult.Failure(AppError.Validation(mapOf("voiceProfile" to "not_ready")))
        }
        delay(MockLatency.LIST_MS)
        val succeeds = current.hasRetriedGeneration
        val updated = current.copy(
            profileStatus = if (succeeds) VoiceProfileStatus.Ready else VoiceProfileStatus.Failed,
            hasRetriedGeneration = true,
        )
        voiceProfiles.value = voiceProfiles.value + (teacherId to updated)
        return AppResult.Success(updated)
    }

    override suspend fun setClonedNarrationEnabled(teacherId: String, enabled: Boolean): AppResult<TeacherVoiceProfile> {
        val current = voiceProfiles.value[teacherId] ?: TeacherVoiceProfile(teacherId = teacherId)
        if (enabled && (!current.consentGranted || current.profileStatus != VoiceProfileStatus.Ready)) {
            return AppResult.Failure(AppError.Validation(mapOf("narration" to "profile_not_ready")))
        }
        val updated = current.copy(clonedNarrationEnabled = enabled)
        voiceProfiles.value = voiceProfiles.value + (teacherId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    private suspend fun updateVoiceProfile(
        teacherId: String,
        transform: (TeacherVoiceProfile) -> TeacherVoiceProfile,
    ): AppResult<TeacherVoiceProfile> {
        val current = voiceProfiles.value[teacherId] ?: TeacherVoiceProfile(teacherId = teacherId)
        val updated = recomputeVoiceReadiness(transform(current))
        voiceProfiles.value = voiceProfiles.value + (teacherId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    /** NotReady ↔ ReadyToGenerate is purely a function of (consent, has a sample); Processing/Ready/Failed only ever change through an explicit [generateVoiceProfile] call, never recomputed here. */
    private fun recomputeVoiceReadiness(profile: TeacherVoiceProfile): TeacherVoiceProfile {
        if (profile.profileStatus == VoiceProfileStatus.Processing ||
            profile.profileStatus == VoiceProfileStatus.Ready ||
            profile.profileStatus == VoiceProfileStatus.Failed
        ) {
            return profile
        }
        val ready = profile.consentGranted && profile.samples.isNotEmpty()
        return profile.copy(profileStatus = if (ready) VoiceProfileStatus.ReadyToGenerate else VoiceProfileStatus.NotReady)
    }

    /**
     * TC-01 ↔ TC-09 sync — the smallest compatible migration: a Recorded [TeacherVoiceSample]
     * from TC-01 ensures a matching sample exists in [TeacherVoiceProfile.samples] (added once,
     * never duplicated on repeat saves) and implies consent (TC-01's own record button is
     * disabled until the consent checkbox is checked); a save back to NotRecorded (TC-01's
     * "re-record" flow) removes that one sample again, leaving any TC-09-only samples alone.
     */
    private fun syncVoiceProfileFromSetup(teacherId: String, voiceSample: TeacherVoiceSample) {
        val current = voiceProfiles.value[teacherId] ?: TeacherVoiceProfile(teacherId = teacherId)
        val updated = when (voiceSample.state) {
            VoiceSampleState.Recorded -> {
                val alreadyLinked = current.samples.any { it.id == TC01_LINKED_SAMPLE_ID }
                if (alreadyLinked) {
                    current.copy(consentGranted = true)
                } else {
                    current.copy(
                        consentGranted = true,
                        samples = current.samples + TeacherVoiceProfileSample(
                            id = TC01_LINKED_SAMPLE_ID,
                            sourceType = VoiceSampleSourceType.Recorded,
                            durationLabel = voiceSample.durationLabel ?: "٠٠:٣٠",
                            qualityStatus = VoiceSampleQualityStatus.Good,
                            qualityFeedback = GOOD_SAMPLE_FEEDBACK,
                        ),
                    )
                }
            }
            VoiceSampleState.NotRecorded -> current.copy(samples = current.samples.filterNot { it.id == TC01_LINKED_SAMPLE_ID })
        }
        voiceProfiles.value = voiceProfiles.value + (teacherId to recomputeVoiceReadiness(updated))
    }

    // ── TC-10 · Quiz Builder / TC-11 · Quiz Results ─────────────────────────────────────────

    override suspend fun getQuizzes(teacherId: String): AppResult<List<TeacherQuiz>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(quizzes.value.values.sortedBy { it.id })
    }

    override suspend fun getQuiz(quizId: String): AppResult<TeacherQuiz> {
        delay(MockLatency.FAST_MS)
        return quizzes.value[quizId]?.let { AppResult.Success(it) } ?: AppResult.Failure(AppError.NotFound)
    }

    override suspend fun createQuiz(courseId: String): AppResult<TeacherQuiz> {
        val course = COURSES.firstOrNull { it.id == courseId } ?: return AppResult.Failure(AppError.NotFound)
        val quiz = TeacherQuiz(
            id = "q-${System.currentTimeMillis()}",
            courseId = courseId,
            courseTitle = course.title,
            title = "",
            status = TeacherQuizStatus.Draft,
            durationMinutes = 15,
            passMarkPercent = 60,
            singleAttempt = true,
        )
        quizzes.value = quizzes.value + (quiz.id to quiz)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(quiz)
    }

    override suspend fun saveQuizMetadata(
        quizId: String,
        title: String,
        instructions: String,
        durationMinutes: Int?,
        passMarkPercent: Int,
        singleAttempt: Boolean,
    ): AppResult<TeacherQuiz> =
        updateQuiz(quizId) {
            it.copy(
                title = title,
                instructions = instructions,
                durationMinutes = durationMinutes,
                passMarkPercent = passMarkPercent.coerceIn(0, 100),
                singleAttempt = singleAttempt,
            )
        }

    override suspend fun saveQuizQuestions(quizId: String, questions: List<TeacherQuizQuestion>): AppResult<TeacherQuiz> =
        updateQuiz(quizId) { it.copy(questions = questions) }

    /** Never trusts the client's own gate check alone — see [TeacherRepository.publishQuiz]'s own doc comment. */
    override suspend fun publishQuiz(quizId: String): AppResult<TeacherQuiz> {
        val quiz = quizzes.value[quizId] ?: return AppResult.Failure(AppError.NotFound)
        if (!canPublishQuiz(quiz)) {
            return AppResult.Failure(AppError.Validation(mapOf("publish" to "quiz_incomplete")))
        }
        delay(MockLatency.FAST_MS)
        val updated = quiz.copy(status = TeacherQuizStatus.Published)
        quizzes.value = quizzes.value + (quizId to updated)
        return AppResult.Success(updated)
    }

    override suspend fun generateAiQuizQuestionCandidates(quizId: String): AppResult<List<TeacherQuizQuestion>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(AI_QUESTION_CANDIDATES)
    }

    override suspend fun getQuizAttempts(quizId: String): AppResult<List<TeacherQuizAttempt>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(quizAttempts.value[quizId].orEmpty())
    }

    override suspend fun saveEssayGrade(
        quizId: String,
        studentId: String,
        questionId: String,
        assignedMark: Int,
        feedback: String,
    ): AppResult<TeacherQuizAttempt> {
        val quiz = quizzes.value[quizId] ?: return AppResult.Failure(AppError.NotFound)
        val question = quiz.questions.firstOrNull { it.question.id == questionId }
            ?: return AppResult.Failure(AppError.NotFound)
        val attempts = quizAttempts.value[quizId].orEmpty()
        val index = attempts.indexOfFirst { it.studentId == studentId }
        if (index == -1) return AppResult.Failure(AppError.NotFound)
        val current = attempts[index]
        val existing = current.essayResponses[questionId] ?: return AppResult.Failure(AppError.NotFound)
        val mark = assignedMark.coerceIn(0, question.points)
        val graded = existing.copy(
            pending = false,
            assignedMark = mark,
            teacherFeedback = feedback,
        )
        val updated = current.copy(
            essayResponses = current.essayResponses + (questionId to graded),
            answers = current.answers + (questionId to (mark >= question.points)),
        )
        val nextAttempts = attempts.toMutableList().also { it[index] = updated }
        quizAttempts.value = quizAttempts.value + (quizId to nextAttempts)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    private suspend fun updateQuiz(quizId: String, transform: (TeacherQuiz) -> TeacherQuiz): AppResult<TeacherQuiz> {
        val current = quizzes.value[quizId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = transform(current)
        quizzes.value = quizzes.value + (quizId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    private fun canPublishQuiz(quiz: TeacherQuiz): Boolean =
        quiz.title.isNotBlank() &&
            COURSES.any { it.id == quiz.courseId } &&
            quiz.questions.isNotEmpty() &&
            quiz.questions.all { it.question.prompt.isNotBlank() } &&
            quiz.questions.all { it.points > 0 } &&
            quiz.questions.all { hasValidCorrectAnswer(it.question) }

    private fun hasValidCorrectAnswer(question: QuizQuestion): Boolean = when (question.type) {
        QuestionType.MultipleChoice, QuestionType.TrueFalse ->
            question.options.size >= 2 && question.options.any { it.id == question.correctAnswer }
        QuestionType.ShortAnswer -> true
        QuestionType.GapFill -> question.correctAnswer.isNotBlank()
    }

    // ── TC-12 · Students List ─────────────────────────────────────────────────────────────────

    override suspend fun getStudents(teacherId: String): AppResult<List<TeacherStudentSummary>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(STUDENTS)
    }

    // ── TC-13 · Student Profile — Teacher View ───────────────────────────────────────────────

    override suspend fun getStudent(studentId: String): AppResult<TeacherStudentSummary> {
        delay(MockLatency.FAST_MS)
        val student = STUDENTS.firstOrNull { it.studentId == studentId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(student)
    }

    override suspend fun getStudentAttendance(studentId: String): AppResult<TeacherStudentAttendance> {
        delay(MockLatency.FAST_MS)
        val student = STUDENTS.firstOrNull { it.studentId == studentId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(TeacherStudentAttendance(studentId = studentId, records = attendanceRecordsFor(student)))
    }

    /** Quiz-submission rows are built from the same [QUIZ_ATTEMPTS] TC-11 already reads — never a re-invented fact; only the course-open/lesson/missing-work rows are deterministic MOCK filler. */
    override suspend fun getStudentActivity(studentId: String): AppResult<List<TeacherActivityItem>> {
        delay(MockLatency.LIST_MS)
        val student = STUDENTS.firstOrNull { it.studentId == studentId } ?: return AppResult.Failure(AppError.NotFound)
        val items = mutableListOf<TeacherActivityItem>()
        items += TeacherActivityItem(
            id = "$studentId-course-open", kind = TeacherActivityKind.CourseOpened,
            title = "فتح مادة \"${student.courseTitle}\"", dateLabel = student.lastActiveLabel,
        )
        quizzes.value.values.sortedBy { it.id }.forEach { quiz ->
            val attempt = quizAttempts.value[quiz.id]?.firstOrNull { it.studentId == studentId }
            if (attempt != null && attempt.status == TeacherQuizAttemptStatus.Completed && attempt.submittedLabel != null) {
                items += TeacherActivityItem(
                    id = "${quiz.id}-submit", kind = TeacherActivityKind.QuizSubmitted,
                    title = "أنهى الاختبار \"${quiz.title}\"", dateLabel = attempt.submittedLabel,
                )
            }
        }
        if (student.flags.contains(StudentFlag.MissingWork)) {
            items += TeacherActivityItem(
                id = "$studentId-missed", kind = TeacherActivityKind.AssignmentMissed,
                title = "لم يُسلَّم واجب مستحق", dateLabel = "قبل ٤ أيام",
            )
        } else {
            items += TeacherActivityItem(
                id = "$studentId-lesson", kind = TeacherActivityKind.LessonCompleted,
                title = "أكمل درساً في \"${student.courseTitle}\"", dateLabel = "قبل ٤ أيام",
            )
        }
        return AppResult.Success(items)
    }

    override suspend fun getPrivateNotes(studentId: String): AppResult<List<TeacherPrivateNote>> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(privateNotes.value.filter { it.studentId == studentId }.sortedByDescending { it.id })
    }

    override suspend fun addPrivateNote(studentId: String, text: String): AppResult<TeacherPrivateNote> {
        val note = TeacherPrivateNote(id = "note-${System.currentTimeMillis()}", studentId = studentId, text = text, createdLabel = "الآن")
        privateNotes.value = privateNotes.value + note
        delay(MockLatency.FAST_MS)
        return AppResult.Success(note)
    }

    override suspend fun updatePrivateNote(noteId: String, text: String): AppResult<TeacherPrivateNote> {
        val current = privateNotes.value.firstOrNull { it.id == noteId } ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(text = text)
        privateNotes.value = privateNotes.value.map { if (it.id == noteId) updated else it }
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    override suspend fun deletePrivateNote(noteId: String): AppResult<Unit> {
        privateNotes.value = privateNotes.value.filterNot { it.id == noteId }
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    /** Distinct from [addPrivateNote] on purpose — see [TeacherParentNote]'s own doc comment. */
    override suspend fun sendParentNote(studentId: String, message: String): AppResult<TeacherParentNote> {
        val note = TeacherParentNote(id = "pnote-${System.currentTimeMillis()}", studentId = studentId, message = message, sentLabel = "الآن")
        parentNotes.value = parentNotes.value + note
        delay(MockLatency.FAST_MS)
        return AppResult.Success(note)
    }

    override suspend fun getParentNotes(studentId: String): AppResult<List<TeacherParentNote>> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(parentNotes.value.filter { it.studentId == studentId })
    }

    override suspend fun sendStudentMessage(studentId: String, message: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    // ── TC-14 · Grades ────────────────────────────────────────────────────────────────────────

    override suspend fun getGradebook(courseId: String): AppResult<List<TeacherGradeEntry>> {
        delay(MockLatency.LIST_MS)
        val studentIds = STUDENTS.filter { it.courseId == courseId }.map { it.studentId }
        val entries = studentIds.map { sid -> gradeEntries.value[gradeKey(sid, courseId)] ?: TeacherGradeEntry(studentId = sid, courseId = courseId) }
        return AppResult.Success(entries)
    }

    override suspend fun saveGradeEntry(studentId: String, courseId: String, courseworkScore: Int?, comment: String): AppResult<TeacherGradeEntry> {
        val key = gradeKey(studentId, courseId)
        val current = gradeEntries.value[key] ?: TeacherGradeEntry(studentId = studentId, courseId = courseId)
        val updated = current.copy(courseworkScore = courseworkScore, comment = comment)
        gradeEntries.value = gradeEntries.value + (key to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    override suspend fun publishGrade(studentId: String, courseId: String): AppResult<TeacherGradeEntry> {
        val key = gradeKey(studentId, courseId)
        val current = gradeEntries.value[key] ?: TeacherGradeEntry(studentId = studentId, courseId = courseId)
        val updated = current.copy(publicationStatus = GradePublicationStatus.Published)
        gradeEntries.value = gradeEntries.value + (key to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    /** Only entries with a coursework score actually entered are published — a still-blank entry has nothing meaningful to publish. */
    override suspend fun publishCourseGrades(courseId: String): AppResult<List<TeacherGradeEntry>> {
        val studentIds = STUDENTS.filter { it.courseId == courseId }.map { it.studentId }
        val updatedMap = gradeEntries.value.toMutableMap()
        val results = studentIds.mapNotNull { sid ->
            val key = gradeKey(sid, courseId)
            val current = updatedMap[key] ?: return@mapNotNull null
            if (current.courseworkScore == null || current.publicationStatus == GradePublicationStatus.Published) return@mapNotNull null
            val updated = current.copy(publicationStatus = GradePublicationStatus.Published)
            updatedMap[key] = updated
            updated
        }
        gradeEntries.value = updatedMap
        delay(MockLatency.FAST_MS)
        return AppResult.Success(results)
    }

    private fun gradeKey(studentId: String, courseId: String) = "$studentId|$courseId"

    // ── TC-15 · Teacher Analytics ────────────────────────────────────────────────────────────

    /**
     * Every figure here is derived from the SAME [STUDENTS]/[QUIZ_ATTEMPTS]/[attendanceRecordsFor]
     * fixtures TC-12/TC-11/TC-13 already read, filtered by [courseId] — never a separately
     * hand-picked number. Engagement "active on day/week/month N" is itself derived from each
     * student's own [StudentMonitoringStatus] (a real, already-established signal) rather than a
     * second independent random series, so the chart is honest MOCK data, not decoration.
     */
    override suspend fun getAnalyticsSnapshot(teacherId: String, courseId: String?, period: AnalyticsPeriod): AppResult<TeacherAnalyticsSnapshot> {
        delay(MockLatency.LIST_MS)
        val roster = STUDENTS.filter { courseId == null || it.courseId == courseId }
        val bucketLabels = engagementBucketLabels(period)
        val engagement = bucketLabels.mapIndexed { index, label ->
            EngagementPoint(label = label, activeCount = roster.count { isActiveOnEngagementBucket(it, index) })
        }
        val enrolled = roster.size
        val started = roster.count { it.progressPercent > 0f }
        val lessonsProgressed = roster.count { it.progressPercent >= 0.3f }
        val allAttempts = QUIZ_ATTEMPTS.values.flatten()
        val quizAttempted = roster.count { student ->
            allAttempts.any { it.studentId == student.studentId && it.status == TeacherQuizAttemptStatus.Completed }
        }
        val completed = roster.count { it.progressPercent >= 0.8f }
        val funnel = listOf(
            FunnelStage(FunnelStageKind.Enrolled, enrolled),
            FunnelStage(FunnelStageKind.Started, started),
            FunnelStage(FunnelStageKind.LessonsProgressed, lessonsProgressed),
            FunnelStage(FunnelStageKind.QuizAttempted, quizAttempted),
            FunnelStage(FunnelStageKind.CourseCompleted, completed),
        )
        val atRisk = roster.mapNotNull { student ->
            val reasons = mutableSetOf<AtRiskReason>()
            if (student.flags.contains(StudentFlag.LowProgress)) reasons += AtRiskReason.LowProgress
            if (student.flags.contains(StudentFlag.QuizRisk)) reasons += AtRiskReason.LowQuizPerformance
            if (student.flags.contains(StudentFlag.MissingWork)) reasons += AtRiskReason.MissingWork
            if (student.status == StudentMonitoringStatus.Inactive) reasons += AtRiskReason.Inactivity
            val attendance = TeacherStudentAttendance(studentId = student.studentId, records = attendanceRecordsFor(student))
            if (attendance.attendancePercent < 0.6f) reasons += AtRiskReason.PoorAttendance
            if (reasons.isEmpty()) null else AtRiskStudent(student = student, reasons = reasons)
        }
        return AppResult.Success(TeacherAnalyticsSnapshot(totalEnrolled = enrolled, engagement = engagement, funnel = funnel, atRiskStudents = atRisk))
    }

    // ── TC-17 · Project Authoring ────────────────────────────────────────────────────────────

    override suspend fun getTeacherProjects(teacherId: String): AppResult<List<TeacherProject>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(teacherProjects.value.values.sortedBy { it.id })
    }

    override suspend fun getTeacherProject(projectId: String): AppResult<TeacherProject> {
        delay(MockLatency.FAST_MS)
        return teacherProjects.value[projectId]?.let { AppResult.Success(it) } ?: AppResult.Failure(AppError.NotFound)
    }

    override suspend fun createTeacherProject(courseId: String): AppResult<TeacherProject> {
        val course = COURSES.firstOrNull { it.id == courseId } ?: return AppResult.Failure(AppError.NotFound)
        val project = TeacherProject(
            id = "tp-${System.currentTimeMillis()}",
            title = "",
            courseId = courseId,
            courseTitle = course.title,
            grade = course.grade,
            medium = ProjectMedium.Digital,
            status = TeacherProjectStatus.Draft,
        )
        teacherProjects.value = teacherProjects.value + (project.id to project)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(project)
    }

    override suspend fun saveTeacherProjectMetadata(
        projectId: String,
        title: String,
        description: String,
        deliverable: String,
        teamSize: Int,
        medium: ProjectMedium,
    ): AppResult<TeacherProject> = updateTeacherProject(projectId) {
        it.copy(title = title, description = description, deliverable = deliverable, teamSize = teamSize, medium = medium)
    }

    override suspend fun saveTeacherProjectMilestones(projectId: String, milestones: List<TeacherProjectMilestone>): AppResult<TeacherProject> =
        updateTeacherProject(projectId) { it.copy(milestones = milestones) }

    override suspend fun saveTeacherProjectRubric(projectId: String, rubric: List<TeacherProjectRubricCriterion>): AppResult<TeacherProject> =
        updateTeacherProject(projectId) { it.copy(rubric = rubric) }

    override suspend fun saveTeacherProjectMaterials(
        projectId: String,
        materials: List<TeacherProjectMaterial>,
        safetyNotes: List<TeacherProjectSafetyNote>,
    ): AppResult<TeacherProject> = updateTeacherProject(projectId) { it.copy(materials = materials, safetyNotes = safetyNotes) }

    override suspend fun saveTeacherProjectMedia(projectId: String, media: List<TeacherProjectMediaItem>): AppResult<TeacherProject> =
        updateTeacherProject(projectId) { it.copy(media = media) }

    /** Never trusts the client's own gate check alone — see [TeacherRepository.publishTeacherProject]'s own doc comment. */
    override suspend fun publishTeacherProject(projectId: String): AppResult<TeacherProject> {
        val project = teacherProjects.value[projectId] ?: return AppResult.Failure(AppError.NotFound)
        if (!canPublishTeacherProject(project)) {
            return AppResult.Failure(AppError.Validation(mapOf("publish" to "project_incomplete")))
        }
        delay(MockLatency.FAST_MS)
        val updated = project.copy(status = TeacherProjectStatus.Published)
        teacherProjects.value = teacherProjects.value + (projectId to updated)
        return AppResult.Success(updated)
    }

    private suspend fun updateTeacherProject(projectId: String, transform: (TeacherProject) -> TeacherProject): AppResult<TeacherProject> {
        val current = teacherProjects.value[projectId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = transform(current)
        teacherProjects.value = teacherProjects.value + (projectId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    /**
     * Publish gate: nonblank title; a real course; nonblank deliverable; team size ≥ 1; at
     * least one milestone, each with a nonblank title; every task that exists has a nonblank
     * title; rubric non-empty with every criterion titled, positively weighted, and summing to
     * exactly 100; and, for [ProjectMedium.Physical] projects only, at least one material
     * defined. Digital projects are never forced through the materials/safety check.
     */
    private fun canPublishTeacherProject(project: TeacherProject): Boolean =
        project.title.isNotBlank() &&
            COURSES.any { it.id == project.courseId } &&
            project.deliverable.isNotBlank() &&
            project.teamSize >= 1 &&
            project.milestones.isNotEmpty() &&
            project.milestones.all { it.title.isNotBlank() } &&
            project.milestones.all { m -> m.tasks.all { it.title.isNotBlank() } } &&
            project.rubric.isNotEmpty() &&
            project.rubric.all { it.title.isNotBlank() && it.weightPercent > 0 } &&
            project.rubricWeightTotal == 100 &&
            (project.medium != ProjectMedium.Physical || project.materials.isNotEmpty())

    // ── TC-18 · Project Review Queue ─────────────────────────────────────────────────────────

    override suspend fun getReviewQueue(teacherId: String): AppResult<List<TeacherProjectSubmission>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(reviewQueue.value.values.sortedBy { it.id }.map { withLiveRubric(it) })
    }

    /** Opening a still-awaiting submission moves it to In review — the one place that happens; see [TeacherRepository.getReviewSubmission]'s own doc comment. */
    override suspend fun getReviewSubmission(submissionId: String): AppResult<TeacherProjectSubmission> {
        delay(MockLatency.FAST_MS)
        val current = reviewQueue.value[submissionId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = if (current.reviewStatus == ProjectReviewStatus.AwaitingReview) {
            current.copy(reviewStatus = ProjectReviewStatus.InReview)
        } else {
            current
        }
        if (updated !== current) reviewQueue.value = reviewQueue.value + (submissionId to updated)
        return AppResult.Success(withLiveRubric(updated))
    }

    override suspend fun saveCriterionOverride(submissionId: String, criterionId: String, teacherScore: Int): AppResult<TeacherProjectSubmission> {
        val current = reviewQueue.value[submissionId] ?: return AppResult.Failure(AppError.NotFound)
        val criterion = withLiveRubric(current).criteria.firstOrNull { it.criterionId == criterionId } ?: return AppResult.Failure(AppError.NotFound)
        if (teacherScore < 0 || teacherScore > criterion.maxScore) {
            return AppResult.Failure(AppError.Validation(mapOf("teacherScore" to "out_of_range")))
        }
        val updated = current.copy(
            criteria = current.criteria.map { if (it.criterionId == criterionId) it.copy(teacherScore = teacherScore, isTeacherConfirmed = true) else it },
        )
        reviewQueue.value = reviewQueue.value + (submissionId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(withLiveRubric(updated))
    }

    override suspend fun saveReviewFeedback(submissionId: String, teacherFeedback: String, teacherPrivateComment: String): AppResult<TeacherProjectSubmission> {
        val current = reviewQueue.value[submissionId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(teacherFeedback = teacherFeedback, teacherPrivateComment = teacherPrivateComment)
        reviewQueue.value = reviewQueue.value + (submissionId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(withLiveRubric(updated))
    }

    /**
     * AI pre-review is advisory only — Finalize NEVER copies an unconfirmed [TeacherCriterionReview.aiSuggestedScore]
     * into [TeacherCriterionReview.teacherScore] on the teacher's behalf. Every criterion must
     * already be [TeacherCriterionReview.isTeacherConfirmed] (via [saveCriterionOverride] —
     * "Accept AI suggestion" or "Override", both explicit teacher actions) before this succeeds;
     * this is re-checked here, not only in the ViewModel's own disabled-button state, the same
     * "never trust the client's own gate check alone" discipline [publishQuiz]/[publishTeacherProject]
     * already use.
     */
    override suspend fun finalizeReview(submissionId: String): AppResult<TeacherProjectSubmission> {
        val current = reviewQueue.value[submissionId] ?: return AppResult.Failure(AppError.NotFound)
        if (!withLiveRubric(current).allCriteriaConfirmed) {
            return AppResult.Failure(AppError.Validation(mapOf("finalize" to "unconfirmed_criteria")))
        }
        val updated = current.copy(reviewStatus = ProjectReviewStatus.Reviewed)
        reviewQueue.value = reviewQueue.value + (submissionId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(withLiveRubric(updated))
    }

    /**
     * TC-18 reads its rubric from the TC-17 project entity, never a copied-in-text fixture —
     * [TeacherCriterionReview.criterionTitle]/[TeacherCriterionReview.maxScore] are refreshed
     * here from the SAME [TeacherProject.rubric] TC-17's editor mutates, on every read, so an
     * edited criterion title/weight is reflected immediately; only [TeacherCriterionReview.aiSuggestedScore]/
     * [TeacherCriterionReview.teacherScore] are genuinely submission-specific and stay untouched.
     * Falls back to the last-known title/weight if the project or that criterion was since
     * deleted, rather than losing the submission's own scoring history.
     */
    private fun withLiveRubric(submission: TeacherProjectSubmission): TeacherProjectSubmission {
        val liveRubric = teacherProjects.value[submission.projectId]?.rubric?.associateBy { it.id } ?: return submission
        return submission.copy(
            criteria = submission.criteria.map { criterion ->
                val live = liveRubric[criterion.criterionId] ?: return@map criterion
                criterion.copy(criterionTitle = live.title, maxScore = live.weightPercent)
            },
        )
    }

    /** Creates the canonical Processing lesson a finished mock upload promised, plus its seeded pipeline — the one place either is created. Returns the new lesson's id. */
    private fun createLessonFromUpload(draft: TeacherLessonUploadDraft): String {
        val lessonId = "${draft.courseId}-u${System.currentTimeMillis()}"
        val lesson = TeacherLesson(
            id = lessonId,
            courseId = draft.courseId,
            title = draft.title,
            order = draft.order,
            contentType = draft.contentType,
            status = TeacherLessonStatus.Processing,
        )
        lessons.value = lessons.value + (draft.courseId to (lessons.value[draft.courseId].orEmpty() + lesson))

        val stages = mutableListOf(
            LessonProcessingStageState(LessonProcessingStage.Extract, LessonProcessingStageStatus.Pending),
            LessonProcessingStageState(LessonProcessingStage.Chunk, LessonProcessingStageStatus.Pending),
            LessonProcessingStageState(
                LessonProcessingStage.Index,
                if (draft.indexForTutor) LessonProcessingStageStatus.Pending else LessonProcessingStageStatus.Skipped,
            ),
            LessonProcessingStageState(
                LessonProcessingStage.Quiz,
                if (draft.generateQuiz) LessonProcessingStageStatus.Pending else LessonProcessingStageStatus.Skipped,
            ),
            LessonProcessingStageState(
                LessonProcessingStage.Narrate,
                if (draft.generateNarration) LessonProcessingStageStatus.Pending else LessonProcessingStageStatus.Skipped,
            ),
        )
        // Extract is never skipped, so the pipeline always has a first stage to start running.
        val firstPending = stages.indexOfFirst { it.status == LessonProcessingStageStatus.Pending }
        if (firstPending != -1) stages[firstPending] = stages[firstPending].copy(status = LessonProcessingStageStatus.Running)

        processingStates.value = processingStates.value +
            (lessonId to TeacherLessonProcessingState(lessonId = lessonId, courseId = draft.courseId, stages = stages))
        return lessonId
    }

    private fun publishLesson(courseId: String, lessonId: String) {
        val updated = lessons.value[courseId].orEmpty().map {
            if (it.id == lessonId) it.copy(status = TeacherLessonStatus.Published) else it
        }
        lessons.value = lessons.value + (courseId to updated)
    }

    /** Committed before the delay, deliberately — same reasoning as PJ-05's saveDraft(): a screen leaving mid-call must not lose the save. */
    private suspend fun updateState(teacherId: String, transform: (TeacherSetupState) -> TeacherSetupState): AppResult<TeacherSetupState> {
        val current = setupStates.value[teacherId] ?: TeacherSetupState(teacherId = teacherId)
        val updated = transform(current)
        setupStates.value = setupStates.value + (teacherId to updated)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(updated)
    }

    private companion object {
        const val COMPLETE_TEACHER_ID = "mock-teacher"
        const val INCOMPLETE_TEACHER_ID = "mock-teacher-new"

        fun completeSetupState(): TeacherSetupState = TeacherSetupState(
            teacherId = COMPLETE_TEACHER_ID,
            identity = TeacherIdentityInfo(
                displayName = "أ. ليلى مراد",
                headline = "معلمة فيزياء ورياضيات لطلاب المرحلة الثانوية",
            ),
            subjectsGrades = TeacherSubjectsGrades(
                subjectIds = setOf("physics", "math"),
                grades = setOf(Grade.Grade11, Grade.Baccalaureate),
            ),
            qualifications = listOf(
                TeacherQualification(id = "q1", title = "بكالوريوس في الفيزياء", institution = "جامعة دمشق", year = "2015"),
                TeacherQualification(id = "q2", title = "دبلوم تأهيل تربوي", institution = "جامعة دمشق", year = "2016"),
            ),
            experience = TeacherExperienceInfo(
                yearsOfExperience = 8,
                description = "درّست الفيزياء والرياضيات في عدة مدارس ثانوية، وأشرفت على تحضير طلاب البكالوريا لعدة سنوات متتالية.",
                teachingModes = setOf("فردي", "مجموعات صغيرة"),
            ),
            documents = listOf(
                TeacherSetupDocument(id = "d1", kind = TeacherDocumentKind.Identity, labelHint = "الهوية الشخصية", fileName = "id_scan.jpg"),
                TeacherSetupDocument(id = "d2", kind = TeacherDocumentKind.Qualification, labelHint = "شهادة التخرج", fileName = "diploma.pdf"),
            ),
            pricing = TeacherPricingInfo(sessionPriceLabel = "١٥٬٠٠٠", currencyLabel = "ل.س"),
            voiceSample = TeacherVoiceSample(state = VoiceSampleState.Recorded, durationLabel = "٠٠:٤٥"),
            completedStepIds = TeacherSetupStepId.entries.toSet(),
        )

        /** Deliberately only Identity + Subjects & Grades saved, so TC-01 resumes at Qualifications with real values intact on the earlier two steps. */
        fun incompleteSetupState(): TeacherSetupState = TeacherSetupState(
            teacherId = INCOMPLETE_TEACHER_ID,
            identity = TeacherIdentityInfo(
                displayName = "أ. عمر ياسين",
                headline = "معلم كيمياء لطلاب الصف العاشر",
            ),
            subjectsGrades = TeacherSubjectsGrades(
                subjectIds = setOf("chemistry"),
                grades = setOf(Grade.Grade10),
            ),
            completedStepIds = setOf(TeacherSetupStepId.Identity, TeacherSetupStepId.SubjectsGrades),
        )

        val DASHBOARD_SUMMARY = TeacherDashboardSummary(
            headlineMetricLabel = "٣ تسليمات بحاجة للمراجعة",
            activeStudentsCount = 42,
            lessonsProcessingCount = 2,
            unreadMessagesCount = 5,
            courseCount = 3,
            workItems = listOf(
                // Links to c1-l3 "العمل والطاقة" — the one lesson [seedProcessingStates] pre-seeds
                // as already failed at the Index stage, so opening TC-06 from here shows exactly
                // the failure this item describes, not a state that has to "catch up" to it.
                TeacherWorkItem(
                    id = "w1", kind = TeacherWorkItemKind.LessonProcessingFailed,
                    title = "فشلت معالجة درس \"العمل والطاقة\"",
                    reason = "تعذّر على النظام فهرسة الدرس للمعلم الذكي",
                    contextLabel = "الفيزياء — الصف الحادي عشر",
                    statusLabel = "فشل",
                    urgency = TeacherWorkItemUrgency.Urgent,
                    courseId = "c1",
                    lessonId = "c1-l3",
                ),
                TeacherWorkItem(
                    id = "w2", kind = TeacherWorkItemKind.SubmissionAwaitingReview,
                    title = "3 تسليمات بانتظار المراجعة",
                    reason = "أنهى الطلاب الواجب وينتظرون تقييمك",
                    contextLabel = "الرياضيات — البكالوريا",
                    statusLabel = "بانتظار المراجعة",
                    urgency = TeacherWorkItemUrgency.Normal,
                ),
                TeacherWorkItem(
                    id = "w3", kind = TeacherWorkItemKind.DraftLesson,
                    title = "درس \"كمية الحركة\" لا يزال مسودة",
                    reason = "لم يُنشر بعد لطلابك",
                    contextLabel = "الفيزياء — الصف الحادي عشر",
                    statusLabel = "مسودة",
                    urgency = TeacherWorkItemUrgency.Normal,
                ),
            ),
        )

        val COURSES = listOf(
            TeacherCourseSummary(
                id = "c1", title = "الفيزياء — الصف الحادي عشر", subjectId = "physics", subjectTitle = "الفيزياء",
                grade = Grade.Grade11, studentCount = 28, lessonCount = 4, status = TeacherCourseStatus.Published,
            ),
            TeacherCourseSummary(
                id = "c2", title = "الرياضيات — البكالوريا", subjectId = "math", subjectTitle = "الرياضيات",
                grade = Grade.Baccalaureate, studentCount = 0, lessonCount = 2, status = TeacherCourseStatus.Draft,
            ),
            TeacherCourseSummary(
                id = "c3", title = "الكيمياء — الصف العاشر", subjectId = "chemistry", subjectTitle = "الكيمياء",
                grade = Grade.Grade10, studentCount = 15, lessonCount = 3, status = TeacherCourseStatus.Published,
            ),
        )

        /**
         * TC-04. [TeacherCourseSummary.lessonCount] above matches each list's size exactly —
         * one canonical count, never a separate number that could drift from the real rows.
         */
        fun seedLessons(): Map<String, List<TeacherLesson>> = mapOf(
            "c1" to listOf(
                TeacherLesson(
                    id = "c1-l1", courseId = "c1", title = "الحركة والمتجهات", order = 1,
                    contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Published, updatedLabel = "قبل أسبوع",
                ),
                TeacherLesson(
                    id = "c1-l2", courseId = "c1", title = "قوانين نيوتن", order = 2,
                    contentType = LessonContentType.Video, status = TeacherLessonStatus.Published,
                    durationLabel = "١٨ دقيقة", updatedLabel = "قبل ٥ أيام",
                ),
                // The one Processing lesson in this slice's fixtures — see
                // [seedProcessingStates]'s own doc comment for its scripted TC-06 journey.
                TeacherLesson(
                    id = "c1-l3", courseId = "c1", title = "العمل والطاقة", order = 3,
                    contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Processing,
                ),
                TeacherLesson(
                    id = "c1-l4", courseId = "c1", title = "كمية الحركة", order = 4,
                    contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Draft,
                ),
            ),
            "c2" to listOf(
                TeacherLesson(id = "c2-l1", courseId = "c2", title = "النهايات", order = 1, contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Draft),
                TeacherLesson(id = "c2-l2", courseId = "c2", title = "المشتقات", order = 2, contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Draft),
            ),
            "c3" to listOf(
                TeacherLesson(
                    id = "c3-l1", courseId = "c3", title = "الذرة والجدول الدوري", order = 1,
                    contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Published, updatedLabel = "قبل أسبوعين",
                ),
                TeacherLesson(
                    id = "c3-l2", courseId = "c3", title = "الروابط الكيميائية", order = 2,
                    contentType = LessonContentType.Video, status = TeacherLessonStatus.Published,
                    durationLabel = "٢٢ دقيقة", updatedLabel = "قبل أسبوع",
                ),
                TeacherLesson(
                    id = "c3-l3", courseId = "c3", title = "التفاعلات الكيميائية", order = 3,
                    contentType = LessonContentType.Pdf, status = TeacherLessonStatus.Published, updatedLabel = "قبل ٣ أيام",
                ),
            ),
        )

        /**
         * TC-06 Scenario B, pre-seeded exactly as [DASHBOARD_SUMMARY]'s "w1" work item already
         * describes it — extract/chunk done, index already failed — so opening TC-06 from that
         * item (or from c1-l3's Processing row on TC-04) never has to "catch up" to a claim the
         * dashboard already made. Retrying (Scenario B → C) is deterministic: [advanceLessonProcessing]
         * only ever fails the Index stage once per lesson, tracked by [TeacherLessonProcessingState.hasRetried].
         */
        fun seedProcessingStates(): Map<String, TeacherLessonProcessingState> = mapOf(
            "c1-l3" to TeacherLessonProcessingState(
                lessonId = "c1-l3",
                courseId = "c1",
                stages = listOf(
                    LessonProcessingStageState(LessonProcessingStage.Extract, LessonProcessingStageStatus.Complete),
                    LessonProcessingStageState(LessonProcessingStage.Chunk, LessonProcessingStageStatus.Complete),
                    LessonProcessingStageState(
                        LessonProcessingStage.Index, LessonProcessingStageStatus.Failed,
                        errorLabel = PROCESSING_FAILURE_MESSAGE,
                    ),
                    LessonProcessingStageState(LessonProcessingStage.Quiz, LessonProcessingStageStatus.Pending),
                    LessonProcessingStageState(LessonProcessingStage.Narrate, LessonProcessingStageStatus.Skipped),
                ),
            ),
        )

        /** The only lesson [advanceLessonProcessing] will ever deterministically fail — and only once, until [retryLessonProcessing] clears it. */
        const val FAILING_LESSON_ID = "c1-l3"
        const val PROCESSING_FAILURE_MESSAGE = "تعذر تجهيز الدرس للمعلم الذكي"

        /** Deterministic upload progression — 10 equal ticks from 0 to [TeacherLessonUploadDraft.mockTotalBytes]. */
        const val UPLOAD_TICKS = 10

        /**
         * TC-07 fixtures. "كمية الحركة" (c1-l4, Draft) is the primary editing fixture — every
         * generated question/insight starts [AiReviewStatus.Unreviewed] so the publish gate is
         * genuinely unmet at first open. "الحركة والمتجهات" (c1-l1, already Published) carries a
         * smaller already-Accepted set purely so TC-08 has real content to show when opened
         * directly from a Published lesson, without needing a Draft detour first.
         */
        fun seedEditorStates(): Map<String, TeacherLessonEditorState> = mapOf(
            "c1-l4" to TeacherLessonEditorState(
                lessonId = "c1-l4",
                courseId = "c1",
                extractedText = "كمية الحركة هي مقدار فيزيائي متجه يساوي حاصل ضرب كتلة الجسم في سرعته، " +
                    "ويُرمز لها بالرمز p = m·v. في غياب أي قوى خارجية، يبقى مجموع كميات الحركة لنظام من " +
                    "الأجسام ثابتاً، وهذا ما يُعرف بقانون حفظ كمية الحركة. يُستخدم هذا المبدأ لتحليل " +
                    "التصادمات المرنة وغير المرنة بين الأجسام، وتحديد سرعاتها بعد الاصطدام.",
                chunks = listOf(
                    TeacherLessonChunk(id = "c1l4-ch1", order = 1, text = "كمية الحركة هي مقدار فيزيائي متجه يساوي حاصل ضرب كتلة الجسم في سرعته، ويُرمز لها بالرمز p = m·v."),
                    TeacherLessonChunk(id = "c1l4-ch2", order = 2, text = "في غياب أي قوى خارجية، يبقى مجموع كميات الحركة لنظام من الأجسام ثابتاً، وهذا ما يُعرف بقانون حفظ كمية الحركة."),
                    TeacherLessonChunk(id = "c1l4-ch3", order = 3, text = "يُستخدم هذا المبدأ لتحليل التصادمات المرنة وغير المرنة بين الأجسام، وتحديد سرعاتها بعد الاصطدام."),
                ),
                generatedQuestions = listOf(
                    TeacherGeneratedQuestion(
                        QuizQuestion(
                            id = "c1l4-q1", type = QuestionType.MultipleChoice,
                            prompt = "ما هي العلاقة الرياضية الصحيحة لكمية الحركة؟",
                            options = listOf(
                                QuizOption("a", "p = m·v"), QuizOption("b", "p = m/v"),
                                QuizOption("c", "p = m + v"), QuizOption("d", "p = v²/m"),
                            ),
                            correctAnswer = "a",
                            explanation = "كمية الحركة تساوي حاصل ضرب الكتلة في السرعة: p = m·v.",
                        ),
                    ),
                    TeacherGeneratedQuestion(
                        QuizQuestion(
                            id = "c1l4-q2", type = QuestionType.MultipleChoice,
                            prompt = "ماذا يحدث لمجموع كميات الحركة لنظام معزول عن القوى الخارجية؟",
                            options = listOf(
                                QuizOption("a", "يزداد باستمرار"), QuizOption("b", "يبقى ثابتاً"),
                                QuizOption("c", "يتناقص باستمرار"), QuizOption("d", "يصبح صفراً دائماً"),
                            ),
                            correctAnswer = "b",
                            explanation = "هذا ما ينص عليه قانون حفظ كمية الحركة.",
                        ),
                    ),
                    TeacherGeneratedQuestion(
                        QuizQuestion(
                            id = "c1l4-q3", type = QuestionType.MultipleChoice,
                            prompt = "في أي نوع من التصادمات تُحفظ الطاقة الحركية بالإضافة إلى كمية الحركة؟",
                            options = listOf(
                                QuizOption("a", "التصادم المرن"), QuizOption("b", "التصادم غير المرن"),
                                QuizOption("c", "التصادم اللدن الكامل"), QuizOption("d", "لا يوجد نوع كهذا"),
                            ),
                            correctAnswer = "a",
                            explanation = "التصادم المرن هو الوحيد الذي تُحفظ فيه الطاقة الحركية الكلية.",
                        ),
                    ),
                ),
                insights = listOf(
                    TeacherLessonInsight(
                        id = "c1l4-i1", kind = LessonInsightKind.DifficultConcept,
                        text = "قد يجد الطلاب صعوبة في التمييز بين كمية الحركة (متجهة) والطاقة الحركية (قياسية) — يُنصح بتوضيح الفرق بمثال عملي.",
                    ),
                    TeacherLessonInsight(
                        id = "c1l4-i2", kind = LessonInsightKind.MisconceptionWarning,
                        text = "يخلط بعض الطلاب بين حفظ كمية الحركة وحفظ الطاقة في التصادمات غير المرنة، رغم أن الطاقة الحركية لا تُحفظ فيها.",
                    ),
                ),
            ),
            "c1-l1" to TeacherLessonEditorState(
                lessonId = "c1-l1",
                courseId = "c1",
                extractedText = "الحركة هي تغيّر موضع الجسم بالنسبة إلى نقطة مرجعية عبر الزمن. تُوصف الحركة باستخدام كميات " +
                    "متجهة مثل الإزاحة والسرعة والتسارع، والتي تمتلك مقداراً واتجاهاً معاً. يساعد فهم المتجهات " +
                    "الطلاب على تحليل حركة الأجسام في بعدين أو أكثر بدقة.",
                chunks = listOf(
                    TeacherLessonChunk(id = "c1l1-ch1", order = 1, text = "الحركة هي تغيّر موضع الجسم بالنسبة إلى نقطة مرجعية عبر الزمن."),
                    TeacherLessonChunk(id = "c1l1-ch2", order = 2, text = "تُوصف الحركة باستخدام كميات متجهة مثل الإزاحة والسرعة والتسارع، والتي تمتلك مقداراً واتجاهاً معاً."),
                    TeacherLessonChunk(id = "c1l1-ch3", order = 3, text = "يساعد فهم المتجهات الطلاب على تحليل حركة الأجسام في بعدين أو أكثر بدقة."),
                ),
                generatedQuestions = listOf(
                    TeacherGeneratedQuestion(
                        QuizQuestion(
                            id = "c1l1-q1", type = QuestionType.MultipleChoice,
                            prompt = "ما الفرق الأساسي بين الكمية المتجهة والكمية القياسية؟",
                            options = listOf(
                                QuizOption("a", "المتجهة لها مقدار واتجاه، والقياسية لها مقدار فقط"),
                                QuizOption("b", "كلاهما له مقدار واتجاه"),
                                QuizOption("c", "كلاهما له مقدار فقط"),
                                QuizOption("d", "لا يوجد فرق بينهما"),
                            ),
                            correctAnswer = "a",
                            explanation = "الكمية المتجهة تمتلك مقداراً واتجاهاً، بينما القياسية مقدار فقط.",
                        ),
                        reviewStatus = AiReviewStatus.Accepted,
                    ),
                    TeacherGeneratedQuestion(
                        QuizQuestion(
                            id = "c1l1-q2", type = QuestionType.MultipleChoice,
                            prompt = "أي مما يلي يُعد كمية متجهة؟",
                            options = listOf(
                                QuizOption("a", "الإزاحة"), QuizOption("b", "الكتلة"),
                                QuizOption("c", "الزمن"), QuizOption("d", "درجة الحرارة"),
                            ),
                            correctAnswer = "a",
                            explanation = "الإزاحة لها مقدار واتجاه، على عكس الكتلة والزمن ودرجة الحرارة.",
                        ),
                        reviewStatus = AiReviewStatus.Accepted,
                    ),
                ),
                insights = listOf(
                    TeacherLessonInsight(
                        id = "c1l1-i1", kind = LessonInsightKind.MisconceptionWarning,
                        text = "يخلط بعض الطلاب بين المسافة والإزاحة — يُفضّل توضيح أن الإزاحة متجهة بينما المسافة قياسية.",
                        reviewStatus = AiReviewStatus.Accepted,
                    ),
                ),
            ),
        )

        /**
         * TC-09 fixtures. The complete teacher persona already carries the TC-01-linked sample
         * (matching [completeSetupState]'s own recorded voice sample exactly, same id
         * [TC01_LINKED_SAMPLE_ID] [syncVoiceProfileFromSetup] would use) plus a Ready profile —
         * a coherent "already set up" story. The incomplete persona starts genuinely blank.
         */
        fun seedVoiceProfiles(): Map<String, TeacherVoiceProfile> = mapOf(
            COMPLETE_TEACHER_ID to TeacherVoiceProfile(
                teacherId = COMPLETE_TEACHER_ID,
                consentGranted = true,
                samples = listOf(
                    TeacherVoiceProfileSample(
                        id = TC01_LINKED_SAMPLE_ID,
                        sourceType = VoiceSampleSourceType.Recorded,
                        durationLabel = "٠٠:٤٥",
                        qualityStatus = VoiceSampleQualityStatus.Good,
                        qualityFeedback = GOOD_SAMPLE_FEEDBACK,
                    ),
                ),
                profileStatus = VoiceProfileStatus.Ready,
                clonedNarrationEnabled = true,
                hasRetriedGeneration = true,
            ),
            INCOMPLETE_TEACHER_ID to TeacherVoiceProfile(teacherId = INCOMPLETE_TEACHER_ID),
        )

        /** The one sample id [syncVoiceProfileFromSetup] ever adds/removes — reserved so it never collides with a TC-09-only sample's `sample-<timestamp>` id. */
        const val TC01_LINKED_SAMPLE_ID = "tc01-sample"
        const val GOOD_SAMPLE_FEEDBACK = "صوت واضح مع ضجيج خلفية منخفض"
        const val NEEDS_IMPROVEMENT_SAMPLE_FEEDBACK = "ضجيج الخلفية مرتفع جداً"

        /**
         * TC-10/TC-11 fixtures. "اختبار قوانين نيوتن" (q1, Published, c1) is the one quiz with
         * attempts — [seedNewtonsLawsAttempts]'s own doc comment explains how its numbers were
         * chosen so every TC-11 summary figure is genuinely derivable from these fixtures rather
         * than a hand-picked average that could silently disagree with them.
         */
        fun seedQuizzes(): Map<String, TeacherQuiz> = listOf(
            TeacherQuiz(
                id = "q1", courseId = "c1", courseTitle = "الفيزياء — الصف الحادي عشر",
                title = "اختبار قوانين نيوتن", status = TeacherQuizStatus.Published,
                questions = newtonsLawsQuestions(),
                durationMinutes = 30, passMarkPercent = 60, singleAttempt = true,
            ),
            TeacherQuiz(
                id = "q2", courseId = "c1", courseTitle = "الفيزياء — الصف الحادي عشر",
                title = "تدريب كمية الحركة", status = TeacherQuizStatus.Draft,
                questions = momentumPracticeQuestions(),
                durationMinutes = 15, passMarkPercent = 60, singleAttempt = true,
            ),
            TeacherQuiz(
                id = "q3", courseId = "c2", courseTitle = "الرياضيات — البكالوريا",
                title = "اختبار المشتقات", status = TeacherQuizStatus.Published,
                questions = derivativesQuizQuestions(),
                durationMinutes = null, passMarkPercent = 60, singleAttempt = true,
            ),
        ).associateBy { it.id }

        private fun mcQuestion(id: String, prompt: String, options: List<Pair<String, String>>, correctId: String, explanation: String) =
            TeacherQuizQuestion(
                question = QuizQuestion(
                    id = id, type = QuestionType.MultipleChoice, prompt = prompt,
                    options = options.map { (optId, text) -> QuizOption(optId, text) },
                    correctAnswer = correctId, explanation = explanation,
                ),
                points = 1,
            )

        fun newtonsLawsQuestions(): List<TeacherQuizQuestion> = listOf(
            mcQuestion(
                "q1-1", "ما هو نص قانون نيوتن الأول؟",
                listOf("a" to "يبقى الجسم في حالته ما لم تؤثر عليه قوة محصلة", "b" to "القوة تساوي حاصل ضرب الكتلة في التسارع", "c" to "لكل فعل رد فعل مساوٍ له ومضاد له", "d" to "الطاقة لا تفنى ولا تُستحدث"),
                "a", "هذا هو قانون القصور الذاتي — نص قانون نيوتن الأول.",
            ),
            mcQuestion(
                "q1-2", "وحدة قياس القوة في النظام الدولي هي؟",
                listOf("a" to "نيوتن", "b" to "جول", "c" to "واط", "d" to "باسكال"),
                "a", "وحدة القوة هي النيوتن (N)، تكريماً لإسحاق نيوتن.",
            ),
            mcQuestion(
                "q1-3", "ماذا ينص قانون نيوتن الثاني؟",
                listOf("a" to "القوة = الكتلة × التسارع", "b" to "القوة = الكتلة ÷ التسارع", "c" to "القوة = الكتلة + التسارع", "d" to "القوة تتناسب عكسياً مع الكتلة"),
                "a", "F = m·a هي الصياغة الرياضية لقانون نيوتن الثاني.",
            ),
            mcQuestion(
                "q1-4", "متى يكون الجسم في حالة اتزان؟",
                listOf("a" to "عندما يكون مجموع القوى المؤثرة عليه صفراً", "b" to "عندما تكون سرعته صفراً دائماً", "c" to "عندما تكون كتلته كبيرة", "d" to "عندما لا يتأثر بالجاذبية"),
                "a", "الاتزان يعني أن محصلة القوى تساوي صفراً، سواء كان الجسم ساكناً أو متحركاً بسرعة ثابتة.",
            ),
            mcQuestion(
                "q1-5", "وفق قانون نيوتن الثالث، عندما يدفع شخص جداراً بقوة معينة، فإن الجدار:",
                listOf("a" to "يدفع الشخص بقوة مساوية ومعاكسة في الاتجاه", "b" to "لا يؤثر بأي قوة على الشخص", "c" to "يدفع الشخص بقوة أكبر", "d" to "يدفع الشخص بقوة أصغر"),
                "a", "لكل فعل رد فعل مساوٍ له في المقدار ومضاد له في الاتجاه — هذا لا يعني إلغاء تأثير القوتين لأنهما تؤثران على جسمين مختلفين.",
            ),
            TeacherQuizQuestion(
                question = QuizQuestion(
                    id = "q1-6", type = QuestionType.TrueFalse,
                    prompt = "عبارة: «الكتلة والوزن لهما نفس الوحدة دائماً» — صحيحة أم خاطئة؟",
                    options = listOf(QuizOption("true", "صحيح"), QuizOption("false", "خطأ")),
                    correctAnswer = "false",
                    explanation = "الكتلة تُقاس بالكيلوغرام، بينما الوزن قوة تُقاس بالنيوتن.",
                ),
                points = 1,
            ),
            mcQuestion(
                "q1-7", "أي مما يلي يزيد من تسارع الجسم عند تطبيق نفس القوة؟",
                listOf("a" to "تقليل كتلة الجسم", "b" to "زيادة كتلة الجسم", "c" to "إبقاء الكتلة كما هي", "d" to "لا شيء مما سبق"),
                "a", "التسارع يتناسب عكسياً مع الكتلة عند ثبات القوة (a = F/m).",
            ),
            TeacherQuizQuestion(
                question = QuizQuestion(
                    id = "q1-8", type = QuestionType.ShortAnswer,
                    prompt = "اشرح قانون نيوتن الثالث بكلماتك، واذكر مثالاً من الحياة اليومية.",
                    correctAnswer = "قانون نيوتن الثالث",
                    explanation = "لكل فعل رد فعل مساوٍ له في المقدار ومضاد له في الاتجاه.",
                ),
                points = 5,
            ),
        )

        fun momentumPracticeQuestions(): List<TeacherQuizQuestion> = listOf(
            mcQuestion("q2-1", "ما هي وحدة قياس كمية الحركة؟", listOf("a" to "كغ·م/ث", "b" to "نيوتن", "c" to "جول", "d" to "واط"), "a", "كمية الحركة p = m·v، ووحدتها كغ·م/ث."),
            mcQuestion("q2-2", "كمية الحركة هي مقدار…", listOf("a" to "متجه", "b" to "قياسي فقط", "c" to "ثابت دائماً", "d" to "لا يتغير أبداً"), "a", "كمية الحركة متجهة، لها مقدار واتجاه."),
            mcQuestion("q2-3", "متى تُحفظ كمية الحركة الكلية لنظام؟", listOf("a" to "عند غياب القوى الخارجية", "b" to "دائماً بغض النظر عن الظروف", "c" to "فقط في التصادمات المرنة", "d" to "لا تُحفظ أبداً"), "a", "قانون حفظ كمية الحركة ينطبق فقط في غياب قوى خارجية محصلة."),
            mcQuestion("q2-4", "العلاقة بين كمية الحركة والقوة المؤثرة هي؟", listOf("a" to "القوة = معدل تغير كمية الحركة", "b" to "لا علاقة بينهما", "c" to "كمية الحركة ثابتة دائماً", "d" to "القوة تساوي كمية الحركة مباشرة"), "a", "F = Δp/Δt."),
            mcQuestion("q2-5", "التصادم الذي تُحفظ فيه الطاقة الحركية يُسمى؟", listOf("a" to "تصادماً مرناً", "b" to "تصادماً غير مرن", "c" to "تصادماً لدناً كاملاً", "d" to "لا يوجد تصادم كهذا"), "a", "التصادم المرن هو الوحيد الذي تُحفظ فيه الطاقة الحركية الكلية."),
        )

        fun derivativesQuizQuestions(): List<TeacherQuizQuestion> = listOf(
            mcQuestion("q3-1", "مشتقة الثابت تساوي؟", listOf("a" to "صفر", "b" to "الثابت نفسه", "c" to "واحد", "d" to "غير معرفة"), "a", "مشتقة أي ثابت تساوي صفراً."),
            mcQuestion("q3-2", "مشتقة x² تساوي؟", listOf("a" to "2x", "b" to "x", "c" to "2", "d" to "x²"), "a", "باستخدام قاعدة الأس: d/dx(xⁿ) = n·xⁿ⁻¹."),
            mcQuestion("q3-3", "مشتقة sin(x) تساوي؟", listOf("a" to "cos(x)", "b" to "-cos(x)", "c" to "sin(x)", "d" to "-sin(x)"), "a", "مشتقة الجيب هي جيب التمام."),
            mcQuestion("q3-4", "مشتقة eˣ تساوي؟", listOf("a" to "eˣ", "b" to "x·eˣ", "c" to "eˣ⁻¹", "d" to "1"), "a", "الدالة الأسية eˣ هي مشتقة نفسها."),
            mcQuestion("q3-5", "قاعدة السلسلة (Chain Rule) تُستخدم من أجل؟", listOf("a" to "اشتقاق الدوال المركبة", "b" to "اشتقاق الثوابت فقط", "c" to "حساب التكامل", "d" to "حل المعادلات الخطية"), "a", "تُستخدم قاعدة السلسلة لاشتقاق دالة داخل دالة أخرى."),
            mcQuestion("q3-6", "مشتقة ln(x) تساوي؟", listOf("a" to "1/x", "b" to "x", "c" to "ln(x)", "d" to "eˣ"), "a", "مشتقة اللوغاريتم الطبيعي هي 1/x."),
            mcQuestion("q3-7", "مشتقة مجموع دالتين تساوي؟", listOf("a" to "مجموع مشتقتيهما", "b" to "حاصل ضرب مشتقتيهما", "c" to "الفرق بين مشتقتيهما", "d" to "لا علاقة بينهما"), "a", "الاشتقاق عملية خطية."),
            mcQuestion("q3-8", "عند أي نقطة تمثل مشتقة الدالة ميل المماس؟", listOf("a" to "عند أي نقطة على منحنى الدالة", "b" to "فقط عند الصفر", "c" to "فقط عند القيم الموجبة", "d" to "لا تمثل المشتقة الميل أبداً"), "a", "مشتقة الدالة عند نقطة تساوي ميل المماس للمنحنى في تلك النقطة."),
            mcQuestion("q3-9", "مشتقة xⁿ تساوي؟", listOf("a" to "n·xⁿ⁻¹", "b" to "xⁿ⁻¹", "c" to "n·xⁿ", "d" to "xⁿ/n"), "a", "قاعدة الأس الأساسية في الاشتقاق."),
            mcQuestion("q3-10", "قاعدة حاصل الضرب تُستخدم عند اشتقاق؟", listOf("a" to "حاصل ضرب دالتين", "b" to "مجموع دالتين", "c" to "دالة واحدة فقط", "d" to "دالة مركبة فقط"), "a", "تُستخدم قاعدة حاصل الضرب عند اشتقاق ناتج دالتين مضروبتين معاً."),
        )

        /** TC-10 AI bulk import — a fixed, deterministic 5-question MOCK set, never a real generation call. Every question here carries [TeacherQuizQuestion.isAiOrigin] = true. */
        val AI_QUESTION_CANDIDATES: List<TeacherQuizQuestion> = listOf(
            mcQuestion("ai-1", "ما هي وحدة قياس الطاقة في النظام الدولي؟", listOf("a" to "جول", "b" to "نيوتن", "c" to "واط", "d" to "باسكال"), "a", "الجول هو وحدة الطاقة والشغل في النظام الدولي.").let { it.copy(isAiOrigin = true) },
            TeacherQuizQuestion(
                question = QuizQuestion(
                    id = "ai-2", type = QuestionType.TrueFalse,
                    prompt = "الطاقة الحركية لجسم تعتمد على كتلته وسرعته معاً.",
                    options = listOf(QuizOption("true", "صحيح"), QuizOption("false", "خطأ")),
                    correctAnswer = "true", explanation = "KE = ½·m·v² — تعتمد على الكتلة ومربع السرعة.",
                ),
                points = 1, isAiOrigin = true,
            ),
            mcQuestion("ai-3", "أي مما يلي يُعد مثالاً على قوة الاحتكاك؟", listOf("a" to "مقاومة سطح لحركة جسم عليه", "b" to "الجاذبية الأرضية", "c" to "القوة الكهربائية", "d" to "القوة المغناطيسية"), "a", "الاحتكاك قوة تنشأ من تلامس سطحين وتقاوم الحركة النسبية بينهما.").let { it.copy(isAiOrigin = true) },
            TeacherQuizQuestion(
                question = QuizQuestion(
                    id = "ai-4", type = QuestionType.ShortAnswer,
                    prompt = "عرّف بإيجاز مفهوم القصور الذاتي.",
                    correctAnswer = "ميل الجسم لمقاومة تغيير حالة حركته",
                    explanation = "القصور الذاتي هو خاصية للمادة تجعلها تقاوم أي تغيير في سرعتها أو اتجاهها.",
                ),
                points = 1, isAiOrigin = true,
            ),
            mcQuestion("ai-5", "ما العلاقة بين الشغل والطاقة؟", listOf("a" to "الشغل المبذول يساوي التغير في الطاقة", "b" to "لا علاقة بينهما", "c" to "الشغل دائماً أكبر من الطاقة", "d" to "الطاقة تساوي القوة فقط"), "a", "نظرية الشغل والطاقة تنص على أن الشغل الكلي المبذول على جسم يساوي التغير في طاقته الحركية.").let { it.copy(isAiOrigin = true) },
        )

        /**
         * TC-11. Twelve students, matching [STUDENTS] one-for-one by id. Auto-scored items still
         * use the original correct-index sets. Essay question `q1-8` is teacher-graded:
         * ريم / سمير / دانا pending, لجين already scored, رنا not submitted.
         */
        fun seedNewtonsLawsAttempts(): List<TeacherQuizAttempt> {
            val questionIds = newtonsLawsQuestions().map { it.question.id }
            val essayId = "q1-8"
            fun autoAnswers(correctIndices: Set<Int>, includeEssayBoolean: Boolean): Map<String, Boolean> =
                questionIds.mapIndexedNotNull { index, id ->
                    if (id == essayId && !includeEssayBoolean) null
                    else id to (index in correctIndices)
                }.toMap()
            fun attempt(
                studentId: String,
                name: String,
                correctIndices: Set<Int>,
                submittedLabel: String,
                essay: TeacherEssayResponse? = null,
            ): TeacherQuizAttempt {
                val pendingEssay = essay?.pending == true
                return TeacherQuizAttempt(
                    studentId = studentId,
                    studentName = name,
                    status = TeacherQuizAttemptStatus.Completed,
                    submittedLabel = submittedLabel,
                    answers = autoAnswers(correctIndices, includeEssayBoolean = essay == null || !pendingEssay),
                    essayResponses = if (essay != null) mapOf(essay.questionId to essay) else emptyMap(),
                )
            }
            return listOf(
                attempt(
                    "s1", "ريم الحلبي", setOf(0, 1, 2, 3, 5, 6), "قبل يوم",
                    TeacherEssayResponse(
                        questionId = essayId,
                        studentText = "قانون نيوتن الثالث يقول إن لكل فعل رد فعل مساوٍ له في المقدار ومعاكس له في الاتجاه. مثلاً إذا دفعتُ الحائط، فالحائط يدفعني بنفس القوة.",
                        pending = true,
                    ),
                ),
                attempt(
                    "s2", "سمير الخطيب", setOf(0, 1, 2, 5), "قبل يومين",
                    TeacherEssayResponse(
                        questionId = essayId,
                        studentText = "هو قانون الفعل ورد الفعل.",
                        pending = true,
                    ),
                ),
                attempt(
                    "s3", "لجين النجار", setOf(0, 1, 2, 3, 4, 5, 6, 7), "قبل يوم",
                    TeacherEssayResponse(
                        questionId = essayId,
                        studentText = "لكل فعل رد فعل مساوٍ له في المقدار ومضاد له في الاتجاه. عند المشي ندفع الأرض للخلف فتدفعنا للأمام.",
                        pending = false,
                        assignedMark = 5,
                        teacherFeedback = "شرح واضح. أحسنت.",
                    ),
                ),
                attempt("s4", "عمر الشامي", setOf(1, 3, 7), "قبل 3 أيام"),
                attempt(
                    "s5", "دانا يوسف", setOf(0, 1, 2, 4, 5, 6), "قبل يومين",
                    TeacherEssayResponse(
                        questionId = essayId,
                        studentText = "عندما يؤثر جسم على آخر بقوة، يؤثر الثاني بقوة معاكسة بنفس المقدار. هذا يفسر حركة المشي لأن الأرض تدفعنا للأمام.",
                        pending = true,
                    ),
                ),
                attempt("s6", "كريم زيدان", setOf(1, 2, 5, 6, 7), "قبل يوم"),
                attempt("s7", "هبة قاسم", setOf(0, 1), "قبل أسبوع"),
                attempt("s8", "طارق حداد", setOf(0, 1, 2, 4, 5, 7), "قبل يومين"),
                attempt("s9", "نور الدين سلوم", setOf(0, 1, 2, 3, 4, 5, 6), "قبل يوم"),
                attempt("s10", "مايا فارس", setOf(0, 1, 2, 6), "قبل 3 أيام"),
                attempt("s11", "زياد المصري", setOf(0, 1, 3, 5, 6), "قبل يومين"),
                TeacherQuizAttempt(studentId = "s12", studentName = "رنا عثمان", status = TeacherQuizAttemptStatus.NotSubmitted),
            )
        }

        fun seedQuizAttempts(): Map<String, List<TeacherQuizAttempt>> = mapOf("q1" to seedNewtonsLawsAttempts())

        val QUIZ_ATTEMPTS: Map<String, List<TeacherQuizAttempt>> = seedQuizAttempts()

        /**
         * TC-12 roster. Ids/names deliberately match [seedNewtonsLawsAttempts] one-for-one —
         * "ريم الحلبي" (s1) and "سمير الخطيب" (s2) also reuse the exact persona names already
         * established for ST-01/ST-02's own fixtures, so the same two names mean the same
         * people everywhere in the app, not a coincidence of two separate fixture writers.
         */
        val STUDENTS: List<TeacherStudentSummary> = listOf(
            TeacherStudentSummary("s1", "ريم الحلبي", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.82f, "نشط الآن", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s2", "سمير الخطيب", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.55f, "قبل يومين", StudentMonitoringStatus.NeedsAttention, setOf(StudentFlag.LowProgress)),
            TeacherStudentSummary("s3", "لجين النجار", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.95f, "قبل يوم", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s4", "عمر الشامي", "c2", "الرياضيات — البكالوريا", Grade.Baccalaureate, 0.40f, "قبل 3 أيام", StudentMonitoringStatus.NeedsAttention, setOf(StudentFlag.LowProgress, StudentFlag.QuizRisk)),
            TeacherStudentSummary("s5", "دانا يوسف", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.70f, "قبل يومين", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s6", "كريم زيدان", "c3", "الكيمياء — الصف العاشر", Grade.Grade10, 0.60f, "قبل يوم", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s7", "هبة قاسم", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.20f, "قبل أسبوع", StudentMonitoringStatus.NeedsAttention, setOf(StudentFlag.LowProgress, StudentFlag.QuizRisk, StudentFlag.MissingWork)),
            TeacherStudentSummary("s8", "طارق حداد", "c2", "الرياضيات — البكالوريا", Grade.Baccalaureate, 0.75f, "قبل يومين", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s9", "نور الدين سلوم", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.85f, "نشط الآن", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s10", "مايا فارس", "c3", "الكيمياء — الصف العاشر", Grade.Grade10, 0.50f, "قبل 3 أيام", StudentMonitoringStatus.NeedsAttention, setOf(StudentFlag.LowProgress)),
            TeacherStudentSummary("s11", "زياد المصري", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.65f, "قبل يومين", StudentMonitoringStatus.Active),
            TeacherStudentSummary("s12", "رنا عثمان", "c1", "الفيزياء — الصف الحادي عشر", Grade.Grade11, 0.10f, "قبل أسبوعين", StudentMonitoringStatus.Inactive, setOf(StudentFlag.MissingWork)),
        )

        /**
         * TC-13/TC-15 attendance. Deterministic per student, derived from the SAME
         * [StudentMonitoringStatus] TC-12 already assigns — never an independent random series —
         * so a student TC-12 already flags NeedsAttention/Inactive also shows a visibly worse
         * attendance record here, and TC-15's "poor attendance" at-risk rule reads the exact
         * same fixture. Ten most-recent days, newest first.
         */
        private val ATTENDANCE_DAY_LABELS = listOf(
            "اليوم", "أمس", "قبل يومين", "قبل ٣ أيام", "قبل ٤ أيام",
            "قبل ٥ أيام", "قبل ٦ أيام", "قبل أسبوع", "قبل ٨ أيام", "قبل ٩ أيام",
        )

        fun attendanceRecordsFor(student: TeacherStudentSummary): List<AttendanceRecord> {
            val seed = student.studentId.filter { it.isDigit() }.toIntOrNull() ?: 0
            return ATTENDANCE_DAY_LABELS.mapIndexed { index, label ->
                val status = when (student.status) {
                    StudentMonitoringStatus.Inactive -> if ((index + seed) % 4 == 0) AttendanceStatus.Present else AttendanceStatus.Absent
                    StudentMonitoringStatus.NeedsAttention -> when ((index + seed) % 3) {
                        0 -> AttendanceStatus.Absent
                        1 -> AttendanceStatus.Late
                        else -> AttendanceStatus.Present
                    }
                    StudentMonitoringStatus.Active -> if ((index + seed) % 6 == 5) AttendanceStatus.Late else AttendanceStatus.Present
                }
                AttendanceRecord(dateLabel = label, status = status)
            }
        }

        /** TC-15 engagement chart bucket labels — 7 daily / 4 weekly / 6 monthly, matching [AnalyticsPeriod]'s three windows. */
        fun engagementBucketLabels(period: AnalyticsPeriod): List<String> = when (period) {
            AnalyticsPeriod.SevenDays -> listOf("قبل ٦ أيام", "قبل ٥ أيام", "قبل ٤ أيام", "قبل ٣ أيام", "أول أمس", "أمس", "اليوم")
            AnalyticsPeriod.ThirtyDays -> listOf("الأسبوع ١", "الأسبوع ٢", "الأسبوع ٣", "الأسبوع ٤")
            AnalyticsPeriod.Term -> listOf("الشهر ١", "الشهر ٢", "الشهر ٣", "الشهر ٤", "الشهر ٥", "الشهر ٦")
        }

        /** Same [StudentMonitoringStatus]-derived determinism as [attendanceRecordsFor] — a real signal, not an independent random series. */
        fun isActiveOnEngagementBucket(student: TeacherStudentSummary, bucketIndex: Int): Boolean {
            val seed = student.studentId.filter { it.isDigit() }.toIntOrNull() ?: 0
            return when (student.status) {
                StudentMonitoringStatus.Active -> (bucketIndex + seed) % 5 != 4
                StudentMonitoringStatus.NeedsAttention -> (bucketIndex + seed) % 2 == 0
                StudentMonitoringStatus.Inactive -> (bucketIndex + seed) % 4 == 0
            }
        }

        /** TC-14. A handful of Physics (c1) students already have a coursework score entered — one Draft, two Published — so TC-14 has real content to review; every other (student, course) pair starts genuinely blank. */
        fun seedGradeEntries(): Map<String, TeacherGradeEntry> = listOf(
            TeacherGradeEntry(studentId = "s1", courseId = "c1", courseworkScore = 87, comment = "عمل ممتاز ومنتظم", publicationStatus = GradePublicationStatus.Published),
            TeacherGradeEntry(studentId = "s3", courseId = "c1", courseworkScore = 95, comment = "", publicationStatus = GradePublicationStatus.Draft),
            TeacherGradeEntry(studentId = "s5", courseId = "c1", courseworkScore = 72, comment = "يحتاج مزيداً من المراجعة", publicationStatus = GradePublicationStatus.Published),
        ).associateBy { "${it.studentId}|${it.courseId}" }

        /**
         * TC-17. "منبّه مستوى الماء" (Water Alarm System) deliberately reuses the id
         * `"water-alarm"` — the SAME id [com.rork.eduspark.data.repository.mock.MockProjectRepository]'s
         * own student-facing `CATALOG` entry uses — identity continuity only, per this slice's
         * own instruction; this row is never read by [com.rork.eduspark.data.repository.ProjectRepository]
         * and does not mutate that catalog. Published, with a complete rubric summing to exactly
         * 100 (40+25+20+15) — the same four criteria/weights [seedReviewQueue] scores against,
         * so TC-17 and TC-18 can never disagree about what this project's rubric says. "تدقيق
         * كفاءة الطاقة" (Energy Efficiency Audit) is the deliberately-incomplete Draft
         * counterpart the brief asks for — Digital medium, no rubric yet, so TC-17's publish
         * gate has a genuine incomplete case to show.
         */
        fun seedTeacherProjects(): Map<String, TeacherProject> = listOf(
            TeacherProject(
                id = "water-alarm",
                title = "منبّه مستوى الماء",
                description = "مشروع عملي يطبّق مفاهيم الدارات الكهربائية والحساسات لبناء جهاز تنبيه فعلي يمكن استخدامه في المنزل.",
                courseId = "c1", courseTitle = "الفيزياء — الصف الحادي عشر", grade = Grade.Grade11,
                deliverable = "جهاز إنذار حقيقي يعمل عند ارتفاع منسوب الماء",
                teamSize = 1, medium = ProjectMedium.Physical, status = TeacherProjectStatus.Published,
                milestones = listOf(
                    TeacherProjectMilestone(
                        id = "wa-m1", order = 1, title = "فهم الدارة والحساس", contextLabel = "الأسبوع الأول",
                        tasks = listOf(
                            TeacherProjectTask(id = "wa-m1-t1", order = 1, title = "التعرّف على مكوّنات الدارة"),
                            TeacherProjectTask(id = "wa-m1-t2", order = 2, title = "اختبار الحساس جافاً ورطباً"),
                        ),
                    ),
                    TeacherProjectMilestone(
                        id = "wa-m2", order = 2, title = "بناء واختبار الجهاز", contextLabel = "الأسبوع الثاني",
                        tasks = listOf(
                            TeacherProjectTask(id = "wa-m2-t1", order = 1, title = "تجميع الدارة الكاملة على اللوحة"),
                            TeacherProjectTask(id = "wa-m2-t2", order = 2, title = "اختبار الجهاز في ظروف واقعية"),
                        ),
                    ),
                ),
                rubric = listOf(
                    TeacherProjectRubricCriterion(id = "r-technical", title = "الدقة التقنية", description = "صحة عمل الدارة والحساس", weightPercent = 40),
                    TeacherProjectRubricCriterion(id = "r-process", title = "التوثيق والعملية", description = "وضوح خطوات العمل والتوثيق", weightPercent = 25),
                    TeacherProjectRubricCriterion(id = "r-collaboration", title = "التعاون الجماعي", description = "المشاركة والتنظيم", weightPercent = 20),
                    TeacherProjectRubricCriterion(id = "r-presentation", title = "العرض النهائي", description = "وضوح الشرح وجودة العرض", weightPercent = 15),
                ),
                materials = listOf(
                    TeacherProjectMaterial(id = "tm-sensor", label = "حساس مستوى الماء", quantityLabel = "١", note = "متوفر في محلات الإلكترونيات"),
                    TeacherProjectMaterial(id = "tm-breadboard", label = "لوحة تجارب (Breadboard)", quantityLabel = "١"),
                    TeacherProjectMaterial(id = "tm-battery", label = "بطارية 9 فولت", quantityLabel = "١"),
                ),
                safetyNotes = listOf(
                    TeacherProjectSafetyNote(id = "ts-1", text = "استخدم مصدر طاقة منخفض الجهد فقط أثناء الاختبار.", severity = SafetySeverity.Important),
                    TeacherProjectSafetyNote(id = "ts-2", text = "تجنّب ملامسة الماء لأي توصيلة كهربائية مكشوفة.", severity = SafetySeverity.Important),
                ),
            ),
            TeacherProject(
                id = "energy-audit",
                title = "تدقيق كفاءة الطاقة",
                description = "مشروع رقمي يحلّل فيه الطلاب استهلاك الطاقة في المنزل ويقترحون خطة لتقليله.",
                courseId = "c1", courseTitle = "الفيزياء — الصف الحادي عشر", grade = Grade.Grade11,
                deliverable = "تقرير رقمي يقترح خطة لتقليل استهلاك الطاقة المنزلي",
                teamSize = 2, medium = ProjectMedium.Digital, status = TeacherProjectStatus.Draft,
                milestones = listOf(
                    TeacherProjectMilestone(id = "ea-m1", order = 1, title = "جمع بيانات الاستهلاك"),
                ),
            ),
        ).associateBy { it.id }

        /**
         * TC-18. Both submissions score the SAME four "water-alarm" criteria [seedTeacherProjects]
         * authors — TC-17 and TC-18 read the identical rubric, never a copied-in-text duplicate.
         * s3's AI suggestion (32/40, 19/25, 17/20, 12/15 → 80/100) is the exact worked example
         * this slice's own brief specifies. s9 is a second Awaiting-review case with different
         * AI numbers; s1 is pre-seeded already [ProjectReviewStatus.Reviewed] with a
         * teacher-confirmed total, so the queue has a genuine "already handled" case to show.
         * Student ids/names match [STUDENTS] one-for-one — the same TC-12/TC-13 personas, never
         * a disconnected cast.
         */
        fun seedReviewQueue(): Map<String, TeacherProjectSubmission> {
            fun criteria(technical: Int, process: Int, collaboration: Int, presentation: Int, teacherConfirmed: Boolean = false) = listOf(
                TeacherCriterionReview("r-technical", "الدقة التقنية", 40, technical, if (teacherConfirmed) technical else null),
                TeacherCriterionReview("r-process", "التوثيق والعملية", 25, process, if (teacherConfirmed) process else null),
                TeacherCriterionReview("r-collaboration", "التعاون الجماعي", 20, collaboration, if (teacherConfirmed) collaboration else null),
                TeacherCriterionReview("r-presentation", "العرض النهائي", 15, presentation, if (teacherConfirmed) presentation else null),
            )
            return listOf(
                TeacherProjectSubmission(
                    id = "sub-1", projectId = "water-alarm", projectTitle = "منبّه مستوى الماء",
                    studentId = "s3", studentName = "لجين النجار", milestoneTitle = "بناء واختبار الجهاز",
                    submittedLabel = "قبل يوم",
                    artifactSummary = "صور للدارة المجمّعة + تسجيل قصير لعمل الجهاز عند ارتفاع الماء",
                    studentComment = "جرّبت الجهاز عدة مرات وكان يعمل بثبات، واجهت صعوبة بسيطة في تثبيت الحساس.",
                    reviewStatus = ProjectReviewStatus.AwaitingReview,
                    aiAvailability = AiPreReviewAvailability.Ready,
                    criteria = criteria(32, 19, 17, 12),
                    aiStrengths = listOf("الدارة تعمل بشكل صحيح ومستقر", "توثيق واضح لخطوات التجميع"),
                    aiConcerns = listOf("لم يوضّح الطالب كيفية تثبيت الحساس بشكل نهائي"),
                    aiSuggestedFeedback = "عمل جيد وموثّق بوضوح — يُفضّل إضافة تفصيل عن طريقة تثبيت الحساس في الإصدار النهائي.",
                ),
                TeacherProjectSubmission(
                    id = "sub-2", projectId = "water-alarm", projectTitle = "منبّه مستوى الماء",
                    studentId = "s9", studentName = "نور الدين سلوم", milestoneTitle = "بناء واختبار الجهاز",
                    submittedLabel = "قبل يومين",
                    artifactSummary = "صورة للدارة + ملاحظات مكتوبة عن نتائج الاختبار",
                    studentComment = "الجهاز يعمل لكن الاستجابة كانت بطيئة قليلاً عند التغيّر السريع لمستوى الماء.",
                    reviewStatus = ProjectReviewStatus.AwaitingReview,
                    aiAvailability = AiPreReviewAvailability.Ready,
                    criteria = criteria(28, 22, 18, 10),
                    aiStrengths = listOf("توثيق تفصيلي لنتائج الاختبار"),
                    aiConcerns = listOf("الدارة تعمل لكن استجابتها أبطأ من المتوقع", "العرض النهائي مختصر جداً"),
                    aiSuggestedFeedback = "التوثيق قوي، لكن يُنصح بتحسين زمن استجابة الحساس وتوسيع قسم العرض النهائي.",
                ),
                TeacherProjectSubmission(
                    id = "sub-3", projectId = "water-alarm", projectTitle = "منبّه مستوى الماء",
                    studentId = "s1", studentName = "ريم الحلبي", milestoneTitle = "بناء واختبار الجهاز",
                    submittedLabel = "قبل أسبوع",
                    artifactSummary = "فيديو قصير لعمل الجهاز + صور للدارة النهائية",
                    studentComment = "أنهيت المشروع واختبرته في أكثر من موقف.",
                    reviewStatus = ProjectReviewStatus.Reviewed,
                    aiAvailability = AiPreReviewAvailability.Ready,
                    criteria = criteria(38, 23, 19, 14, teacherConfirmed = true),
                    aiStrengths = listOf("تنفيذ دقيق ومضبوط", "عرض نهائي واضح ومقنع"),
                    aiConcerns = emptyList(),
                    aiSuggestedFeedback = "عمل ممتاز على جميع المستويات.",
                    teacherFeedback = "عمل ممتاز — دقة تقنية عالية وعرض نهائي واضح. أحسنتِ.",
                ),
            ).associateBy { it.id }
        }
    }
}

/**
 * Learning fixtures for ST-01/ST-02. Deterministic and reuses the same "Reem Al-Halabi /
 * Samer Al-Khatib / Mathematics Unit 3" persona already established in the onboarding
 * fixtures, so a tester walking the whole funnel sees one consistent story rather than a
 * new cast of names per screen. Titles are intentionally mixed-direction where the anchor
 * shows it ("درس Python الأول") to keep bidirectional text shaping honest during development.
 */
class MockLearningRepository(
    private val entitlements: MockStudentEntitlements,
) : LearningRepository {

    // The single shared "which lessons are done" source of truth — see the interface's own
    // doc comment. Only "math-3" can ever land here in this slice (it's the one lesson with
    // real player content students can actually complete), so the helpers below only need to
    // account for that one case rather than a fully generic recomputation.
    private val completedLessonIdsFlow = MutableStateFlow<Set<String>>(emptySet())
    override val completedLessonIds: Flow<Set<String>> = completedLessonIdsFlow.asStateFlow()

    override suspend fun markLessonCompleted(lessonId: String) {
        completedLessonIdsFlow.update { it + lessonId }
    }

    private fun isMathLesson3Completed(): Boolean = "math-3" in completedLessonIdsFlow.value
    private fun mathCompletedLessonCount(): Int = MATH_BASE_COMPLETED_COUNT + if (isMathLesson3Completed()) 1 else 0
    private fun mathProgress(): Float = mathCompletedLessonCount().toFloat() / MATH_TOTAL_LESSON_COUNT

    override suspend fun getStudentHome(): AppResult<StudentHomeSnapshot> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(
            StudentHomeSnapshot(
                studentName = "ريم الحلبي",
                grade = Grade.Baccalaureate,
                streakDays = 7,
                gamification = GamificationSnapshot(
                    level = 4, xp = 340, progressToNextLevel = 340f / 500f, streakDays = 7,
                    xpForNextLevel = 500, streakHistory = MOCK_STREAK_HISTORY,
                ),
                continueItem = if (isMathLesson3Completed()) {
                    ContinueLearningItem(
                        lessonId = "math-4",
                        courseId = "math",
                        lessonTitle = "قاعدة السلسلة",
                        subjectTitle = "الرياضيات",
                        subjectSubtitle = "الوحدة الثالثة — المشتقات وتطبيقاتها",
                        minutesLeft = 22,
                        lessonIndex = 4,
                        lessonTotal = 16,
                        mediaTypes = setOf(LessonMediaType.Video),
                        teacherName = "الأستاذ سامر الخطيب",
                    )
                } else {
                    ContinueLearningItem(
                        lessonId = "math-3",
                        courseId = "math",
                        lessonTitle = "المشتقة الثانية",
                        subjectTitle = "الرياضيات",
                        subjectSubtitle = "الوحدة الثالثة — المشتقات وتطبيقاتها",
                        minutesLeft = 12,
                        lessonIndex = 3,
                        lessonTotal = 16,
                        mediaTypes = setOf(LessonMediaType.Video, LessonMediaType.Pdf, LessonMediaType.Audio),
                        teacherName = "الأستاذ سامر الخطيب",
                    )
                },
                todayPlan = listOf(
                    PlannerItem(time = "17:00", title = "مراجعة قواعد الاشتقاق", durationMinutes = 15),
                    PlannerItem(time = "19:30", title = "تمارين الفيزياء — الفصل 6", durationMinutes = 20),
                    PlannerItem(time = "21:00", title = "محادثة إنجليزية مع جوري", durationMinutes = 10),
                ),
                subjects = listOf(
                    SubjectProgress("math", "الرياضيات", mathProgress(), if (isMathLesson3Completed()) "الوحدة 2 · الدرس 4" else "الوحدة 2 · الدرس 3", teacherName = "الأستاذ سامر الخطيب"),
                    SubjectProgress("physics", "الفيزياء", 0.17f, "الوحدة 1 · الدرس 2", teacherName = "الأستاذة لينا حداد"),
                    SubjectProgress("chemistry", "الكيمياء", 0.12f, "الوحدة 1 · الدرس 2", teacherName = "الأستاذة هدى العلي"),
                ),
                // Neither Projects nor the Language module has a backend yet (Source Audit
                // §1) — these gates stay false rather than fabricating progress for either.
                hasActiveProject = false,
                englishAvailable = false,
                // Consistent with math-1/math-2 (completed) + physics-1 (completed) across the
                // three in-progress subjects above, plus math-3 once the student completes it.
                completedLessonsTotal = 3 + if (isMathLesson3Completed()) 1 else 0,
                lastQuizScorePercent = 85,
            )
        )
    }

    override suspend fun getPath(pathId: String): AppResult<LearningPath> = when (pathId) {
        "math" -> AppResult.Success(mathCourse())
        "physics" -> AppResult.Success(physicsCourse())
        "chemistry" -> AppResult.Success(unpublishedChemistryCourse())
        "biology" -> AppResult.Success(lockedBiologyCourse())
        else -> {
            delay(MockLatency.FAST_MS)
            AppResult.Failure(AppError.NotFound)
        }
    }

    /**
     * STUDENT_COURSES tab (course discovery — Test-2SY's `MySubjectsSection`/`SubjectCatalogCard`
     * reference). Projects the SAME four course fixtures [getPath] already serves down to a
     * card-sized summary — one source of truth for a course's identity/teacher/progress/lock
     * state, never a second hand-authored list that could drift from it.
     */
    override suspend fun getStudentCourses(): AppResult<List<StudentCourseSummary>> {
        delay(MockLatency.LIST_MS)
        val courses = listOf(mathCourse(), physicsCourse(), unpublishedChemistryCourse(), lockedBiologyCourse())
        return AppResult.Success(
            courses.map { course ->
                StudentCourseSummary(
                    courseId = course.id,
                    title = course.title,
                    teacherName = course.teacherName,
                    progress = course.progress,
                    currentLabel = course.subtitle,
                    isEntitled = course.isEntitled,
                    isPublished = course.isPublished,
                    completedLessonCount = course.completedLessonCount,
                    totalLessonCount = course.totalLessonCount,
                )
            }
        )
    }

    override suspend fun getGamification(): AppResult<GamificationSnapshot> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(
            GamificationSnapshot(
                level = 4, xp = 340, progressToNextLevel = 340f / 500f, streakDays = 7,
                xpForNextLevel = 500, streakHistory = MOCK_STREAK_HISTORY,
            )
        )
    }

    /**
     * ST-03. Hand-authored per lesson rather than derived from [mathCourse]/[physicsCourse] —
     * those two build a full [LearningPath] (with their own latency) every call, and the
     * player only ever needs one lesson at a time. "math-3" is the one lesson ST-02, ST-03,
     * ST-04 and ST-05 all share, so a tester walking the whole slice sees one continuous story.
     */
    override suspend fun getLesson(lessonId: String): AppResult<LessonDetail> {
        delay(MockLatency.FAST_MS)
        val lesson = lessonFixtures[lessonId]
            ?: lessonFromCourseStep(lessonId)
            ?: return AppResult.Failure(AppError.NotFound)
        val isCompleted = lesson.isCompleted || lessonId in completedLessonIdsFlow.value
        return AppResult.Success(lesson.copy(isCompleted = isCompleted))
    }

    private val lessonFixtures: Map<String, LessonDetail> = mapOf(
        "math-1" to LessonDetail(
            id = "math-1", courseId = "math", courseTitle = "الرياضيات", teacherName = "الأستاذ سامر الخطيب",
            title = "الحدود والاتصال", status = LessonStatus.Processed,
            mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Video), durationMinutes = 20,
            pageCount = 8, lessonIndex = 1, lessonTotal = 16, isCompleted = true, quizId = null,
            keyIdeas = listOf(
                "النهاية تصف سلوك الدالة وهي تقترب من نقطة معيّنة، لا قيمتها عندها بالضرورة",
                "الدالة متصلة عند نقطة إذا كانت نهايتها عندها تساوي قيمتها فيها",
                "كل دالة قابلة للاشتقاق متصلة، لكن العكس غير صحيح دائماً",
            ),
        ),
        "math-2" to LessonDetail(
            id = "math-2", courseId = "math", courseTitle = "الرياضيات", teacherName = "الأستاذ سامر الخطيب",
            title = "قواعد الاشتقاق", status = LessonStatus.Processed,
            mediaTypes = setOf(LessonMediaType.Pdf), durationMinutes = 18,
            pageCount = 7, lessonIndex = 2, lessonTotal = 16, isCompleted = true, quizId = null,
            keyIdeas = listOf(
                "مشتقة الدالة xⁿ تساوي n·x^(n-1)",
                "مشتقة مجموع دالتين تساوي مجموع مشتقتيهما",
                "قاعدة الضرب وقاعدة القسمة تُستخدمان عندما تكون الدالة حاصل ضرب أو قسمة دالتين",
            ),
        ),
        // The anchor's exact ST-02→ST-09 continuity lesson.
        "math-3" to LessonDetail(
            id = "math-3", courseId = "math", courseTitle = "الرياضيات", teacherName = "الأستاذ سامر الخطيب",
            title = "المشتقة الثانية", status = LessonStatus.Processed,
            mediaTypes = setOf(LessonMediaType.Video, LessonMediaType.Pdf, LessonMediaType.Audio), durationMinutes = 12,
            pageCount = 6, lessonIndex = 3, lessonTotal = 16, isCompleted = false, quizId = "quiz-math-3",
            keyIdeas = listOf(
                "المشتقة الثانية هي مشتقة المشتقة الأولى للدالة",
                "تخبرنا المشتقة الثانية عن تقعّر منحنى الدالة — موجبة يعني مقعّر لأعلى",
                "نقطة الانعطاف هي حيث تتغيّر إشارة المشتقة الثانية",
            ),
        ),
        "physics-1" to LessonDetail(
            id = "physics-1", courseId = "physics", courseTitle = "الفيزياء", teacherName = "الأستاذة لينا حداد",
            title = "القوى والحركة", status = LessonStatus.Processed,
            mediaTypes = setOf(LessonMediaType.Video), durationMinutes = 22,
            lessonIndex = 1, lessonTotal = PHYSICS_TOTAL_LESSON_COUNT, isCompleted = true, quizId = null,
            keyIdeas = listOf(
                "القوة هي أي تأثير يغيّر من سرعة أو اتجاه حركة الجسم",
                "السرعة كمية متجهة، بينما السرعة العددية كمية قياسية فقط",
                "التسارع هو معدل تغيّر السرعة مع الزمن",
            ),
        ),
        "physics-2" to LessonDetail(
            id = "physics-2", courseId = "physics", courseTitle = "الفيزياء", teacherName = "الأستاذة لينا حداد",
            title = "قوانين نيوتن", status = LessonStatus.Processed,
            mediaTypes = setOf(LessonMediaType.Pdf), durationMinutes = 20,
            pageCount = 5, lessonIndex = 2, lessonTotal = PHYSICS_TOTAL_LESSON_COUNT, isCompleted = false, quizId = null,
            keyIdeas = listOf(
                "قانون نيوتن الأول: الجسم الساكن يبقى ساكناً ما لم تؤثر عليه قوة خارجية",
                "قانون نيوتن الثاني: القوة تساوي الكتلة مضروبة بالتسارع (F = m·a)",
                "قانون نيوتن الثالث: لكل فعل ردّ فعل مساوٍ له بالمقدار ومعاكس بالاتجاه",
            ),
        ),
    )

    /** The anchor's exact ST-02 example: Mathematics — Unit 3, derivatives and applications. */
    private suspend fun mathCourse(): LearningPath {
        delay(MockLatency.LIST_MS)
        val math3Completed = isMathLesson3Completed()
        return LearningPath(
            id = "math",
            title = "الرياضيات",
            subtitle = "الوحدة الثانية — المشتقات وتطبيقاتها",
            progress = mathProgress(),
            teacherName = "الأستاذ سامر الخطيب",
            quizCount = 2,
            lastUpdatedLabel = "آخر تحديث اليوم",
            completedLessonCount = mathCompletedLessonCount(),
            totalLessonCount = MATH_TOTAL_LESSON_COUNT,
            steps = listOf(
                LearningStep(
                    id = "math-1", title = "الحدود والاتصال", subtitle = null,
                    status = LessonStatus.Processed, isCurrent = false, isCompleted = true,
                    durationMinutes = 20, mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Video), xpEarned = 20,
                ),
                LearningStep(
                    id = "math-2", title = "قواعد الاشتقاق", subtitle = null,
                    status = LessonStatus.Processed, isCurrent = false, isCompleted = true,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf), xpEarned = 18,
                ),
                LearningStep(
                    id = "math-3", title = "المشتقة الثانية", subtitle = null,
                    status = LessonStatus.Processed, isCurrent = !math3Completed, isCompleted = math3Completed,
                    durationMinutes = 12, mediaTypes = setOf(LessonMediaType.Video, LessonMediaType.Pdf, LessonMediaType.Audio),
                    minutesLeft = if (math3Completed) null else 12,
                    xpEarned = if (math3Completed) 15 else null,
                ),
                LearningStep(
                    id = "math-4", title = "قاعدة السلسلة", subtitle = null,
                    status = if (math3Completed) LessonStatus.Processed else LessonStatus.LockedSequential,
                    isCurrent = math3Completed,
                    isCompleted = false,
                    durationMinutes = 22, mediaTypes = setOf(LessonMediaType.Video),
                    minutesLeft = if (math3Completed) 22 else null,
                    lockedReason = if (math3Completed) null else LockedReason.RequiresStep("المشتقة الثانية"),
                ),
                LearningStep(
                    id = "math-5", title = "تطبيقات المشتقة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 25, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("قاعدة السلسلة"),
                ),
                LearningStep(
                    id = "math-6", title = "اختبار الوحدة الثالثة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    isMilestone = true, lockedReason = LockedReason.RequiresStepCount(4),
                ),
                LearningStep(
                    id = "math-7", title = "دراسة التزايد والتناقص", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("اختبار الوحدة الثالثة"),
                ),
                LearningStep(
                    id = "math-8", title = "رسم منحنى الدالة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 24, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("دراسة التزايد والتناقص"),
                ),
                LearningStep(
                    id = "math-9", title = "النهايات اللانهائية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 20, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("رسم منحنى الدالة"),
                ),
                LearningStep(
                    id = "math-10", title = "المقاربـات", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 16, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("النهايات اللانهائية"),
                ),
                LearningStep(
                    id = "math-11", title = "تكاملات مباشرة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 22, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("المقاربـات"),
                ),
                LearningStep(
                    id = "math-12", title = "تطبيقات التكامل", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 24, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("تكاملات مباشرة"),
                ),
                LearningStep(
                    id = "math-13", title = "مراجعة المشتقات", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Audio),
                    lockedReason = LockedReason.RequiresStep("تطبيقات التكامل"),
                ),
                LearningStep(
                    id = "math-14", title = "نماذج امتحانية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 26, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("مراجعة المشتقات"),
                ),
                LearningStep(
                    id = "math-15", title = "اختبار شامل", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    isMilestone = true, lockedReason = LockedReason.RequiresStepCount(14),
                ),
                LearningStep(
                    id = "math-16", title = "خطة الإعادة النهائية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 14, mediaTypes = setOf(LessonMediaType.Audio),
                    lockedReason = LockedReason.RequiresStep("اختبار شامل"),
                ),
            ),
        )
    }

    /** A second, shorter course so ST-01's subject grid has somewhere real to lead. */
    private suspend fun physicsCourse(): LearningPath {
        delay(MockLatency.LIST_MS)
        return physicsPath()
    }

    private fun lessonFromCourseStep(lessonId: String): LessonDetail? {
        val course = when (lessonId.substringBefore("-")) {
            "physics" -> physicsPath()
            else -> return null
        }
        val index = course.steps.indexOfFirst { it.id == lessonId }
        if (index < 0) return null
        val step = course.steps[index]
        return LessonDetail(
            id = step.id,
            courseId = course.id,
            courseTitle = course.title,
            teacherName = course.teacherName,
            title = step.title,
            status = if (step.status == LessonStatus.LockedSequential || step.status == LessonStatus.LockedByEntitlement) {
                step.status
            } else {
                LessonStatus.Processed
            },
            mediaTypes = step.mediaTypes.ifEmpty { setOf(LessonMediaType.Pdf) },
            durationMinutes = step.durationMinutes,
            pageCount = if (LessonMediaType.Pdf in step.mediaTypes) 4 else 0,
            lessonIndex = index + 1,
            lessonTotal = course.totalLessonCount,
            isCompleted = step.isCompleted,
            quizId = null,
            keyIdeas = listOf(
                step.title,
                course.subtitle,
                "طبّق الفكرة على مثال قصير ثم تأكد بسؤال واحد",
            ),
        )
    }

    private fun physicsPath(): LearningPath {
        val extraCompleted = completedLessonIdsFlow.value
        val raw = listOf(
                LearningStep(
                    id = "physics-1", title = "القوى والحركة", subtitle = null,
                    status = LessonStatus.Processed, isCurrent = false, isCompleted = true,
                    durationMinutes = 22, mediaTypes = setOf(LessonMediaType.Video), xpEarned = 22,
                ),
                LearningStep(
                    id = "physics-2", title = "قوانين نيوتن", subtitle = null,
                    status = LessonStatus.Processed, isCurrent = true, isCompleted = false,
                    durationMinutes = 20, mediaTypes = setOf(LessonMediaType.Pdf), minutesLeft = 14,
                ),
                LearningStep(
                    id = "physics-3", title = "الطاقة والشغل", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("قوانين نيوتن"),
                ),
                LearningStep(
                    id = "physics-4", title = "الحركة الدائرية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 12, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("الطاقة والشغل"),
                ),
                LearningStep(
                    id = "physics-5", title = "العزم", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 10, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("الحركة الدائرية"),
                ),
                LearningStep(
                    id = "physics-6", title = "اختبار القوى", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    isMilestone = true, lockedReason = LockedReason.RequiresStepCount(5),
                ),
                LearningStep(
                    id = "physics-7", title = "الطاقة الحركية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 16, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("اختبار القوى"),
                ),
                LearningStep(
                    id = "physics-8", title = "حفظ الطاقة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("الطاقة الحركية"),
                ),
                LearningStep(
                    id = "physics-9", title = "النبض وكمية الحركة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 20, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("حفظ الطاقة"),
                ),
                LearningStep(
                    id = "physics-10", title = "التصادمات", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("النبض وكمية الحركة"),
                ),
                LearningStep(
                    id = "physics-11", title = "مراجعة الطاقة والحركة", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 22, mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Audio),
                    lockedReason = LockedReason.RequiresStep("التصادمات"),
                ),
                LearningStep(
                    id = "physics-12", title = "اختبار شامل", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    isMilestone = true, lockedReason = LockedReason.RequiresStepCount(11),
                ),
                LearningStep(
                    id = "physics-13", title = "الحركة التوافقية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 16, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = LockedReason.RequiresStep("اختبار شامل"),
                ),
                LearningStep(
                    id = "physics-14", title = "الموجات الصوتية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 14, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = LockedReason.RequiresStep("الحركة التوافقية"),
                ),
                LearningStep(
                    id = "physics-15", title = "مراجعة ختامية", subtitle = null,
                    status = LessonStatus.LockedSequential, isCurrent = false, isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Pdf, LessonMediaType.Audio),
                    lockedReason = LockedReason.RequiresStep("الموجات الصوتية"),
                ),
            )
        val withCompletion = raw.map { step ->
            step.copy(isCompleted = step.isCompleted || step.id in extraCompleted)
        }
        val unlocked = withCompletion.mapIndexed { index, step ->
            val previousDone = index == 0 || withCompletion[index - 1].isCompleted
            when {
                step.isCompleted -> step.copy(
                    status = LessonStatus.Processed,
                    isCurrent = false,
                    lockedReason = null,
                    minutesLeft = null,
                )
                previousDone -> step.copy(
                    status = LessonStatus.Processed,
                    isCurrent = false,
                    lockedReason = null,
                )
                else -> step.copy(isCurrent = false)
            }
        }
        val currentId = unlocked.firstOrNull { !it.isCompleted && it.status == LessonStatus.Processed }?.id
        val steps = unlocked.map { it.copy(isCurrent = it.id == currentId) }
        val done = steps.count { it.isCompleted }
        return LearningPath(
            id = "physics",
            title = "الفيزياء",
            subtitle = "الوحدة الأولى — الحركة",
            progress = done.toFloat() / PHYSICS_TOTAL_LESSON_COUNT,
            teacherName = "الأستاذة لينا حداد",
            quizCount = 1,
            lastUpdatedLabel = "آخر تحديث أمس",
            completedLessonCount = done,
            totalLessonCount = PHYSICS_TOTAL_LESSON_COUNT,
            steps = steps,
        )
    }

    /** ST-02's "not published yet" state — a course with a teacher but no steps at all. */
    private suspend fun unpublishedChemistryCourse(): LearningPath {
        delay(MockLatency.FAST_MS)
        return LearningPath(
            id = "chemistry",
            title = "الكيمياء",
            subtitle = "الوحدة الأولى",
            progress = 0f,
            teacherName = "الأستاذة هدى العلي",
            isPublished = false,
            steps = emptyList(),
        )
    }

    /**
     * ST-02's whole-course locked/entitlement state (CourseDetailLocked.dc.html). Published
     * (a real, browsable course), just not paid for — [LearningPath.isEntitled] false. Reuses
     * the exact same "biology" id [MockPaymentRepository.OFFERS] already prices, so the
     * Subscribe CTA's [com.rork.eduspark.ui.navigation.Routes.studentPaywallRoute] hand-off
     * resolves to a real, matching [com.rork.eduspark.data.model.CourseOffer] — one course
     * identity, not two.
     */
    private suspend fun lockedBiologyCourse(): LearningPath {
        delay(MockLatency.LIST_MS)
        val isActivated = entitlements.isActivated("biology")
        return LearningPath(
            id = "biology",
            title = "الأحياء",
            subtitle = "الوحدة الأولى — الخلية ووظائفها",
            progress = if (isActivated) 0.08f else 0f,
            teacherName = "الدكتورة ديمة نصور",
            quizCount = 2,
            isEntitled = isActivated,
            completedLessonCount = if (isActivated) 1 else 0,
            totalLessonCount = 12,
            steps = listOf(
                LearningStep(
                    id = "biology-1", title = "مقدّمة في الخلية", subtitle = null,
                    status = if (isActivated) LessonStatus.Processed else LessonStatus.LockedByEntitlement,
                    isCurrent = isActivated,
                    isCompleted = false,
                    durationMinutes = 18, mediaTypes = setOf(LessonMediaType.Video),
                    lockedReason = if (isActivated) null else LockedReason.RequiresEntitlement,
                ),
                LearningStep(
                    id = "biology-2", title = "الأغشية الخلوية", subtitle = null,
                    status = if (isActivated) LessonStatus.LockedSequential else LessonStatus.LockedByEntitlement,
                    isCurrent = false, isCompleted = false,
                    durationMinutes = 16, mediaTypes = setOf(LessonMediaType.Pdf),
                    lockedReason = if (isActivated) LockedReason.RequiresStep("مقدّمة في الخلية") else LockedReason.RequiresEntitlement,
                ),
            ),
        )
    }

    private companion object {
        /** "math"'s fixed baseline (math-1, math-2 already done) — see [mathCompletedLessonCount]. */
        const val MATH_BASE_COMPLETED_COUNT = 2
        const val MATH_TOTAL_LESSON_COUNT = 16
        const val PHYSICS_TOTAL_LESSON_COUNT = 15
    }
}

/**
 * SO-03 fixtures. Deterministic — every subject id resolves to the same two or three
 * teachers every time, so screens and screenshots stay stable across runs.
 */
class MockOnboardingRepository : OnboardingRepository {

    override suspend fun getTeachers(subjectId: String): AppResult<List<OnboardingTeacher>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(TeacherFixtures[subjectId].orEmpty())
    }

    private object TeacherFixtures {
        private fun teacher(
            id: String,
            subjectId: String,
            name: String,
            years: Int,
            rating: Float,
            students: Int,
            price: String,
            clipSeconds: Int = 20,
        ) = OnboardingTeacher(id, subjectId, name, years, rating, students, price, clipSeconds)

        private val bySubject: Map<String, List<OnboardingTeacher>> = mapOf(
            "math" to listOf(
                teacher("t-math-1", "math", "سامر الخطيب", 12, 4.8f, 312, "3$"),
                teacher("t-math-2", "math", "رنا يوسف", 7, 4.6f, 148, "2$"),
            ),
            "physics" to listOf(
                teacher("t-physics-1", "physics", "لينا حداد", 9, 4.9f, 204, "مجاناً"),
                teacher("t-physics-2", "physics", "فادي عيسى", 15, 4.7f, 421, "4$"),
            ),
            "chemistry" to listOf(
                teacher("t-chem-1", "chemistry", "هدى العلي", 10, 4.7f, 176, "3$"),
                teacher("t-chem-2", "chemistry", "ماهر سلوم", 6, 4.5f, 92, "2$"),
            ),
            "biology" to listOf(
                teacher("t-bio-1", "biology", "ديمة نصور", 8, 4.8f, 133, "3$"),
                teacher("t-bio-2", "biology", "وائل حمدان", 11, 4.6f, 201, "مجاناً"),
            ),
            "arabic" to listOf(
                teacher("t-arabic-1", "arabic", "منى الشريف", 14, 4.9f, 288, "2$"),
                teacher("t-arabic-2", "arabic", "زياد قاسم", 9, 4.6f, 119, "2$"),
            ),
            "english" to listOf(
                teacher("t-english-1", "english", "مازن العلي", 10, 4.7f, 254, "3$"),
                teacher("t-english-2", "english", "سارة نعمة", 6, 4.8f, 167, "مجاناً"),
            ),
            "french" to listOf(
                teacher("t-french-1", "french", "كريم فرحات", 7, 4.5f, 88, "3$"),
            ),
            "informatics" to listOf(
                teacher("t-info-1", "informatics", "علي درويش", 5, 4.7f, 143, "2$"),
                teacher("t-info-2", "informatics", "رهف قدور", 8, 4.9f, 210, "4$"),
            ),
            "philosophy" to listOf(
                teacher("t-philo-1", "philosophy", "نبيل صبري", 13, 4.6f, 97, "2$"),
            ),
        )

        operator fun get(subjectId: String) = bySubject[subjectId]
    }
}

/**
 * A-12 fixtures. The code selects the outcome so the not-found branch can be walked by hand
 * without a backend: a blank code or one starting with "invalid" reports not-found; a code in
 * [REGISTRY] resolves to its own specific record — PJ-11's project certificate is registered
 * here rather than a parallel verification path — and every other non-blank code preserves the
 * original single fixture below, so existing QA that types any arbitrary code still verifies.
 */
class MockCertificateRepository : CertificateRepository {

    override suspend fun verify(code: String): AppResult<CertificateVerification> {
        delay(MockLatency.FAST_MS)
        if (code.isBlank() || code.startsWith("invalid", ignoreCase = true)) {
            return AppResult.Failure(AppError.NotFound)
        }
        return AppResult.Success(REGISTRY[code] ?: DEFAULT_LANGUAGE_CERTIFICATE)
    }

    private companion object {
        val DEFAULT_LANGUAGE_CERTIFICATE = CertificateVerification(
            isValid = true,
            holderName = "ريم الحلبي",
            certificateTitle = "شهادة إتمام الوحدة الثالثة",
            levelOrProjectName = "الرياضيات — المشتقات وتطبيقاتها",
            issueDate = "2026-05-12",
            issuingTeacher = "الأستاذ سامر الخطيب",
        )

        /**
         * PJ-11. Keyed by the same code [MockProjectRepository]'s `CERTIFICATE_CODES` hands out
         * for a completed project — [issuingTeacher] names the platform, not a person, since a
         * project is graded by the deterministic MOCK rubric system (PJ-06), never a human
         * teacher. [holderName] matches [MockProfileRepository]'s own seeded student verbatim.
         */
        val REGISTRY: Map<String, CertificateVerification> = mapOf(
            "EDU-PROJ-GC01" to CertificateVerification(
                isValid = true,
                holderName = "ريم الحلبي",
                certificateTitle = "شهادة إتمام مشروع",
                levelOrProjectName = "حاسبة المعدل الدراسي",
                issueDate = "2026-08-20",
                issuingTeacher = "منصّة EduMind",
                skills = listOf("المنطق البرمجي الأساسي", "التعامل مع المتغيرات والعمليات الحسابية", "تصميم واجهة بسيطة"),
            ),
        )
    }
}

/**
 * ST-04 / ST-05 fixtures. Deterministic, lesson-grounded replies — no LLM, no RAG, no
 * streaming. The student's message is keyword-matched so every reply variant is reachable
 * by hand: "مثال" → a worked example, "أبسط"/"بسيط" → a simpler restating, "تجديد" →
 * a rephrased default, anything else → the Socratic default hint. All four are grounded in
 * "المشتقة الثانية" (the second derivative) — the same math-3 lesson ST-02 and ST-03 already
 * use — so the tutor's answers read as if they actually came from that lesson.
 */
class MockTutorRepository : TutorRepository {

    override suspend fun sendMessage(lessonId: String, message: String): AppResult<TutorReply> {
        delay(MockLatency.TUTOR_MS)
        return AppResult.Success(TutorReply(text = replyFor(message)))
    }

    private fun replyFor(message: String): String = when {
        message.contains("مثال") -> EXAMPLE_REPLY
        message.contains("أبسط") || message.contains("بسيط") -> SIMPLER_REPLY
        message.contains("تجديد") -> REGENERATE_REPLY
        else -> DEFAULT_REPLY
    }

    private companion object {
        const val DEFAULT_REPLY =
            "لن أعطيك الجواب مباشرة — لنبدأ خطوة بخطوة: ما هي مشتقة الدالة الأصلية f'(x) في هذا التمرين؟ " +
                "اكتبها أولاً، ثم نشتقها مرة ثانية معاً لنصل إلى f''(x)."
        const val SIMPLER_REPLY =
            "بعبارة أبسط: المشتقة الثانية هي ببساطة مشتقة المشتقة. احسب f'(x) أولاً، ثم اشتق الناتج " +
                "مرة أخرى لتحصل على f''(x)."
        const val EXAMPLE_REPLY =
            "مثال: إذا كانت f(x) = x³، فإن f'(x) = 3x²، وباشتقاقها مرة أخرى نحصل على f''(x) = 6x. " +
                "جرّب الآن مع الدالة الموجودة في درسك."
        const val REGENERATE_REPLY =
            "بصيغة أخرى: فكّر أولاً بمشتقة الدالة الأصلية، ثم اشتقها مرة ثانية. ما ناتج اشتقاق f'(x) عندك؟"
    }
}

/**
 * ST-06 / ST-07 / ST-08 / ST-09 fixtures.
 *
 * Two quizzes, both grounded in the same "math" course / "المشتقة الثانية" lesson thread
 * ST-02→ST-05 already established: [QUIZ_MATH_3] is the AI lesson quiz (immediate feedback,
 * a 5-minute timer, all four question types), [QUIZ_MANUAL_MATH] is the teacher's course
 * review (deferred feedback, no timer) — between them every fixture combination the runtime
 * QA pass needs is reachable: timer present/absent, immediate/deferred, and — because
 * scoring is exact-string matching, not fuzzy — a tester reaches "wrong answer" on any
 * question just by not typing/selecting the value in each question's own explanation, and
 * "correct answer" by typing/selecting exactly that value.
 *
 * Attempts, results and any built remedial quiz all live in-memory on this instance — the
 * whole point of "bail out and resume" and "Practice these again" is that nothing here talks
 * to a repository *layer* deeper than a [MutableMap], because no such backend call exists.
 */
class MockQuizRepository : QuizRepository {

    private val quizzes: MutableMap<String, Quiz> = mutableMapOf(
        QUIZ_MATH_3.id to QUIZ_MATH_3,
        QUIZ_MANUAL_MATH.id to QUIZ_MANUAL_MATH,
        QUIZ_MANUAL_PHYSICS.id to QUIZ_MANUAL_PHYSICS,
    )
    private val attempts = mutableMapOf<String, QuizAttempt>()
    private val results = mutableMapOf<String, QuizResult>()

    override suspend fun getQuiz(quizId: String): AppResult<Quiz> {
        delay(MockLatency.FAST_MS)
        val quiz = quizzes[quizId] ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(quiz)
    }

    override fun getAttempt(quizId: String): QuizAttempt =
        attempts.getOrPut(quizId) { QuizAttempt(quizId = quizId) }

    override fun saveAnswer(quizId: String, answer: QuizAnswer): QuizAttempt {
        val updated = getAttempt(quizId).let { it.copy(answers = it.answers + (answer.questionId to answer)) }
        attempts[quizId] = updated
        return updated
    }

    override fun goToQuestion(quizId: String, index: Int): QuizAttempt {
        val updated = getAttempt(quizId).copy(currentQuestionIndex = index)
        attempts[quizId] = updated
        return updated
    }

    override fun resetAttempt(quizId: String): QuizAttempt {
        val fresh = QuizAttempt(quizId = quizId)
        attempts[quizId] = fresh
        results.remove(quizId)
        return fresh
    }

    override suspend fun submitQuiz(quizId: String): AppResult<QuizResult> {
        delay(MockLatency.FAST_MS)
        val quiz = quizzes[quizId] ?: return AppResult.Failure(AppError.NotFound)
        val attempt = getAttempt(quizId).copy(isCompleted = true)
        attempts[quizId] = attempt
        val scored = score(quiz, attempt)
        results[quizId] = scored
        return AppResult.Success(scored)
    }

    override suspend fun getResult(quizId: String): AppResult<QuizResult> {
        delay(MockLatency.FAST_MS)
        return results[quizId]?.let { AppResult.Success(it) } ?: AppResult.Failure(AppError.NotFound)
    }

    override suspend fun buildRemedialQuiz(sourceQuizId: String): AppResult<Quiz> {
        delay(MockLatency.FAST_MS)
        val source = quizzes[sourceQuizId] ?: return AppResult.Failure(AppError.NotFound)
        val attempt = attempts[sourceQuizId]?.takeIf { it.isCompleted } ?: return AppResult.Failure(AppError.NotFound)
        val wrongQuestions = source.questions.filter { q -> !attempt.answers[q.id]?.response.matchesQuizAnswer(q.correctAnswer) }
        if (wrongQuestions.isEmpty()) return AppResult.Failure(AppError.Domain("no_wrong_answers"))

        val remedialId = "remedial-$sourceQuizId"
        val remedial = source.copy(
            id = remedialId,
            title = source.title,
            feedbackMode = FeedbackMode.Immediate,
            timerSeconds = null,
            questions = wrongQuestions,
            isRemedial = true,
        )
        quizzes[remedialId] = remedial
        attempts.remove(remedialId)
        results.remove(remedialId)
        return AppResult.Success(remedial)
    }

    private fun score(quiz: Quiz, attempt: QuizAttempt): QuizResult {
        val correctCount = quiz.questions.count { q -> attempt.answers[q.id]?.response.matchesQuizAnswer(q.correctAnswer) }
        val wrongCount = quiz.questions.size - correctCount
        return QuizResult(
            quiz = quiz,
            attempt = attempt,
            correctCount = correctCount,
            totalCount = quiz.questions.size,
            xpEarned = correctCount * QUIZ_XP_PER_CORRECT,
            // No real stopwatch exists yet — a deterministic, realistic-enough mock estimate
            // (average pace per question, wrong answers assumed to take longer) for ST-07's
            // approved "time taken" stat.
            timeTakenSeconds = quiz.questions.size * SECONDS_PER_QUESTION + wrongCount * EXTRA_SECONDS_PER_WRONG_ANSWER,
        )
    }

    private companion object {
        const val SECONDS_PER_QUESTION = 40
        const val EXTRA_SECONDS_PER_WRONG_ANSWER = 20
        val QUIZ_MATH_3 = Quiz(
            id = "quiz-math-3",
            origin = QuizOrigin.AiLesson,
            lessonId = "math-3",
            lessonTitle = "المشتقة الثانية",
            title = "اختبار: المشتقة الثانية",
            teacherName = "الأستاذ سامر الخطيب",
            feedbackMode = FeedbackMode.Immediate,
            timerSeconds = 300,
            questions = listOf(
                QuizQuestion(
                    id = "q1", type = QuestionType.MultipleChoice,
                    prompt = "ما هي مشتقة الدالة f(x) = x²؟",
                    options = listOf(
                        QuizOption("a", "2x"), QuizOption("b", "x"),
                        QuizOption("c", "x²"), QuizOption("d", "2"),
                    ),
                    correctAnswer = "a",
                    explanation = "مشتقة xⁿ هي n·x^(n-1)، وبالتالي مشتقة x² هي 2x.",
                    hint = "تذكّر: مشتقة xⁿ هي n·x^(n−1).",
                ),
                QuizQuestion(
                    id = "q2", type = QuestionType.TrueFalse,
                    prompt = "المشتقة الثانية هي مشتقة المشتقة الأولى للدالة.",
                    options = listOf(QuizOption("true", "صح"), QuizOption("false", "خطأ")),
                    correctAnswer = "true",
                    explanation = "بالضبط — f''(x) هي مشتقة f'(x).",
                    hint = "فكّر في تعريف \"الثانية\" حرفياً — مشتقة الشيء الذي اشتققته للتو.",
                ),
                QuizQuestion(
                    id = "q3", type = QuestionType.GapFill,
                    prompt = "إذا كانت f'(x) = 3x²، فإن f''(x) = ___",
                    correctAnswer = "6x",
                    explanation = "نشتق 3x² مرة أخرى: (3x²)‎' = 6x.",
                    hint = "اشتق 3x² بنفس القاعدة التي استخدمتها في السؤال الأول.",
                ),
                QuizQuestion(
                    id = "q4", type = QuestionType.ShortAnswer,
                    prompt = "أوجد f''(x) عندما تكون f(x) = x⁴.",
                    correctAnswer = "12x^2",
                    explanation = "f'(x) = 4x³، ثم f''(x) = 12x².",
                    hint = "ابدأ باشتقاق x⁴ مرة واحدة، ثم اشتق الناتج مرة أخرى.",
                ),
            ),
        )

        val QUIZ_MANUAL_MATH = Quiz(
            id = "manual-math",
            origin = QuizOrigin.TeacherManual,
            lessonId = "math-3",
            lessonTitle = "المشتقة الثانية",
            title = "اختبار الوحدة الثالثة — الرياضيات",
            teacherName = "الأستاذ سامر الخطيب",
            feedbackMode = FeedbackMode.Deferred,
            timerSeconds = null,
            questions = listOf(
                QuizQuestion(
                    id = "m1", type = QuestionType.MultipleChoice,
                    prompt = "ما موضوع الوحدة الثالثة في الرياضيات؟",
                    options = listOf(
                        QuizOption("a", "المشتقات وتطبيقاتها"), QuizOption("b", "التكامل"),
                        QuizOption("c", "الهندسة الفراغية"), QuizOption("d", "الإحصاء"),
                    ),
                    correctAnswer = "a",
                    explanation = "الوحدة الثالثة مخصصة للمشتقات وتطبيقاتها، كما وضّح الأستاذ سامر في الدروس.",
                ),
                QuizQuestion(
                    id = "m2", type = QuestionType.TrueFalse,
                    prompt = "قاعدة السلسلة تُستخدم لاشتقاق دالة داخل دالة أخرى.",
                    options = listOf(QuizOption("true", "صح"), QuizOption("false", "خطأ")),
                    correctAnswer = "true",
                    explanation = "صحيح — قاعدة السلسلة هي أداة اشتقاق الدوال المركّبة.",
                ),
                QuizQuestion(
                    id = "m3", type = QuestionType.GapFill,
                    prompt = "مشتقة الثابت تساوي ___",
                    correctAnswer = "0",
                    explanation = "مشتقة أي ثابت تساوي صفراً لأن معدل تغيره صفر.",
                ),
                QuizQuestion(
                    id = "m4", type = QuestionType.ShortAnswer,
                    prompt = "اذكر خطوة واحدة تُستخدم لإيجاد نقاط الانعطاف لدالة.",
                    correctAnswer = "نساوي المشتقة الثانية بالصفر",
                    explanation = "نساوي المشتقة الثانية بالصفر ونحل المعادلة لإيجاد نقاط الانعطاف المحتملة.",
                ),
            ),
        )

        /** Short — just enough that ST-02's physics quiz-count row has somewhere real to go. */
        val QUIZ_MANUAL_PHYSICS = Quiz(
            id = "manual-physics",
            origin = QuizOrigin.TeacherManual,
            lessonId = "physics-2",
            lessonTitle = "قوانين نيوتن",
            title = "اختبار الوحدة الثانية — الفيزياء",
            teacherName = "الأستاذة لينا حداد",
            feedbackMode = FeedbackMode.Deferred,
            timerSeconds = null,
            questions = listOf(
                QuizQuestion(
                    id = "p1", type = QuestionType.MultipleChoice,
                    prompt = "أي قانون ينص على أن القوة تساوي الكتلة مضروبة في التسارع؟",
                    options = listOf(
                        QuizOption("a", "قانون نيوتن الأول"), QuizOption("b", "قانون نيوتن الثاني"),
                        QuizOption("c", "قانون نيوتن الثالث"), QuizOption("d", "قانون الجاذبية"),
                    ),
                    correctAnswer = "b",
                    explanation = "قانون نيوتن الثاني: F = m·a.",
                ),
                QuizQuestion(
                    id = "p2", type = QuestionType.TrueFalse,
                    prompt = "الجسم الساكن يبقى ساكناً ما لم تؤثر عليه قوة خارجية.",
                    options = listOf(QuizOption("true", "صح"), QuizOption("false", "خطأ")),
                    correctAnswer = "true",
                    explanation = "هذا نص قانون نيوتن الأول — قانون القصور الذاتي.",
                ),
            ),
        )
    }
}

/**
 * ST-10 / ST-11 fixtures. [weekPlan] is the single in-memory source of truth both screens
 * read — see [PlannerRepository]'s own doc comment for why a hot flow rather than a plain
 * getter. Today is deterministically Thursday: everything Sunday…Wednesday reads as history
 * (completed/missed), Thursday onward as upcoming — so the empty state (Friday), a missed
 * session (Tuesday chemistry) and a prioritised session (Thursday math) are all reachable
 * without any date math this codebase has nowhere else needed (no java.time desugaring).
 */
class MockPlannerRepository : PlannerRepository {

    private val _weekPlan = MutableStateFlow<WeekPlan?>(null)
    override val weekPlan: Flow<WeekPlan?> = _weekPlan.asStateFlow()
    private val _recommendations = MutableStateFlow(initialRecommendations())
    override val recommendations: Flow<List<PlannerRecommendation>> = _recommendations.asStateFlow()

    private val pendingProposals = mutableMapOf<String, PlannerChangeProposal>()
    private var proposalCounter = 0
    private var messageCounter = 0

    override suspend fun loadWeekPlan(): AppResult<WeekPlan> {
        delay(MockLatency.LIST_MS)
        val plan = _weekPlan.value ?: initialWeekPlan()
        _weekPlan.value = plan
        return AppResult.Success(plan)
    }

    override suspend fun regenerateWeek(): AppResult<WeekPlan> {
        delay(MockLatency.LIST_MS)
        val regenerated = regeneratedWeekPlan()
        _weekPlan.value = regenerated
        _recommendations.value = listOf(
            PlannerRecommendation("rec-regen-1", "نقلت الكيمياء إلى الجمعة لتخفيف ضغط الخميس.", PlannerPriority.High, "الخميس فيه رياضيات مع سبب أولوية واختبار قريب."),
            PlannerRecommendation("rec-regen-2", "أضفت مراجعة فيزياء قصيرة يوم السبت.", PlannerPriority.Medium, "جلسات نهاية الأسبوع تساعد على تثبيت الفصل السادس."),
            PlannerRecommendation("rec-regen-3", "اترك ليلة الجمعة أخف إذا كان عندك نشاط عائلي.", PlannerPriority.Low, "الروتين يعطيك مساحة راحة قبل بداية أسبوع جديد."),
        )
        pendingProposals.clear()
        return AppResult.Success(regenerated)
    }

    override suspend fun toggleSessionCompletion(sessionId: String): AppResult<WeekPlan> {
        delay(MockLatency.FAST_MS)
        val current = _weekPlan.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(
            sessions = current.sessions.map { session ->
                if (session.id != sessionId) {
                    session
                } else {
                    session.copy(status = if (session.status == SessionStatus.Completed) SessionStatus.Upcoming else SessionStatus.Completed)
                }
            },
        )
        _weekPlan.value = updated
        return AppResult.Success(updated)
    }

    /** A shorter wait than the tutor's — Source Audit: planner chat is regex + template
     *  replies, not a real generation call, so it should feel quick, not "thinking". */
    override suspend fun sendPlannerChatMessage(message: String): AppResult<PlannerChatMessage> {
        delay(MockLatency.LIST_MS)
        val plan = _weekPlan.value ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(replyTo(message, plan))
    }

    override suspend fun acceptProposal(proposalId: String): AppResult<WeekPlan> {
        delay(MockLatency.FAST_MS)
        val proposal = pendingProposals[proposalId] ?: return AppResult.Failure(AppError.NotFound)
        val current = _weekPlan.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(
            sessions = current.sessions.map { session ->
                if (session.id == proposal.sessionId) {
                    session.copy(day = proposal.newDay, startTime = proposal.newStartTime)
                } else {
                    session
                }
            },
        )
        _weekPlan.value = updated
        _recommendations.value = _recommendations.value.map {
            if (it.id == "rec-1") it.copy(text = "تم تحديث الخطة، راقب جلسة ${proposal.subjectTitle} في يومها الجديد.", reason = proposal.reason) else it
        }
        pendingProposals.remove(proposalId)
        return AppResult.Success(updated)
    }

    override suspend fun rejectProposal(proposalId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        pendingProposals.remove(proposalId)
        return AppResult.Success(Unit)
    }

    override suspend fun applyRecommendation(recommendationId: String): AppResult<WeekPlan> {
        delay(MockLatency.FAST_MS)
        val current = _weekPlan.value ?: return AppResult.Failure(AppError.NotFound)
        val rec = _recommendations.value.firstOrNull { it.id == recommendationId }
            ?: return AppResult.Failure(AppError.NotFound)
        val updated = when {
            rec.text.contains("الكيمياء") -> current.copy(
                sessions = current.sessions.map { session ->
                    if (session.id == "p-thu-chem") session.copy(day = Weekday.Friday, startTime = "17:00") else session
                },
            )
            rec.text.contains("الفيزياء") -> current.copy(
                sessions = current.sessions.map { session ->
                    if (session.subjectId == "physics" && session.status == SessionStatus.Upcoming) {
                        session.copy(startTime = "19:00")
                    } else {
                        session
                    }
                },
            )
            else -> current
        }
        _weekPlan.value = updated
        _recommendations.value = _recommendations.value.filter { it.id != recommendationId }
        return AppResult.Success(updated)
    }

    override suspend fun dismissRecommendation(recommendationId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _recommendations.value = _recommendations.value.filter { it.id != recommendationId }
        return AppResult.Success(Unit)
    }

    /** Deterministic keyword parsing + template replies — the same shape as the real "regex + template" pipeline, not a fake LLM call. */
    private fun replyTo(message: String, plan: WeekPlan): PlannerChatMessage {
        val subjectId = SubjectKeywords.entries.firstOrNull { (keyword, _) -> message.contains(keyword) }?.second
        val mentionedDay = DayKeywords.entries.firstOrNull { (keyword, _) -> message.contains(keyword) }?.second
        val isWhyQuestion = message.contains("لماذا") || message.contains("ليش")

        if (isWhyQuestion && subjectId != null) {
            val session = plan.sessions.firstOrNull { it.subjectId == subjectId }
            val reply = session?.priorityReason
                ?: "لا يوجد سبب خاص مسجَّل لهذه الحصة — إنها جزء من التوزيع العام للأسبوع."
            return assistantMessage(reply)
        }

        if (subjectId != null) {
            val session = plan.sessions.firstOrNull { it.status == SessionStatus.Upcoming && it.subjectId == subjectId }
                ?: return assistantMessage("لا توجد حصة قادمة لهذه المادة هذا الأسبوع لأقترح نقلها.")

            val avoidDay = mentionedDay ?: session.day
            val newDay = nextDay(avoidDay)
            proposalCounter += 1
            val proposal = PlannerChangeProposal(
                id = "proposal-$proposalCounter",
                sessionId = session.id,
                subjectTitle = session.subjectTitle,
                oldDay = session.day,
                oldStartTime = session.startTime,
                newDay = newDay,
                newStartTime = session.startTime,
                reason = "بناءً على طلبك، حصة ${session.subjectTitle} تنتقل بعيداً عن هذا اليوم دون أن تغيّر وقتها.",
            )
            pendingProposals[proposal.id] = proposal
            return assistantMessage(text = "فهمت — إليك اقتراحاً لنقل حصة ${session.subjectTitle}:", proposal = proposal)
        }

        return assistantMessage("لم أفهم طلبك بالكامل. جرّب ذكر اسم المادة واليوم، مثل: «انقل حصة الكيمياء عن يوم الثلاثاء».")
    }

    private fun assistantMessage(text: String, proposal: PlannerChangeProposal? = null): PlannerChatMessage {
        messageCounter += 1
        return PlannerChatMessage(id = "planner-msg-$messageCounter", sender = PlannerChatSender.Assistant, text = text, proposedChange = proposal)
    }

    private fun nextDay(day: Weekday): Weekday {
        val values = Weekday.entries
        return values[(day.ordinal + 1) % values.size]
    }

    private object SubjectKeywords {
        val entries = listOf("رياضيات" to "math", "فيزياء" to "physics", "كيمياء" to "chemistry")
    }

    private object DayKeywords {
        val entries = listOf(
            "الأحد" to Weekday.Sunday,
            "الاثنين" to Weekday.Monday,
            "الإثنين" to Weekday.Monday,
            "الثلاثاء" to Weekday.Tuesday,
            "الأربعاء" to Weekday.Wednesday,
            "الاربعاء" to Weekday.Wednesday,
            "الخميس" to Weekday.Thursday,
            "الجمعة" to Weekday.Friday,
            "السبت" to Weekday.Saturday,
        )
    }

    private fun initialWeekPlan() = WeekPlan(
        weekLabel = "هذا الأسبوع",
        today = Weekday.Thursday,
        generatedAtLabel = "آخر تحديث: اليوم",
        sessions = listOf(
            PlannerSession(
                id = "p-sun-math", day = Weekday.Sunday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "مراجعة قواعد الاشتقاق", startTime = "17:00", durationMinutes = 15, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-mon-physics", day = Weekday.Monday, subjectId = "physics", subjectTitle = "الفيزياء",
                title = "تمارين على قوانين نيوتن", startTime = "19:00", durationMinutes = 20, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-tue-chem", day = Weekday.Tuesday, subjectId = "chemistry", subjectTitle = "الكيمياء",
                title = "مراجعة المعادلات الكيميائية", startTime = "17:30", durationMinutes = 20, status = SessionStatus.Missed,
            ),
            PlannerSession(
                id = "p-wed-physics", day = Weekday.Wednesday, subjectId = "physics", subjectTitle = "الفيزياء",
                title = "حل تمارين الفصل السادس", startTime = "18:00", durationMinutes = 20, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-thu-math", day = Weekday.Thursday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "حل مسائل على المشتقة الثانية", startTime = "17:00", durationMinutes = 25, status = SessionStatus.Upcoming,
                priorityReason = "تحضيراً لاختبار الوحدة الثالثة القادم",
            ),
            PlannerSession(
                id = "p-thu-chem", day = Weekday.Thursday, subjectId = "chemistry", subjectTitle = "الكيمياء",
                title = "مراجعة سريعة قبل التجربة العملية", startTime = "19:30", durationMinutes = 15, status = SessionStatus.Upcoming,
            ),
            // Friday intentionally empty — ST-10's empty-day state.
            PlannerSession(
                id = "p-sat-math", day = Weekday.Saturday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "مراجعة عامة قبل الأسبوع القادم", startTime = "16:30", durationMinutes = 30, status = SessionStatus.Upcoming,
                priorityReason = "لتثبيت مفاهيم الأسبوع قبل البدء بأسبوع جديد",
            ),
        ),
    )

    /** A visibly different arrangement so "Regenerate my week" has something real to show. */
    private fun regeneratedWeekPlan() = WeekPlan(
        weekLabel = "هذا الأسبوع",
        today = Weekday.Thursday,
        generatedAtLabel = "آخر تحديث: الآن",
        sessions = listOf(
            PlannerSession(
                id = "p-sun-math", day = Weekday.Sunday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "مراجعة قواعد الاشتقاق", startTime = "17:00", durationMinutes = 15, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-mon-physics", day = Weekday.Monday, subjectId = "physics", subjectTitle = "الفيزياء",
                title = "تمارين على قوانين نيوتن", startTime = "19:00", durationMinutes = 20, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-tue-chem", day = Weekday.Tuesday, subjectId = "chemistry", subjectTitle = "الكيمياء",
                title = "مراجعة المعادلات الكيميائية", startTime = "17:30", durationMinutes = 20, status = SessionStatus.Missed,
            ),
            PlannerSession(
                id = "p-wed-physics", day = Weekday.Wednesday, subjectId = "physics", subjectTitle = "الفيزياء",
                title = "حل تمارين الفصل السادس", startTime = "18:00", durationMinutes = 20, status = SessionStatus.Completed,
            ),
            PlannerSession(
                id = "p-thu-math", day = Weekday.Thursday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "حل مسائل على المشتقة الثانية", startTime = "17:30", durationMinutes = 25, status = SessionStatus.Upcoming,
                priorityReason = "أُعيد ترتيبها لتكون بعد وقت الراحة مباشرة",
            ),
            PlannerSession(
                id = "p-fri-chem", day = Weekday.Friday, subjectId = "chemistry", subjectTitle = "الكيمياء",
                title = "مراجعة سريعة قبل التجربة العملية", startTime = "17:00", durationMinutes = 15, status = SessionStatus.Upcoming,
                priorityReason = "نُقلت من الخميس لتوزيع الحمل الدراسي بشكل أفضل",
            ),
            PlannerSession(
                id = "p-sat-math", day = Weekday.Saturday, subjectId = "math", subjectTitle = "الرياضيات",
                title = "مراجعة عامة قبل الأسبوع القادم", startTime = "16:30", durationMinutes = 30, status = SessionStatus.Upcoming,
            ),
            PlannerSession(
                id = "p-sat-physics", day = Weekday.Saturday, subjectId = "physics", subjectTitle = "الفيزياء",
                title = "مراجعة تراكمية للفصل السادس", startTime = "17:15", durationMinutes = 20, status = SessionStatus.Upcoming,
                priorityReason = "إضافة لتعويض حصة الكيمياء الفائتة",
            ),
        ),
    )

    private fun initialRecommendations() = listOf(
        PlannerRecommendation("rec-1", "ابدأ بالرياضيات اليوم لأنها مرتبطة باختبار قريب.", PlannerPriority.High, "الخطة تضع الجلسة بعد المدرسة والراحة القصيرة حتى لا تصطدم بالروتين."),
        PlannerRecommendation("rec-2", "عوّض الكيمياء الفائتة بجلسة قصيرة قبل التجربة العملية.", PlannerPriority.Medium, "المادة ظهرت كأضعف مسار في الأسبوع الحالي."),
        PlannerRecommendation("rec-3", "حافظ على يوم الجمعة خفيفًا إذا لم تضف امتحانًا جديدًا.", PlannerPriority.Low, "الراحة جزء من ثبات الخطة وليس فراغًا بلا معنى."),
    )
}

/**
 * ST-12 / ST-13 fixtures. [buildRoutine] is a deterministic function of the six builder
 * answers — the same "rule-based, not AI" shape the real "smart planner generate" already
 * uses (Source Audit §6) — so confirming the same answers twice always produces the same
 * week. Today is Thursday, matching [MockPlannerRepository]'s own fixture, so the two
 * screens read as one consistent persona rather than two different "todays". Saturday is
 * deliberately left with zero slots — ST-13's empty-day state needs one reachable regardless
 * of which commitments/study windows the student picked.
 */
class MockRoutineRepository : RoutineRepository {

    private val _routineProfile = MutableStateFlow<RoutineProfile?>(null)
    override val routineProfile: Flow<RoutineProfile?> = _routineProfile.asStateFlow()
    private val _routineDraft = MutableStateFlow<RoutineDraft?>(null)
    override val routineDraft: Flow<RoutineDraft?> = _routineDraft.asStateFlow()

    override suspend fun loadRoutine(): AppResult<RoutineProfile> {
        delay(MockLatency.LIST_MS)
        val profile = _routineProfile.value ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(profile)
    }

    override suspend fun confirmRoutine(answers: RoutineBuilderAnswers): AppResult<RoutineProfile> {
        delay(MockLatency.LIST_MS)
        val profile = buildRoutine(answers)
        _routineProfile.value = profile
        return AppResult.Success(profile)
    }

    override suspend fun startRoutineAiBuild(answers: RoutineBuilderAnswers): AppResult<RoutineDraft> {
        delay(MockLatency.LIST_MS)
        val profile = buildRoutine(answers)
        val firstDay = Weekday.entries.first()
        val draft = RoutineDraft(
            answers = answers,
            messages = listOf(
                RoutineBuildMessage("routine-ai-1", PlannerChatSender.Assistant, "جاهز أبني أسبوعك يوم بيوم. سأبدأ من الأحد وأراعي الدوام، النوم، والالتزامات."),
                RoutineBuildMessage("routine-ai-2", PlannerChatSender.Assistant, "الأحد جاهز: وضعت المدرسة أولًا، ثم نافذة دراسة بعد الراحة."),
            ),
            dayDrafts = Weekday.entries.map { day ->
                RoutineDayDraft(
                    day = day,
                    slots = profile.slots.filter { it.day == day }.sortedBy { it.startTime },
                    confirmed = false,
                    reasoning = routineDayReason(day),
                )
            },
            currentDay = firstDay,
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun confirmRoutineDraftDay(day: Weekday): AppResult<RoutineDraft> {
        delay(MockLatency.FAST_MS)
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val updatedDays = current.dayDrafts.map { if (it.day == day) it.copy(confirmed = true) else it }
        val nextDay = updatedDays.firstOrNull { !it.confirmed }?.day ?: day
        val draft = current.copy(
            dayDrafts = updatedDays,
            currentDay = nextDay,
            messages = current.messages + RoutineBuildMessage(
                "routine-ai-${current.messages.size + 1}",
                PlannerChatSender.Assistant,
                if (updatedDays.all { it.confirmed }) "كل الأيام جاهزة. راجع الاقتراحات قبل تثبيت الأسبوع." else "تم تثبيت ${day.arabicLabel()} مؤقتًا. أراجع الآن ${nextDay.arabicLabel()}.",
            ),
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun adjustRoutineDraft(message: String): AppResult<RoutineDraft> {
        delay(MockLatency.FAST_MS)
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val day = current.currentDay
        val adjustedDays = current.dayDrafts.map { draft ->
            if (draft.day != day) draft else draft.copy(
                slots = draft.slots.map { slot ->
                    if (slot.type == RoutineSlotType.StudyWindow) slot.copy(startTime = "18:30", endTime = "19:30") else slot
                },
                reasoning = "عدّلت نافذة الدراسة بناءً على رسالتك: $message",
            )
        }
        val draft = current.copy(
            dayDrafts = adjustedDays,
            messages = current.messages +
                RoutineBuildMessage("routine-user-${current.messages.size + 1}", PlannerChatSender.Student, message) +
                RoutineBuildMessage("routine-ai-${current.messages.size + 2}", PlannerChatSender.Assistant, "عدّلت اليوم الحالي وخففت ضغط الدراسة بعد المدرسة."),
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun reviewRoutineDraft(): AppResult<RoutineDraft> {
        delay(MockLatency.LIST_MS)
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val draft = current.copy(
            reviewText = "راجعت الأسبوع كاملًا. أهم شيء هو حماية النوم وتخفيف الأيام التي فيها درس خصوصي أو اختبار.",
            suggestions = listOf(
                com.rork.eduspark.data.model.RoutineSuggestion("rs-1", "خفف يوم الدرس الخصوصي", "انقل نافذة الدراسة الثقيلة إلى اليوم التالي.", PlannerPriority.High),
                com.rork.eduspark.data.model.RoutineSuggestion("rs-2", "ثبّت مراجعة صباحية قصيرة", "قبل المدرسة أفضل للمراجعة الخفيفة وليس لحل مسائل طويلة.", PlannerPriority.Medium),
                com.rork.eduspark.data.model.RoutineSuggestion("rs-3", "اترك مساء الجمعة حرًا", "هذا يحافظ على الاستمرارية بدل إرهاق نهاية الأسبوع.", PlannerPriority.Low),
            ),
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun setRoutineSuggestion(suggestionId: String, accepted: Boolean?): AppResult<RoutineDraft> {
        delay(MockLatency.FAST_MS)
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val draft = current.copy(
            suggestions = current.suggestions.map { if (it.id == suggestionId) it.copy(accepted = accepted) else it },
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun finalizeRoutineDraft(): AppResult<RoutineProfile> {
        delay(MockLatency.LIST_MS)
        val draft = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val accepted = draft.suggestions.filter { it.accepted == true }.map { it.id }.toSet()
        val slots = draft.dayDrafts.flatMap { it.slots }.map { slot ->
            if ("rs-1" in accepted && slot.type == RoutineSlotType.StudyWindow && slot.day == Weekday.Monday) {
                slot.copy(day = Weekday.Tuesday, startTime = "18:30", endTime = "19:30")
            } else {
                slot
            }
        }
        val profile = RoutineProfile(
            weekLabel = "هذا الأسبوع",
            today = Weekday.Thursday,
            slots = slots,
            lastConfirmedLabel = "تم بناء الروتين بمساعدة الذكاء الاصطناعي",
            needsRenewal = true,
        )
        _routineProfile.value = profile
        return AppResult.Success(profile)
    }

    override suspend fun updateSlotStatus(slotId: String, status: RoutineSlotStatus): AppResult<RoutineProfile> {
        delay(MockLatency.FAST_MS)
        val current = _routineProfile.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(
            slots = current.slots.map { slot -> if (slot.id == slotId) slot.copy(status = status) else slot },
        )
        _routineProfile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun acknowledgeRenewal(): AppResult<RoutineProfile> {
        delay(MockLatency.FAST_MS)
        val current = _routineProfile.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(needsRenewal = false)
        _routineProfile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun renewRoutineWeek(): AppResult<RoutineProfile> {
        delay(MockLatency.LIST_MS)
        val current = _routineProfile.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(
            weekLabel = "الأسبوع الجديد",
            lastConfirmedLabel = "تم تجديد الروتين لهذا الأسبوع",
            needsRenewal = false,
            slots = current.slots.map { it.copy(status = RoutineSlotStatus.Upcoming) },
        )
        _routineProfile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun deleteRoutine(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _routineProfile.value = null
        _routineDraft.value = null
        return AppResult.Success(Unit)
    }

    private fun routineDayReason(day: Weekday): String = when (day) {
        Weekday.Sunday, Weekday.Monday, Weekday.Tuesday, Weekday.Wednesday, Weekday.Thursday -> "تم وضع الدراسة بعد الدوام والراحة لأن المدرسة ثابتة صباحًا."
        Weekday.Friday -> "اليوم أخف، لذلك أبقيت الالتزامات فقط إن وجدت."
        Weekday.Saturday -> "يوم مفتوح للتجديد أو الراحة حسب طاقتك."
    }

    private fun Weekday.arabicLabel(): String = when (this) {
        Weekday.Sunday -> "الأحد"
        Weekday.Monday -> "الاثنين"
        Weekday.Tuesday -> "الثلاثاء"
        Weekday.Wednesday -> "الأربعاء"
        Weekday.Thursday -> "الخميس"
        Weekday.Friday -> "الجمعة"
        Weekday.Saturday -> "السبت"
    }

    private fun buildRoutine(answers: RoutineBuilderAnswers): RoutineProfile {
        val schoolDays = listOf(Weekday.Sunday, Weekday.Monday, Weekday.Tuesday, Weekday.Wednesday, Weekday.Thursday)
        val pastDays = setOf(Weekday.Sunday, Weekday.Monday, Weekday.Tuesday, Weekday.Wednesday)
        val schoolHours = SCHOOL_HOURS[answers.schoolHoursId] ?: SCHOOL_HOURS.getValue("standard")
        val wake = answers.wakeTime ?: "6:30"
        val sleep = answers.sleepTime ?: "22:00"

        val slots = mutableListOf<RoutineSlot>()

        // Friday and Saturday intentionally skip wake/sleep/school — Saturday ends up with
        // zero slots at all (ST-13's empty-day state); Friday only carries a commitment if
        // one was deterministically assigned to it.
        (schoolDays + Weekday.Friday).forEach { day ->
            val statusFor = { pastStatus: RoutineSlotStatus -> if (day in pastDays) pastStatus else RoutineSlotStatus.Upcoming }
            slots += RoutineSlot(
                id = "wake-${day.name}", day = day, type = RoutineSlotType.Wake,
                title = "الاستيقاظ", startTime = wake, status = statusFor(RoutineSlotStatus.Completed),
            )
            if (day in schoolDays) {
                slots += RoutineSlot(
                    id = "school-${day.name}", day = day, type = RoutineSlotType.School,
                    title = "الدوام المدرسي", startTime = schoolHours.first, endTime = schoolHours.second,
                    status = statusFor(RoutineSlotStatus.Completed),
                )
            }
            slots += RoutineSlot(
                id = "sleep-${day.name}", day = day, type = RoutineSlotType.Sleep,
                title = "النوم", startTime = sleep, status = statusFor(RoutineSlotStatus.Completed),
            )
        }

        answers.commitmentIds.forEach { commitmentId ->
            val commitment = COMMITMENTS[commitmentId] ?: return@forEach
            // Approved design's nested schedule card (RoutineBuilder.dc.html) — the student's
            // own days/time when supplied, falling back to this commitment's default schedule
            // otherwise. A partial custom answer (e.g. days chosen but no time yet) still
            // falls back per-field, never leaving a slot with a blank time.
            val customSchedule = answers.commitmentSchedules[commitmentId]
            val days = customSchedule?.days?.takeIf { it.isNotEmpty() } ?: commitment.days.toSet()
            val start = customSchedule?.startTime ?: commitment.start
            val end = customSchedule?.endTime ?: commitment.end
            days.forEach { day ->
                val isMissed = day == Weekday.Monday && commitmentId == "tutoring" // one deterministic missed slot for QA.
                slots += RoutineSlot(
                    id = "commitment-$commitmentId-${day.name}", day = day, type = RoutineSlotType.Commitment,
                    title = commitment.title, startTime = start, endTime = end,
                    status = when {
                        day !in pastDays -> RoutineSlotStatus.Upcoming
                        isMissed -> RoutineSlotStatus.Missed
                        else -> RoutineSlotStatus.Completed
                    },
                )
            }
        }

        answers.studyWindowIds.forEach { windowId ->
            val window = STUDY_WINDOWS[windowId] ?: return@forEach
            schoolDays.forEach { day ->
                slots += RoutineSlot(
                    id = "study-$windowId-${day.name}", day = day, type = RoutineSlotType.StudyWindow,
                    title = window.title, startTime = window.start, endTime = window.end,
                    status = if (day in pastDays) RoutineSlotStatus.Completed else RoutineSlotStatus.Upcoming,
                )
            }
        }

        return RoutineProfile(
            weekLabel = "هذا الأسبوع",
            today = Weekday.Thursday,
            slots = slots,
            lastConfirmedLabel = "تم تأكيد الروتين هذا الأسبوع",
            needsRenewal = true,
        )
    }

    private data class Commitment(val title: String, val days: List<Weekday>, val start: String, val end: String)
    private data class StudyWindow(val title: String, val start: String, val end: String)

    private companion object {
        val SCHOOL_HOURS: Map<String, Pair<String, String>> = mapOf(
            "early" to ("8:00" to "14:00"),
            "standard" to ("8:00" to "15:00"),
            "late" to ("9:00" to "15:30"),
        )

        val COMMITMENTS: Map<String, Commitment> = mapOf(
            "sports" to Commitment("تدريب رياضي", listOf(Weekday.Tuesday, Weekday.Thursday), "16:00", "17:30"),
            "tutoring" to Commitment("دروس خصوصية", listOf(Weekday.Monday), "17:00", "18:00"),
            "club" to Commitment("نادٍ مدرسي", listOf(Weekday.Wednesday), "15:30", "16:30"),
            "volunteer" to Commitment("نشاط تطوعي", listOf(Weekday.Friday), "10:00", "12:00"),
        )

        val STUDY_WINDOWS: Map<String, StudyWindow> = mapOf(
            "early_morning" to StudyWindow("مراجعة صباحية قبل المدرسة", "6:45", "7:15"),
            "after_school" to StudyWindow("وقت دراسة بعد المدرسة", "15:30", "17:00"),
            "evening" to StudyWindow("وقت دراسة مسائي", "19:00", "20:30"),
            "late_night" to StudyWindow("وقت دراسة ليلي", "21:30", "22:30"),
        )
    }
}

/**
 * ST-14 fixtures. [captureSchedule] simulates the whole capture→OCR round trip in one call —
 * a real pipeline would separate "upload" from "processing", but there is no image to upload
 * here, so a single deterministic delay stands in for both. The three confidence tiers are
 * reachable every time: math and physics come back clean, chemistry needs a date correction,
 * and the fourth row is unrecognised entirely.
 */
class MockExamRepository : ExamRepository {

    private val _examSchedule = MutableStateFlow<ExamSchedule?>(null)
    override val examSchedule: Flow<ExamSchedule?> = _examSchedule.asStateFlow()

    override suspend fun captureSchedule(): AppResult<ExamSchedule> {
        delay(MockLatency.TUTOR_MS)
        val schedule = ExamSchedule(entries = extractedEntries(), isConfirmed = false)
        return AppResult.Success(schedule)
    }

    override suspend fun confirmSchedule(entries: List<ExamEntry>): AppResult<ExamSchedule> {
        delay(MockLatency.FAST_MS)
        val schedule = ExamSchedule(entries = entries, isConfirmed = true)
        _examSchedule.value = schedule
        return AppResult.Success(schedule)
    }

    private fun extractedEntries(): List<ExamEntry> = listOf(
        ExamEntry(
            id = "exam-math", subjectId = "math", subjectTitle = "الرياضيات",
            date = SimpleDate(2026, 9, 14), time = "09:00", confidence = OcrConfidence.High,
        ),
        ExamEntry(
            id = "exam-physics", subjectId = "physics", subjectTitle = "الفيزياء",
            date = SimpleDate(2026, 9, 16), time = "09:00", confidence = OcrConfidence.High,
        ),
        ExamEntry(
            id = "exam-chemistry", subjectId = "chemistry", subjectTitle = "الكيمياء",
            date = SimpleDate(2026, 9, 18), time = null, confidence = OcrConfidence.Medium,
        ),
        ExamEntry(
            id = "exam-unclear", subjectId = null, subjectTitle = "؟؟؟",
            date = null, time = null, confidence = OcrConfidence.Low,
        ),
    )
}

/**
 * ST-15 fixtures. Four earned, four locked, covering every example category the Screen
 * Inventory names. No leaderboard, coins, gems or social ranking — none of those exist in
 * the product definition, so none are modelled or faked here. "Course progress" ties back to
 * the exact math-course completion (62%) [MockLearningRepository] already reports, so the
 * two screens read as the same story rather than two disconnected numbers.
 */
class MockAchievementRepository : AchievementRepository {

    override suspend fun getAchievements(): AppResult<List<Achievement>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(FIXTURES)
    }

    private companion object {
        val FIXTURES = listOf(
            Achievement(
                id = "streak-7", kind = AchievementKind.Streak,
                title = "أسبوع من الانضباط", description = "ادرس لمدة 7 أيام متتالية.",
                status = AchievementStatus.Earned, earnedDateLabel = "قبل يومين",
            ),
            Achievement(
                id = "streak-14", kind = AchievementKind.Streak,
                title = "أسبوعان متتاليان", description = "ادرس لمدة 14 يوماً متتالياً بلا انقطاع.",
                status = AchievementStatus.Locked, progress = AchievementProgress(7, 14),
            ),
            Achievement(
                id = "lesson-first", kind = AchievementKind.LessonCompletion,
                title = "الدرس الأول", description = "أكمل أول درس في EduMind.",
                status = AchievementStatus.Earned, earnedDateLabel = "منذ 3 أسابيع",
            ),
            Achievement(
                id = "lesson-10", kind = AchievementKind.LessonCompletion,
                title = "عشرة دروس", description = "أكمل 10 دروس في أي مادة.",
                status = AchievementStatus.Locked, progress = AchievementProgress(6, 10),
            ),
            Achievement(
                id = "quiz-perfect", kind = AchievementKind.QuizPerformance,
                title = "علامة كاملة", description = "أنهِ اختباراً بإجابات صحيحة كاملة.",
                status = AchievementStatus.Locked, progress = AchievementProgress(0, 1),
            ),
            Achievement(
                id = "consistency-5", kind = AchievementKind.StudyConsistency,
                title = "أسبوع دراسة متوازن", description = "ادرس في 5 أيام مختلفة خلال أسبوع واحد.",
                status = AchievementStatus.Locked, progress = AchievementProgress(3, 5),
            ),
            Achievement(
                id = "course-half", kind = AchievementKind.CourseProgress,
                title = "نصف الطريق", description = "أكمل 50% من أي مقرر دراسي.",
                status = AchievementStatus.Earned, earnedDateLabel = "منذ أسبوع",
            ),
            Achievement(
                id = "course-complete", kind = AchievementKind.CourseProgress,
                title = "إتمام المقرر", description = "أكمل 100% من أي مقرر دراسي.",
                status = AchievementStatus.Locked, progress = AchievementProgress(62, 100),
            ),
        )
    }
}

/**
 * ST-16 fixtures. One of each [SubscriptionStatus] so every required state is reachable by
 * hand, plus one course the student hasn't subscribed to yet. Course ids and teacher names
 * match [MockLearningRepository]'s own fixtures — the same three courses, the same persona.
 */
class MockSubscriptionRepository(
    private val entitlements: MockStudentEntitlements,
) : SubscriptionRepository {

    override suspend fun getSubscriptions(): AppResult<List<CourseSubscription>> {
        delay(MockLatency.LIST_MS)
        val activatedBiology = entitlements.isActivated("biology")
        return AppResult.Success(
            buildList {
                add(
                    CourseSubscription(
                        courseId = "math", courseTitle = "الرياضيات", teacherName = "الأستاذ سامر الخطيب",
                        status = SubscriptionStatus.Active, expiryDateLabel = "1 كانون الأول 2026", daysUntilExpiry = 90,
                        includedFeatures = STANDARD_FEATURES,
                    ),
                )
                add(
                    CourseSubscription(
                        courseId = "physics", courseTitle = "الفيزياء", teacherName = "الأستاذة لينا حداد",
                        status = SubscriptionStatus.ExpiringSoon, expiryDateLabel = "5 أيلول 2026", daysUntilExpiry = 5,
                        includedFeatures = STANDARD_FEATURES,
                    ),
                )
                add(
                    CourseSubscription(
                        courseId = "chemistry", courseTitle = "الكيمياء", teacherName = "الأستاذة هدى العلي",
                        status = SubscriptionStatus.Expired, expiryDateLabel = "20 آب 2026", daysUntilExpiry = null,
                        includedFeatures = STANDARD_FEATURES,
                    ),
                )
                if (activatedBiology) {
                    add(
                        CourseSubscription(
                            courseId = "biology",
                            courseTitle = "الأحياء",
                            teacherName = "الدكتورة ديمة نصور",
                            status = SubscriptionStatus.Active,
                            expiryDateLabel = "4 كانون الأول 2026",
                            daysUntilExpiry = 91,
                            includedFeatures = STANDARD_FEATURES,
                        ),
                    )
                }
            }
        )
    }

    override suspend fun getAvailableCourses(): AppResult<List<AvailableCourse>> {
        delay(MockLatency.FAST_MS)
        if (entitlements.isActivated("biology")) return AppResult.Success(emptyList())
        return AppResult.Success(
            listOf(
                AvailableCourse(
                    courseId = "biology",
                    courseTitle = "الأحياء",
                    teacherName = "الدكتورة ديمة نصور",
                    priceLabel = "45000 ل.س",
                    price = Money(45000, "SYP"),
                    benefits = listOf("وصول كامل للمادة", "اختبارات وتغذية راجعة", "معلم ذكي ضمن الدروس"),
                    includedFeatures = STANDARD_FEATURES,
                ),
            )
        )
    }

    private companion object {
        val STANDARD_FEATURES = listOf("دروس", "اختبارات", "معلّم ذكي", "تقدم")
    }
}

/**
 * ST-17/ST-18/ST-19 fixtures. Offers exist only for courses ST-16 can actually route here from:
 * "physics"/"chemistry" (renewal — [SubscriptionCard][com.rork.eduspark.ui.screens.student.SubscriptionCard]
 * shows Renew for anything other than Active) and "biology" (new subscribe, the one
 * [MockSubscriptionRepository] available course). "math" has no offer on purpose — it's Active,
 * so ST-17 shows "already subscribed" for it rather than a price. [submitPayment] always
 * succeeds deterministically, same convention as every other mock slice; the Failed path is
 * fully implemented in [PaymentPendingViewModel][com.rork.eduspark.ui.screens.student.PaymentPendingViewModel]
 * but not reachable from these fixtures.
 */
class MockPaymentRepository(
    private val entitlements: MockStudentEntitlements,
) : PaymentRepository {

    private val _pendingPayment = MutableStateFlow<PendingPayment?>(null)
    override val pendingPayment: Flow<PendingPayment?> = _pendingPayment.asStateFlow()

    private val _verifiedUnactivatedPayment = MutableStateFlow<PendingPayment?>(SEEDED_VERIFIED_PAYMENT)
    override val verifiedUnactivatedPayment: Flow<PendingPayment?> = _verifiedUnactivatedPayment.asStateFlow()

    override suspend fun getCourseOffer(courseId: String): AppResult<CourseOffer> {
        delay(MockLatency.FAST_MS)
        val offer = OFFERS[courseId] ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(offer)
    }

    override suspend fun getPaymentMethods(): AppResult<List<PaymentMethod>> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(METHODS)
    }

    override suspend fun submitPayment(request: PaymentRequest): AppResult<PendingPayment> {
        _pendingPayment.value?.let { existing ->
            if (existing.courseId == request.courseId) return AppResult.Success(existing)
        }
        delay(MockLatency.LIST_MS)
        val pending = PendingPayment(
            referenceId = "PMT-${request.courseId.uppercase()}-0417",
            courseId = request.courseId,
            courseTitle = request.courseTitle,
            amount = request.amount,
            methodName = request.methodName,
            status = PaymentStatus.Pending,
            submittedAtLabel = "اليوم",
            teacherName = OFFERS[request.courseId]?.teacherName,
        )
        _pendingPayment.value = pending
        return AppResult.Success(pending)
    }

    override suspend fun getPurchaseAccess(courseId: String): AppResult<PurchaseAccess?> {
        delay(MockLatency.FAST_MS)
        val isActivated = entitlements.isActivated(courseId)
        val payment = when {
            // Not yet activated — the live seeded record itself carries it.
            _verifiedUnactivatedPayment.value?.courseId == courseId -> _verifiedUnactivatedPayment.value
            // Already activated — activateAccess() already cleared the seeded record above, so
            // re-derive the same Verified payment from the fixture for idempotent re-entry.
            isActivated && SEEDED_VERIFIED_PAYMENT.courseId == courseId -> SEEDED_VERIFIED_PAYMENT
            // Otherwise fall back to a live ST-17–19 payment for this course, if any (Pending).
            else -> _pendingPayment.value?.takeIf { it.courseId == courseId }
        } ?: return AppResult.Success(null)
        return AppResult.Success(PurchaseAccess(payment = payment, isActivated = isActivated))
    }

    override suspend fun activateAccess(courseId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (entitlements.isActivated(courseId)) return AppResult.Success(Unit)
        entitlements.activate(courseId)
        if (_verifiedUnactivatedPayment.value?.courseId == courseId) {
            _verifiedUnactivatedPayment.value = null
        }
        return AppResult.Success(Unit)
    }

    private companion object {
        const val SEEDED_VERIFIED_COURSE_ID = "biology"
        val SEEDED_VERIFIED_PAYMENT = PendingPayment(
            referenceId = "PMT-BIOLOGY-0102",
            courseId = SEEDED_VERIFIED_COURSE_ID,
            courseTitle = "الأحياء",
            amount = Money(45000, "SYP"),
            methodName = "تحويل عبر محفظة إلكترونية",
            status = PaymentStatus.Verified,
            submittedAtLabel = "أمس",
            teacherName = "الدكتورة ديمة نصور",
        )

        val OFFERS = mapOf(
            "physics" to CourseOffer(
                courseId = "physics", courseTitle = "الفيزياء", teacherName = "الأستاذة لينا حداد",
                accessSummary = "جدد اشتراكك لتفادي انقطاع الوصول إلى دروس الفيزياء واختباراتها ومتابعة تقدمك فيها.",
                accessPeriodLabel = "3 أشهر", price = Money(2), isRenewal = true,
            ),
            "chemistry" to CourseOffer(
                courseId = "chemistry", courseTitle = "الكيمياء", teacherName = "الأستاذة هدى العلي",
                accessSummary = "جدد اشتراكك لمتابعة دروس الكيمياء واختباراتها دون انقطاع.",
                accessPeriodLabel = "3 أشهر", price = Money(4), isRenewal = true,
            ),
            // Batch 1c: SYP confirmed as the product's real currency (approved design +
            // Test-2SY's formatSyrianPrice()/currency:'SYP' both agree) — updated for this
            // specific approved test case (Money is fully currency-code-driven, see
            // [com.rork.eduspark.core.format.formatMoney]; physics/chemistry above are left in
            // USD since their consumer, ST-16 Subscriptions, is outside this batch's scope).
            "biology" to CourseOffer(
                courseId = "biology", courseTitle = "الأحياء", teacherName = "الدكتورة ديمة نصور",
                accessSummary = "اشترك للوصول الكامل إلى دروس مادة الأحياء واختباراتها ومساعدة المعلم الذكي فيها.",
                accessPeriodLabel = "3 أشهر", price = Money(45000, "SYP"), isRenewal = false,
            ),
        )
        // Four direct-payment methods (Test-2SY confirmed: card/transfer/wallet/cash, matching
        // the approved design's 2×2 icon grid exactly) — no card/Stripe/PayPal/Google Play
        // gateway; "card" is a direct/manual method here too, same as the other three.
        val METHODS = listOf(
            PaymentMethod(
                id = "card",
                name = "بطاقة",
                instruction = "أدخل بيانات البطاقة عند التأكيد لإتمام الدفع.",
            ),
            PaymentMethod(
                id = "transfer",
                name = "حوالة",
                instruction = "حوّل المبلغ عبر شركة حوالات وأدخل رقم الحوالة عند التأكيد.",
            ),
            PaymentMethod(
                id = "wallet",
                name = "محفظة",
                instruction = "حوّل المبلغ إلى محفظة EduMind وأدخل رقم عملية التحويل عند التأكيد.",
            ),
            PaymentMethod(
                id = "cash",
                name = "نقداً",
                instruction = "ادفع نقداً في أقرب مكتب EduMind واحتفظ بإيصالك للمراجعة.",
            ),
        )
    }
}

/**
 * ST-21 fixtures. Codes are matched case/whitespace-insensitively (trim + uppercase) — the
 * doc calls for a scratch-card code to be "forgiving of case and spacing." [redeemedCodes]
 * is this repository's own session-local ledger — completely independent of
 * [MockPaymentRepository]'s activation tracking, matching [VoucherRepository]'s own doc
 * comment about being its own entitlement rail. "biology" is reused as the granted course —
 * the same catalog id ST-16/17 already use for the subscribe demo — so a voucher and a paid
 * subscription can be seen granting access to the same real course.
 */
class MockVoucherRepository : VoucherRepository {

    private val redeemedCodes = MutableStateFlow<Set<String>>(emptySet())

    override suspend fun validateVoucher(code: String): AppResult<VoucherValidationResult> {
        delay(MockLatency.FAST_MS)
        val normalized = normalize(code)
        if (normalized in redeemedCodes.value) {
            val fixture = FIXTURES[normalized]
            return AppResult.Success(
                VoucherValidationResult(
                    status = VoucherStatus.Valid,
                    courseId = fixture?.courseId,
                    courseTitle = fixture?.courseTitle,
                    accessPeriodLabel = fixture?.accessPeriodLabel,
                )
            )
        }
        val fixture = FIXTURES[normalized]
        return AppResult.Success(
            when {
                fixture == null -> VoucherValidationResult(status = VoucherStatus.Invalid)
                fixture.status != VoucherStatus.Valid -> VoucherValidationResult(status = fixture.status)
                else -> VoucherValidationResult(
                    status = VoucherStatus.Valid,
                    courseId = fixture.courseId,
                    courseTitle = fixture.courseTitle,
                    accessPeriodLabel = fixture.accessPeriodLabel,
                )
            }
        )
    }

    override suspend fun redeemVoucher(code: String): AppResult<RedeemedVoucher> {
        val normalized = normalize(code)
        val fixture = FIXTURES[normalized] ?: return AppResult.Failure(AppError.NotFound)

        if (normalized in redeemedCodes.value) {
            return AppResult.Success(
                RedeemedVoucher(normalized, fixture.courseId!!, fixture.courseTitle!!, fixture.accessPeriodLabel!!)
            )
        }
        if (fixture.status != VoucherStatus.Valid) {
            return AppResult.Failure(AppError.Validation(mapOf("code" to fixture.status.name)))
        }

        val courseId = fixture.courseId
        val courseTitle = fixture.courseTitle
        val accessPeriodLabel = fixture.accessPeriodLabel
        if (courseId == null || courseTitle == null || accessPeriodLabel == null) {
            // A Valid fixture is expected to always carry a grant, but the type doesn't
            // enforce that — fail safely rather than construct a RedeemedVoucher with a
            // fabricated course.
            return AppResult.Failure(AppError.Unknown)
        }

        delay(MockLatency.LIST_MS)
        redeemedCodes.value = redeemedCodes.value + normalized
        return AppResult.Success(RedeemedVoucher(normalized, courseId, courseTitle, accessPeriodLabel))
    }

    private fun normalize(code: String) = code.trim().uppercase()

    private data class VoucherFixture(
        val status: VoucherStatus,
        val courseId: String? = null,
        val courseTitle: String? = null,
        val accessPeriodLabel: String? = null,
    )

    private companion object {
        val FIXTURES = mapOf(
            "EDU-VALID-001" to VoucherFixture(
                status = VoucherStatus.Valid, courseId = "biology", courseTitle = "الأحياء", accessPeriodLabel = "3 أشهر",
            ),
            "EDU-EXPIRED-01" to VoucherFixture(status = VoucherStatus.Expired),
            "EDU-USED-001" to VoucherFixture(status = VoucherStatus.AlreadyUsed),
        )
    }
}

/**
 * ST-22/ST-23 fixtures. Seeded from the exact same persona [MockLearningRepository.getStudentHome]
 * already uses ("ريم الحلبي", [Grade.Baccalaureate]) so the two screens agree at first load;
 * an edit here only ever updates this repository's own copy — see [ProfileRepository]'s own
 * doc comment for why ST-01 is never retroactively touched. One linked parent is seeded so
 * both "linked" and, after revoking, "no linked parents" are reachable by hand.
 */
class MockProfileRepository : ProfileRepository {

    private val _profile = MutableStateFlow(
        StudentProfile(
            displayName = "ريم الحلبي",
            grade = Grade.Baccalaureate,
            school = "مدرسة الفارابي الثانوية",
            avatarInitial = "ر",
            parentLinkCode = "REEM-7429",
        )
    )
    override val profile: Flow<StudentProfile> = _profile.asStateFlow()

    private val _linkedParents = MutableStateFlow(
        listOf(LinkedParent(id = "parent-1", name = "محمد الحلبي", relationship = "الأب", email = "m.halabi@example.com"))
    )
    override val linkedParents: Flow<List<LinkedParent>> = _linkedParents.asStateFlow()

    override suspend fun getProfile(): AppResult<StudentProfile> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(_profile.value)
    }

    override suspend fun updateProfile(displayName: String, grade: Grade, school: String): AppResult<StudentProfile> {
        delay(MockLatency.FAST_MS)
        val updated = _profile.value.copy(displayName = displayName, grade = grade, school = school, avatarInitial = displayName.take(1))
        _profile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun getLinkedParents(): AppResult<List<LinkedParent>> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(_linkedParents.value)
    }

    override suspend fun revokeLinkedParent(parentId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _linkedParents.value = _linkedParents.value.filterNot { it.id == parentId }
        return AppResult.Success(Unit)
    }

    private val _learningPreferences = MutableStateFlow(
        LearningPreferences(
            goal = LearningGoal.ImproveGrades,
            explanationLength = ExplanationLength.Balanced,
            interests = setOf(LearningInterest.Football, LearningInterest.Gaming),
        )
    )
    override val learningPreferences: Flow<LearningPreferences> = _learningPreferences.asStateFlow()

    override suspend fun getLearningPreferences(): AppResult<LearningPreferences> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(_learningPreferences.value)
    }

    override suspend fun updateLearningPreferences(preferences: LearningPreferences): AppResult<LearningPreferences> {
        delay(MockLatency.FAST_MS)
        _learningPreferences.value = preferences
        return AppResult.Success(preferences)
    }
}

/**
 * ST-24 fixtures. [confirmEnableTwoFactor] accepts the exact same deterministic code
 * ([MockAuthRepository.VALID_CODE], "123456") every other email-OTP flow in this app does —
 * a separate code would be an arbitrary inconsistency, not a real product difference. Two
 * sessions are seeded — the current device (no revoke offered) and one other — so "content",
 * revoking the one other session, and "no other active sessions" are all reachable by hand.
 */
class MockSecurityRepository : SecurityRepository {

    private val _securitySettings = MutableStateFlow(SecuritySettings(twoFactorEnabled = false))
    override val securitySettings: Flow<SecuritySettings> = _securitySettings.asStateFlow()

    private val _activeSessions = MutableStateFlow(
        listOf(
            ActiveSession(id = "session-current", deviceLabel = "هاتف أندرويد (هذا الجهاز)", isCurrentDevice = true, lastSeenLabel = "نشط الآن"),
            ActiveSession(id = "session-browser", deviceLabel = "متصفح Chrome — ويندوز", isCurrentDevice = false, lastSeenLabel = "قبل يومين"),
        )
    )
    override val activeSessions: Flow<List<ActiveSession>> = _activeSessions.asStateFlow()

    override suspend fun getSecuritySettings(): AppResult<SecuritySettings> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(_securitySettings.value)
    }

    override suspend fun requestEnableTwoFactor(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    override suspend fun confirmEnableTwoFactor(code: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (code != TWO_FACTOR_CODE) return AppResult.Failure(AppError.Domain("invalid_code"))
        _securitySettings.value = _securitySettings.value.copy(twoFactorEnabled = true)
        return AppResult.Success(Unit)
    }

    override suspend fun disableTwoFactor(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _securitySettings.value = _securitySettings.value.copy(twoFactorEnabled = false)
        return AppResult.Success(Unit)
    }

    override suspend fun getActiveSessions(): AppResult<List<ActiveSession>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(_activeSessions.value)
    }

    override suspend fun revokeSession(sessionId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _activeSessions.value = _activeSessions.value.filterNot { it.id == sessionId && !it.isCurrentDevice }
        return AppResult.Success(Unit)
    }

    override suspend fun revokeAllOtherSessions(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _activeSessions.value = _activeSessions.value.filter { it.isCurrentDevice }
        return AppResult.Success(Unit)
    }

    private companion object {
        const val TWO_FACTOR_CODE = "123456"
    }
}

/**
 * PJ-01/PJ-02/PJ-03 fixtures. "water-alarm" is pre-seeded as this student's one active
 * project — physics, physical, solo — with a full completed → current (completed/current/
 * blocked tasks) → locked milestone spread, so every required PJ-03 state is reachable by
 * hand. "grades-calculator" (computing, digital, solo) is startable from Discover.
 * "ecosystem-model" (biology, physical, team) is PJ-08's fixture — pre-seeded as already
 * active (the mock team already exists with the student in it, so there is no "join a new
 * team over a network" flow to fabricate; [startProject] is still never called for it, same
 * as before). Subject ids/titles for physics and biology reuse the exact same course identity
 * ST-01/ST-16/ST-21 already use; "computing" is a project-only subject since no matching
 * course exists in Student Core yet.
 */
class MockProjectRepository : ProjectRepository {

    private val _activeProjects = MutableStateFlow(
        listOf(seedActiveWaterAlarm(), seedActiveEcosystemModel(), seedActiveGradesCalculator())
    )
    override val activeProjects: Flow<List<ActiveProject>> = _activeProjects.asStateFlow()

    private val checkedMaterials = MutableStateFlow<Map<String, Set<String>>>(emptyMap())

    /** Both keyed by taskId — PJ-05 drafts and PJ-06 submissions, session-local, never cleared on navigation. */
    private val drafts = MutableStateFlow<Map<String, SubmissionDraft>>(emptyMap())
    private val submissions = MutableStateFlow<Map<String, ProjectSubmission>>(emptyMap())

    /**
     * How many times [submitTask] has genuinely created a new submission for a task — 1-based,
     * absent means "never submitted". Repository/session state, not view state, so it survives
     * PJ-06 being recreated. Only [submitTask]'s new-submission branch increments this; a
     * retried call that hits its idempotency guard never does (see that method's own doc
     * comment). This is what lets [getReview] hand back a different deterministic fixture after
     * a genuine resubmission — never randomised, never timed.
     */
    private val submissionAttempts = MutableStateFlow<Map<String, Int>>(emptyMap())

    /** PJ-07, keyed by taskId — this slice has exactly one deterministic assignment, so one entry is all either map ever holds. */
    private val peerReviewDrafts = MutableStateFlow<Map<String, PeerReviewDraft>>(emptyMap())
    private val peerReviews = MutableStateFlow<Map<String, PeerReview>>(emptyMap())

    /** PJ-08, both keyed by projectId — session-local only, never a real peer network or real-time sync. */
    private val teamTaskAssignments = MutableStateFlow(mapOf(TEAM_PROJECT_ID to INITIAL_TEAM_ASSIGNMENTS))
    private val teamMessages = MutableStateFlow(mapOf(TEAM_PROJECT_ID to INITIAL_TEAM_MESSAGES))

    /** PJ-09, keyed by "projectId:milestoneId" — repository/session-level so PJ-10 can read it back later. */
    private val reflections = MutableStateFlow(SEEDED_REFLECTIONS)

    override suspend fun getCatalog(): AppResult<List<Project>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(CATALOG)
    }

    override suspend fun getProject(projectId: String): AppResult<Project> {
        delay(MockLatency.FAST_MS)
        val project = CATALOG.firstOrNull { it.id == projectId } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(project)
    }

    override suspend fun getActiveProjects(): AppResult<List<ActiveProject>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(_activeProjects.value)
    }

    override suspend fun startProject(projectId: String): AppResult<ActiveProject> {
        _activeProjects.value.firstOrNull { it.projectId == projectId }?.let { return AppResult.Success(it) }
        val project = CATALOG.firstOrNull { it.id == projectId } ?: return AppResult.Failure(AppError.NotFound)
        delay(MockLatency.FAST_MS)

        // A freshly-started project isn't fully locked-looking — its very first task is
        // already Current, so the student has an immediate "what do I do next" moment.
        val milestones = project.milestones.mapIndexed { milestoneIndex, milestone ->
            if (milestoneIndex != 0) return@mapIndexed milestone
            milestone.copy(
                tasks = milestone.tasks.mapIndexed { taskIndex, task ->
                    if (taskIndex == 0) task.copy(status = ProjectTaskStatus.Current) else task
                }
            )
        }
        val active = ActiveProject(projectId = projectId, milestones = milestones)
        _activeProjects.value = _activeProjects.value + active
        return AppResult.Success(active)
    }

    override suspend fun getCheckedMaterials(projectId: String): AppResult<Set<String>> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(checkedMaterials.value[projectId] ?: emptySet())
    }

    override suspend fun setMaterialChecked(projectId: String, materialId: String, checked: Boolean): AppResult<Unit> {
        val current = checkedMaterials.value[projectId] ?: emptySet()
        val updated = if (checked) current + materialId else current - materialId
        checkedMaterials.value = checkedMaterials.value + (projectId to updated)
        return AppResult.Success(Unit)
    }

    // ── PJ-04 · Task Detail ─────────────────────────────────────────────────
    override suspend fun getTask(projectId: String, taskId: String): AppResult<ProjectTask> {
        delay(MockLatency.FAST_MS)
        val task = findTask(projectId, taskId) ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(task)
    }

    override suspend fun startTaskWork(projectId: String, taskId: String): AppResult<ProjectTask> {
        delay(MockLatency.FAST_MS)
        val updated = updateTask(projectId, taskId) { task ->
            if (task.workflowStatus == TaskWorkflowStatus.NotStarted) task.copy(workflowStatus = TaskWorkflowStatus.InProgress) else task
        } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(updated)
    }

    // ── PJ-05 · Submission Composer ──────────────────────────────────────────
    override suspend fun getDraft(projectId: String, taskId: String): AppResult<SubmissionDraft> {
        delay(MockLatency.FAST_MS)
        drafts.value[taskId]?.let { return AppResult.Success(it) }
        submissions.value[taskId]?.let { submission ->
            return AppResult.Success(
                SubmissionDraft(
                    taskId = taskId,
                    writtenReflection = submission.writtenReflection,
                    link = submission.link,
                    attachments = submission.attachments,
                )
            )
        }
        return AppResult.Success(SubmissionDraft(taskId = taskId))
    }

    override suspend fun saveDraft(draft: SubmissionDraft): AppResult<SubmissionDraft> {
        // Committed *before* the delay, deliberately — PJ-05 auto-saves on back navigation,
        // which can tear this coroutine's scope down mid-call; the write must already be
        // durable by then, not waiting on the other side of a suspension point.
        drafts.value = drafts.value + (draft.taskId to draft)
        if (draft.hasContent) {
            findProjectIdForTask(draft.taskId)?.let { projectId ->
                updateTask(projectId, draft.taskId) { task ->
                    if (task.workflowStatus == TaskWorkflowStatus.InProgress) task.copy(workflowStatus = TaskWorkflowStatus.ReadyToSubmit) else task
                }
            }
        }
        delay(MockLatency.FAST_MS)
        return AppResult.Success(draft)
    }

    override suspend fun submitTask(projectId: String, taskId: String): AppResult<ProjectSubmission> {
        // Idempotency is scoped to the *current* attempt via the canonical workflow status,
        // not "ever submitted" — once beginResubmission() resets it back to InProgress, this
        // guard no longer matches, and a genuinely new submission is created below. A retry
        // that hits this branch (status still Submitted/Reviewed) never reaches the increment
        // further down, so it can never inflate the attempt count.
        val currentStatus = findTask(projectId, taskId)?.workflowStatus
        if (currentStatus == TaskWorkflowStatus.Submitted || currentStatus == TaskWorkflowStatus.Reviewed) {
            submissions.value[taskId]?.let { return AppResult.Success(it) }
        }
        val draft = drafts.value[taskId] ?: SubmissionDraft(taskId = taskId)
        if (!draft.hasContent) return AppResult.Failure(AppError.Validation(mapOf("submission" to "empty")))

        delay(MockLatency.LIST_MS)
        val submission = ProjectSubmission(
            taskId = taskId,
            writtenReflection = draft.writtenReflection,
            link = draft.link,
            attachments = draft.attachments,
            submittedAtLabel = "اليوم",
        )
        submissions.value = submissions.value + (taskId to submission)
        submissionAttempts.value = submissionAttempts.value + (taskId to ((submissionAttempts.value[taskId] ?: 0) + 1))
        updateTask(projectId, taskId) { it.copy(workflowStatus = TaskWorkflowStatus.Submitted) }
        return AppResult.Success(submission)
    }

    override suspend fun getSubmission(taskId: String): AppResult<ProjectSubmission?> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(submissions.value[taskId])
    }

    // ── PJ-06 · AI Review & Rubric ────────────────────────────────────────────
    override suspend fun getReview(projectId: String, taskId: String): AppResult<ProjectReview> {
        delay(MockLatency.LIST_MS)
        val reviews = REVIEWS[taskId] ?: return AppResult.Failure(AppError.NotFound)
        // 1-based attempt number → 0-based fixture index; any attempt beyond the last fixture
        // clamps to the last one, so a task can never run out of a deterministic review to show.
        val attempt = submissionAttempts.value[taskId] ?: 1
        val review = reviews.getOrElse((attempt - 1).coerceIn(0, reviews.lastIndex)) { reviews.last() }
        updateTask(projectId, taskId) { task ->
            val newStatus = if (review.isAcceptable) ProjectTaskStatus.Completed else task.status
            task.copy(workflowStatus = TaskWorkflowStatus.Reviewed, status = newStatus)
        }
        return AppResult.Success(review)
    }

    override suspend fun beginResubmission(projectId: String, taskId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        updateTask(projectId, taskId) { task ->
            if (task.workflowStatus == TaskWorkflowStatus.Reviewed) task.copy(workflowStatus = TaskWorkflowStatus.InProgress) else task
        }
        return AppResult.Success(Unit)
    }

    // ── PJ-07 · Peer Review ────────────────────────────────────────────────────
    override suspend fun getPeerReviewAssignment(): AppResult<PeerSubmissionPreview> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(PEER_REVIEW_ASSIGNMENT)
    }

    override suspend fun getPeerReviewDraft(taskId: String): AppResult<PeerReviewDraft> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(peerReviewDrafts.value[taskId] ?: PeerReviewDraft(taskId = taskId))
    }

    override suspend fun savePeerReviewDraft(draft: PeerReviewDraft): AppResult<PeerReviewDraft> {
        // Same "commit before the delay" rule saveDraft() follows for PJ-05 — a screen leaving
        // mid-call must not lose the draft.
        peerReviewDrafts.value = peerReviewDrafts.value + (draft.taskId to draft)
        delay(MockLatency.FAST_MS)
        return AppResult.Success(draft)
    }

    override suspend fun submitPeerReview(draft: PeerReviewDraft): AppResult<PeerReview> {
        peerReviews.value[draft.taskId]?.let { return AppResult.Success(it) }
        val criteria = PEER_REVIEW_ASSIGNMENT.criteria
        delay(MockLatency.LIST_MS)
        val review = PeerReview(
            taskId = draft.taskId,
            ratings = criteria.map { criterion ->
                RubricResult(
                    criterionId = criterion.id,
                    criterionTitle = criterion.title,
                    score = draft.scores[criterion.id] ?: 0,
                    maxScore = criterion.maxScore,
                    reason = "",
                )
            },
            comment = draft.comment,
            submittedAtLabel = "اليوم",
        )
        peerReviews.value = peerReviews.value + (draft.taskId to review)
        return AppResult.Success(review)
    }

    // ── PJ-08 · Team Workspace ───────────────────────────────────────────────────
    override suspend fun getTeam(projectId: String): AppResult<ProjectTeam> {
        delay(MockLatency.LIST_MS)
        if (projectId != TEAM_PROJECT_ID) return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(
            ProjectTeam(
                projectId = TEAM_PROJECT_ID,
                teamName = TEAM_NAME,
                members = TEAM_MEMBERS,
                taskAssignments = teamTaskAssignments.value[projectId] ?: emptyList(),
                messages = teamMessages.value[projectId] ?: emptyList(),
                deliverable = TEAM_DELIVERABLE,
            )
        )
    }

    override suspend fun assignTaskToSelf(projectId: String, taskId: String): AppResult<TeamTaskAssignment> {
        delay(MockLatency.FAST_MS)
        val self = TEAM_MEMBERS.first { it.isCurrentStudent }
        val updated = TeamTaskAssignment(taskId = taskId, assigneeMemberId = self.id)
        setTeamAssignment(projectId, updated)
        return AppResult.Success(updated)
    }

    override suspend fun unassignOwnTask(projectId: String, taskId: String): AppResult<TeamTaskAssignment> {
        delay(MockLatency.FAST_MS)
        val self = TEAM_MEMBERS.first { it.isCurrentStudent }
        val current = teamTaskAssignments.value[projectId]?.firstOrNull { it.taskId == taskId }
        // Only ever releases the student's own claim — never someone else's assignment.
        if (current?.assigneeMemberId != self.id) {
            return AppResult.Success(current ?: TeamTaskAssignment(taskId = taskId, assigneeMemberId = null))
        }
        val updated = TeamTaskAssignment(taskId = taskId, assigneeMemberId = null)
        setTeamAssignment(projectId, updated)
        return AppResult.Success(updated)
    }

    private fun setTeamAssignment(projectId: String, assignment: TeamTaskAssignment) {
        val current = teamTaskAssignments.value[projectId] ?: emptyList()
        val next = if (current.any { it.taskId == assignment.taskId }) {
            current.map { if (it.taskId == assignment.taskId) assignment else it }
        } else {
            current + assignment
        }
        teamTaskAssignments.value = teamTaskAssignments.value + (projectId to next)
    }

    override suspend fun sendTeamMessage(projectId: String, text: String): AppResult<TeamMessage> {
        delay(MockLatency.FAST_MS)
        val self = TEAM_MEMBERS.first { it.isCurrentStudent }
        val message = TeamMessage(
            id = "msg-${System.currentTimeMillis()}",
            senderMemberId = self.id,
            text = text,
            sentAtLabel = "الآن",
        )
        val current = teamMessages.value[projectId] ?: emptyList()
        teamMessages.value = teamMessages.value + (projectId to (current + message))
        return AppResult.Success(message)
    }

    // ── PJ-09 · Reflection Log ────────────────────────────────────────────────────
    override suspend fun getReflection(projectId: String, milestoneId: String): AppResult<ProjectReflection?> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(reflections.value[reflectionKey(projectId, milestoneId)])
    }

    override suspend fun saveReflection(reflection: ProjectReflection): AppResult<ProjectReflection> {
        delay(MockLatency.FAST_MS)
        reflections.value = reflections.value + (reflectionKey(reflection.projectId, reflection.milestoneId) to reflection)
        return AppResult.Success(reflection)
    }

    // ── PJ-11 · Project Certificate ───────────────────────────────────────────────
    override suspend fun getCertificateCode(projectId: String): AppResult<String?> {
        delay(MockLatency.FAST_MS)
        val active = _activeProjects.value.firstOrNull { it.projectId == projectId }
        if (active == null || !active.isFullyCompleted) return AppResult.Success(null)
        return AppResult.Success(CERTIFICATE_CODES[projectId])
    }

    private fun findProjectIdForTask(taskId: String): String? =
        _activeProjects.value.firstOrNull { active -> active.milestones.any { m -> m.tasks.any { it.id == taskId } } }?.projectId

    /** The one lookup [getTask] and [submitTask]'s attempt-scoped idempotency guard both read from. */
    private fun findTask(projectId: String, taskId: String): ProjectTask? =
        _activeProjects.value.firstOrNull { it.projectId == projectId }
            ?.milestones?.flatMap { it.tasks }?.firstOrNull { it.id == taskId }

    /** The one place a task inside an [ActiveProject] is ever mutated — every PJ-04/05/06 write goes through this, so [activeProjects] (PJ-01/PJ-03's shared state) always reflects it immediately. */
    private fun updateTask(projectId: String, taskId: String, transform: (ProjectTask) -> ProjectTask): ProjectTask? {
        val active = _activeProjects.value.firstOrNull { it.projectId == projectId } ?: return null
        var updatedTask: ProjectTask? = null
        val newMilestones = active.milestones.map { milestone ->
            if (milestone.tasks.none { it.id == taskId }) {
                milestone
            } else {
                milestone.copy(
                    tasks = milestone.tasks.map { task ->
                        if (task.id != taskId) {
                            task
                        } else {
                            transform(task).also { updatedTask = it }
                        }
                    }
                )
            }
        }
        if (updatedTask == null) return null
        _activeProjects.value = _activeProjects.value.map { if (it.projectId == projectId) it.copy(milestones = newMilestones) else it }
        return updatedTask
    }

    private companion object {
        fun seedActiveWaterAlarm(): ActiveProject = ActiveProject(
            projectId = "water-alarm",
            milestones = listOf(
                ProjectMilestone(
                    id = "wa-m1", title = "جمع المواد والتخطيط",
                    tasks = listOf(
                        ProjectTask(id = "wa-m1-t1", title = "قراءة قائمة المواد المطلوبة", status = ProjectTaskStatus.Completed),
                        ProjectTask(id = "wa-m1-t2", title = "تجهيز أدوات العمل", status = ProjectTaskStatus.Completed),
                    ),
                ),
                ProjectMilestone(
                    id = "wa-m2", title = "تركيب الدارة الكهربائية",
                    tasks = listOf(
                        ProjectTask(id = "wa-m2-t1", title = "توصيل حساس المستوى بالمقاومة", status = ProjectTaskStatus.Completed),
                        waM2T2(status = ProjectTaskStatus.Current, workflowStatus = TaskWorkflowStatus.NotStarted),
                        ProjectTask(
                            id = "wa-m2-t3", title = "اختبار الدارة على مصدر الطاقة", status = ProjectTaskStatus.Blocked,
                            blockerLabel = "بانتظار توفر بطارية 9 فولت",
                        ),
                    ),
                ),
                ProjectMilestone(
                    id = "wa-m3", title = "تركيب الجهاز داخل الحاوية",
                    tasks = listOf(
                        ProjectTask(id = "wa-m3-t1", title = "قص فتحة للحساس في الحاوية", status = ProjectTaskStatus.Upcoming),
                        ProjectTask(id = "wa-m3-t2", title = "تثبيت الدارة داخل الحاوية", status = ProjectTaskStatus.Upcoming),
                    ),
                ),
                ProjectMilestone(
                    id = "wa-m4", title = "الاختبار النهائي والعرض",
                    tasks = listOf(
                        ProjectTask(id = "wa-m4-t1", title = "اختبار الجهاز بماء حقيقي", status = ProjectTaskStatus.Upcoming),
                        ProjectTask(id = "wa-m4-t2", title = "تسجيل عرض قصير للجهاز", status = ProjectTaskStatus.Upcoming),
                    ),
                ),
            ),
        )

        /** PJ-08's fixture — pre-seeded active so the team already exists with the student in it; task titles are shared verbatim with the catalog's "ecosystem-model" template above. */
        fun seedActiveEcosystemModel(): ActiveProject = ActiveProject(
            projectId = TEAM_PROJECT_ID,
            milestones = listOf(
                ProjectMilestone(
                    id = "em-m1", title = "تخطيط النظام البيئي",
                    tasks = listOf(
                        ProjectTask(id = "em-m1-t1", title = "اختيار الكائنات الحية المناسبة", status = ProjectTaskStatus.Completed),
                        ProjectTask(id = "em-m1-t2", title = "توزيع المهام على أعضاء الفريق", status = ProjectTaskStatus.Completed),
                    ),
                ),
                ProjectMilestone(
                    id = "em-m2", title = "بناء النموذج",
                    tasks = listOf(
                        ProjectTask(id = "em-m2-t1", title = "تجهيز الوعاء والتربة", status = ProjectTaskStatus.Current),
                        ProjectTask(id = "em-m2-t2", title = "زراعة النباتات وإغلاق الوعاء", status = ProjectTaskStatus.Upcoming),
                    ),
                ),
                ProjectMilestone(
                    id = "em-m3", title = "المراقبة والتسجيل",
                    tasks = listOf(
                        ProjectTask(id = "em-m3-t1", title = "تسجيل ملاحظات يومية لمدة أسبوعين", status = ProjectTaskStatus.Upcoming),
                    ),
                ),
            ),
        )

        /**
         * PJ-10's one deterministic completed fixture — every task Completed, [ActiveProject.completedAtLabel]
         * set. Deliberately "grades-calculator", not the actively-QA'd water-alarm/ecosystem-model
         * instances, so the portfolio is populated without marking either of those falsely done.
         * Task titles are shared verbatim with the catalog's "grades-calculator" template below.
         */
        fun seedActiveGradesCalculator(): ActiveProject = ActiveProject(
            projectId = "grades-calculator",
            completedAtLabel = "2026-08-20",
            milestones = listOf(
                ProjectMilestone(
                    id = "gc-m1", title = "تصميم فكرة التطبيق",
                    tasks = listOf(
                        ProjectTask(id = "gc-m1-t1", title = "تحديد العلامات والأوزان المطلوبة", status = ProjectTaskStatus.Completed),
                        ProjectTask(id = "gc-m1-t2", title = "رسم شاشة التطبيق على ورقة", status = ProjectTaskStatus.Completed),
                    ),
                ),
                ProjectMilestone(
                    id = "gc-m2", title = "برمجة حساب المعدل",
                    tasks = listOf(
                        ProjectTask(id = "gc-m2-t1", title = "برمجة إدخال العلامات", status = ProjectTaskStatus.Completed),
                        ProjectTask(id = "gc-m2-t2", title = "برمجة معادلة حساب المعدل", status = ProjectTaskStatus.Completed),
                    ),
                ),
                ProjectMilestone(
                    id = "gc-m3", title = "الاختبار والمشاركة",
                    tasks = listOf(
                        ProjectTask(id = "gc-m3-t1", title = "اختبار التطبيق بعلامات حقيقية", status = ProjectTaskStatus.Completed),
                    ),
                ),
            ),
        )

        /**
         * PJ-04's one rich fixture task, shared verbatim between the seeded active instance
         * (with real [workflowStatus]) and the catalog template (workflowStatus null — a
         * not-yet-started project has no workflow to speak of), so the two never disagree on
         * content, only on per-student state.
         */
        fun waM2T2(status: ProjectTaskStatus, workflowStatus: TaskWorkflowStatus?): ProjectTask = ProjectTask(
            id = "wa-m2-t2",
            title = "بناء واختبار دارة الحساس",
            status = status,
            workflowStatus = workflowStatus,
            objective = "اجمع الحساس مع بقية الدارة، وتحقق أنه يستجيب بشكل صحيح قبل تركيبه داخل الجهاز.",
            instructions = listOf(
                "ركّب حساس مستوى الماء على لوحة التجارب بحسب مخطط التوصيل.",
                "وصّل الحساس بالمقاومة التي ركّبتها في المهمة السابقة.",
                "اختبر الدارة وهي جافة، وسجّل ماذا يحدث.",
                "اختبر الدارة بعد غمر طرف الحساس بالماء، وسجّل الفرق.",
            ),
            safetyNote = "استخدم مصدر طاقة منخفض الجهد فقط أثناء الاختبار، وتجنّب ملامسة الماء لأي توصيلة مكشوفة.",
            whatGoodLooksLike = listOf(
                "يستجيب الحساس بثبات عند تغيّر مستوى الماء",
                "التوصيلات مرتبة وواضحة وسهلة التتبع",
                "يستطيع الطالب شرح ما تغيّر بين الحالة الجافة والرطبة ولماذا",
            ),
            hints = listOf(
                TaskHint(id = "wa-m2-t2-hint-1", text = "تأكد أن طرفي الحساس لا يتلامسان مباشرة إلا عبر الماء.", xpCost = 5),
                TaskHint(id = "wa-m2-t2-hint-2", text = "إذا لم تتغيّر القراءة، جرّب توصيل المقاومة من الجهة الأخرى.", xpCost = 10),
            ),
            acceptedSubmissionTypes = setOf(SubmissionType.Photo, SubmissionType.WrittenReflection),
        )

        val CATALOG = listOf(
            Project(
                id = "water-alarm",
                title = "منبّه مستوى الماء",
                deliverable = "ستبني جهاز إنذار حقيقياً يعمل عند ارتفاع منسوب الماء",
                description = "مشروع عملي يطبّق مفاهيم الدارات الكهربائية والحساسات لبناء جهاز تنبيه فعلي يمكن استخدامه في المنزل.",
                subjectId = "physics", subjectTitle = "الفيزياء",
                skills = listOf("قراءة الدارات الكهربائية", "التعامل مع الحساسات", "حل المشكلات العملي"),
                estimatedDurationLabel = "أسبوعان",
                difficulty = ProjectDifficulty.Intermediate,
                mode = ProjectMode.Solo,
                medium = ProjectMedium.Physical,
                materials = listOf(
                    ProjectMaterial(
                        id = "mat-sensor", label = "حساس مستوى الماء", quantityLabel = "١",
                        estimatedCostLabel = "٨$", localSourcingNote = "متوفر في أغلب محلات الإلكترونيات",
                    ),
                    ProjectMaterial(
                        id = "mat-breadboard", label = "لوحة تجارب (Breadboard)", quantityLabel = "١",
                        estimatedCostLabel = "٣$", localSourcingNote = "محلات الإلكترونيات، أو من مختبر المدرسة",
                    ),
                    ProjectMaterial(
                        id = "mat-battery", label = "بطارية 9 فولت", quantityLabel = "١",
                        estimatedCostLabel = "٢$", localSourcingNote = "متوفرة في أي سوبرماركت أو محل أدوات منزلية",
                    ),
                    ProjectMaterial(
                        id = "mat-wires", label = "أسلاك توصيل", quantityLabel = "مجموعة صغيرة",
                        estimatedCostLabel = "١$", localSourcingNote = "محلات الإلكترونيات، أو أسلاك معاد استخدامها من المنزل",
                    ),
                    ProjectMaterial(
                        id = "mat-container", label = "علبة بلاستيكية شفافة لتغليف الجهاز", quantityLabel = "١",
                        isRequired = false, estimatedCostLabel = "٢$",
                        localSourcingNote = "اختيارية — يمكن إعادة استخدام علبة موجودة في المنزل",
                    ),
                ),
                showcaseSamples = listOf(
                    ProjectShowcaseSample("wa-sample-1", "نسخة أحد الطلاب من الجهاز بعد التركيب الكامل"),
                    ProjectShowcaseSample("wa-sample-2", "نسخة أخرى مركّبة داخل حاوية بلاستيكية شفافة"),
                ),
                milestones = listOf(
                    ProjectMilestone(
                        id = "wa-m1", title = "جمع المواد والتخطيط",
                        tasks = listOf(
                            ProjectTask("wa-m1-t1", "قراءة قائمة المواد المطلوبة", ProjectTaskStatus.Upcoming),
                            ProjectTask("wa-m1-t2", "تجهيز أدوات العمل", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "wa-m2", title = "تركيب الدارة الكهربائية",
                        tasks = listOf(
                            ProjectTask("wa-m2-t1", "توصيل حساس المستوى بالمقاومة", ProjectTaskStatus.Upcoming),
                            waM2T2(status = ProjectTaskStatus.Upcoming, workflowStatus = null),
                            ProjectTask("wa-m2-t3", "اختبار الدارة على مصدر الطاقة", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "wa-m3", title = "تركيب الجهاز داخل الحاوية",
                        tasks = listOf(
                            ProjectTask("wa-m3-t1", "قص فتحة للحساس في الحاوية", ProjectTaskStatus.Upcoming),
                            ProjectTask("wa-m3-t2", "تثبيت الدارة داخل الحاوية", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "wa-m4", title = "الاختبار النهائي والعرض",
                        tasks = listOf(
                            ProjectTask("wa-m4-t1", "اختبار الجهاز بماء حقيقي", ProjectTaskStatus.Upcoming),
                            ProjectTask("wa-m4-t2", "تسجيل عرض قصير للجهاز", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                ),
                safetyNotes = listOf(
                    ProjectSafetyNote(
                        id = "wa-safety-1", severity = SafetySeverity.Important,
                        text = "استخدم فقط بطارية منخفضة الجهد (9 فولت) — لا تستخدم مصدر كهرباء منزلي مباشر أبداً.",
                    ),
                    ProjectSafetyNote(
                        id = "wa-safety-2", severity = SafetySeverity.Important,
                        text = "تجنّب ملامسة الماء لأي توصيلة كهربائية مكشوفة أثناء الاختبار.",
                    ),
                    ProjectSafetyNote(
                        id = "wa-safety-3", severity = SafetySeverity.Caution,
                        text = "عند قص فتحة الحساس في الحاوية، اطلب إشراف أحد الوالدين أو المعلم عند استخدام أدوات القص.",
                    ),
                ),
                estimatedTotalCostLabel = "الإجمالي التقريبي: ١٦$ (تقديري)",
            ),
            Project(
                id = "grades-calculator",
                title = "حاسبة المعدل الدراسي",
                deliverable = "ستبني تطبيقاً بسيطاً يحسب معدلك الفصلي تلقائياً من علاماتك",
                description = "مشروع برمجي يطبّق أساسيات المنطق البرمجي والعمليات الحسابية لبناء أداة يمكنك استخدامها فعلياً كل فصل.",
                subjectId = "computing", subjectTitle = "الحوسبة والبرمجة",
                skills = listOf("المنطق البرمجي الأساسي", "التعامل مع المتغيرات والعمليات الحسابية", "تصميم واجهة بسيطة"),
                estimatedDurationLabel = "أسبوع واحد",
                difficulty = ProjectDifficulty.Beginner,
                mode = ProjectMode.Solo,
                medium = ProjectMedium.Digital,
                materials = listOf(
                    ProjectMaterial("mat-device", "حاسوب أو هاتف لتشغيل بيئة البرمجة"),
                    ProjectMaterial("mat-account", "حساب مجاني في منصة البرمجة المستخدمة"),
                ),
                showcaseSamples = listOf(
                    ProjectShowcaseSample("gc-sample-1", "نسخة أحد الطلاب من التطبيق تعرض المعدل والتقدير"),
                ),
                milestones = listOf(
                    ProjectMilestone(
                        id = "gc-m1", title = "تصميم فكرة التطبيق",
                        tasks = listOf(
                            ProjectTask("gc-m1-t1", "تحديد العلامات والأوزان المطلوبة", ProjectTaskStatus.Upcoming),
                            ProjectTask("gc-m1-t2", "رسم شاشة التطبيق على ورقة", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "gc-m2", title = "برمجة حساب المعدل",
                        tasks = listOf(
                            ProjectTask("gc-m2-t1", "برمجة إدخال العلامات", ProjectTaskStatus.Upcoming),
                            ProjectTask("gc-m2-t2", "برمجة معادلة حساب المعدل", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "gc-m3", title = "الاختبار والمشاركة",
                        tasks = listOf(
                            ProjectTask("gc-m3-t1", "اختبار التطبيق بعلامات حقيقية", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                ),
            ),
            Project(
                id = "ecosystem-model",
                title = "نموذج نظام بيئي مصغر",
                deliverable = "ستبني مع فريقك نظاماً بيئياً مصغراً مغلقاً يوضح التوازن بين الكائنات الحية",
                description = "مشروع جماعي يطبّق مفاهيم النظام البيئي والتوازن الحيوي عبر بناء نموذج مصغر قابل للمراقبة والتسجيل.",
                subjectId = "biology", subjectTitle = "الأحياء",
                skills = listOf("العمل ضمن فريق", "الملاحظة العلمية المنهجية", "تصميم تجربة بيئية"),
                estimatedDurationLabel = "ثلاثة أسابيع",
                difficulty = ProjectDifficulty.Advanced,
                mode = ProjectMode.Team,
                medium = ProjectMedium.Physical,
                materials = listOf(
                    ProjectMaterial("mat-jar", "وعاء زجاجي شفاف مغلق"),
                    ProjectMaterial("mat-soil", "تربة وحصى نظيفة"),
                    ProjectMaterial("mat-plants", "نباتات صغيرة مقاومة"),
                    ProjectMaterial("mat-log", "دفتر لتسجيل الملاحظات اليومية"),
                ),
                showcaseSamples = listOf(
                    ProjectShowcaseSample("em-sample-1", "نموذج أحد الفرق بعد أسبوعين من المراقبة"),
                ),
                milestones = listOf(
                    ProjectMilestone(
                        id = "em-m1", title = "تخطيط النظام البيئي",
                        tasks = listOf(
                            ProjectTask("em-m1-t1", "اختيار الكائنات الحية المناسبة", ProjectTaskStatus.Upcoming),
                            ProjectTask("em-m1-t2", "توزيع المهام على أعضاء الفريق", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "em-m2", title = "بناء النموذج",
                        tasks = listOf(
                            ProjectTask("em-m2-t1", "تجهيز الوعاء والتربة", ProjectTaskStatus.Upcoming),
                            ProjectTask("em-m2-t2", "زراعة النباتات وإغلاق الوعاء", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                    ProjectMilestone(
                        id = "em-m3", title = "المراقبة والتسجيل",
                        tasks = listOf(
                            ProjectTask("em-m3-t1", "تسجيل ملاحظات يومية لمدة أسبوعين", ProjectTaskStatus.Upcoming),
                        ),
                    ),
                ),
            ),
        )

        /**
         * PJ-06's deterministic MOCK evaluations, keyed by taskId — a fixed lookup per attempt,
         * never a live scoring pass, so runtime QA gets the same result every time. Index 0 is
         * the first attempt: circuit setup is full marks, test evidence and explanation are
         * not, so [ProjectReview.isAcceptable] is false and Resubmit is exercised. Index 1 is
         * the improved resubmission every later attempt clamps to (see
         * [MockProjectRepository.getReview]): every criterion is full marks, so it is
         * acceptable and Continue Project is exercised. Neither list entry is randomised or
         * timed — [MockProjectRepository.submissionAttempts] alone selects which one a call gets.
         */
        val REVIEWS = mapOf(
            "wa-m2-t2" to listOf(
                // Attempt 1 — not acceptable.
                ProjectReview(
                    taskId = "wa-m2-t2",
                    rubricResults = listOf(
                        RubricResult(
                            criterionId = "circuit-setup", criterionTitle = "تركيب الدارة",
                            score = 2, maxScore = 2,
                            reason = "التوصيلات مرتبة وواضحة، والحساس موصول بشكل صحيح مع المقاومة.",
                        ),
                        RubricResult(
                            criterionId = "test-evidence", criterionTitle = "دليل الاختبار",
                            score = 1, maxScore = 2,
                            reason = "الصورة توضح الاختبار الجاف فقط — لا يظهر دليل واضح على اختبار الحالة الرطبة.",
                        ),
                        RubricResult(
                            criterionId = "explanation", criterionTitle = "الشرح",
                            score = 0, maxScore = 2,
                            reason = "لم يوضّح الانعكاس ما الذي تغيّر بين الحالتين ولماذا استجاب الحساس بهذا الشكل.",
                        ),
                    ),
                    strengths = listOf(
                        "دارة الحساس مركّبة بشكل منظم وواضح التتبع.",
                        "الحساس يستجيب بشكل صحيح عند الاختبار الجاف.",
                    ),
                    improvement = "أضف صورة أو وصفاً واضحاً لاختبار الحالة الرطبة، مع شرح ما تغيّر ولماذا استجاب الحساس بهذا الشكل.",
                ),
                // Attempt 2+ — the improved resubmission, acceptable.
                ProjectReview(
                    taskId = "wa-m2-t2",
                    rubricResults = listOf(
                        RubricResult(
                            criterionId = "circuit-setup", criterionTitle = "تركيب الدارة",
                            score = 2, maxScore = 2,
                            reason = "التوصيلات ما زالت مرتبة وواضحة، والحساس موصول بشكل صحيح مع المقاومة.",
                        ),
                        RubricResult(
                            criterionId = "test-evidence", criterionTitle = "دليل الاختبار",
                            score = 2, maxScore = 2,
                            reason = "الصورة الجديدة توضح الاختبار في الحالتين الجافة والرطبة بوضوح.",
                        ),
                        RubricResult(
                            criterionId = "explanation", criterionTitle = "الشرح",
                            score = 2, maxScore = 2,
                            reason = "الانعكاس يوضح بدقة ما الذي تغيّر بين الحالتين ولماذا استجاب الحساس بهذا الشكل.",
                        ),
                    ),
                    strengths = listOf(
                        "أضفت دليلاً واضحاً على اختبار الحالة الرطبة كما طُلب.",
                        "الشرح أصبح دقيقاً ويربط بين الملاحظة والسبب.",
                    ),
                    improvement = "واصل توثيق ملاحظاتك بهذا الوضوح في المهام القادمة.",
                ),
            ),
        )

        // ── PJ-07 fixture ────────────────────────────────────────────────────────
        /** The rubric this slice's one peer assignment reviews against — the same criteria [REVIEWS]'s first attempt scores, stripped of score/reason, since PJ-07 rates them fresh. */
        val PEER_REVIEW_CRITERIA = REVIEWS.getValue("wa-m2-t2").first().rubricResults.map {
            RubricCriterion(id = it.criterionId, title = it.criterionTitle, maxScore = it.maxScore)
        }

        /** The one deterministic peer submission this slice's QA reviews — a fictional classmate's work, never the actual student's own "wa-m2-t2" submission. */
        val PEER_REVIEW_ASSIGNMENT = PeerSubmissionPreview(
            taskId = "wa-m2-t2",
            anonymizedLabel = "زميل من صفك",
            submission = ProjectSubmission(
                taskId = "wa-m2-t2",
                writtenReflection = "ركّبت الحساس واختبرته جافاً ثم غمرت طرفه بالماء، ولاحظت أن القراءة تتغيّر بسرعة عند التماس مع الماء.",
                link = "",
                attachments = listOf(SubmissionAttachment(id = "peer-att-1", type = SubmissionType.Photo, label = "IMG_014.jpg")),
                submittedAtLabel = "أمس",
            ),
            criteria = PEER_REVIEW_CRITERIA,
        )

        // ── PJ-08 fixture ────────────────────────────────────────────────────────
        const val TEAM_PROJECT_ID = "ecosystem-model"
        const val TEAM_NAME = "فريق النظام البيئي المصغّر"

        /** Fixed, fictional demo members — never real students. Exactly one carries [TeamMember.isCurrentStudent]. */
        val TEAM_MEMBERS = listOf(
            TeamMember(id = "em-mem-1", displayName = "سارة", role = TeamRole.Leader, isCurrentStudent = false),
            TeamMember(id = "em-mem-2", displayName = "أنت", role = TeamRole.Member, isCurrentStudent = true),
            TeamMember(id = "em-mem-3", displayName = "يوسف", role = TeamRole.Member, isCurrentStudent = false),
        )

        /** One assignee per completed/current task, and two explicit unassigned tasks — every required PJ-08 state reachable by hand. */
        val INITIAL_TEAM_ASSIGNMENTS = listOf(
            TeamTaskAssignment(taskId = "em-m1-t1", assigneeMemberId = "em-mem-1"),
            TeamTaskAssignment(taskId = "em-m1-t2", assigneeMemberId = "em-mem-2"),
            TeamTaskAssignment(taskId = "em-m2-t1", assigneeMemberId = "em-mem-3"),
            TeamTaskAssignment(taskId = "em-m2-t2", assigneeMemberId = null),
            TeamTaskAssignment(taskId = "em-m3-t1", assigneeMemberId = null),
        )

        val INITIAL_TEAM_MESSAGES = listOf(
            TeamMessage(id = "em-msg-1", senderMemberId = "em-mem-1", text = "بدأنا اختيار الكائنات المناسبة، شو رأيكم نضيف نبتة صبّار صغيرة؟", sentAtLabel = "أمس"),
            TeamMessage(id = "em-msg-2", senderMemberId = "em-mem-3", text = "فكرة حلوة، بس خلينا نتأكد إنها ما تحتاج عناية كثيرة.", sentAtLabel = "أمس"),
            TeamMessage(id = "em-msg-3", senderMemberId = "em-mem-2", text = "تمام، بدي أجهز الوعاء والتربة اليوم.", sentAtLabel = "اليوم"),
        )

        /** Never a real file upload — [SharedDeliverable.referenceLabel] is an honest MOCK placeholder, same boundary [SubmissionAttachment] draws for PJ-05. */
        val TEAM_DELIVERABLE = SharedDeliverable(
            title = "سجل المراقبة اليومي للنظام البيئي",
            stateLabel = "قيد الإعداد",
            lastUpdatedByMemberId = "em-mem-1",
            lastUpdatedAtLabel = "أمس",
            referenceLabel = "ملف مشترك لتسجيل الملاحظات (مثال تجريبي)",
        )

        // ── PJ-09 fixture ────────────────────────────────────────────────────────
        fun reflectionKey(projectId: String, milestoneId: String) = "$projectId:$milestoneId"

        /** wa-m1 ships with a saved reflection; every other milestone (wa-m2, em-m1, em-m2…) deliberately has none yet, so both required PJ-09 states are reachable by hand. */
        val SEEDED_REFLECTIONS: Map<String, ProjectReflection> = run {
            val waterAlarmReflection = ProjectReflection(
                projectId = "water-alarm",
                milestoneId = "wa-m1",
                milestoneTitle = "جمع المواد والتخطيط",
                projectTitle = "منبّه مستوى الماء",
                sessionLabel = "الجلسة الأولى",
                transcript = "جمعت كل المواد المطلوبة وتأكدت من توفرها، وخططت للخطوات القادمة في تركيب الدارة.",
                durationLabel = "٠٠:٣٨",
            )
            // PJ-10's showcase detail needs at least one reflection on its one completed
            // fixture, reused verbatim from PJ-09's own repository state — never a second copy.
            val gradesCalculatorReflection = ProjectReflection(
                projectId = "grades-calculator",
                milestoneId = "gc-m3",
                milestoneTitle = "الاختبار والمشاركة",
                projectTitle = "حاسبة المعدل الدراسي",
                sessionLabel = "الجلسة الأخيرة",
                transcript = "اختبرت التطبيق بعلامات حقيقية وتأكدت أن حساب المعدل صحيح، وشعرت بالفخر لأنني بنيت أداة أستخدمها فعلاً.",
                durationLabel = "٠١:٠٢",
            )
            listOf(waterAlarmReflection, gradesCalculatorReflection)
                .associateBy { reflectionKey(it.projectId, it.milestoneId) }
        }

        /**
         * PJ-11. Project id → certificate verification code — kept here (project domain), not
         * in [MockCertificateRepository] (verification domain); the literal code string is
         * intentionally duplicated in both places rather than one repository depending on the
         * other, the same boundary [ProfileRepository]/every other pair of independent mock
         * repositories in this file already keeps.
         */
        val CERTIFICATE_CODES = mapOf("grades-calculator" to "EDU-PROJ-GC01")
    }
}

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-01 · Messages List / X-02 · Conversation Thread / X-03 · New Conversation — Phase 6.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One canonical MOCK thread store shared by every Student and Teacher session. Identities
 * reuse the SAME literal id/name values [MockTeacherRepository]'s own TC-01 persona and TC-12
 * roster already established ("mock-teacher" / "أ. ليلى مراد", "s1".."s12") — duplicated as
 * plain fixture values rather than a runtime dependency on that repository, the exact
 * independent-mock-repository boundary [MockProjectRepository.CERTIFICATE_CODES]'s own doc
 * comment already documents for this file. [CURRENT_STUDENT_MESSAGING_ID] is the one seam
 * where the Student session's own "mock-student" id is deliberately re-pointed at the
 * existing "s1" roster identity — see that constant's own doc comment for why.
 *
 * Every method is keyed by an explicit `viewerId`/`viewerRole`, never an implicit "current
 * user" — nothing here reads [AuthRepository] itself, same boundary [TeacherRepository]
 * already keeps.
 */
class MockMessagingRepository : MessagingRepository {

    private val _threads = MutableStateFlow(seedThreads())
    override val threads: Flow<List<MessageThread>> = _threads.map { it.values.toList() }

    override suspend fun getThreads(): AppResult<List<MessageThread>> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(_threads.value.values.toList())
    }

    override suspend fun getThread(threadId: String): AppResult<MessageThread> {
        delay(MockLatency.FAST_MS)
        val thread = _threads.value[threadId] ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(thread)
    }

    override suspend fun getPermittedContacts(
        viewerId: String,
        viewerRole: MessageParticipantRole,
    ): AppResult<List<MessageParticipant>> {
        delay(MockLatency.FAST_MS)
        val contacts = when (viewerRole) {
            MessageParticipantRole.Teacher -> STUDENT_DIRECTORY.values.toList() + PARENT_DIRECTORY.values
            MessageParticipantRole.Student -> listOf(TEACHER)
            MessageParticipantRole.Parent -> emptyList()
        }
        return AppResult.Success(contacts)
    }

    override suspend fun openOrCreateThread(
        viewerId: String,
        viewerRole: MessageParticipantRole,
        contactId: String,
    ): AppResult<MessageThread> {
        delay(MockLatency.FAST_MS)
        if (viewerRole == MessageParticipantRole.Parent) return AppResult.Failure(AppError.NotFound)
        if (viewerRole == MessageParticipantRole.Teacher) {
            val parent = PARENT_DIRECTORY[contactId]
            if (parent != null) {
                val studentId = parent.relatedStudentId ?: return AppResult.Failure(AppError.NotFound)
                if (viewerId != TEACHER.id) return AppResult.Failure(AppError.NotFound)
                val threadId = parentThreadIdFor(TEACHER.id, studentId)
                val existing = _threads.value[threadId]
                if (existing != null) return AppResult.Success(existing)
                val created = MessageThread(id = threadId, teacherParticipant = TEACHER, studentParticipant = parent)
                _threads.value = _threads.value + (threadId to created)
                return AppResult.Success(created)
            }
        }
        val (teacherId, studentId) = when (viewerRole) {
            MessageParticipantRole.Teacher -> viewerId to contactId
            MessageParticipantRole.Student -> contactId to viewerId
            MessageParticipantRole.Parent -> return AppResult.Failure(AppError.NotFound)
        }
        if (teacherId != TEACHER.id) return AppResult.Failure(AppError.NotFound)
        val studentParticipant = STUDENT_DIRECTORY[studentId] ?: return AppResult.Failure(AppError.NotFound)

        val threadId = threadIdFor(teacherId, studentId)
        val existing = _threads.value[threadId]
        if (existing != null) return AppResult.Success(existing)

        val created = MessageThread(id = threadId, teacherParticipant = TEACHER, studentParticipant = studentParticipant)
        _threads.value = _threads.value + (threadId to created)
        return AppResult.Success(created)
    }

    override suspend fun getParentThreadForStudent(teacherId: String, studentId: String): AppResult<MessageThread> {
        delay(MockLatency.FAST_MS)
        val thread = _threads.value.values.firstOrNull { row ->
            row.teacherParticipant.id == teacherId &&
                row.studentParticipant.role == MessageParticipantRole.Parent &&
                row.studentParticipant.relatedStudentId == studentId
        } ?: return AppResult.Failure(AppError.NotFound)
        return AppResult.Success(thread)
    }

    override suspend fun sendMessage(
        threadId: String,
        senderId: String,
        body: String,
        attachment: MessageAttachment?,
    ): AppResult<MessagingChatMessage> {
        delay(MockLatency.FAST_MS)
        val thread = _threads.value[threadId] ?: return AppResult.Failure(AppError.NotFound)
        if (body.isBlank() && attachment == null) {
            return AppResult.Failure(AppError.Validation(mapOf("body" to "required")))
        }
        val message = MessagingChatMessage(
            id = "$threadId-m${thread.messages.size + 1}",
            senderId = senderId,
            body = body,
            sentAtLabel = "الآن",
            sentAtMillis = System.currentTimeMillis(),
            isRead = false,
            attachment = attachment,
        )
        val updated = thread.copy(messages = thread.messages + message)
        _threads.value = _threads.value + (threadId to updated)
        return AppResult.Success(message)
    }

    override suspend fun markThreadRead(threadId: String, viewerId: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        val thread = _threads.value[threadId] ?: return AppResult.Failure(AppError.NotFound)
        val updated = thread.copy(
            messages = thread.messages.map { msg ->
                if (msg.senderId != viewerId && !msg.isRead) msg.copy(isRead = true) else msg
            },
        )
        _threads.value = _threads.value + (threadId to updated)
        return AppResult.Success(Unit)
    }

    private companion object {
        fun threadIdFor(teacherId: String, studentId: String) = "thread-$teacherId-$studentId"
        fun parentThreadIdFor(teacherId: String, studentId: String) = "thread-$teacherId-parent-$studentId"

        val TEACHER = MessageParticipant(
            id = "mock-teacher",
            displayName = "أ. ليلى مراد",
            role = MessageParticipantRole.Teacher,
            avatarInitial = "ل",
            contextLabel = "الفيزياء · الرياضيات",
        )

        // Same s1..s12 roster identities TC-12/TC-13 already established (id, name, course) —
        // duplicated as plain literal values, never invented. Only s1..s3 are seeded WITH a
        // thread below; every other roster id is still a valid X-03 contact, it simply starts
        // with no history yet.
        val STUDENT_DIRECTORY: Map<String, MessageParticipant> = listOf(
            MessageParticipant("s1", "ريم الحلبي", MessageParticipantRole.Student, "ر", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s2", "سمير الخطيب", MessageParticipantRole.Student, "س", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s3", "لجين النجار", MessageParticipantRole.Student, "ل", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s4", "عمر الشامي", MessageParticipantRole.Student, "ع", "الرياضيات — البكالوريا"),
            MessageParticipant("s5", "دانا يوسف", MessageParticipantRole.Student, "د", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s6", "كريم زيدان", MessageParticipantRole.Student, "ك", "الكيمياء — الصف العاشر"),
            MessageParticipant("s7", "هبة قاسم", MessageParticipantRole.Student, "ه", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s8", "طارق حداد", MessageParticipantRole.Student, "ط", "الرياضيات — البكالوريا"),
            MessageParticipant("s9", "نور الدين سلوم", MessageParticipantRole.Student, "ن", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s10", "مايا فارس", MessageParticipantRole.Student, "م", "الكيمياء — الصف العاشر"),
            MessageParticipant("s11", "زياد المصري", MessageParticipantRole.Student, "ز", "الفيزياء — الصف الحادي عشر"),
            MessageParticipant("s12", "رنا عثمان", MessageParticipantRole.Student, "ر", "الفيزياء — الصف الحادي عشر"),
        ).associateBy { it.id }

        val PARENT_DIRECTORY: Map<String, MessageParticipant> = listOf(
            MessageParticipant(
                id = "parent-s1",
                displayName = "محمد الحلبي",
                role = MessageParticipantRole.Parent,
                avatarInitial = "م",
                contextLabel = "ولي أمر ريم · الحادي عشر",
                relatedStudentId = "s1",
            ),
        ).associateBy { it.id }

        /** TEACHER↔s1/s2/s3 start with real history so X-01 is never empty on first open; every other roster id is a genuinely fresh X-03 contact. */
        fun seedThreads(): Map<String, MessageThread> {
            val now = System.currentTimeMillis()
            val day = 24 * 60 * 60 * 1000L
            val minute = 60 * 1000L

            val s1 = STUDENT_DIRECTORY.getValue("s1")
            val s2 = STUDENT_DIRECTORY.getValue("s2")
            val s3 = STUDENT_DIRECTORY.getValue("s3")
            val parentS1 = PARENT_DIRECTORY.getValue("parent-s1")

            val thread1 = MessageThread(
                id = threadIdFor(TEACHER.id, s1.id),
                teacherParticipant = TEACHER,
                studentParticipant = s1,
                messages = listOf(
                    MessagingChatMessage(
                        "t1-m1", TEACHER.id, "ريم، كمّلي اختبار المشتقة قبل الجمعة.",
                        "أمس", now - day - 40 * minute, isRead = true,
                    ),
                    MessagingChatMessage(
                        "t1-m2", s1.id, "تمام أستاذ، رح أراجع وأقدّمه.",
                        "أمس", now - day - 20 * minute, isRead = true,
                    ),
                    MessagingChatMessage(
                        "t1-m3", TEACHER.id, "إذا علقتِ بنقطة الانعطاف، اسألي المعلّم الذكي.",
                        "أمس", now - day - 5 * minute, isRead = false,
                    ),
                ),
            )

            val thread2 = MessageThread(
                id = threadIdFor(TEACHER.id, s2.id),
                teacherParticipant = TEACHER,
                studentParticipant = s2,
                messages = listOf(
                    MessagingChatMessage(
                        id = "t2-m1", senderId = TEACHER.id,
                        body = "لاحظت تراجعاً بسيطاً في نتائجك الأخيرة، هذا الملف يلخّص النقاط المهمة.",
                        sentAtLabel = "قبل يومين", sentAtMillis = now - 2 * day, isRead = true,
                        attachment = MessageAttachment(MessageAttachmentType.File, "lesson_notes.pdf"),
                    ),
                    MessagingChatMessage("t2-m2", s2.id, "شكراً أستاذة، سأراجعه وأعاود التواصل.", "قبل يومين", now - 2 * day + 30 * minute, isRead = true),
                ),
            )

            val thread3 = MessageThread(
                id = threadIdFor(TEACHER.id, s3.id),
                teacherParticipant = TEACHER,
                studentParticipant = s3,
                messages = listOf(
                    MessagingChatMessage("t3-m1", TEACHER.id, "لجين، وصلك ملف المشروع؟", "قبل يومين", now - 2 * day, isRead = true),
                    MessagingChatMessage(
                        id = "t3-m2", senderId = s3.id, body = "أرسلت ملف المشروع",
                        sentAtLabel = "٢ي", sentAtMillis = now - 2 * day + 40 * minute,
                        isRead = true, attachment = MessageAttachment(MessageAttachmentType.File, "project.pdf"),
                    ),
                ),
            )

            val parentThread = MessageThread(
                id = parentThreadIdFor(TEACHER.id, "s1"),
                teacherParticipant = TEACHER,
                studentParticipant = parentS1,
                messages = listOf(
                    MessagingChatMessage(
                        "tp-m1", parentS1.id, "هل اختبار المشتقة إجباري هذا الأسبوع؟",
                        "١٢د", now - 12 * minute, isRead = false,
                    ),
                    MessagingChatMessage(
                        "tp-m2", TEACHER.id, "نعم، مطلوب قبل الجمعة. ريم ما قدّمته بعد.",
                        "١٢:06", now - 10 * minute, isRead = true,
                    ),
                    MessagingChatMessage(
                        "tp-m3", parentS1.id, "تمام أستاذ، رح نراجع معها الليلة.",
                        "١٢د", now - 8 * minute, isRead = false,
                    ),
                ),
            )

            return listOf(parentThread, thread1, thread2, thread3).associateBy { it.id }
        }
    }
}

class MockNotificationRepository : NotificationRepository {

    private val _notifications = MutableStateFlow(seedNotifications())
    override val notifications: Flow<List<StudentNotification>> = _notifications.asStateFlow()

    override suspend fun markRead(notificationId: String): AppResult<StudentNotification> {
        delay(MockLatency.FAST_MS)
        val notification = _notifications.value.firstOrNull { it.id == notificationId }
            ?: return AppResult.Failure(AppError.NotFound)
        val updated = notification.copy(isRead = true)
        _notifications.update { list -> list.map { if (it.id == notificationId) updated else it } }
        return AppResult.Success(updated)
    }

    override suspend fun markAllRead(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        _notifications.update { list -> list.map { it.copy(isRead = true) } }
        return AppResult.Success(Unit)
    }

    private companion object {
        fun seedNotifications(): List<StudentNotification> {
            val now = System.currentTimeMillis()
            return listOf(
                StudentNotification(
                    id = "n-message-teacher",
                    type = StudentNotificationType.InternalMessage,
                    title = "رسالة من أ. ليلى مراد",
                    body = "إذا علقتِ بنقطة الانعطاف، اسألي المعلّم الذكي.",
                    timestampLabel = "أمس",
                    createdAtMillis = now - 24 * 60 * 60 * 1000L,
                    isRead = false,
                    threadId = "thread-mock-teacher-s1",
                ),
                StudentNotification(
                    id = "n-payment-verified",
                    type = StudentNotificationType.PaymentStatus,
                    title = "تم تأكيد دفع سابق",
                    body = "دفعة مادة الأحياء جاهزة لتفعيل الوصول.",
                    timestampLabel = "أمس",
                    createdAtMillis = now - 26 * 60 * 60 * 1000L,
                    isRead = false,
                    courseId = "biology",
                ),
                StudentNotification(
                    id = "n-lesson-update",
                    type = StudentNotificationType.LessonUpdate,
                    title = "درس جديد متاح",
                    body = "تم تحديث مواد المراجعة في الفيزياء.",
                    timestampLabel = "قبل يومين",
                    createdAtMillis = now - 2 * 24 * 60 * 60 * 1000L,
                    isRead = true,
                    courseId = "physics",
                ),
            )
        }
    }
}
