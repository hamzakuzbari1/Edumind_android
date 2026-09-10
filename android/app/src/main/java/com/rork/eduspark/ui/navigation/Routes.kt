package com.rork.eduspark.ui.navigation

import android.net.Uri
import androidx.annotation.StringRes
import com.rork.eduspark.core.locale.AppLocale
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CalendarViewWeek
import androidx.compose.material.icons.filled.Class
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.CalendarViewWeek
import androidx.compose.material.icons.outlined.Class
import androidx.compose.material.icons.outlined.CreditCard
import androidx.compose.material.icons.outlined.EmojiEvents
import androidx.compose.material.icons.outlined.EventNote
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Insights
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Forum
import androidx.compose.material.icons.outlined.Quiz
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.SupervisorAccount
import androidx.compose.material.icons.outlined.Translate
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.ui.graphics.vector.ImageVector
import com.rork.eduspark.R

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Navigation graph — route constants.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Structure mirrors the Screen Inventory exactly: one auth graph plus three role graphs,
 * each role graph owning its own five-tab shell.
 *
 * Screens themselves are NOT built yet (foundation phase). Every destination below is
 * declared so the shape of the app is real and reviewable, and each one currently renders
 * an honest placeholder naming its screen ID and phase.
 */
object Routes {

    // ── Root ──────────────────────────────────────────────────────────────
    const val FOUNDATION = "foundation"

    // ── Auth graph (Phase 0) ──────────────────────────────────────────────
    const val AUTH_GRAPH = "auth"
    const val SPLASH = "auth/splash"                    // A-01
    const val VALUE_CAROUSEL = "auth/carousel"          // A-02
    const val ROLE_SELECT = "auth/role"                 // A-03
    const val LOGIN = "auth/login"                      // A-04
    const val REGISTER_STUDENT = "auth/register/student" // A-05
    const val REGISTER_PARENT = "auth/register/parent"   // A-06
    const val REGISTER_TEACHER = "auth/register/teacher" // A-07

    // A-08 and A-09 both need the email the previous screen was working with (Register's
    // new address, or Login's unverified/2FA-pending one), so the route carries it as an
    // argument rather than relying on a shared ViewModel or global state to smuggle it across.
    private const val EMAIL_ARG = "email"
    const val VERIFY_EMAIL = "auth/verify-email/{$EMAIL_ARG}" // A-08 — route pattern
    const val TWO_FACTOR = "auth/two-factor/{$EMAIL_ARG}"     // A-09 — route pattern
    fun verifyEmailRoute(email: String) = "auth/verify-email/${Uri.encode(email)}"
    fun twoFactorRoute(email: String) = "auth/two-factor/${Uri.encode(email)}"

    const val FORGOT_PASSWORD = "auth/forgot" // A-10 — no arguments

    // A-11 — token is required; email is optional context carried from A-10's hand-off or a
    // deep link that included it. Absent, the screen falls back to generic copy rather than
    // fabricating an address (see ResetPasswordScreen).
    private const val TOKEN_ARG = "token"
    const val RESET_PASSWORD = "auth/reset?$TOKEN_ARG={$TOKEN_ARG}&$EMAIL_ARG={$EMAIL_ARG}" // A-11 pattern
    fun resetPasswordRoute(token: String, email: String = "") =
        "auth/reset?$TOKEN_ARG=${Uri.encode(token)}&$EMAIL_ARG=${Uri.encode(email)}"

    // A-12 — public, no auth, deep-linked. Outside every graph — see AppNavigation.
    private const val CODE_ARG = "code"
    const val CERTIFICATE_VERIFY = "certificate/verify/{$CODE_ARG}" // A-12 pattern
    fun certificateVerifyRoute(code: String) = "certificate/verify/${Uri.encode(code)}"

    // A-13 — the target locale to switch to.
    private const val LOCALE_ARG = "locale"
    const val LOCALE_SWITCH = "auth/locale-switch/{$LOCALE_ARG}" // A-13 pattern
    fun localeSwitchRoute(locale: AppLocale) = "auth/locale-switch/${locale.tag}"

    // ── Student Onboarding (SO-01…SO-05) — isolated from Student Core ──────
    // A verified student with no completed onboarding lands here instead of STUDENT_GRAPH;
    // Teacher and Parent never enter it. All five routes share one graph-scoped ViewModel
    // (see AppNavigation's onboardingGraph), so back navigation preserves every selection
    // without any of the screens knowing about persistence.
    const val ONBOARDING_GRAPH = "onboarding"
    const val SO_GRADE = "onboarding/grade"             // SO-01
    const val SO_SUBJECTS = "onboarding/subjects"       // SO-02
    const val SO_TEACHERS = "onboarding/teachers"       // SO-03
    const val SO_PERSONALIZE = "onboarding/personalize" // SO-04
    const val SO_COMPLETE = "onboarding/complete"       // SO-05

