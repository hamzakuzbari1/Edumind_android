package com.rork.eduspark.data.repository

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.model.ExamEntry
import com.rork.eduspark.data.model.ExamSchedule
import com.rork.eduspark.data.model.LessonDetail
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.model.MessageAttachment
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.data.model.PaymentRequest
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.model.ParentAttendancePeriod
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.PeerReview
import com.rork.eduspark.data.model.PeerReviewDraft
import com.rork.eduspark.data.model.PeerSubmissionPreview
import com.rork.eduspark.data.model.PlannerChangeProposal
import com.rork.eduspark.data.model.PlannerChatMessage
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectReflection
import com.rork.eduspark.data.model.ProjectReview
import com.rork.eduspark.data.model.ProjectSubmission
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.ProjectTeam
import com.rork.eduspark.data.model.PurchaseAccess
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizAttempt
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.RedeemedVoucher
import com.rork.eduspark.data.model.SecuritySettings
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.RoutineBuilderAnswers
import com.rork.eduspark.data.model.RoutineDraft
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.model.StudentNotification
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.AnalyticsPeriod
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherActivityItem
import com.rork.eduspark.data.model.TeacherAnalyticsSnapshot
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherCriterionReview
import com.rork.eduspark.data.model.TeacherProject
import com.rork.eduspark.data.model.TeacherProjectMaterial
import com.rork.eduspark.data.model.TeacherProjectMediaItem
import com.rork.eduspark.data.model.TeacherProjectMilestone
import com.rork.eduspark.data.model.TeacherProjectRubricCriterion
import com.rork.eduspark.data.model.TeacherProjectSafetyNote
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.data.model.TeacherDashboardSummary
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonChunk
import com.rork.eduspark.data.model.TeacherLessonEditorState
import com.rork.eduspark.data.model.TeacherLessonProcessingState
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.model.TeacherGradeEntry
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.TeacherPrivateNote
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherStudentAttendance
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceProfile
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.model.VoiceSampleSourceType
import com.rork.eduspark.data.model.SubmissionDraft
import com.rork.eduspark.data.model.TeamMessage
import com.rork.eduspark.data.model.TeamTaskAssignment
import com.rork.eduspark.data.model.TutorReply
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.model.VoucherValidationResult
import com.rork.eduspark.data.model.WeekPlan
import kotlinx.coroutines.flow.Flow

/**
 * ══════════════════════════════════════════════════════════════════════════
 * REPOSITORY CONTRACTS — the swap point for the real FastAPI client.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every contract below describes a capability the **existing backend already has**,
 * verified against the Source Audit. Nothing here invents an endpoint, a field name or a
 * response shape; method names describe intent, not routes.
 *
 * Today these are fulfilled by the isolated mock implementations in
 * `data/repository/mock`. When the generated client lands, a `Remote…Repository`
 * implements the same interface, Koin binds it instead, and no ViewModel or composable
 * changes at all.
 *
 * Features with **no backend** (Projects, push, real payments, offline sync endpoints)
 * deliberately have no contract yet. They get one when the backend does — see
 * [FeatureAvailability].
 */

/**
 * Auth — Source Audit §3.
 *
 * Capabilities that exist: register (student|teacher|parent), login, logout (revokes the
 * server session), `/auth/me`, password reset, email verification, email-OTP 2FA.
 *
 * Capability that does NOT exist: **token refresh**. There is no `refresh()` on this
 * interface on purpose. Every consumer must treat expiry as "sign in again".
 */
interface AuthRepository {

    /** Emits the current session, or null when signed out. */
    val session: Flow<SessionUser?>

    suspend fun signIn(email: String, password: String): AppResult<SignInOutcome>

    suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<SessionUser>

    /** Email verification exists on the backend but is NOT enforced at login. */
    suspend fun verifyEmail(code: String): AppResult<Unit>

    suspend fun resendEmailCode(): AppResult<Unit>

    /** Email OTP only — the platform returns 501 for TOTP. */
    suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): AppResult<SessionUser>

    suspend fun requestPasswordReset(email: String): AppResult<Unit>

    suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit>

    /**
     * SO-05. Source Audit §3 confirms the backend already carries an `onboarding_complete`
     * flag on the session (`/auth/me`) — this marks it, it does not invent it. Grade,
     * subjects and teacher choices themselves are Student Core writes, out of scope for the
     * onboarding slice; this call only flips the gate Splash and post-auth routing read.
     *
     * TC-01 reuses this exact call for "has this teacher finished setup" — the same session
     * flag, never a second parallel one; see
     * [com.rork.eduspark.ui.screens.teacher.TeacherSetupViewModel]'s own doc comment.
     */
    suspend fun completeOnboarding(): AppResult<Unit>

    /** Revokes the session server-side and clears local credentials. */
    suspend fun signOut()
}

/** What login can lead to. Mirrors the real branching of A-04. */
sealed interface SignInOutcome {
    data class Authenticated(val user: SessionUser) : SignInOutcome

    /** Backend reports the address is unverified → route to A-08. */
    data class EmailVerificationRequired(val email: String) : SignInOutcome

    /** Backend requires the email OTP second factor → route to A-09. */
    data class TwoFactorRequired(val email: String) : SignInOutcome
}

/**
 * Learning paths — courses and their lessons.
 *
 * Backend equivalents exist (student dashboard, course detail, lesson list) and are
 * marked READY in the Source Audit's mobile reuse map. Students only ever see
 * **processed** lessons on **paid** courses; the entitlement gate is a server decision,
 * never re-implemented on the client.
 */
interface LearningRepository {
    /** ST-01. [StudentHomeSnapshot.continueItem] null is the legitimate first-day empty state. */
    suspend fun getStudentHome(): AppResult<StudentHomeSnapshot>

    /** ST-02. [pathId] is a course id here — the same contract serves language/project paths later. */
    suspend fun getPath(pathId: String): AppResult<LearningPath>

    /** STUDENT_COURSES tab — every course the student's grade offers, entitled or not (course
     *  discovery: Test-2SY's `MySubjectsSection` reference). See [StudentCourseSummary]. */
    suspend fun getStudentCourses(): AppResult<List<StudentCourseSummary>>

    suspend fun getGamification(): AppResult<GamificationSnapshot>

    /** ST-03. [lessonId] is a [com.rork.eduspark.data.model.LearningStep] id from a path's steps. */
    suspend fun getLesson(lessonId: String): AppResult<LessonDetail>