    // ── Student graph (Phase 1) ───────────────────────────────────────────
    const val STUDENT_GRAPH = "student"
    const val STUDENT_HOME = "student/home"
    const val STUDENT_COURSES = "student/courses"
    const val STUDENT_PROJECTS = "student/projects"
    const val STUDENT_ENGLISH = "student/english"
    const val STUDENT_ME = "student/me"

    // ST-02 — pushed above the tab bar (no tabs visible), a sibling of STUDENT_HOME within
    // STUDENT_GRAPH rather than nested inside RoleShell's own tab-scoped NavHost, because
    // the anchor shows Course Detail with its own back arrow and no bottom tabs at all.
    private const val COURSE_ID_ARG = "courseId"
    const val STUDENT_COURSE_DETAIL = "student/course/{$COURSE_ID_ARG}" // ST-02 — route pattern
    fun studentCourseDetailRoute(courseId: String) = "student/course/${Uri.encode(courseId)}"

    // ST-03 — lessonId identifies which LearningStep to render; ST-02's sticky Continue bar
    // and any tappable current/completed lesson row both carry it.
    private const val LESSON_ID_ARG = "lessonId"
    const val STUDENT_LESSON = "student/lesson/{$LESSON_ID_ARG}" // ST-03 — route pattern
    fun studentLessonRoute(lessonId: String) = "student/lesson/${Uri.encode(lessonId)}"

    // ST-06 · Quiz Runner / ST-08 · Remedial Quiz / ST-09 · Manual Quiz Runner — one route
    // pattern, one screen (QuizRunnerScreen); a quiz has its own identity independent of any
    // lesson (a manual/course quiz is not lesson-scoped at all), so this is keyed by quizId,
    // not lessonId. ST-08's remedial quiz and ST-09's manual quiz are just quiz ids fetched
    // through the same repository — no separate route pattern needed for either.
    private const val QUIZ_ID_ARG = "quizId"
    const val STUDENT_QUIZ = "student/quiz/{$QUIZ_ID_ARG}" // ST-06/08/09 — route pattern
    fun studentQuizRoute(quizId: String) = "student/quiz/${Uri.encode(quizId)}"

    // ST-07 — reached by submitting the last question of any quiz in STUDENT_QUIZ.
    const val STUDENT_QUIZ_RESULTS = "student/quiz/{$QUIZ_ID_ARG}/results" // route pattern
    fun studentQuizResultsRoute(quizId: String) = "student/quiz/${Uri.encode(quizId)}/results"

    // ST-04 · AI Tutor Chat / ST-05 · AI Tutor Voice Mode — one small nested graph so both
    // share the same TutorChatViewModel instance (same mechanism as ONBOARDING_GRAPH): a
    // voice exchange in ST-05 must still be in the transcript when the student backs out to
    // ST-04, which only works if both screens resolve one shared, graph-scoped ViewModel.
    const val TUTOR_GRAPH = "student/tutor"
    // Optional query arg — a contextual prompt carried in from a lesson concept action (ST-03)
    // or a mistake-review "Ask Tutor" tap (ST-07). Absent for the plain "Ask Tutor" entry point,
    // which still opens to an empty transcript exactly as before.
    const val TUTOR_PROMPT_ARG = "prompt"
    const val TUTOR_CHAT = "student/tutor/chat/{$LESSON_ID_ARG}?$TUTOR_PROMPT_ARG={$TUTOR_PROMPT_ARG}" // ST-04 — route pattern
    const val TUTOR_VOICE = "student/tutor/voice/{$LESSON_ID_ARG}" // ST-05 — route pattern
    fun tutorChatRoute(lessonId: String, prompt: String? = null): String {
        val base = "student/tutor/chat/${Uri.encode(lessonId)}"
        return if (prompt.isNullOrBlank()) base else "$base?$TUTOR_PROMPT_ARG=${Uri.encode(prompt)}"
    }
    fun tutorVoiceRoute(lessonId: String) = "student/tutor/voice/${Uri.encode(lessonId)}"

    // ST-10 · Planner / ST-11 · Planner AI Chat — no arguments for either: the week plan and
    // the chat are both single, student-scoped resources (PlannerRepository already knows
    // who's asking, same as LearningRepository's ST-01 methods), not per-id destinations.
    const val STUDENT_PLANNER = "student/planner"       // ST-10
    const val STUDENT_PLANNER_CHAT = "student/planner/chat" // ST-11

    // ST-12 · Routine Builder / ST-13 · Routine Week View — same "no arguments, one
    // student-scoped resource" reasoning as the Planner pair above. Routine and Planner are
    // deliberately separate route families, not variants of one another.
    const val STUDENT_ROUTINE_BUILDER = "student/routine/builder" // ST-12
    const val STUDENT_ROUTINE = "student/routine"                  // ST-13

    // ST-14 · Exam Schedule Capture — also no arguments; ExamRepository is the single
    // student-scoped resource, same shape as everything else in this group.
    const val STUDENT_EXAM_CAPTURE = "student/exam-capture" // ST-14

    // ST-15 · Achievements / ST-16 · Subscriptions — reached from the STUDENT_ME tab's account
    // hub, not the bottom nav itself; no arguments, same "single student-scoped resource" shape.
    const val STUDENT_ACHIEVEMENTS = "student/achievements" // ST-15
    const val STUDENT_SUBSCRIPTIONS = "student/subscriptions" // ST-16

    // ST-17 · Course Paywall Sheet — courseId-scoped, same shape as STUDENT_COURSE_DETAIL.
    // Pushed (not a dialog/overlay) so ST-18's "back → ST-17" is a plain backstack pop; its
    // own screen styles itself as a sheet (rounded top, dismiss handle) rather than reusing
    // EduScaffold's title-bar chrome, since there is no bottom-sheet-as-destination mechanism
    // anywhere else in this nav graph to reuse instead.
    const val STUDENT_PAYWALL = "student/paywall/{$COURSE_ID_ARG}" // ST-17 — route pattern
    fun studentPaywallRoute(courseId: String) = "student/paywall/${Uri.encode(courseId)}"

    // ST-18 · Payment Method Select — same courseId; PAYMENT_MODE is "direct" so there is no
    // gateway/session id to carry, only the course this attempt is for.
    const val STUDENT_PAYMENT_METHOD = "student/payment/method/{$COURSE_ID_ARG}" // ST-18 — route pattern
    fun studentPaymentMethodRoute(courseId: String) = "student/payment/method/${Uri.encode(courseId)}"

    // ST-19 · Payment Pending — courseId + the method chosen on ST-18, so ST-19 can build the
    // same PaymentRequest ST-18 would have without a third repository field just to carry a
    // draft between two screens. PaymentRepository.pendingPayment (a hot flow, same shape as
    // PlannerRepository.weekPlan) is what actually survives navigating away and back.
    private const val PAYMENT_METHOD_ID_ARG = "paymentMethodId"
    const val STUDENT_PAYMENT_PENDING = "student/payment/pending/{$COURSE_ID_ARG}/{$PAYMENT_METHOD_ID_ARG}" // ST-19 — route pattern
    fun studentPaymentPendingRoute(courseId: String, methodId: String) =
        "student/payment/pending/${Uri.encode(courseId)}/${Uri.encode(methodId)}"

    // ST-20 · Purchase Success — courseId-scoped; reached only for a course whose payment is
    // already Verified (see PaymentRepository.getPurchaseAccess's own doc comment), never
    // pushed automatically from ST-19 on a timer.
    const val STUDENT_PURCHASE_SUCCESS = "student/purchase-success/{$COURSE_ID_ARG}" // ST-20 — route pattern
    fun studentPurchaseSuccessRoute(courseId: String) = "student/purchase-success/${Uri.encode(courseId)}"

    // ST-21 · Voucher Redeem — no arguments; the code itself determines which course it grants,
    // reachable from both the paywall (ST-17) and Subscriptions (ST-16), never nested inside
    // Payment Method Select as a third method.
    const val STUDENT_VOUCHER_REDEEM = "student/voucher"

    // ST-22 · Student Profile has no route of its own — the numbering-collision decision for
    // this slice is that ST-22 IS the STUDENT_ME tab (see StudentProfileScreen's own doc
    // comment); creating a second pushed destination for it would be the "second ST-22" this
    // slice was explicitly told not to create.

    // ST-23 · Settings — Account / ST-24 · Settings — Security — both no-argument, single
    // student-scoped resources, reached only from the STUDENT_ME tab's own links section.
    const val STUDENT_ACCOUNT_SETTINGS = "student/settings/account" // ST-23
    const val STUDENT_SECURITY_SETTINGS = "student/settings/security" // ST-24