    /** The single shared source of truth for "which lessons has the student finished" — every
     *  read above ([getLesson], [getPath], [getStudentHome], [getStudentCourses]) reflects it,
     *  so completing a lesson in ST-03 shows up on Course Detail and Home without a restart,
     *  the same hot-flow shape [PlannerRepository.weekPlan] already establishes. */
    val completedLessonIds: Flow<Set<String>>

    /** ST-03's Mark Complete, after the completion-verification sheet confirms. */
    suspend fun markLessonCompleted(lessonId: String)
}

/**
 * ST-04 / ST-05 — the lesson-grounded AI tutor chat. Source Audit §4 lists an AI tutor chat
 * endpoint as implemented, RAG-grounded against the current lesson, and genuinely
 * **non-streaming**: one complete reply after 5–30+ seconds, not a token stream. ST-05's
 * voice mode reuses this exact same contract — only how [message] was produced differs
 * (typed vs. on-device transcription), which is why there is one method here, not two.
 */
interface TutorRepository {
    suspend fun sendMessage(lessonId: String, message: String): AppResult<TutorReply>
}

/**
 * ST-06 / ST-07 / ST-08 / ST-09 — one contract for every quiz the runner shell plays,
 * whatever [Quiz.origin] it carries. Source Audit §6 lists `/student/quiz/…` and
 * `/student/manual-quizzes/…` as separate, both READY; this interface does not distinguish
 * them by method, only by the [Quiz.id] passed in — exactly like the real endpoints differ
 * by resource id, not by shape.
 *
 * Attempt state (current question, saved answers) lives in the repository's memory, not in
 * this interface's return types — that is what makes "bail out and resume" and "Previous
 * preserves answers" free: the mock simply never forgets an attempt until the process dies.
 */
interface QuizRepository {
    suspend fun getQuiz(quizId: String): AppResult<Quiz>

    /** Restores the in-progress (or completed) attempt, or seeds a fresh one — never fails. */
    fun getAttempt(quizId: String): QuizAttempt

    fun saveAnswer(quizId: String, answer: QuizAnswer): QuizAttempt

    fun goToQuestion(quizId: String, index: Int): QuizAttempt

    /** ST-08's retry — clears answers and position, keeps the same question set. */
    fun resetAttempt(quizId: String): QuizAttempt

    suspend fun submitQuiz(quizId: String): AppResult<QuizResult>

    /** Re-reads a result already computed by [submitQuiz] — for returning to ST-07 without resubmitting. */
    suspend fun getResult(quizId: String): AppResult<QuizResult>

    /** ST-07's "Practice these again" — a new [Quiz] made only of [sourceQuizId]'s wrong questions. */
    suspend fun buildRemedialQuiz(sourceQuizId: String): AppResult<Quiz>
}

/**
 * ST-10 · Planner / ST-11 · Planner AI Chat. Source Audit §6/§7: "smart planner generate" is
 * a rule-based optimizer (not LLM), and "planner chat" is regex parsing with template
 * replies — this mock does the same shape of work, not a fake LLM call.
 *
 * [weekPlan] is a hot flow rather than a plain suspend getter on purpose: ST-10 and ST-11 are
 * two independent screens (no graph-scoped shared ViewModel between them, unlike ST-04/05),
 * so a change accepted in ST-11's chat has to reach ST-10 through the one thing both already
 * read from — this repository — rather than through navigation state.
 */
interface PlannerRepository {
    val weekPlan: Flow<WeekPlan?>
    val recommendations: Flow<List<PlannerRecommendation>>

    /** Populates [weekPlan] if empty, or re-confirms the cached one — the screen's initial fetch. */
    suspend fun loadWeekPlan(): AppResult<WeekPlan>

    suspend fun regenerateWeek(): AppResult<WeekPlan>

    suspend fun toggleSessionCompletion(sessionId: String): AppResult<WeekPlan>

    suspend fun sendPlannerChatMessage(message: String): AppResult<PlannerChatMessage>

    /** Only this mutates the week plan — the proposal itself never applies on its own. */
    suspend fun acceptProposal(proposalId: String): AppResult<WeekPlan>

    suspend fun rejectProposal(proposalId: String): AppResult<Unit>

    /** Applies the single visible Home/Planner recommendation, then removes it. */
    suspend fun applyRecommendation(recommendationId: String): AppResult<WeekPlan>

    suspend fun dismissRecommendation(recommendationId: String): AppResult<Unit>
}

/**
 * ST-12 · Routine Builder / ST-13 · Routine Week View. Source Audit §6: "Daily routine —
 * Implemented", `/student/routine/…`. Deliberately a separate contract from
 * [PlannerRepository] — see [RoutineProfile]'s own doc comment for why the two models never
 * merge — but the same hot-flow shape, for the same reason: ST-12 and ST-13 are independent
 * screens that need to see one another's writes without a shared ViewModel.
 */
interface RoutineRepository {
    val routineProfile: Flow<RoutineProfile?>
    val routineDraft: Flow<RoutineDraft?>

    /** Restores the confirmed routine if one exists; [AppError.NotFound] means "never built yet" — ST-13 routes to ST-12. */
    suspend fun loadRoutine(): AppResult<RoutineProfile>

    /** ST-12's confirm step — builds and stores the week's slots from the six answers. */
    suspend fun confirmRoutine(answers: RoutineBuilderAnswers): AppResult<RoutineProfile>

    suspend fun startRoutineAiBuild(answers: RoutineBuilderAnswers): AppResult<RoutineDraft>

    suspend fun confirmRoutineDraftDay(day: Weekday): AppResult<RoutineDraft>

    suspend fun adjustRoutineDraft(message: String): AppResult<RoutineDraft>

    suspend fun reviewRoutineDraft(): AppResult<RoutineDraft>

    suspend fun setRoutineSuggestion(suggestionId: String, accepted: Boolean?): AppResult<RoutineDraft>

    suspend fun finalizeRoutineDraft(): AppResult<RoutineProfile>

    /** ST-13's Complete / Miss / Undo — all three are just a different [RoutineSlotStatus]. */
    suspend fun updateSlotStatus(slotId: String, status: RoutineSlotStatus): AppResult<RoutineProfile>

    /** Clears [RoutineProfile.needsRenewal] without changing any slot — "still works for me". */
    suspend fun acknowledgeRenewal(): AppResult<RoutineProfile>

    suspend fun renewRoutineWeek(): AppResult<RoutineProfile>

    suspend fun deleteRoutine(): AppResult<Unit>
}

/**
 * ST-14 · Exam Schedule Capture. No OCR engine behind this — see [ExamSchedule]'s own doc
 * comment. A hot flow for the same reason as [PlannerRepository.weekPlan]: ST-10 reads the
 * confirmed schedule to show that exams now exist, without ST-14 needing to hand anything
 * back through navigation.
 */
interface ExamRepository {
    val examSchedule: Flow<ExamSchedule?>

    /** Simulates capture + OCR in one call — there is no real image, so there is nothing to upload separately. */
    suspend fun captureSchedule(): AppResult<ExamSchedule>

    /** ST-14's confirm step — the corrected entry list becomes the schedule Planner reflects. */
    suspend fun confirmSchedule(entries: List<ExamEntry>): AppResult<ExamSchedule>
}

/**
 * Certificate verification — Source Audit §5: public verify endpoint, no auth required.
 * A-12 is reached by deep link and must render correctly with no session at all, so this
 * contract carries no dependency on [AuthRepository].
 */
interface CertificateRepository {
    suspend fun verify(code: String): AppResult<CertificateVerification>
}

/**
 * SO-03 — teacher browsing per subject during onboarding. Source Audit §2 lists onboarding's
 * grade → subjects → teachers flow as implemented; grade and subject catalogues are static
 * curriculum reference data (kept local, same as A-07's subject/grade lists), but teacher
 * profiles (bio, rating, pricing) are genuinely server-driven, so that part gets a contract.
 */
interface OnboardingRepository {
    suspend fun getTeachers(subjectId: String): AppResult<List<OnboardingTeacher>>
}

/**
 * ST-15 · Achievements. Source Audit §2: "Achievements / XP — Implemented." The level/XP/
 * streak header reuses [LearningRepository.getGamification] — this contract only adds the
 * badge list itself, so gamification data is never modelled twice.
 */
interface AchievementRepository {
    suspend fun getAchievements(): AppResult<List<Achievement>>
}

/**
 * ST-16 · Subscriptions. Source Audit §2/§6: "Subscriptions — Demo payment only",
 * `/student/subscriptions/…`. Read-only on purpose — see [CourseSubscription]'s own doc
 * comment for why nothing here can mutate a subscription to active.
 */
interface SubscriptionRepository {
    suspend fun getSubscriptions(): AppResult<List<CourseSubscription>>
    suspend fun getAvailableCourses(): AppResult<List<AvailableCourse>>
}

/**
 * ST-17 · Course Paywall / ST-18 · Payment Method Select / ST-19 · Payment Pending /
 * ST-20 · Purchase Success.
 * `PAYMENT_MODE = "direct"` — see [PendingPayment]'s own doc comment for why nothing here can
 * reach [com.rork.eduspark.data.model.PaymentStatus.Pending] into an active subscription.
 *
 * [pendingPayment] is a hot flow — same "cross-screen mutable shared state" shape as
 * [PlannerRepository.weekPlan] — because ST-19 must show the same pending record whether the
 * student just submitted it or is returning to it later in the same session.
 */
interface PaymentRepository {
    /** ST-17/ST-18. [AppError.NotFound][com.rork.eduspark.core.result.AppError.NotFound] when [courseId] has no purchasable/renewable offer. */
    suspend fun getCourseOffer(courseId: String): AppResult<CourseOffer>

    /** ST-18. The direct-payment methods available in this build. */
    suspend fun getPaymentMethods(): AppResult<List<PaymentMethod>>

    val pendingPayment: Flow<PendingPayment?>

    /**
     * ST-19. Safe to call more than once for the same [PaymentRequest.courseId] — same
     * "re-confirms the cached one" idempotency [PlannerRepository.loadWeekPlan] already uses,
     * so retrying after a failed attempt, or simply returning to ST-19 later, never creates a
     * second pending transaction for the same course.
     */
    suspend fun submitPayment(request: PaymentRequest): AppResult<PendingPayment>

    /**
     * ST-20's entry point from ST-16 — the one pre-seeded [com.rork.eduspark.data.model.PaymentStatus.Verified]
     * payment that hasn't been activated yet, or null once activated. Never derived from
     * [pendingPayment]/[submitPayment] — nothing in this build promotes Pending into Verified.
     */
    val verifiedUnactivatedPayment: Flow<PendingPayment?>

    /** ST-20. Looks up whatever payment exists for [courseId] — Pending, Verified, or none — plus whether access was already activated. */
    suspend fun getPurchaseAccess(courseId: String): AppResult<PurchaseAccess?>

    /**
     * ST-20. Idempotent — a no-op success once [courseId] is already activated, never a second
     * grant. The caller must have already confirmed the underlying payment is
     * [com.rork.eduspark.data.model.PaymentStatus.Verified]; this call only records the fact.
     */
    suspend fun activateAccess(courseId: String): AppResult<Unit>
}

/**
 * ST-21 · Voucher Redeem. Its own entitlement rail, independent of [PaymentRepository] — see
 * [com.rork.eduspark.data.model.VoucherValidationResult]'s own doc comment. Redemption is
 * idempotent per code, tracked entirely within this repository.
 */
interface VoucherRepository {
    /** Read-only check — never marks a code used. */
    suspend fun validateVoucher(code: String): AppResult<VoucherValidationResult>

    /** Commits the redemption. Calling this again for a code this session already redeemed returns the same grant, never a duplicate. */
    suspend fun redeemVoucher(code: String): AppResult<RedeemedVoucher>
}

/**
 * ST-22 · Student Profile / ST-23 · Settings — Account (name + avatar).
 *
 * [profile] is the *one* place this student's editable name/grade/school live — ST-01's
 * [LearningRepository.getStudentHome] snapshot is seeded from the same persona but is never
 * re-read or mutated by this repository, so an edit here does not retroactively change what
 * ST-01 already displayed this session (same "no cross-repository mutation" boundary every
 * other slice this session has kept). [linkedParents] is a hot flow so a revoke is reflected
 * immediately without a manual reload.
 */
interface ProfileRepository {
    val profile: Flow<StudentProfile>
    suspend fun getProfile(): AppResult<StudentProfile>
    suspend fun updateProfile(displayName: String, grade: Grade, school: String): AppResult<StudentProfile>

    val linkedParents: Flow<List<LinkedParent>>
    suspend fun getLinkedParents(): AppResult<List<LinkedParent>>

    /** Session-persistent — a revoked parent stays revoked; never silently removed without this explicit call. */
    suspend fun revokeLinkedParent(parentId: String): AppResult<Unit>

    /** Learning Preferences — a persistent, re-editable ST-22 extension (see [LearningPreferences]'s own doc comment). */
    val learningPreferences: Flow<LearningPreferences>
    suspend fun getLearningPreferences(): AppResult<LearningPreferences>
    suspend fun updateLearningPreferences(preferences: LearningPreferences): AppResult<LearningPreferences>
}