    // ST-25 · Settings — Language & Display / ST-26 · Settings — Notifications — same shape,
    // also reached only from the STUDENT_ME tab's links section. The final Student Core slice.
    const val STUDENT_LANGUAGE_DISPLAY = "student/settings/language" // ST-25
    const val STUDENT_NOTIFICATIONS = "student/settings/notifications" // ST-26

    // Learning Preferences — new, proposed extension of ST-22 (approved design:
    // LearningPreferences.dc.html). Same "no-argument, single student-scoped resource" shape
    // as ST-23…ST-26 above, reached only from the STUDENT_ME tab's own links section.
    const val STUDENT_LEARNING_PREFERENCES = "student/settings/learning-preferences"
    const val STUDENT_PARENT_LINKING = "student/parent-linking"

    // ── Phase 2 · Projects ─────────────────────────────────────────────────
    // PJ-01 has no route of its own — it IS the existing STUDENT_PROJECTS tab (same
    // "override an existing tab root" mechanism ST-01/ST-22 already use), never a new
    // bottom-navigation destination.
    private const val PROJECT_ID_ARG = "projectId"

    // PJ-02 · Project Detail — reached only from PJ-01's Discover list.
    const val STUDENT_PROJECT_DETAIL = "student/project/{$PROJECT_ID_ARG}" // route pattern
    fun studentProjectDetailRoute(projectId: String) = "student/project/${Uri.encode(projectId)}"

    // PJ-03 · Milestone Board — reached from PJ-01's My Projects, or from PJ-02 after
    // starting a solo project. Same courseId-style single-arg shape as STUDENT_COURSE_DETAIL.
    const val STUDENT_MILESTONE_BOARD = "student/project/{$PROJECT_ID_ARG}/board" // route pattern
    fun studentMilestoneBoardRoute(projectId: String) = "student/project/${Uri.encode(projectId)}/board"

    private const val TASK_ID_ARG = "taskId"

    // PJ-04 · Task Detail — reached only from a task tap on PJ-03.
    const val STUDENT_TASK_DETAIL = "student/project/{$PROJECT_ID_ARG}/task/{$TASK_ID_ARG}" // route pattern
    fun studentTaskDetailRoute(projectId: String, taskId: String) =
        "student/project/${Uri.encode(projectId)}/task/${Uri.encode(taskId)}"

    // PJ-05 · Submission Composer — reached from PJ-04's Submit Work action, or PJ-06's Resubmit.
    const val STUDENT_SUBMISSION_COMPOSER = "student/project/{$PROJECT_ID_ARG}/task/{$TASK_ID_ARG}/submit" // route pattern
    fun studentSubmissionComposerRoute(projectId: String, taskId: String) =
        "student/project/${Uri.encode(projectId)}/task/${Uri.encode(taskId)}/submit"

    // PJ-06 · AI Review & Rubric — reached only after a successful PJ-05 submission.
    const val STUDENT_PROJECT_REVIEW = "student/project/{$PROJECT_ID_ARG}/task/{$TASK_ID_ARG}/review" // route pattern
    fun studentProjectReviewRoute(projectId: String, taskId: String) =
        "student/project/${Uri.encode(projectId)}/task/${Uri.encode(taskId)}/review"

    // PJ-07 · Peer Review — no arguments; this slice has exactly one deterministic assignment,
    // not a per-task queue, so there is nothing to key the route on.
    const val STUDENT_PEER_REVIEW = "student/peer-review"

    // PJ-08 · Team Workspace — reached from a Team-mode project's PJ-03; keyed by projectId,
    // same single-arg shape as STUDENT_MILESTONE_BOARD.
    const val STUDENT_TEAM_WORKSPACE = "student/project/{$PROJECT_ID_ARG}/team" // route pattern
    fun studentTeamWorkspaceRoute(projectId: String) = "student/project/${Uri.encode(projectId)}/team"

    // PJ-09 · Reflection Log — reached from a completed/current milestone's contextual action
    // on PJ-03; keyed by both ids, since a reflection belongs to one milestone of one project.
    private const val MILESTONE_ID_ARG = "milestoneId"
    const val STUDENT_REFLECTION_LOG = "student/project/{$PROJECT_ID_ARG}/milestone/{$MILESTONE_ID_ARG}/reflection" // route pattern
    fun studentReflectionLogRoute(projectId: String, milestoneId: String) =
        "student/project/${Uri.encode(projectId)}/milestone/${Uri.encode(milestoneId)}/reflection"

    // PJ-10 · Project Portfolio — no arguments; the one showcase, reached from PJ-01.
    const val STUDENT_PORTFOLIO = "student/portfolio"

    // PJ-10 · Project Showcase Detail — keyed by projectId, same single-arg shape as
    // STUDENT_MILESTONE_BOARD; only ever resolves for a fully completed project.
    const val STUDENT_PROJECT_SHOWCASE_DETAIL = "student/portfolio/{$PROJECT_ID_ARG}" // route pattern
    fun studentProjectShowcaseDetailRoute(projectId: String) = "student/portfolio/${Uri.encode(projectId)}"

    // PJ-11 · Project Certificate — reached only from a completed project's showcase detail.
    const val STUDENT_PROJECT_CERTIFICATE = "student/portfolio/{$PROJECT_ID_ARG}/certificate" // route pattern
    fun studentProjectCertificateRoute(projectId: String) = "student/portfolio/${Uri.encode(projectId)}/certificate"

    // PJ-12 · Materials & Safety Sheet — reached from PJ-02's materials section (Physical
    // projects only); absent entirely for Digital-only projects.
    const val STUDENT_MATERIALS_SAFETY = "student/project/{$PROJECT_ID_ARG}/materials-safety" // route pattern
    fun studentMaterialsSafetyRoute(projectId: String) = "student/project/${Uri.encode(projectId)}/materials-safety"

    // TC-01 · Teacher Setup Wizard — outside every graph, same shape as ONBOARDING_GRAPH:
    // reached only right after auth for a Teacher session whose setup isn't done, with
    // nothing meaningful behind it in the back stack.
    const val TEACHER_SETUP = "teacher/setup"

    // ── Teacher graph (Phase 3) ───────────────────────────────────────────
    const val TEACHER_GRAPH = "teacher"
    const val TEACHER_DASHBOARD = "teacher/dashboard"
    const val TEACHER_COURSES = "teacher/courses"
    const val TEACHER_STUDENTS = "teacher/students"
    const val TEACHER_PROJECTS = "teacher/projects"
    const val TEACHER_ME = "teacher/me"

    // TC-04 · Course Detail — pushed above the tab bar, a sibling of the TEACHER_DASHBOARD tab
    // root within TEACHER_GRAPH, same shape as STUDENT_COURSE_DETAIL within STUDENT_GRAPH.
    // Reuses COURSE_ID_ARG — the same argument name, not a second "course id" concept.
    const val TEACHER_COURSE_DETAIL = "teacher/course/{$COURSE_ID_ARG}" // route pattern
    fun teacherCourseDetailRoute(courseId: String) = "teacher/course/${Uri.encode(courseId)}"

    // TC-05 · Lesson Upload — reached only from TC-04's Add Lesson action.
    const val TEACHER_LESSON_UPLOAD = "teacher/course/{$COURSE_ID_ARG}/lesson/upload" // route pattern
    fun teacherLessonUploadRoute(courseId: String) = "teacher/course/${Uri.encode(courseId)}/lesson/upload"

    // TC-06 · Lesson Processing Status — reached from TC-04 (a Processing lesson row), TC-05
    // (a finished mock upload) or TC-02's work queue (a lesson-linked failed item). Keyed by
    // both ids, same two-arg shape as STUDENT_TASK_DETAIL.
    const val TEACHER_LESSON_PROCESSING = "teacher/course/{$COURSE_ID_ARG}/lesson/{$LESSON_ID_ARG}/processing" // route pattern
    fun teacherLessonProcessingRoute(courseId: String, lessonId: String) =
        "teacher/course/${Uri.encode(courseId)}/lesson/${Uri.encode(lessonId)}/processing"

    // TC-07 · Lesson Editor — reached from TC-04's Draft lesson row.
    const val TEACHER_LESSON_EDITOR = "teacher/course/{$COURSE_ID_ARG}/lesson/{$LESSON_ID_ARG}/edit" // route pattern
    fun teacherLessonEditorRoute(courseId: String, lessonId: String) =
        "teacher/course/${Uri.encode(courseId)}/lesson/${Uri.encode(lessonId)}/edit"

    // TC-08 · Lesson Preview — reached from TC-04's Published lesson row, or from TC-07's own
    // Preview/Publish actions. Same two-arg shape; the screen itself derives "still Draft" vs
    // "Published" purely from the lesson's own current status, never a navigation-carried flag.
    const val TEACHER_LESSON_PREVIEW = "teacher/course/{$COURSE_ID_ARG}/lesson/{$LESSON_ID_ARG}/preview" // route pattern
    fun teacherLessonPreviewRoute(courseId: String, lessonId: String) =
        "teacher/course/${Uri.encode(courseId)}/lesson/${Uri.encode(lessonId)}/preview"