/**
 * ST-24 · Settings — Security. Source Audit: email OTP is the only second factor the backend
 * supports — see [SecuritySettings]'s own doc comment for why there is no TOTP path here.
 * [activeSessions] and [SecuritySettings.twoFactorEnabled] are both hot state so a revoke or a
 * toggle is reflected immediately, same shape as [ProfileRepository.linkedParents].
 */
interface SecurityRepository {
    val securitySettings: Flow<SecuritySettings>
    suspend fun getSecuritySettings(): AppResult<SecuritySettings>

    /** Sends the email OTP — same mock code every other email-OTP flow in this app accepts. */
    suspend fun requestEnableTwoFactor(): AppResult<Unit>
    suspend fun confirmEnableTwoFactor(code: String): AppResult<Unit>

    /** No re-verification needed to turn it off — the screen gates this behind its own confirmation instead. */
    suspend fun disableTwoFactor(): AppResult<Unit>

    val activeSessions: Flow<List<ActiveSession>>
    suspend fun getActiveSessions(): AppResult<List<ActiveSession>>

    /** [sessionId] must not be the current device's session — see [ActiveSession.isCurrentDevice]'s own doc comment. */
    suspend fun revokeSession(sessionId: String): AppResult<Unit>

    /** Revokes every *other* session — the current device's session is excluded by construction, never by the caller remembering to skip it. */
    suspend fun revokeAllOtherSessions(): AppResult<Unit>
}

/**
 * PR-01/PR-13 · Parent account and student linking.
 *
 * Parent linking is parent-owned at the contract boundary: Student screens continue to read
 * [ProfileRepository], while Parent screens type codes and read linked-student summaries here.
 * Mock implementations may share one relationship store so both role-facing contracts stay
 * synchronized without either UI reaching across the other's repository.
 */
interface ParentRepository {
    val linkedStudents: Flow<List<ParentLinkedStudent>>
    suspend fun getLinkedStudents(): AppResult<List<ParentLinkedStudent>>
    suspend fun linkStudent(code: String): AppResult<ParentLinkedStudent>
    suspend fun getDashboardSnapshot(studentId: String): AppResult<ParentDashboardSnapshot>
    suspend fun getPerformanceSnapshot(studentId: String): AppResult<ParentPerformanceSnapshot>
    suspend fun getAttendanceStudyTime(
        studentId: String,
        period: ParentAttendancePeriod,
    ): AppResult<ParentAttendanceStudyTimeSnapshot>
    suspend fun getLessonProgress(studentId: String): AppResult<ParentLessonProgressSnapshot>
    suspend fun getLessonDetails(lessonId: String): AppResult<ParentLessonDetails>
}

/**
 * PJ-01 · Projects Hub / PJ-02 · Project Detail / PJ-03 · Milestone Board.
 *
 * Source Audit: Projects has no implemented backend contract at all yet (see
 * [FeatureAvailability.PROJECTS_BACKEND_READY]) — every method here is backed by deterministic
 * MOCK fixtures. [activeProjects] is a hot flow, same "cross-screen mutable shared state" shape
 * as [PlannerRepository.weekPlan], because My Projects (PJ-01), Project Detail (PJ-02) and the
 * Milestone Board (PJ-03) must all agree on the same started/not-started state without a
 * manual reload.
 */
interface ProjectRepository {
    suspend fun getCatalog(): AppResult<List<Project>>
    suspend fun getProject(projectId: String): AppResult<Project>

    val activeProjects: Flow<List<ActiveProject>>
    suspend fun getActiveProjects(): AppResult<List<ActiveProject>>

    /**
     * Idempotent — starting a project the student already started returns the existing
     * [ActiveProject] rather than creating a second one, same "re-confirms the cached one"
     * idempotency [PlannerRepository.loadWeekPlan]/[PaymentRepository.submitPayment] already use.
     * Only ever called for [com.rork.eduspark.data.model.ProjectMode.Solo] projects — team
     * formation is not implemented in this slice.
     */
    suspend fun startProject(projectId: String): AppResult<ActiveProject>

    /**
     * Preparation-checklist state, tracked independently of [ActiveProject] on purpose — a
     * material is tickable *before* the project is started, and ticking one never marks a
     * milestone/task complete.
     */
    suspend fun getCheckedMaterials(projectId: String): AppResult<Set<String>>
    suspend fun setMaterialChecked(projectId: String, materialId: String, checked: Boolean): AppResult<Unit>

    /** PJ-04/PJ-05/PJ-06 all resolve a task through this one lookup — the same [ActiveProject.milestones] the spine renders from, never a second copy. */
    suspend fun getTask(projectId: String, taskId: String): AppResult<ProjectTask>

    /** PJ-04. [com.rork.eduspark.data.model.TaskWorkflowStatus.NotStarted] → [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress] only — opening the screen alone never calls this. */
    suspend fun startTaskWork(projectId: String, taskId: String): AppResult<ProjectTask>

    /**
     * PJ-05. Never null — an untouched task returns an empty [SubmissionDraft], and once a
     * [ProjectSubmission] exists (e.g. after Resubmit), returns a draft seeded from it so the
     * previous content is available to edit, rather than a second "resubmit" call needing to
     * exist just to thread that content back in.
     */
    suspend fun getDraft(projectId: String, taskId: String): AppResult<SubmissionDraft>

    /** Persists the draft locally and flips [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress] → [com.rork.eduspark.data.model.TaskWorkflowStatus.ReadyToSubmit] once it has content. */
    suspend fun saveDraft(draft: SubmissionDraft): AppResult<SubmissionDraft>

    /**
     * Idempotent *per attempt* — calling this again while the task is already
     * [com.rork.eduspark.data.model.TaskWorkflowStatus.Submitted] or
     * [com.rork.eduspark.data.model.TaskWorkflowStatus.Reviewed] returns the existing
     * [ProjectSubmission] rather than creating a second, same "re-confirms the cached one"
     * idempotency [PaymentRepository.submitPayment]/[VoucherRepository.redeemVoucher] already
     * use. Once [beginResubmission] resets the task back to
     * [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress], the next call here creates
     * a genuinely new submission and counts as the next attempt for [getReview] — never on a
     * plain retry. Always submits whatever [SubmissionDraft] is currently saved for the task.
     */
    suspend fun submitTask(projectId: String, taskId: String): AppResult<ProjectSubmission>

    suspend fun getSubmission(taskId: String): AppResult<ProjectSubmission?>