    // TC-09 · Voice Profile — no arguments; one profile per signed-in teacher. Canonical
    // access is the Account hub (حسابي → الصوت). The route is unchanged.
    const val TEACHER_VOICE_PROFILE = "teacher/voice-profile"

    // TC-10 · Quiz Builder — Teacher bottom navigation tab (الاختبارات). The same route
    // remains a pushed sibling of the tab shell for editor/results back-stack compatibility.
    const val TEACHER_QUIZZES = "teacher/quizzes"

    // Reuses QUIZ_ID_ARG — the same argument name ST-06's STUDENT_QUIZ already declared above.
    const val TEACHER_QUIZ_EDITOR = "teacher/quiz/{$QUIZ_ID_ARG}/edit" // route pattern
    fun teacherQuizEditorRoute(quizId: String) = "teacher/quiz/${Uri.encode(quizId)}/edit"

    // TC-11 · Quiz Results — reached only from a Published quiz's own Results action.
    const val TEACHER_QUIZ_RESULTS = "teacher/quiz/{$QUIZ_ID_ARG}/results" // route pattern
    fun teacherQuizResultsRoute(quizId: String) = "teacher/quiz/${Uri.encode(quizId)}/results"

    private const val TEACHER_STUDENT_ID_ARG = "studentId"
    private const val ESSAY_QUESTION_ID_ARG = "questionId"
    const val TEACHER_QUIZ_ESSAY_GRADE = "teacher/quiz/{$QUIZ_ID_ARG}/grade/{$TEACHER_STUDENT_ID_ARG}/{$ESSAY_QUESTION_ID_ARG}"
    fun teacherQuizEssayGradeRoute(quizId: String, studentId: String, questionId: String) =
        "teacher/quiz/${Uri.encode(quizId)}/grade/${Uri.encode(studentId)}/${Uri.encode(questionId)}"

    // TC-13 · Student Profile — Teacher View — reached from TC-12's student row tap (replacing
    // its former Coming Soon boundary) or from TC-15's at-risk list. A private student-id
    // argument name — deliberately not STUDENT_ID_ARG shared with anything else, since no
    // other Teacher route currently identifies a student by id.
    const val TEACHER_STUDENT_DETAIL = "teacher/student/{$TEACHER_STUDENT_ID_ARG}" // route pattern
    fun teacherStudentDetailRoute(studentId: String) = "teacher/student/${Uri.encode(studentId)}"

    const val TEACHER_PARENT_NOTE = "teacher/student/{$TEACHER_STUDENT_ID_ARG}/parent-note"
    fun teacherParentNoteRoute(studentId: String) = "teacher/student/${Uri.encode(studentId)}/parent-note"

    // TC-14 · Grades — no natural tab/existing route fits (Screen Inventory's Teacher tab bar
    // has no Grades slot either), so — same reasoning as TEACHER_VOICE_PROFILE/TEACHER_QUIZZES
    // above — this is reached via a link on TC-02 Dashboard, never a sixth bottom-nav tab.
    const val TEACHER_GRADES = "teacher/grades"

    // TC-15 · Teacher Analytics — same "Dashboard link, no new tab" reasoning as TC-14 above.
    const val TEACHER_ANALYTICS = "teacher/analytics"

    // TC-16 · Account hub lives on the existing TEACHER_ME tab. Edit Profile and Teaching Page
    // are pushed destinations that reuse the same Teacher setup/identity state.
    const val TEACHER_PROFILE_EDIT = "teacher/profile/edit"
    const val TEACHER_LIVE_PREVIEW = "teacher/profile/preview"

    // TC-17 · Project Authoring — TEACHER_PROJECTS itself becomes this slice's real content for
    // the existing tab root (same `overrides` mechanism as TC-16 above); the editor is a pushed
    // destination, parameterised by which project — reuses PROJECT_ID_ARG, the same argument
    // name the Student Projects graph already declared, not a second "project id" concept.
    const val TEACHER_PROJECT_EDITOR = "teacher/project/{$PROJECT_ID_ARG}/edit" // route pattern
    fun teacherProjectEditorRoute(projectId: String) = "teacher/project/${Uri.encode(projectId)}/edit"

    // TC-18 · Project Review Queue — reached from TC-17's project list/editor.
    const val TEACHER_REVIEW_QUEUE = "teacher/review-queue"

    private const val SUBMISSION_ID_ARG = "submissionId"
    const val TEACHER_REVIEW_DETAIL = "teacher/review/{$SUBMISSION_ID_ARG}" // route pattern
    fun teacherReviewDetailRoute(submissionId: String) = "teacher/review/${Uri.encode(submissionId)}"

    // ── Parent graph (Phase 4) ────────────────────────────────────────────
    const val PARENT_GRAPH = "parent"
    const val PARENT_HOME = "parent/home"
    const val PARENT_PROGRESS = "parent/progress"
    const val PARENT_REPORTS = "parent/reports"
    const val PARENT_MESSAGES = "parent/messages"
    const val PARENT_ME = "parent/me"
    const val PARENT_LINK_STUDENT = "parent/link-student"
    const val PARENT_PLANNER = "parent/home/planner"
    const val PARENT_ALERTS = "parent/home/alerts"
    const val PARENT_ATTENDANCE_STUDY_TIME = "parent/progress/attendance-study-time"
    const val PARENT_LESSON_PROGRESS = "parent/progress/lessons"
    const val PARENT_LESSON_DETAILS = "parent/progress/lessons/{$LESSON_ID_ARG}"
    fun parentLessonDetailsRoute(lessonId: String) = "parent/progress/lessons/${Uri.encode(lessonId)}"
    const val PARENT_SUBJECTS_TEACHERS = "parent/progress/subjects-teachers"

    // ── Cross-cutting (Phase 6) ───────────────────────────────────────────
    const val MESSAGES = "messages" // X-01 · Messages List
    const val NOTIFICATIONS = "notifications"

    // X-02 · Conversation Thread — reached only from X-01's own thread rows, or from X-03
    // after opening/creating one. Reused by every role; the screen resolves which side of the
    // thread the current viewer is on, never the route itself.
    private const val THREAD_ID_ARG = "threadId"
    const val MESSAGE_THREAD = "messages/thread/{$THREAD_ID_ARG}" // route pattern
    fun messageThreadRoute(threadId: String) = "messages/thread/${Uri.encode(threadId)}"

    // X-03 · New Conversation — reached only from X-01's own "new conversation" action.
    const val NEW_CONVERSATION = "messages/new"
}

/**
 * A bottom-tab destination.
 *
 * Labels are string resources, never literals — the tab bar is the first thing a user
 * sees in their language, and hard-coding it would break the "no literal user-facing
 * text" rule at the most visible point in the app.
 */
data class TabDestination(
    val route: String,
    @param:StringRes val labelRes: Int,
    val icon: ImageVector,
    val selectedIcon: ImageVector,
)

/** Student tabs — الرئيسية · روتيني · اللغات · مشاريعي · موادي · حسابي. */
val StudentTabs: List<TabDestination> = listOf(
    TabDestination(Routes.STUDENT_HOME, R.string.tab_student_home, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.STUDENT_ROUTINE, R.string.tab_student_routine, Icons.Outlined.CalendarViewWeek, Icons.Filled.CalendarViewWeek),
    TabDestination(Routes.STUDENT_ENGLISH, R.string.tab_student_english, Icons.Outlined.Language, Icons.Filled.Language),
    TabDestination(Routes.STUDENT_PROJECTS, R.string.tab_student_projects, Icons.Outlined.Build, Icons.Filled.Build),
    TabDestination(Routes.STUDENT_COURSES, R.string.tab_student_courses, Icons.Outlined.AutoStories, Icons.Filled.AutoStories),
    TabDestination(Routes.STUDENT_ME, R.string.tab_student_me, Icons.Outlined.Person, Icons.Filled.Person),
)

/**
 * Mobile drawer translation of Test-2SY's Student sidebar:
 * Journey/courses, Messages, Languages, Subscriptions, Routine, Planner,
 * Achievements, Profile, Settings. Projects remains because it is an approved Android module.
 */