    /**
     * PJ-06. A deterministic MOCK evaluation, not a live AI call — idempotent, safe to call on
     * every PJ-06 visit; repeat calls for the same [submitTask] attempt always return the same
     * fixture. Which fixture that is depends only on how many times [submitTask] has genuinely
     * created a new submission for this task (repository-tracked, never a random or timed
     * choice) — a first attempt reproducibly needs work, a resubmission reproducibly passes,
     * so runtime QA can exercise both the Resubmit and the Continue path on demand. The call
     * whose review is acceptable is what flips
     * [com.rork.eduspark.data.model.TaskWorkflowStatus.Reviewed] and [ProjectTask.status] to
     * [com.rork.eduspark.data.model.ProjectTaskStatus.Completed] — never before, and never
     * from anywhere but here.
     */
    suspend fun getReview(projectId: String, taskId: String): AppResult<ProjectReview>

    /** PJ-06 Resubmit. [com.rork.eduspark.data.model.TaskWorkflowStatus.Reviewed] (rejected) → back to [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress]. */
    suspend fun beginResubmission(projectId: String, taskId: String): AppResult<Unit>

    /** PJ-07. The one deterministic MOCK peer submission available to review this slice — no real peer network, no queue of many candidates. */
    suspend fun getPeerReviewAssignment(): AppResult<PeerSubmissionPreview>

    suspend fun getPeerReviewDraft(taskId: String): AppResult<PeerReviewDraft>

    suspend fun savePeerReviewDraft(draft: PeerReviewDraft): AppResult<PeerReviewDraft>

    /** Idempotent — a repeat call after the assignment is already reviewed returns the existing [PeerReview] rather than creating a second, same idempotency shape [submitTask] uses. */
    suspend fun submitPeerReview(draft: PeerReviewDraft): AppResult<PeerReview>

    /** PJ-08. [com.rork.eduspark.data.model.ProjectMode.Team] projects only — deterministic MOCK membership, never a real peer network. */
    suspend fun getTeam(projectId: String): AppResult<ProjectTeam>

    /**
     * PJ-08. Self-assign only — a student can only ever claim or release THEIR OWN
     * [com.rork.eduspark.data.model.TeamMember] row's tasks, never reassign someone else's.
     * There is no admin/permissions surface in this slice by design.
     */
    suspend fun assignTaskToSelf(projectId: String, taskId: String): AppResult<TeamTaskAssignment>

    suspend fun unassignOwnTask(projectId: String, taskId: String): AppResult<TeamTaskAssignment>

    /** PJ-08. Appends to the team's session-local message history — no WebSocket, no real-time delivery to anyone else. */
    suspend fun sendTeamMessage(projectId: String, text: String): AppResult<TeamMessage>

    /** PJ-09. Null means no reflection has been saved for this milestone yet — the screen's own "no reflection yet" state, not a fabricated empty one. */
    suspend fun getReflection(projectId: String, milestoneId: String): AppResult<ProjectReflection?>

    /** PJ-09. Also acts as the update — saving again for the same ([projectId], [milestoneId]) replaces the existing reflection rather than creating a second. */
    suspend fun saveReflection(reflection: ProjectReflection): AppResult<ProjectReflection>

    /**
     * PJ-11. Null when [projectId] has no certificate yet — only a project whose
     * [com.rork.eduspark.data.model.ActiveProject.isFullyCompleted] is true ever has one. This
     * only tells the caller which code to look up; [CertificateRepository.verify] — the SAME
     * verification path A-12 already uses — is what actually resolves the code to a record.
     */
    suspend fun getCertificateCode(projectId: String): AppResult<String?>
}

/**
 * Phase 3 · TC-01 Teacher Setup Wizard / TC-02 Teacher Dashboard / TC-03 Courses List.
 *
 * MOCK domain state only — the real FastAPI teacher backend (course/lesson management,
 * PDF/video/homework upload, AI lesson processing, voice profile, quiz builder,
 * students/analytics) already exists server-side and is deliberately not integrated here.
 * Every method is keyed by [teacherId] ([SessionUser.id]) rather than an implicit "current
 * teacher" — the same "no cross-repository dependency" boundary every other repository in
 * this app keeps; the caller (a ViewModel, which already holds [AuthRepository]) resolves
 * which teacher is asking.
 *
 * "Saved" and "completed" are the same event for every wizard step: each `save…()` call marks
 * its own [com.rork.eduspark.data.model.TeacherSetupStepId] in
 * [com.rork.eduspark.data.model.TeacherSetupState.completedStepIds], independent of the other
 * steps, so TC-01 is resumable from whichever step was last saved with its values intact.
 */
interface TeacherRepository {
    suspend fun getSetupState(teacherId: String): AppResult<TeacherSetupState>

    suspend fun saveIdentity(teacherId: String, identity: TeacherIdentityInfo): AppResult<TeacherSetupState>
    suspend fun saveSubjectsGrades(teacherId: String, subjectsGrades: TeacherSubjectsGrades): AppResult<TeacherSetupState>
    suspend fun saveQualifications(teacherId: String, qualifications: List<TeacherQualification>): AppResult<TeacherSetupState>
    suspend fun saveExperience(teacherId: String, experience: TeacherExperienceInfo): AppResult<TeacherSetupState>
    suspend fun saveDocuments(teacherId: String, documents: List<TeacherSetupDocument>): AppResult<TeacherSetupState>
    suspend fun savePricing(teacherId: String, pricing: TeacherPricingInfo): AppResult<TeacherSetupState>
    suspend fun saveVoiceSample(teacherId: String, voiceSample: TeacherVoiceSample): AppResult<TeacherSetupState>

    /**
     * Fails with [com.rork.eduspark.core.result.AppError.Validation] if Identity or Subjects &
     * Grades were never saved with real content (a non-blank display name; at least one
     * subject and one grade) — this never silently completes a required step the teacher
     * skipped. Every other step may stay empty and setup still finishes.
     */
    suspend fun finishSetup(teacherId: String): AppResult<TeacherSetupState>

    /** TC-02. Only ever called once setup is complete. */
    suspend fun getDashboard(teacherId: String): AppResult<TeacherDashboardSummary>

    /** TC-03. */
    suspend fun getCourses(teacherId: String): AppResult<List<TeacherCourseSummary>>

    /** TC-04. Same [com.rork.eduspark.data.model.TeacherCourseSummary] rows [getCourses] returns, looked up by id. */
    suspend fun getCourse(courseId: String): AppResult<TeacherCourseSummary>

    /** TC-04. Ordered by [com.rork.eduspark.data.model.TeacherLesson.order]. */
    suspend fun getLessons(courseId: String): AppResult<List<TeacherLesson>>