val StudentDrawerSections: List<RoleDrawerSection> = listOf(
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.STUDENT_HOME, R.string.tab_student_home, Icons.Outlined.Home),
            RoleDrawerDestination(Routes.STUDENT_COURSES, R.string.tab_student_courses, Icons.Outlined.AutoStories),
            RoleDrawerDestination(Routes.STUDENT_PLANNER, R.string.st10_title, Icons.Outlined.EventNote),
            RoleDrawerDestination(Routes.STUDENT_ROUTINE, R.string.tab_student_routine, Icons.Outlined.CalendarViewWeek),
            RoleDrawerDestination(Routes.STUDENT_ENGLISH, R.string.tab_student_english, Icons.Outlined.Language),
            RoleDrawerDestination(Routes.STUDENT_PROJECTS, R.string.tab_student_projects, Icons.Outlined.Build),
            RoleDrawerDestination(Routes.STUDENT_SUBSCRIPTIONS, R.string.st16_title, Icons.Outlined.CreditCard),
        ),
    ),
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.STUDENT_ACHIEVEMENTS, R.string.st15_title, Icons.Outlined.EmojiEvents),
            RoleDrawerDestination(Routes.MESSAGES, R.string.topbar_messages, Icons.Outlined.Forum),
        ),
    ),
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.STUDENT_ME, R.string.tab_student_me, Icons.Outlined.Person),
            RoleDrawerDestination(Routes.STUDENT_PARENT_LINKING, R.string.st_parent_link_title, Icons.Outlined.SupervisorAccount),
            RoleDrawerDestination(Routes.STUDENT_LEARNING_PREFERENCES, R.string.st_lp_title, Icons.Outlined.Tune),
            RoleDrawerDestination(Routes.STUDENT_ACCOUNT_SETTINGS, R.string.st23_title, Icons.Outlined.Settings),
            RoleDrawerDestination(Routes.STUDENT_SECURITY_SETTINGS, R.string.st24_title, Icons.Outlined.Lock),
            RoleDrawerDestination(Routes.STUDENT_LANGUAGE_DISPLAY, R.string.st25_title, Icons.Outlined.Translate),
            RoleDrawerDestination(Routes.STUDENT_NOTIFICATIONS, R.string.st26_title, Icons.Outlined.Notifications),
        ),
    ),
)

/** Teacher tabs — الرئيسية · الصفوف · الطلاب · الاختبارات · حسابي */
val TeacherTabs: List<TabDestination> = listOf(
    TabDestination(Routes.TEACHER_DASHBOARD, R.string.tab_teacher_dashboard, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.TEACHER_COURSES, R.string.tab_teacher_courses, Icons.Outlined.Class, Icons.Filled.Class),
    TabDestination(Routes.TEACHER_STUDENTS, R.string.tab_teacher_students, Icons.Outlined.Groups, Icons.Filled.Groups),
    TabDestination(Routes.TEACHER_QUIZZES, R.string.tab_teacher_quizzes, Icons.Outlined.Quiz, Icons.Filled.Quiz),
    TabDestination(Routes.TEACHER_ME, R.string.tab_teacher_me, Icons.Outlined.Person, Icons.Filled.Person),
)

/**
 * Teacher drawer — secondary destinations plus the five tab roots.
 * Messages and Analytics are drawer-only. Projects / Gradebook / Review queue are not listed.
 */
val TeacherDrawerSections: List<RoleDrawerSection> = listOf(
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.TEACHER_DASHBOARD, R.string.tab_teacher_dashboard, Icons.Outlined.Home),
            RoleDrawerDestination(Routes.TEACHER_COURSES, R.string.tab_teacher_courses, Icons.Outlined.Class),
            RoleDrawerDestination(Routes.TEACHER_STUDENTS, R.string.tab_teacher_students, Icons.Outlined.Groups),
            RoleDrawerDestination(Routes.TEACHER_QUIZZES, R.string.tab_teacher_quizzes, Icons.Outlined.Quiz),
        ),
    ),
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.MESSAGES, R.string.topbar_messages, Icons.Outlined.Forum),
            RoleDrawerDestination(Routes.TEACHER_ANALYTICS, R.string.tc15_title, Icons.Outlined.Insights),
        ),
    ),
    RoleDrawerSection(
        listOf(
            RoleDrawerDestination(Routes.TEACHER_ME, R.string.tab_teacher_me, Icons.Outlined.Person),
        ),
    ),
)

/** Parent tabs — الرئيسية · التقدم · التقارير · الرسائل · حسابي */
val ParentTabs: List<TabDestination> = listOf(
    TabDestination(Routes.PARENT_HOME, R.string.tab_parent_home, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.PARENT_PROGRESS, R.string.tab_parent_progress, Icons.Outlined.Insights, Icons.Filled.Insights),
    TabDestination(Routes.PARENT_REPORTS, R.string.tab_parent_reports, Icons.Outlined.Assessment, Icons.Filled.Assessment),
    TabDestination(Routes.PARENT_MESSAGES, R.string.tab_parent_messages, Icons.Outlined.Forum, Icons.Filled.Forum),
    TabDestination(Routes.PARENT_ME, R.string.tab_parent_me, Icons.Outlined.Person, Icons.Filled.Person),
)