    suspend fun getLesson(courseId: String, lessonId: String): AppResult<TeacherLesson>

    /** TC-04 drag reorder. [orderedLessonIds] is the new top-to-bottom order for every lesson currently in [courseId] — reassigns [com.rork.eduspark.data.model.TeacherLesson.order] and persists it. */
    suspend fun reorderLessons(courseId: String, orderedLessonIds: List<String>): AppResult<List<TeacherLesson>>

    /** TC-05. The in-flight upload for [courseId], or null if none is running — the screen's own "resume where I left off" read. */
    suspend fun getUploadDraft(courseId: String): AppResult<TeacherLessonUploadDraft?>

    /**
     * TC-05. Starts a fresh mock upload for [courseId], replacing any prior draft for the same
     * course. Progress lives entirely in the returned/stored
     * [com.rork.eduspark.data.model.TeacherLessonUploadDraft] from this call onward — see that
     * model's own doc comment for why the ViewModel is never the source of truth for it.
     */
    suspend fun startLessonUpload(
        courseId: String,
        contentType: LessonContentType,
        mockFileName: String,
        mockTotalBytes: Long,
        title: String,
        order: Int,
        generateQuiz: Boolean,
        generateNarration: Boolean,
        indexForTutor: Boolean,
    ): AppResult<TeacherLessonUploadDraft>

    /** TC-05. Advances the in-flight upload by one deterministic chunk; a no-op success once already [com.rork.eduspark.data.model.LessonUploadStage.Completed]. */
    suspend fun advanceLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft>

    suspend fun pauseLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft>
    suspend fun resumeLessonUpload(courseId: String): AppResult<TeacherLessonUploadDraft>

    /** TC-05 Cancel. Discards the draft outright — since no lesson exists until upload completes, this never leaves a phantom Processing lesson behind. */
    suspend fun cancelLessonUpload(courseId: String): AppResult<Unit>

    /** TC-06. */
    suspend fun getLessonProcessingState(lessonId: String): AppResult<TeacherLessonProcessingState>

    /** TC-06. Resolves whichever stage is currently [com.rork.eduspark.data.model.LessonProcessingStageStatus.Running] to Complete or (deterministically, at most once per lesson) Failed, then starts the next pending stage. Once every relevant stage is complete, also flips the owning [com.rork.eduspark.data.model.TeacherLesson.status] to Published — the one place that happens. */
    suspend fun advanceLessonProcessing(lessonId: String): AppResult<TeacherLessonProcessingState>

    /** TC-06 Retry. Only valid while the pipeline is [com.rork.eduspark.data.model.LessonProcessingOverallStatus.Failed]; always succeeds on the next [advanceLessonProcessing] call. */
    suspend fun retryLessonProcessing(lessonId: String): AppResult<TeacherLessonProcessingState>

    /** TC-07/TC-08. Never null — an untouched Draft lesson gets a blank [TeacherLessonEditorState], the same "seed a blank record on first read" convention [getSetupState] already uses. */
    suspend fun getLessonEditorState(courseId: String, lessonId: String): AppResult<TeacherLessonEditorState>

    /** TC-07 · Lesson Content section's explicit Save. */
    suspend fun saveExtractedText(courseId: String, lessonId: String, text: String): AppResult<TeacherLessonEditorState>

    /** TC-07 · Chunks section — the full replacement list, covering plain edits, split and merge alike; ordering is reassigned from list position, never trusted from the caller. */
    suspend fun saveChunks(courseId: String, lessonId: String, chunks: List<TeacherLessonChunk>): AppResult<TeacherLessonEditorState>

    /** TC-07. Replaces one generated question's [QuizQuestion] content in place; leaves its [AiReviewStatus] untouched — see [TeacherGeneratedQuestion]'s own doc comment for why an edit never resets review state. */
    suspend fun saveGeneratedQuestionEdit(courseId: String, lessonId: String, questionId: String, edited: QuizQuestion): AppResult<TeacherLessonEditorState>

    suspend fun reviewGeneratedQuestion(courseId: String, lessonId: String, questionId: String, status: AiReviewStatus): AppResult<TeacherLessonEditorState>

    suspend fun reviewInsight(courseId: String, lessonId: String, insightId: String, status: AiReviewStatus): AppResult<TeacherLessonEditorState>

    /**
     * TC-07 Publish. Re-checks [TeacherLessonEditorState]'s own gate server-side (same
     * "never trust the client's own gate check alone" discipline [finishSetup] already uses)
     * and, only once it passes, flips the lesson to Published — the one place that happens for
     * a Draft lesson, mirroring [advanceLessonProcessing]'s Publish for a Processing one.
     */
    suspend fun submitLessonForPublish(courseId: String, lessonId: String): AppResult<TeacherLesson>

    /**
     * TC-09 · Voice Profile. Never null — an untouched teacher gets a blank
     * [TeacherVoiceProfile], same convention as [getLessonEditorState]. Kept in sync with
     * [TeacherSetupState.voiceSample] (TC-01) by [saveVoiceSample]'s own implementation — see
     * [TeacherVoiceProfile]'s own doc comment for why these are one source of truth, not two.
     */
    suspend fun getVoiceProfile(teacherId: String): AppResult<TeacherVoiceProfile>

    suspend fun setVoiceConsent(teacherId: String, granted: Boolean): AppResult<TeacherVoiceProfile>

    /** Deterministic MOCK fixture per [sourceType] — alternates good/needs-improvement quality across successive samples, see [com.rork.eduspark.data.repository.mock.MockTeacherRepository]'s own doc comment. */
    suspend fun addVoiceSample(teacherId: String, sourceType: VoiceSampleSourceType): AppResult<TeacherVoiceProfile>

    suspend fun removeVoiceSample(teacherId: String, sampleId: String): AppResult<TeacherVoiceProfile>

    /** Generate and Regenerate are the same call. Deterministically fails the first time a profile is generated, then always succeeds once retried — never a real cloning pipeline. */
    suspend fun generateVoiceProfile(teacherId: String): AppResult<TeacherVoiceProfile>

    /** Fails with [com.rork.eduspark.core.result.AppError.Validation] if consent or a Ready profile is missing — the same defensive re-check [finishSetup] uses, never trusting the toggle's own enabled/disabled UI state alone. */
    suspend fun setClonedNarrationEnabled(teacherId: String, enabled: Boolean): AppResult<TeacherVoiceProfile>

    /** TC-10. Every quiz across every course this teacher owns — the screen groups/filters by course itself, the same "load once, filter locally" shape [getCourses] already established for TC-03. */
    suspend fun getQuizzes(teacherId: String): AppResult<List<TeacherQuiz>>

    suspend fun getQuiz(quizId: String): AppResult<TeacherQuiz>

    /** TC-10 Create quiz. Starts a blank [com.rork.eduspark.data.model.TeacherQuizStatus.Draft] quiz for [courseId] and returns its new id. */
    suspend fun createQuiz(courseId: String): AppResult<TeacherQuiz>

    suspend fun saveQuizMetadata(
        quizId: String,
        title: String,
        instructions: String,
        durationMinutes: Int? = 15,
        passMarkPercent: Int = 60,
        singleAttempt: Boolean = true,
    ): AppResult<TeacherQuiz>

    /** TC-10 · question add/edit/delete/duplicate/reorder all funnel through one full-list replace — same "whole list, order reassigned from position" shape [reorderLessons]/[saveChunks] already use, so there is only ever one place question order is written. */
    suspend fun saveQuizQuestions(quizId: String, questions: List<TeacherQuizQuestion>): AppResult<TeacherQuiz>

    /**
     * TC-10 Publish. Re-checks the same gate TC-10 itself shows client-side — never trusting
     * the client's own check alone, the same discipline [finishSetup]/[submitLessonForPublish]
     * already use.
     */
    suspend fun publishQuiz(quizId: String): AppResult<TeacherQuiz>

    /** TC-10 AI bulk import. A deterministic MOCK fixture set, never a real generation call — every returned question already has [com.rork.eduspark.data.model.TeacherQuizQuestion.isAiOrigin] = true. */
    suspend fun generateAiQuizQuestionCandidates(quizId: String): AppResult<List<TeacherQuizQuestion>>

    /** TC-11. Every attempt (including [com.rork.eduspark.data.model.TeacherQuizAttemptStatus.NotSubmitted] ones) for [quizId] — TC-11 derives every summary number from this same list, never a separately stored average. */
    suspend fun getQuizAttempts(quizId: String): AppResult<List<TeacherQuizAttempt>>

    /**
     * Teacher-manual essay grade on an existing [TeacherQuizAttempt]. Writes [assignedMark],
     * [feedback], and `pending=false` into that attempt's [com.rork.eduspark.data.model.TeacherEssayResponse]
     * — not a second grading store. Auto-scored questions are left untouched.
     */
    suspend fun saveEssayGrade(
        quizId: String,
        studentId: String,
        questionId: String,
        assignedMark: Int,
        feedback: String,
    ): AppResult<TeacherQuizAttempt>

    /** TC-12. [com.rork.eduspark.data.model.TeacherStudentSummary.studentId] values match [TeacherQuizAttempt.studentId] wherever the same fixture persona appears in both, so TC-11 and TC-12 never disagree about who a student is. */
    suspend fun getStudents(teacherId: String): AppResult<List<TeacherStudentSummary>>

    /** TC-13. The same [TeacherStudentSummary] row [getStudents] already returns, looked up by id — never a second, competing student record. */
    suspend fun getStudent(studentId: String): AppResult<TeacherStudentSummary>

    /** TC-13 attendance. Deterministic MOCK fixture per student — no real attendance system exists. */
    suspend fun getStudentAttendance(studentId: String): AppResult<TeacherStudentAttendance>

    /** TC-13 activity timeline. Quiz-submission entries are built from the same [TeacherQuizAttempt] data [getQuizAttempts] returns — see [TeacherActivityItem]'s own doc comment. */
    suspend fun getStudentActivity(studentId: String): AppResult<List<TeacherActivityItem>>

    /** TC-13 private notes — newest first, never exposed to any student/parent-facing repository or screen. */
    suspend fun getPrivateNotes(studentId: String): AppResult<List<TeacherPrivateNote>>

    suspend fun addPrivateNote(studentId: String, text: String): AppResult<TeacherPrivateNote>

    suspend fun updatePrivateNote(noteId: String, text: String): AppResult<TeacherPrivateNote>

    suspend fun deletePrivateNote(noteId: String): AppResult<Unit>

    /** TC-13 "Send note to parent" — a mock send, distinct from [addPrivateNote]; see [TeacherParentNote]'s own doc comment. */
    suspend fun sendParentNote(studentId: String, message: String): AppResult<TeacherParentNote>

    /** Reads the mock parent-note list [sendParentNote] already appends — no second store. */
    suspend fun getParentNotes(studentId: String): AppResult<List<TeacherParentNote>>

    /** TC-13 teacher→student message action — an honest mock composer/send, never a real chat thread or push notification. */
    suspend fun sendStudentMessage(studentId: String, message: String): AppResult<Unit>

    /**
     * TC-14. Every student enrolled in [courseId] gets a row — an untouched student's entry is
     * a blank [TeacherGradeEntry] (courseworkScore null, [com.rork.eduspark.data.model.GradePublicationStatus.Draft]),
     * the same "seed a blank record on first read" convention [getLessonEditorState] already uses.
     */
    suspend fun getGradebook(courseId: String): AppResult<List<TeacherGradeEntry>>

    /** TC-14 grade entry/adjustment. [courseworkScore] must already be validated 0-100 by the caller; this never silently clamps an out-of-range value. */
    suspend fun saveGradeEntry(studentId: String, courseId: String, courseworkScore: Int?, comment: String): AppResult<TeacherGradeEntry>

    suspend fun publishGrade(studentId: String, courseId: String): AppResult<TeacherGradeEntry>

    /** TC-14 bulk publish — every current [com.rork.eduspark.data.model.GradePublicationStatus.Draft] entry in [courseId] becomes Published; the screen gates this behind its own confirmation. */
    suspend fun publishCourseGrades(courseId: String): AppResult<List<TeacherGradeEntry>>

    /**
     * TC-15. [courseId] null means "every course"; [com.rork.eduspark.data.model.TeacherAnalyticsSnapshot]
     * is computed fresh from the same roster/quiz-attempt/attendance fixtures TC-12/TC-11/TC-13
     * already read — never a separately hand-picked set of numbers.
     */
    suspend fun getAnalyticsSnapshot(teacherId: String, courseId: String?, period: AnalyticsPeriod): AppResult<TeacherAnalyticsSnapshot>

    // ── TC-17 · Project Authoring ────────────────────────────────────────────────────────────

    /** TC-17. Every project this teacher has authored — Draft and Published alike. */
    suspend fun getTeacherProjects(teacherId: String): AppResult<List<TeacherProject>>

    suspend fun getTeacherProject(projectId: String): AppResult<TeacherProject>

    /** TC-17 Create project. Starts a blank [com.rork.eduspark.data.model.TeacherProjectStatus.Draft] project for [courseId]. */
    suspend fun createTeacherProject(courseId: String): AppResult<TeacherProject>

    suspend fun saveTeacherProjectMetadata(
        projectId: String,
        title: String,
        description: String,
        deliverable: String,
        teamSize: Int,
        medium: ProjectMedium,
    ): AppResult<TeacherProject>

    /** TC-17 · milestone/task add/edit/delete/reorder all funnel through one full-tree replace — same "whole list, order reassigned from position" shape [saveQuizQuestions]/[reorderLessons] already use. */
    suspend fun saveTeacherProjectMilestones(projectId: String, milestones: List<TeacherProjectMilestone>): AppResult<TeacherProject>

    suspend fun saveTeacherProjectRubric(projectId: String, rubric: List<TeacherProjectRubricCriterion>): AppResult<TeacherProject>

    suspend fun saveTeacherProjectMaterials(projectId: String, materials: List<TeacherProjectMaterial>, safetyNotes: List<TeacherProjectSafetyNote>): AppResult<TeacherProject>

    suspend fun saveTeacherProjectMedia(projectId: String, media: List<TeacherProjectMediaItem>): AppResult<TeacherProject>

    /** TC-17 Publish. Re-checks the same gate TC-17 itself shows client-side — never trusting the client's own check alone, the same discipline [publishQuiz]/[submitLessonForPublish] already use. */
    suspend fun publishTeacherProject(projectId: String): AppResult<TeacherProject>

    // ── TC-18 · Project Review Queue ─────────────────────────────────────────────────────────

    /** TC-18. Every submission across every [TeacherProject] this teacher owns. */
    suspend fun getReviewQueue(teacherId: String): AppResult<List<TeacherProjectSubmission>>

    /** TC-18. Opening a still-[com.rork.eduspark.data.model.ProjectReviewStatus.AwaitingReview] submission moves it to [com.rork.eduspark.data.model.ProjectReviewStatus.InReview] — the one place that transition happens. */
    suspend fun getReviewSubmission(submissionId: String): AppResult<TeacherProjectSubmission>

    /** TC-18. Sets or clears this criterion's teacher-confirmed score; null [teacherScore] is never valid here — pass the AI suggestion itself to "confirm as-is". */
    suspend fun saveCriterionOverride(submissionId: String, criterionId: String, teacherScore: Int): AppResult<TeacherProjectSubmission>

    suspend fun saveReviewFeedback(submissionId: String, teacherFeedback: String, teacherPrivateComment: String): AppResult<TeacherProjectSubmission>

    /**
     * TC-18 Finalize. Any criterion still missing a teacher-confirmed score is filled with its
     * AI suggestion first (an explicit "confirm the rest as-is", never a silent default), then
     * [com.rork.eduspark.data.model.ProjectReviewStatus.Reviewed] is set — the one place that
     * happens, after which [TeacherProjectSubmission.finalScore] is always non-null.
     */
    suspend fun finalizeReview(submissionId: String): AppResult<TeacherProjectSubmission>
}

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-01 · Messages List / X-02 · Conversation Thread / X-03 · New Conversation — Phase 6.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One repository, one canonical MOCK thread store, shared by Student and Teacher sessions
 * alike — never a per-screen fixture. Same "no cross-repository dependency, every method
 * keyed by an explicit id" boundary [TeacherRepository] already keeps: nothing here reads
 * [AuthRepository.session] itself — the caller (a ViewModel, which already holds
 * [AuthRepository]) resolves who is asking and passes that id in.
 *
 * [getPermittedContacts] for a Teacher includes roster students plus any seeded Parent
 * counterparts. Parent threads live in the same [threads] store.
 */
interface MessagingRepository {

    /** Every canonical thread, both roles, unfiltered — a ViewModel derives its own filtered/sorted view via [MessageThread.involves]. Hot; survives navigation/recreation. */
    val threads: Flow<List<MessageThread>>

    suspend fun getThreads(): AppResult<List<MessageThread>>

    suspend fun getThread(threadId: String): AppResult<MessageThread>

    /** Who [viewerId] is permitted to start a new conversation with — Student↔their teacher, Teacher↔their students. */
    suspend fun getPermittedContacts(viewerId: String, viewerRole: MessageParticipantRole): AppResult<List<MessageParticipant>>

    /** Existing-thread-first: returns [contactId]'s thread with [viewerId], creating one only if none exists yet — never a duplicate. */
    suspend fun openOrCreateThread(
        viewerId: String,
        viewerRole: MessageParticipantRole,
        contactId: String,
    ): AppResult<MessageThread>

    /**
     * The Teacher↔Parent thread linked to [studentId], if one exists in the mock store.
     * Does not create a parent — only ريم has a seeded parent conversation.
     */
    suspend fun getParentThreadForStudent(teacherId: String, studentId: String): AppResult<MessageThread>

    suspend fun sendMessage(
        threadId: String,
        senderId: String,
        body: String,
        attachment: MessageAttachment? = null,
    ): AppResult<MessagingChatMessage>

    /** Marks every message [viewerId] did not send as read — reflected immediately in [threads]. */
    suspend fun markThreadRead(threadId: String, viewerId: String): AppResult<Unit>
}

/**
 * X-04 · Student notifications. In-app only in this batch: no push token, no FCM/APNs, and
 * message notifications deep-link into the canonical [MessagingRepository] thread.
 */
interface NotificationRepository {
    val notifications: Flow<List<StudentNotification>>

    suspend fun markRead(notificationId: String): AppResult<StudentNotification>

    suspend fun markAllRead(): AppResult<Unit>
}

/**
 * Single source of truth for "does this part of the product have a backend yet".
 *
 * Screens read this instead of hard-coding assumptions, so a pending feature can present
 * an honest state rather than a fabricated one, and flipping it on later is one edit.
 */
object FeatureAvailability {
    /** Projects module (PJ-01…PJ-12) — no endpoints, no tables. Mock data only. */
    const val PROJECTS_BACKEND_READY = false

    /** Push notifications — in-app only today; no FCM/APNs registration exists. */
    const val PUSH_BACKEND_READY = false

    /** Real payment rails — only a demo checkout exists. */
    const val PAYMENTS_BACKEND_READY = false

    /** Offline bootstrap/push sync endpoints — planned, not built. */
    const val SYNC_ENDPOINTS_READY = false

    /** Token refresh — no endpoint exists; 401 always means re-login. */
    const val TOKEN_REFRESH_READY = false
}
