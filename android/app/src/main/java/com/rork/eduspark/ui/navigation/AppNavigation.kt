package com.rork.eduspark.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavHostController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import androidx.navigation.navigation
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.TextSizePreference
import com.rork.eduspark.core.preferences.ThemeMode
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.FeatureAvailability
import com.rork.eduspark.ui.screens.PlaceholderScreen
import com.rork.eduspark.ui.screens.auth.CertificateVerifyScreen
import com.rork.eduspark.ui.screens.auth.ForgotPasswordScreen
import com.rork.eduspark.ui.screens.auth.LocaleSwitchScreen
import com.rork.eduspark.ui.screens.auth.LoginScreen
import com.rork.eduspark.ui.screens.auth.RegisterScreen
import com.rork.eduspark.ui.screens.auth.ResetPasswordScreen
import com.rork.eduspark.ui.screens.auth.RoleSelectScreen
import com.rork.eduspark.ui.screens.auth.SplashDecision
import com.rork.eduspark.ui.screens.auth.SplashScreen
import com.rork.eduspark.ui.screens.auth.SplashViewModel
import com.rork.eduspark.ui.screens.auth.TwoFactorScreen
import com.rork.eduspark.ui.screens.auth.ValueCarouselScreen
import com.rork.eduspark.ui.screens.auth.ValueCarouselViewModel
import com.rork.eduspark.ui.screens.auth.VerifyEmailScreen
import com.rork.eduspark.ui.screens.foundation.FoundationScreen
import com.rork.eduspark.ui.screens.messaging.ConversationThreadScreen
import com.rork.eduspark.ui.screens.messaging.MessagesBadgeViewModel
import com.rork.eduspark.ui.screens.messaging.MessagesListScreen
import com.rork.eduspark.ui.screens.messaging.NewConversationScreen
import com.rork.eduspark.ui.screens.messaging.NotificationsPanelEvent
import com.rork.eduspark.ui.screens.messaging.NotificationsPanelViewModel
import com.rork.eduspark.ui.screens.messaging.StudentNotificationsSheet
import com.rork.eduspark.ui.screens.messaging.TeacherContactEvent
import com.rork.eduspark.ui.screens.messaging.TeacherContactViewModel
import com.rork.eduspark.ui.screens.onboarding.OnboardingCompleteScreen
import com.rork.eduspark.ui.screens.onboarding.OnboardingGradeScreen
import com.rork.eduspark.ui.screens.onboarding.OnboardingPersonalizeScreen
import com.rork.eduspark.ui.screens.onboarding.OnboardingSubjectsScreen
import com.rork.eduspark.ui.screens.onboarding.OnboardingTeachersScreen
import com.rork.eduspark.ui.screens.onboarding.OnboardingViewModel
import com.rork.eduspark.ui.screens.student.AccountSettingsScreen
import com.rork.eduspark.ui.screens.student.AchievementScreen
import com.rork.eduspark.ui.screens.student.CoursePaywallScreen
import com.rork.eduspark.ui.screens.student.CourseDetailScreen
import com.rork.eduspark.ui.screens.student.ExamCaptureScreen
import com.rork.eduspark.ui.screens.student.LanguageDisplayScreen
import com.rork.eduspark.ui.screens.student.LanguageModuleScreen
import com.rork.eduspark.ui.screens.student.LessonPlayerScreen
import com.rork.eduspark.ui.screens.student.NotificationSettingsScreen
import com.rork.eduspark.ui.screens.student.PaymentMethodScreen
import com.rork.eduspark.ui.screens.student.LearningPreferencesScreen
import com.rork.eduspark.ui.screens.student.PaymentPendingScreen
import com.rork.eduspark.ui.screens.student.ParentLinkingScreen
import com.rork.eduspark.ui.screens.student.StudentCoursesScreen
import com.rork.eduspark.ui.screens.student.MilestoneBoardScreen
import com.rork.eduspark.ui.screens.student.MaterialsSafetyScreen
import com.rork.eduspark.ui.screens.student.PeerReviewScreen
import com.rork.eduspark.ui.screens.student.PlannerChatScreen
import com.rork.eduspark.ui.screens.student.PortfolioScreen
import com.rork.eduspark.ui.screens.student.ProjectCertificateScreen
import com.rork.eduspark.ui.screens.student.ProjectDetailScreen
import com.rork.eduspark.ui.screens.student.ProjectReviewScreen
import com.rork.eduspark.ui.screens.student.ProjectShowcaseDetailScreen
import com.rork.eduspark.ui.screens.student.ProjectsHubScreen
import com.rork.eduspark.ui.screens.student.PurchaseSuccessScreen
import com.rork.eduspark.ui.screens.student.PlannerScreen
import com.rork.eduspark.ui.screens.student.QuizResultsScreen
import com.rork.eduspark.ui.screens.student.ReflectionLogScreen
import com.rork.eduspark.ui.screens.student.RoutineBuilderScreen
import com.rork.eduspark.ui.screens.student.RoutineScreen
import com.rork.eduspark.ui.screens.student.RoutineTabRootScreen
import com.rork.eduspark.ui.screens.student.QuizRunnerScreen
import com.rork.eduspark.ui.screens.student.SecuritySettingsScreen
import com.rork.eduspark.ui.screens.student.StudentHomeScreen
import com.rork.eduspark.ui.screens.student.StudentProfileScreen
import com.rork.eduspark.ui.screens.student.SubmissionComposerScreen
import com.rork.eduspark.ui.screens.student.SubscriptionScreen
import com.rork.eduspark.ui.screens.student.TaskDetailScreen
import com.rork.eduspark.ui.screens.student.TeamWorkspaceScreen
import com.rork.eduspark.ui.screens.student.TutorChatScreen
import com.rork.eduspark.ui.screens.student.TutorChatViewModel
import com.rork.eduspark.ui.screens.student.TutorVoiceScreen
import com.rork.eduspark.ui.screens.teacher.TeacherAccountScreen
import com.rork.eduspark.ui.screens.teacher.TeacherEssayGradeScreen
import com.rork.eduspark.ui.screens.teacher.TeacherAnalyticsScreen
import com.rork.eduspark.ui.screens.teacher.TeacherCourseDetailScreen
import com.rork.eduspark.ui.screens.teacher.TeacherCoursesScreen
import com.rork.eduspark.ui.screens.teacher.TeacherDashboardScreen
import com.rork.eduspark.ui.screens.teacher.TeacherGradebookScreen
import com.rork.eduspark.ui.screens.teacher.TeacherLessonEditorScreen
import com.rork.eduspark.ui.screens.teacher.TeacherLessonPreviewScreen
import com.rork.eduspark.ui.screens.teacher.TeacherLessonProcessingScreen
import com.rork.eduspark.ui.screens.teacher.TeacherLessonUploadScreen
import com.rork.eduspark.ui.screens.teacher.TeacherProfilePreviewScreen
import com.rork.eduspark.ui.screens.teacher.TeacherProfileScreen
import com.rork.eduspark.ui.screens.teacher.TeacherProjectEditorScreen
import com.rork.eduspark.ui.screens.teacher.TeacherQuizEditorScreen
import com.rork.eduspark.ui.screens.teacher.TeacherQuizListScreen
import com.rork.eduspark.ui.screens.teacher.TeacherQuizResultsScreen
import com.rork.eduspark.ui.screens.teacher.TeacherReviewDetailScreen
import com.rork.eduspark.ui.screens.teacher.TeacherReviewQueueScreen
import com.rork.eduspark.ui.screens.teacher.TeacherSetupScreen
import com.rork.eduspark.ui.screens.teacher.TeacherStudentProfileScreen
import com.rork.eduspark.ui.screens.teacher.TeacherParentNoteScreen
import com.rork.eduspark.ui.screens.teacher.TeacherStudentsScreen
import com.rork.eduspark.ui.screens.teacher.TeacherVoiceProfileScreen
import com.rork.eduspark.ui.screens.student.VoucherRedeemScreen
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * The application navigation graph.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Five graphs, matching the Screen Inventory:
 *   • auth       — A-01…A-13, the Phase 0 entry funnel
 *   • onboarding — SO-01…SO-05, Student-only, isolated from Student Core (see
 *     [routeAfterAuthentication] and [onboardingGraph])
 *   • student    — Phase 1 + 2, five tabs
 *   • teacher    — Phase 3, five tabs
 *   • parent     — Phase 4, five tabs
 *
 * plus A-12 Certificate Verification and A-13 Locale Switch Transition, both of which sit
 * OUTSIDE every graph — A-12 because it is public, deep-linked and must render with no
 * session at all; A-13 because it is a transitional frame around the locale recreate, not a
 * destination a screen "arrives at".
 *
 * **Phase 0 is fully built (A-01 → A-14; A-14 is the shared component set in
 * `ui/components/state`, not a route). Student Onboarding (SO-01 → SO-05) is now built as
 * well**, reached only by a verified student whose session reports
 * `hasCompletedOnboarding = false`. **Student Core has started: ST-01 Student Home, ST-02
 * Course Detail, ST-03 Lesson Player and ST-04/ST-05 AI Tutor (chat + voice) are real.**
 * ST-06 Quiz Runner onward, and every Teacher/Parent tab, still render an honest
 * [PlaceholderScreen] naming its screen ID and phase via [RoleShell]. The foundation gallery
 * stays registered at [Routes.FOUNDATION] as a development surface, but it is no longer the
 * start destination — the app now opens on the real splash.
 */
@Composable
fun AppNavigation(
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    themeMode: ThemeMode = ThemeMode.System,
    onThemeModeChange: (ThemeMode) -> Unit = {},
    numeralSystem: NumeralSystem = NumeralSystem.Western,
    onNumeralSystemChange: (NumeralSystem) -> Unit = {},
    useHijriDates: Boolean = false,
    onUseHijriDatesChange: (Boolean) -> Unit = {},
    textSizePreference: TextSizePreference = TextSizePreference.Default,
    onTextSizePreferenceChange: (TextSizePreference) -> Unit = {},
    locale: AppLocale = AppLocale.Default,
    onSelectLocale: (AppLocale) -> Unit = {},
    isOffline: Boolean = false,
) {
    NavHost(
        navController = navController,
        startDestination = Routes.AUTH_GRAPH,
        modifier = modifier,
    ) {
        authGraph(
            navController = navController,
            locale = locale,
            onSelectLocale = onSelectLocale,
        )
        onboardingGraph(navController)
        studentGraph(
            navController = navController,
            themeMode = themeMode,
            onThemeModeChange = onThemeModeChange,
            numeralSystem = numeralSystem,
            onNumeralSystemChange = onNumeralSystemChange,
            useHijriDates = useHijriDates,
            onUseHijriDatesChange = onUseHijriDatesChange,
            textSizePreference = textSizePreference,
            onTextSizePreferenceChange = onTextSizePreferenceChange,
            locale = locale,
            onSelectLocale = onSelectLocale,
        )
        teacherGraph(navController)
        parentGraph()

        // ── Phase 6 · X-01/X-02/X-03 — outside every role graph, same shape as
        // TEACHER_SETUP/CERTIFICATE_VERIFY below: reached via the SAME shared [navController]
        // from either the Student or Teacher root shell's TopBar Messages action, so back
        // correctly returns to whichever root shell opened it regardless of role.
        composable(Routes.MESSAGES) {
            MessagesListScreen(
                onBack = { navController.popBackStack() },
                onOpenThread = { threadId -> navController.navigate(Routes.messageThreadRoute(threadId)) },
                onOpenNewConversation = { navController.navigate(Routes.NEW_CONVERSATION) },
            )
        }

        composable(
            route = Routes.MESSAGE_THREAD,
            arguments = listOf(navArgument(THREAD_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val threadId = backStackEntry.arguments?.getString(THREAD_ID_ARG).orEmpty()
            ConversationThreadScreen(
                threadId = threadId,
                onBack = { navController.popBackStack() },
                onOpenParticipantProfile = { studentId ->
                    navController.navigate(Routes.teacherStudentDetailRoute(studentId))
                },
            )
        }

        composable(Routes.NEW_CONVERSATION) {
            NewConversationScreen(
                onBack = { navController.popBackStack() },
                onOpenThread = { threadId ->
                    // X-03 itself is popped on the way to X-02 — same "the finished picker
                    // never sits behind the next screen" shape TC-05 → TC-06 already uses —
                    // so back from the thread returns to X-01, never to the picker.
                    navController.navigate(Routes.messageThreadRoute(threadId)) {
                        popUpTo(Routes.NEW_CONVERSATION) { inclusive = true }
                        launchSingleTop = true
                    }
                },
            )
        }

        // TC-01 · Teacher Setup Wizard — outside every graph, same shape as ONBOARDING_GRAPH:
        // reached only via routeAfterAuthentication for a Teacher session whose setup isn't
        // done. Finishing pops TEACHER_SETUP itself off the stack on the way into the real
        // Teacher shell, so back can never return to a completed wizard.
        composable(Routes.TEACHER_SETUP) {
            TeacherSetupScreen(
                onFinished = {
                    navController.navigate(Routes.TEACHER_GRAPH) {
                        popUpTo(Routes.TEACHER_SETUP) { inclusive = true }
                        launchSingleTop = true
                    }
                },
            )
        }

        // A-12 — public, no auth, reached by deep link. Deliberately outside every graph:
        // it must render correctly for a reader who never opened the app and never signs in.
        composable(
            route = Routes.CERTIFICATE_VERIFY,
            arguments = listOf(navArgument(CODE_ARG) { type = NavType.StringType }),
            deepLinks = listOf(navDeepLink { uriPattern = "edumind://certificate/verify/{$CODE_ARG}" }),
        ) { backStackEntry ->
            val code = backStackEntry.arguments?.getString(CODE_ARG).orEmpty()
            CertificateVerifyScreen(code = code)
        }

        // A-13 — also outside every graph: it is a transitional frame around the locale
        // recreate, not a destination any screen "arrives at" in the usual sense. See
        // LocaleSwitchScreen's doc comment for why the auth graph routes through it.
        composable(
            route = Routes.LOCALE_SWITCH,
            arguments = listOf(navArgument(LOCALE_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val target = AppLocale.fromTag(backStackEntry.arguments?.getString(LOCALE_ARG)) ?: AppLocale.Default
            LocaleSwitchScreen(target = target, onComplete = { onSelectLocale(target) })
        }

        // Development-only review surface for the token system and component kit.
        composable(Routes.FOUNDATION) {
            FoundationScreen(
                onOpenStudentShell = { navController.navigate(Routes.STUDENT_GRAPH) },
                onOpenTeacherShell = { navController.navigate(Routes.TEACHER_GRAPH) },
                onOpenParentShell = { navController.navigate(Routes.PARENT_GRAPH) },
                onOpenAuth = { navController.navigate(Routes.AUTH_GRAPH) },
                themeMode = themeMode,
                onThemeModeChange = onThemeModeChange,
                numeralSystem = numeralSystem,
                onNumeralSystemChange = onNumeralSystemChange,
                onToggleLocale = {
                    onSelectLocale(
                        if (locale == AppLocale.Arabic) AppLocale.English else AppLocale.Arabic
                    )
                },
                isOffline = isOffline,
            )
        }
    }
}

/**
 * Phase 0 — Foundation & Auth.
 *
 * The funnel is A-01 → A-02 → A-03 → A-04. Each step replaces the previous one in the back
 * stack only where returning to it would be meaningless: the language gate is popped once a
 * language exists, but the carousel is kept so that A-03's visible back arrow has somewhere
 * to go, and A-03 is kept so A-04's does.
 */
private fun NavGraphBuilder.authGraph(
    navController: NavHostController,
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
) {
    // A-13: every screen below that offers a mid-flow language toggle routes through the
    // branded transition instead of flipping the locale immediately — [onSelectLocale] itself
    // (the real setter) is only ever called from inside LocaleSwitchScreen's onComplete, once
    // the sweep has played. A-01's own first-run choice deliberately bypasses this: there is
    // no prior direction to flip *from* on first launch (see LocaleSwitchScreen's doc comment).
    val startLocaleTransition: (AppLocale) -> Unit = { target ->
        if (target != locale) navController.navigate(Routes.localeSwitchRoute(target))
    }

    navigation(startDestination = Routes.SPLASH, route = Routes.AUTH_GRAPH) {

        // ── A-01 · Splash & Language Gate ────────────────────────────────
        composable(Routes.SPLASH) {
            val viewModel = koinViewModel<SplashViewModel>()
            val state by viewModel.state.collectAsStateWithLifecycle()

            SplashScreen(
                isLanguageGate = state.decision == SplashDecision.LanguageGate,
                onChooseLanguage = { chosen ->
                    // Applied through the shell so the whole app (theme, direction, and the
                    // A-13 reload) sees one source of truth, and through the ViewModel so the
                    // splash can advance when the direction did not actually change.
                    onSelectLocale(chosen)
                    viewModel.chooseLanguage(chosen)
                },
            )

            LaunchedDecision(state.decision) { decision ->
                when (decision) {
                    SplashDecision.Carousel -> navController.replaceWith(Routes.VALUE_CAROUSEL)
                    SplashDecision.Login -> navController.replaceWith(Routes.ROLE_SELECT)
                    is SplashDecision.Home -> navController.routeAfterAuthentication(decision.user)
                    else -> Unit
                }
            }
        }

        // ── A-02 · Value Carousel ────────────────────────────────────────
        composable(Routes.VALUE_CAROUSEL) {
            val viewModel = koinViewModel<ValueCarouselViewModel>()
            ValueCarouselScreen(
                locale = locale,
                onSelectLocale = startLocaleTransition,
                onFinished = {
                    viewModel.markSeen()
                    navController.navigate(Routes.ROLE_SELECT)
                },
            )
        }

        // ── A-03 · Role Select ───────────────────────────────────────────
        composable(Routes.ROLE_SELECT) {
            val canGoBack = navController.previousBackStackEntry != null

            RoleSelectScreen(
                locale = locale,
                onSelectLocale = startLocaleTransition,
                onSelectRole = { role ->
                    navController.navigate(
                        when (role) {
                            UserRole.Student -> Routes.REGISTER_STUDENT
                            UserRole.Teacher -> Routes.REGISTER_TEACHER
                            UserRole.Parent -> Routes.REGISTER_PARENT
                        }
                    )
                },
                onLogin = { navController.navigate(Routes.LOGIN) },
                onBack = if (canGoBack) {
                    { navController.popBackStack() }
                } else {
                    null
                },
            )
        }

        // ── A-04 · Login ─────────────────────────────────────────────────
        composable(Routes.LOGIN) {
            val canGoBack = navController.previousBackStackEntry != null

            LoginScreen(
                locale = locale,
                onSelectLocale = startLocaleTransition,
                onAuthenticated = navController::routeAfterAuthentication,
                onTwoFactorRequired = { email -> navController.navigate(Routes.twoFactorRoute(email)) },
                onVerifyEmail = { email -> navController.navigate(Routes.verifyEmailRoute(email)) },
                onForgotPassword = { navController.navigate(Routes.FORGOT_PASSWORD) },
                onCreateAccount = { navController.navigate(Routes.ROLE_SELECT) },
                onBack = if (canGoBack) {
                    { navController.popBackStack() }
                } else {
                    null
                },
            )
        }

        // ── A-05 / A-06 / A-07 · Register ────────────────────────────────
        // Three routes, one screen: same form, same shell, one role-specific block each.
        registerDestination(navController, Routes.REGISTER_STUDENT, UserRole.Student, locale, startLocaleTransition)
        registerDestination(navController, Routes.REGISTER_PARENT, UserRole.Parent, locale, startLocaleTransition)
        registerDestination(navController, Routes.REGISTER_TEACHER, UserRole.Teacher, locale, startLocaleTransition)

        // ── A-08 · Verify Email ───────────────────────────────────────────
        // Reached from Register (a real session already exists, unverified) and from
        // Login's "resend link" notice (the platform never authenticates an unverified
        // sign-in attempt, so there is no session yet). VerifyEmailScreen reports which
        // case it was via a nullable role rather than assuming one.
        composable(
            route = Routes.VERIFY_EMAIL,
            arguments = listOf(navArgument(EMAIL_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val email = backStackEntry.arguments?.getString(EMAIL_ARG).orEmpty()
            VerifyEmailScreen(
                email = email,
                onBack = { navController.popBackStack() },
                onVerified = { user ->
                    if (user != null) {
                        navController.routeAfterAuthentication(user)
                    } else {
                        // No session behind this verification — the honest next step is
                        // back to Login, where the now-verified address can sign in.
                        navController.popBackStack()
                    }
                },
                onChangeEmail = { navController.popBackStack() },
            )
        }

        // ── A-09 · Two-Factor Verify ──────────────────────────────────────
        composable(
            route = Routes.TWO_FACTOR,
            arguments = listOf(navArgument(EMAIL_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val email = backStackEntry.arguments?.getString(EMAIL_ARG).orEmpty()
            TwoFactorScreen(
                email = email,
                onBack = { navController.popBackStack() },
                onAuthenticated = navController::routeAfterAuthentication,
            )
        }

        // ── A-10 · Forgot Password ────────────────────────────────────────
        composable(Routes.FORGOT_PASSWORD) {
            ForgotPasswordScreen(
                onBack = { navController.popBackStack() },
                onLogin = { navController.navigate(Routes.LOGIN) { launchSingleTop = true } },
            )
        }

        // ── A-11 · Reset Password ─────────────────────────────────────────
        // Reached by deep link in the common case (see the manifest intent-filter); both
        // arguments default to empty so a link missing either one still matches instead of
        // failing to route at all — ResetPasswordViewModel treats a blank token as already
        // expired, which is the correct, non-dead-end behaviour for a malformed link.
        composable(
            route = Routes.RESET_PASSWORD,
            arguments = listOf(
                navArgument(TOKEN_ARG) { type = NavType.StringType; defaultValue = "" },
                navArgument(EMAIL_ARG) { type = NavType.StringType; defaultValue = "" },
            ),
            deepLinks = listOf(
                navDeepLink { uriPattern = "edumind://reset-password?$TOKEN_ARG={$TOKEN_ARG}&$EMAIL_ARG={$EMAIL_ARG}" }
            ),
        ) { backStackEntry ->
            val token = backStackEntry.arguments?.getString(TOKEN_ARG).orEmpty()
            val email = backStackEntry.arguments?.getString(EMAIL_ARG).orEmpty()
            ResetPasswordScreen(
                token = token,
                email = email,
                onBack = { navController.popBackStack() },
                onNeedEmail = {
                    navController.navigate(Routes.FORGOT_PASSWORD) { launchSingleTop = true }
                },
                onCompleted = {
                    // Resetting a password never returns a session (Source Audit §3) — the
                    // honest next step is Login, same as A-08's no-session branch.
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.AUTH_GRAPH) { inclusive = false }
                        launchSingleTop = true
                    }
                },
            )
        }
    }
}

private const val EMAIL_ARG = "email"
private const val TOKEN_ARG = "token"
private const val CODE_ARG = "code"
private const val LOCALE_ARG = "locale"
private const val COURSE_ID_ARG = "courseId"
private const val LESSON_ID_ARG = "lessonId"
private const val QUIZ_ID_ARG = "quizId"
private const val TEACHER_STUDENT_ID_ARG = "studentId"
private const val ESSAY_QUESTION_ID_ARG = "questionId"
private const val SUBMISSION_ID_ARG = "submissionId"
private const val PAYMENT_METHOD_ID_ARG = "paymentMethodId"
private const val PROJECT_ID_ARG = "projectId"
private const val TASK_ID_ARG = "taskId"
private const val MILESTONE_ID_ARG = "milestoneId"
private const val THREAD_ID_ARG = "threadId"

/**
 * Registers one of the three register destinations.
 *
 * Every role gets identical wiring — back returns to A-03, the cross-link reaches login,
 * and success goes to A-08 Verify Email, which is where all three funnels meet before their
 * role onboarding.
 */
private fun NavGraphBuilder.registerDestination(
    navController: NavHostController,
    route: String,
    role: UserRole,
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
) {
    composable(route) {
        RegisterScreen(
            role = role,
            locale = locale,
            onSelectLocale = onSelectLocale,
            onRegistered = { email ->
                navController.navigate(Routes.verifyEmailRoute(email)) { launchSingleTop = true }
            },
            onLogin = {
                navController.navigate(Routes.LOGIN) { launchSingleTop = true }
            },
            onBack = { navController.popBackStack() },
        )
    }
}

/** Replaces the current destination, so the splash never sits in the back stack. */
private fun NavHostController.replaceWith(route: String) {
    navigate(route) {
        popUpTo(Routes.SPLASH) { inclusive = true }
        launchSingleTop = true
    }
}

/**
 * Signed in: the whole auth graph is dropped so back cannot return to a login form.
 *
 * A student whose session says `hasCompletedOnboarding = false` — freshly registered, or an
 * onboarding flow that was killed mid-way and relaunched — routes into SO-01 instead of
 * Student Core. A Teacher whose session reports the same flag false (reused verbatim for
 * "has this role's setup wizard been finished" — see [com.rork.eduspark.ui.screens.teacher.TeacherSetupViewModel]'s
 * own doc comment) routes into TC-01 instead of the Teacher shell, the identical shape one
 * layer up. Parent always goes straight to its shell; neither onboarding nor setup applies to it.
 */
private fun NavHostController.routeAfterAuthentication(user: SessionUser) {
    val destination = when {
        user.role == UserRole.Student && !user.hasCompletedOnboarding -> Routes.ONBOARDING_GRAPH
        user.role == UserRole.Teacher && !user.hasCompletedOnboarding -> Routes.TEACHER_SETUP
        else -> when (user.role) {
            UserRole.Student -> Routes.STUDENT_GRAPH
            UserRole.Teacher -> Routes.TEACHER_GRAPH
            UserRole.Parent -> Routes.PARENT_GRAPH
        }
    }
    navigate(destination) {
        popUpTo(Routes.AUTH_GRAPH) { inclusive = true }
        launchSingleTop = true
    }
}

/**
 * SO-01…SO-05 · Student Onboarding — isolated from Student Core, its own top-level graph.
 *
 * All five routes resolve the *same* [OnboardingViewModel] instance via [onboardingViewModel]
 * below, scoped to this graph's own back-stack entry rather than to any one screen — that is
 * the entire mechanism behind "back navigation with state preservation". Completing SO-05
 * pops this whole graph and replaces it with Student Core, so back can never return here
 * once onboarding is done.
 */
private fun NavGraphBuilder.onboardingGraph(navController: NavHostController) {
    navigation(startDestination = Routes.SO_GRADE, route = Routes.ONBOARDING_GRAPH) {

        composable(Routes.SO_GRADE) { backStackEntry ->
            OnboardingGradeScreen(
                onBack = { navController.popBackStack() },
                onContinue = { navController.navigate(Routes.SO_SUBJECTS) },
                viewModel = onboardingViewModel(navController, backStackEntry),
            )
        }

        composable(Routes.SO_SUBJECTS) { backStackEntry ->
            OnboardingSubjectsScreen(
                onBack = { navController.popBackStack() },
                onContinue = { navController.navigate(Routes.SO_TEACHERS) },
                viewModel = onboardingViewModel(navController, backStackEntry),
            )
        }

        composable(Routes.SO_TEACHERS) { backStackEntry ->
            OnboardingTeachersScreen(
                onBack = { navController.popBackStack() },
                onContinue = { navController.navigate(Routes.SO_PERSONALIZE) },
                viewModel = onboardingViewModel(navController, backStackEntry),
            )
        }

        composable(Routes.SO_PERSONALIZE) { backStackEntry ->
            OnboardingPersonalizeScreen(
                onBack = { navController.popBackStack() },
                onContinue = { navController.navigate(Routes.SO_COMPLETE) },
                viewModel = onboardingViewModel(navController, backStackEntry),
            )
        }

        composable(Routes.SO_COMPLETE) { backStackEntry ->
            OnboardingCompleteScreen(
                // "Change" — SO-05 reads every choice back before committing; each link pops
                // to the exact step that made it, keeping every other answer in place because
                // it's the same shared ViewModel instance underneath.
                onChangeGrade = { navController.popBackStack(Routes.SO_GRADE, inclusive = false) },
                onChangeSubjects = { navController.popBackStack(Routes.SO_SUBJECTS, inclusive = false) },
                onChangeTeachers = { navController.popBackStack(Routes.SO_TEACHERS, inclusive = false) },
                onChangeStudy = { navController.popBackStack(Routes.SO_PERSONALIZE, inclusive = false) },
                onStart = {
                    // Do NOT implement ST-01 yet — this still lands on Student Core's
                    // placeholder shell, same as a directly-authenticated, already-onboarded
                    // student would.
                    navController.navigate(Routes.STUDENT_GRAPH) {
                        popUpTo(Routes.ONBOARDING_GRAPH) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                viewModel = onboardingViewModel(navController, backStackEntry),
            )
        }
    }
}

/** Resolves the one [OnboardingViewModel] shared by every SO-0x screen, graph-scoped. */
@Composable
private fun onboardingViewModel(
    navController: NavHostController,
    backStackEntry: NavBackStackEntry,
): OnboardingViewModel {
    val parentEntry = remember(backStackEntry) {
        navController.getBackStackEntry(Routes.ONBOARDING_GRAPH)
    }
    return koinViewModel(viewModelStoreOwner = parentEntry)
}

/** Runs [onDecision] once per distinct splash decision. */
@Composable
private fun LaunchedDecision(
    decision: SplashDecision,
    onDecision: (SplashDecision) -> Unit,
) {
    androidx.compose.runtime.LaunchedEffect(decision) { onDecision(decision) }
}

/**
 * Phase 1 (Student Core) + Phase 2 (Projects).
 *
 * ST-01 is now real — wired into [RoleShell] via its `overrides` slot, so the Home tab shows
 * [StudentHomeScreen] while Courses/Projects/English/Me stay exactly the honest placeholders
 * they were. ST-02 (Course Detail), ST-03 (Lesson Player) and the ST-04/ST-05 tutor graph are
 * all **siblings** of [Routes.STUDENT_HOME] inside this same graph, not nested inside
 * RoleShell's own tab NavHost — the anchor shows each with its own back arrow and no bottom
 * tab bar at all, so pushing any of them here replaces the whole shell rather than living
 * inside one tab's back stack.
 *
 * ST-04/ST-05 are nested in their own [Routes.TUTOR_GRAPH] purely so both can resolve the
 * *same* [TutorChatViewModel] instance via [tutorChatViewModel] below — the same mechanism
 * [onboardingGraph] uses for SO-01…SO-05.
 */
private fun NavGraphBuilder.studentGraph(
    navController: NavHostController,
    themeMode: ThemeMode,
    onThemeModeChange: (ThemeMode) -> Unit,
    numeralSystem: NumeralSystem,
    onNumeralSystemChange: (NumeralSystem) -> Unit,
    useHijriDates: Boolean,
    onUseHijriDatesChange: (Boolean) -> Unit,
    textSizePreference: TextSizePreference,
    onTextSizePreferenceChange: (TextSizePreference) -> Unit,
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
) {
    // ST-25 — same "route through the branded transition" rule the auth graph's
    // startLocaleTransition already established; see LocaleSwitchScreen's own doc comment.
    val startLocaleTransition: (AppLocale) -> Unit = { target ->
        if (target != locale) navController.navigate(Routes.localeSwitchRoute(target))
    }
    navigation(startDestination = Routes.STUDENT_HOME, route = Routes.STUDENT_GRAPH) {
        composable(Routes.STUDENT_HOME) {
            val messagesBadgeViewModel = koinViewModel<MessagesBadgeViewModel>()
            val unreadMessages by messagesBadgeViewModel.unreadCount.collectAsStateWithLifecycle()
            val notificationsViewModel = koinViewModel<NotificationsPanelViewModel>()
            val notificationState by notificationsViewModel.state.collectAsStateWithLifecycle()
            var showNotifications by remember { mutableStateOf(false) }
            val drawerViewModel = koinViewModel<StudentNavigationDrawerViewModel>()
            val drawerState by drawerViewModel.state.collectAsStateWithLifecycle()
            val studentTabNavController = rememberNavController()

            LaunchedEffect(notificationsViewModel) {
                notificationsViewModel.events.collect { event ->
                    when (event) {
                        is NotificationsPanelEvent.OpenThread -> {
                            showNotifications = false
                            navController.navigate(Routes.messageThreadRoute(event.threadId))
                        }
                        is NotificationsPanelEvent.OpenCourse -> {
                            showNotifications = false
                            navController.navigate(Routes.studentCourseDetailRoute(event.courseId))
                        }
                        is NotificationsPanelEvent.OpenPurchaseSuccess -> {
                            showNotifications = false
                            navController.navigate(Routes.studentPurchaseSuccessRoute(event.courseId))
                        }
                    }
                }
            }

            RoleShell(
                tabs = StudentTabs,
                tabNavController = studentTabNavController,
                unreadMessages = unreadMessages,
                unreadNotifications = notificationState.unreadCount,
                onOpenMessages = { navController.navigate(Routes.MESSAGES) },
                onOpenNotifications = { showNotifications = true },
                homeRoute = Routes.STUDENT_HOME,
                homeLabelRes = R.string.tab_student_home,
                drawerUser = drawerState.user?.let { user ->
                    RoleDrawerUser(
                        displayName = user.displayName,
                        email = user.email,
                    )
                },
                drawerSections = StudentDrawerSections,
                onOpenDrawerDestination = { route -> navController.navigate(route) },
                onConfirmSignOut = {
                    drawerViewModel.signOut {
                        navController.navigate(Routes.ROLE_SELECT) {
                            popUpTo(Routes.STUDENT_GRAPH) { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                },
                isSigningOut = drawerState.isSigningOut,
                screenIdFor = { route ->
                    when (route) {
                        Routes.STUDENT_HOME -> "ST-01 · Student Home"
                        // STUDENT_COURSES is now a real override (course discovery) — no
                        // placeholder label needed; this branch is unreachable.
                        Routes.STUDENT_ROUTINE -> "ST-13 · Routine Week"
                        Routes.STUDENT_PROJECTS -> "PJ-01 · Projects Hub"
                        Routes.STUDENT_ENGLISH -> "LN-01 · Languages Hub"
                        else -> "ST-22 · Student Profile"
                    }
                },
                phaseFor = { route ->
                    when (route) {
                        Routes.STUDENT_ROUTINE -> "Phase 1"
                        Routes.STUDENT_PROJECTS -> "Phase 2"
                        Routes.STUDENT_ENGLISH -> "Phase 5"
                        else -> "Phase 1"
                    }
                },
                // Projects has no backend at all — the shell says so rather than implying one.
                backendPendingFor = { route ->
                    route == Routes.STUDENT_PROJECTS && !FeatureAvailability.PROJECTS_BACKEND_READY
                },
                overrides = mapOf<String, @Composable () -> Unit>(
                    Routes.STUDENT_HOME to {
                        StudentHomeScreen(
                            onOpenCourse = { courseId ->
                                navController.navigate(Routes.studentCourseDetailRoute(courseId))
                            },
                            onOpenLesson = { lessonId -> navController.navigate(Routes.studentLessonRoute(lessonId)) },
                            onOpenPlanner = { navController.navigate(Routes.STUDENT_PLANNER) },
                            onOpenRoutine = {
                                studentTabNavController.navigate(Routes.STUDENT_ROUTINE) {
                                    popUpTo(Routes.STUDENT_HOME) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            onOpenSubscriptions = { navController.navigate(Routes.STUDENT_SUBSCRIPTIONS) },
                            onOpenAchievements = { navController.navigate(Routes.STUDENT_ACHIEVEMENTS) },
                        )
                    },
                    Routes.STUDENT_ROUTINE to {
                        RoutineTabRootScreen(
                            onBuildRoutine = { navController.navigate(Routes.STUDENT_ROUTINE_BUILDER) },
                            onRebuild = { navController.navigate(Routes.STUDENT_ROUTINE_BUILDER) },
                            onOpenPlanner = { navController.navigate(Routes.STUDENT_PLANNER) },
                        )
                    },
                    // Course discovery (Test-2SY: MySubjectsSection/SubjectCatalogCard) — every
                    // course for the student's grade, entitled or not. A locked card opens the
                    // exact same ST-02 destination as an entitled one; CourseDetailViewModel
                    // itself resolves which content to render, so there is nothing to branch on
                    // here.
                    Routes.STUDENT_COURSES to {
                        StudentCoursesScreen(
                            onOpenCourse = { courseId ->
                                navController.navigate(Routes.studentCourseDetailRoute(courseId))
                            },
                            onOpenSubscriptions = { navController.navigate(Routes.STUDENT_SUBSCRIPTIONS) },
                        )
                    },
                    // LN-01/LN-04 — the Language tab is now the real module root. The
                    // module owns its access/placement gates internally so the existing
                    // five-tab Student shell stays intact.
                    Routes.STUDENT_ENGLISH to {
                        LanguageModuleScreen()
                    },
                    // Me is now ST-22 Student Profile itself — the primary identity surface,
                    // with links to Settings/Security/Achievements/Subscriptions from the same
                    // screen. Same overrides mechanism as Home; still one hub, not a second one.
                    Routes.STUDENT_ME to {
                        StudentProfileScreen(
                            onOpenAchievements = { navController.navigate(Routes.STUDENT_ACHIEVEMENTS) },
                            onOpenSubscriptions = { navController.navigate(Routes.STUDENT_SUBSCRIPTIONS) },
                            onOpenAccountSettings = { navController.navigate(Routes.STUDENT_ACCOUNT_SETTINGS) },
                            onOpenSecuritySettings = { navController.navigate(Routes.STUDENT_SECURITY_SETTINGS) },
                            onOpenLanguageDisplay = { navController.navigate(Routes.STUDENT_LANGUAGE_DISPLAY) },
                            onOpenNotifications = { navController.navigate(Routes.STUDENT_NOTIFICATIONS) },
                            onOpenLearningPreferences = { navController.navigate(Routes.STUDENT_LEARNING_PREFERENCES) },
                            onOpenParentLinking = { navController.navigate(Routes.STUDENT_PARENT_LINKING) },
                            onLogout = {
                                drawerViewModel.signOut {
                                    navController.navigate(Routes.ROLE_SELECT) {
                                        popUpTo(Routes.STUDENT_GRAPH) { inclusive = true }
                                        launchSingleTop = true
                                    }
                                }
                            },
                            localeLabel = stringResource(
                                if (locale == AppLocale.Arabic) R.string.st25_language_ar else R.string.st25_language_en,
                            ),
                            appearanceLabel = stringResource(
                                when (themeMode) {
                                    ThemeMode.System -> R.string.st25_theme_system
                                    ThemeMode.Light -> R.string.st25_theme_light
                                    ThemeMode.Dark -> R.string.st25_theme_dark
                                },
                            ),
                        )
                    },
                    // PJ-01 — the actual Projects-tab root now, same overrides mechanism as
                    // Home/Me. Discover → PJ-02; an already-active card → PJ-03 directly.
                    Routes.STUDENT_PROJECTS to {
                        ProjectsHubScreen(
                            onOpenProjectDetail = { projectId ->
                                navController.navigate(Routes.studentProjectDetailRoute(projectId))
                            },
                            onOpenMilestoneBoard = { projectId ->
                                navController.navigate(Routes.studentMilestoneBoardRoute(projectId))
                            },
                            onOpenPortfolio = { navController.navigate(Routes.STUDENT_PORTFOLIO) },
                        )
                    },
                ),
            )

            if (showNotifications) {
                StudentNotificationsSheet(
                    state = notificationState,
                    onDismiss = { showNotifications = false },
                    onMarkAllRead = notificationsViewModel::markAllRead,
                    onNotificationClick = notificationsViewModel::openNotification,
                )
            }
        }

        // ── ST-02 · Course Detail ─────────────────────────────────────────
        composable(
            route = Routes.STUDENT_COURSE_DETAIL,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            val teacherContactViewModel = koinViewModel<TeacherContactViewModel>()
            LaunchedEffect(teacherContactViewModel) {
                teacherContactViewModel.events.collect { event ->
                    when (event) {
                        is TeacherContactEvent.OpenThread -> navController.navigate(Routes.messageThreadRoute(event.threadId))
                    }
                }
            }
            CourseDetailScreen(
                courseId = courseId,
                onBack = { navController.popBackStack() },
                onContinueLesson = { lessonId -> navController.navigate(Routes.studentLessonRoute(lessonId)) },
                // ST-09 — the course's manual quiz has a deterministic id derived from the
                // course it belongs to, and there is no quiz-list screen to build this
                // slice, so tapping the quiz count opens it directly.
                onOpenManualQuiz = { navController.navigate(Routes.studentQuizRoute("manual-$courseId")) },
                // Whole-course-locked state's Subscribe CTA — the existing ST-17 paywall
                // sheet, never a second payment entry point.
                onSubscribe = { navController.navigate(Routes.STUDENT_SUBSCRIPTIONS) },
                onMessageTeacher = teacherContactViewModel::openCourseTeacherThread,
            )
        }

        // ── ST-03 · Lesson Player ─────────────────────────────────────────
        composable(
            route = Routes.STUDENT_LESSON,
            arguments = listOf(navArgument(LESSON_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
            LessonPlayerScreen(
                lessonId = lessonId,
                onBack = { navController.popBackStack() },
                onBackToCourse = { courseId -> navController.navigate(Routes.studentCourseDetailRoute(courseId)) },
                onAskTutor = { navController.navigate(Routes.tutorChatRoute(lessonId)) },
                onAskTutorWithPrompt = { prompt -> navController.navigate(Routes.tutorChatRoute(lessonId, prompt)) },
                onTakeQuiz = { quizId -> navController.navigate(Routes.studentQuizRoute(quizId)) },
                onOpenQuizResults = { quizId -> navController.navigate(Routes.studentQuizResultsRoute(quizId)) },
            )
        }

        // ── ST-06 · Quiz Runner / ST-08 · Remedial Quiz / ST-09 · Manual Quiz Runner ───────
        // One screen for all three — see QuizRunnerScreen's own doc comment. Submitting a
        // non-remedial quiz pops it off the stack on the way to ST-07, so back from Results
        // returns to the lesson, not to a completed runner; a remedial quiz is pushed ON TOP
        // of ST-07 instead, so "back to results" is a plain pop.
        composable(
            route = Routes.STUDENT_QUIZ,
            arguments = listOf(navArgument(QUIZ_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val quizId = backStackEntry.arguments?.getString(QUIZ_ID_ARG).orEmpty()
            QuizRunnerScreen(
                quizId = quizId,
                onBack = { navController.popBackStack() },
                onSubmitted = { submittedQuizId ->
                    navController.navigate(Routes.studentQuizResultsRoute(submittedQuizId)) {
                        popUpTo(Routes.STUDENT_QUIZ) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                onRemedialBackToResults = { navController.popBackStack() },
                onRemedialBackToLesson = { lessonId ->
                    navController.popBackStack(Routes.studentLessonRoute(lessonId), inclusive = false)
                },
            )
        }

        // ── ST-07 · Quiz Results ───────────────────────────────────────────
        composable(
            route = Routes.STUDENT_QUIZ_RESULTS,
            arguments = listOf(navArgument(QUIZ_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val quizId = backStackEntry.arguments?.getString(QUIZ_ID_ARG).orEmpty()
            QuizResultsScreen(
                quizId = quizId,
                onBack = { navController.popBackStack() },
                onPracticeAgain = { remedialQuizId ->
                    navController.navigate(Routes.studentQuizRoute(remedialQuizId))
                },
                onAskTutorAboutMistake = { lessonId, prompt ->
                    navController.navigate(Routes.tutorChatRoute(lessonId, prompt))
                },
            )
        }

        // ── ST-04 · AI Tutor Chat / ST-05 · AI Tutor Voice Mode ────────────
        navigation(startDestination = Routes.TUTOR_CHAT, route = Routes.TUTOR_GRAPH) {
            composable(
                route = Routes.TUTOR_CHAT,
                arguments = listOf(
                    navArgument(LESSON_ID_ARG) { type = NavType.StringType },
                    navArgument(Routes.TUTOR_PROMPT_ARG) { type = NavType.StringType; nullable = true; defaultValue = null },
                ),
            ) { backStackEntry ->
                val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
                val initialPrompt = backStackEntry.arguments?.getString(Routes.TUTOR_PROMPT_ARG)
                TutorChatScreen(
                    onBack = { navController.popBackStack() },
                    onVoiceMode = { navController.navigate(Routes.tutorVoiceRoute(lessonId)) },
                    viewModel = tutorChatViewModel(navController, backStackEntry, lessonId, initialPrompt),
                )
            }

            composable(
                route = Routes.TUTOR_VOICE,
                arguments = listOf(navArgument(LESSON_ID_ARG) { type = NavType.StringType }),
            ) { backStackEntry ->
                val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
                TutorVoiceScreen(
                    onBack = { navController.popBackStack() },
                    viewModel = tutorChatViewModel(navController, backStackEntry, lessonId),
                )
            }
        }

        // ── ST-10 · Planner / ST-11 · Planner AI Chat ──────────────────────
        // Siblings, not graph-scoped — unlike the tutor pair, ST-10 and ST-11 don't share a
        // ViewModel; the shared week plan already lives one layer down, in PlannerRepository's
        // own hot flow (see PlannerViewModel's doc comment), so plain independent ViewModels
        // are enough for both.
        composable(Routes.STUDENT_PLANNER) {
            PlannerScreen(
                onBack = { navController.popBackStack() },
                onAskAssistant = { navController.navigate(Routes.STUDENT_PLANNER_CHAT) },
                onOpenRoutine = { navController.navigate(Routes.STUDENT_ROUTINE) },
                onOpenExamCapture = { navController.navigate(Routes.STUDENT_EXAM_CAPTURE) },
            )
        }

        composable(Routes.STUDENT_PLANNER_CHAT) {
            PlannerChatScreen(
                onBack = { navController.popBackStack() },
                // ST-14 entry point from chat — the existing route/screen, nothing new to
                // register. A plain push, so "return to the previous chat/planner flow"
                // after confirming is just ST-14's own onConfirmed = popBackStack().
                onOpenExamCapture = { navController.navigate(Routes.STUDENT_EXAM_CAPTURE) },
            )
        }

        // ── ST-12 · Routine Builder / ST-13 · Routine Week View ────────────
        // Same independent-ViewModel shape as the Planner pair — RoutineRepository's hot
        // flow is what ST-13 sees update the moment ST-12 confirms, not shared navigation
        // state. Confirming pops the builder off the stack (back from ST-13 should not
        // return to a just-completed setup); "edit/rebuild" from ST-13 is a plain push, so
        // back from the builder returns to the week view underneath it.
        composable(Routes.STUDENT_ROUTINE_BUILDER) {
            RoutineBuilderScreen(
                onBack = { navController.popBackStack() },
                onOpenExamCapture = { navController.navigate(Routes.STUDENT_EXAM_CAPTURE) },
                onComplete = { navController.popBackStack() },
            )
        }

        composable(Routes.STUDENT_ROUTINE) {
            RoutineScreen(
                onBack = { navController.popBackStack() },
                onRebuild = { navController.navigate(Routes.STUDENT_ROUTINE_BUILDER) },
            )
        }

        // ── ST-14 · Exam Schedule Capture ───────────────────────────────────
        // Always entered from Planner, so a plain pop is "return to Planner ... with
        // confirmed exams preserved" — PlannerViewModel is already collecting
        // ExamRepository's flow, so nothing needs to be threaded back through navigation.
        composable(Routes.STUDENT_EXAM_CAPTURE) {
            ExamCaptureScreen(
                onBack = { navController.popBackStack() },
                onConfirmed = { navController.popBackStack() },
            )
        }

        // ── ST-15 · Achievements ────────────────────────────────────────────
        // Reached only from the STUDENT_ME account hub, same "pushed above the tab bar,
        // own back arrow" shape as ST-02/ST-14 — not nested in RoleShell's own tab NavHost.
        composable(Routes.STUDENT_ACHIEVEMENTS) {
            AchievementScreen(onBack = { navController.popBackStack() })
        }

        // ── ST-16 · Subscriptions ───────────────────────────────────────────
        // Renew/Subscribe both open the same ST-17 paywall, keyed by which course they're for.
        // The voucher entry point and the "confirmed access, tap to open" ST-20 banner both
        // live here too — the natural subscription/access management surface.
        composable(Routes.STUDENT_SUBSCRIPTIONS) {
            SubscriptionScreen(
                onBack = { navController.popBackStack() },
                onOpenCourse = { courseId -> navController.navigate(Routes.studentCourseDetailRoute(courseId)) },
                onRenew = { courseId -> navController.navigate(Routes.studentPaywallRoute(courseId)) },
                onSubscribe = { courseId -> navController.navigate(Routes.studentPaywallRoute(courseId)) },
                onRedeemVoucher = { navController.navigate(Routes.STUDENT_VOUCHER_REDEEM) },
                onOpenVerifiedPurchase = { courseId -> navController.navigate(Routes.studentPurchaseSuccessRoute(courseId)) },
            )
        }

        // ── ST-17 · Course Paywall Sheet ─────────────────────────────────────
        composable(
            route = Routes.STUDENT_PAYWALL,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            CoursePaywallScreen(
                courseId = courseId,
                onDismiss = { navController.popBackStack() },
                onContinueToPayment = { navController.navigate(Routes.studentPaymentMethodRoute(courseId)) },
                onRedeemVoucher = { navController.navigate(Routes.STUDENT_VOUCHER_REDEEM) },
            )
        }

        // ── ST-18 · Payment Method Select ────────────────────────────────────
        // Continue pops ST-17/ST-18 off the stack on the way to ST-19, so ST-19's back goes
        // straight to STUDENT_SUBSCRIPTIONS — no half-completed purchase step to land back on,
        // and nothing left to accidentally resubmit.
        composable(
            route = Routes.STUDENT_PAYMENT_METHOD,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            PaymentMethodScreen(
                courseId = courseId,
                onBack = { navController.popBackStack() },
                onSubmit = { methodId ->
                    navController.navigate(Routes.studentPaymentPendingRoute(courseId, methodId)) {
                        popUpTo(Routes.STUDENT_SUBSCRIPTIONS) { inclusive = false }
                        launchSingleTop = true
                    }
                },
            )
        }

        // ── ST-19 · Payment Pending ───────────────────────────────────────────
        composable(
            route = Routes.STUDENT_PAYMENT_PENDING,
            arguments = listOf(
                navArgument(COURSE_ID_ARG) { type = NavType.StringType },
                navArgument(PAYMENT_METHOD_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            val methodId = backStackEntry.arguments?.getString(PAYMENT_METHOD_ID_ARG).orEmpty()
            PaymentPendingScreen(
                courseId = courseId,
                methodId = methodId,
                onDone = { navController.popBackStack() },
            )
        }

        // ── ST-20 · Purchase Success ──────────────────────────────────────────
        // Only reached via ST-16's "confirmed access" banner (a pre-verified mock fixture) —
        // never pushed automatically from ST-19; see PurchaseSuccessViewModel's own doc comment.
        composable(
            route = Routes.STUDENT_PURCHASE_SUCCESS,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            PurchaseSuccessScreen(
                courseId = courseId,
                onOpenCourse = { navController.navigate(Routes.studentCourseDetailRoute(courseId)) },
                onBackToSubscriptions = { navController.popBackStack() },
            )
        }

        // ── ST-21 · Voucher Redeem ────────────────────────────────────────────
        // Reachable from both ST-16 and ST-17, never nested inside ST-18 as a payment method.
        composable(Routes.STUDENT_VOUCHER_REDEEM) {
            VoucherRedeemScreen(
                onBack = { navController.popBackStack() },
                onOpenCourse = { courseId -> navController.navigate(Routes.studentCourseDetailRoute(courseId)) },
            )
        }

        // ── Learning Preferences — new, extends ST-22 ───────────────────────
        composable(Routes.STUDENT_LEARNING_PREFERENCES) {
            LearningPreferencesScreen(onBack = { navController.popBackStack() })
        }

        composable(Routes.STUDENT_PARENT_LINKING) {
            ParentLinkingScreen(onBack = { navController.popBackStack() })
        }

        // ── ST-23 · Settings — Account ────────────────────────────────────────
        composable(Routes.STUDENT_ACCOUNT_SETTINGS) {
            AccountSettingsScreen(onBack = { navController.popBackStack() })
        }

        // ── ST-24 · Settings — Security ───────────────────────────────────────
        composable(Routes.STUDENT_SECURITY_SETTINGS) {
            SecuritySettingsScreen(onBack = { navController.popBackStack() })
        }

        // ── ST-25 · Settings — Language & Display ───────────────────────────────
        // Purely presentational — no ViewModel of its own; every value/callback here already
        // flows from AppShellViewModel via this same graph's own parameters, same pattern
        // FoundationScreen already uses for themeMode/numeralSystem.
        composable(Routes.STUDENT_LANGUAGE_DISPLAY) {
            LanguageDisplayScreen(
                onBack = { navController.popBackStack() },
                locale = locale,
                onSelectLanguage = startLocaleTransition,
                themeMode = themeMode,
                onThemeModeChange = onThemeModeChange,
                numeralSystem = numeralSystem,
                onNumeralSystemChange = onNumeralSystemChange,
                useHijriDates = useHijriDates,
                onUseHijriDatesChange = onUseHijriDatesChange,
                textSizePreference = textSizePreference,
                onTextSizePreferenceChange = onTextSizePreferenceChange,
            )
        }

        // ── ST-26 · Settings — Notifications ──────────────────────────────────
        composable(Routes.STUDENT_NOTIFICATIONS) {
            NotificationSettingsScreen(onBack = { navController.popBackStack() })
        }

        // ── PJ-02 · Project Detail ────────────────────────────────────────────
        // Back → PJ-01 (a plain pop, same as every other "pushed above the tab bar" screen).
        composable(
            route = Routes.STUDENT_PROJECT_DETAIL,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            ProjectDetailScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
                onOpenMilestoneBoard = { navController.navigate(Routes.studentMilestoneBoardRoute(projectId)) },
                onOpenMaterialsSafety = { pid -> navController.navigate(Routes.studentMaterialsSafetyRoute(pid)) },
            )
        }

        // ── PJ-03 · Milestone Board ───────────────────────────────────────────
        // Back → whichever surface pushed it (PJ-01's My Projects, or PJ-02) — a plain pop
        // returns there correctly either way, no special-casing needed.
        composable(
            route = Routes.STUDENT_MILESTONE_BOARD,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            MilestoneBoardScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
                onOpenTask = { taskId -> navController.navigate(Routes.studentTaskDetailRoute(projectId, taskId)) },
                onOpenTeamWorkspace = { navController.navigate(Routes.studentTeamWorkspaceRoute(projectId)) },
                onOpenReflection = { milestoneId ->
                    navController.navigate(Routes.studentReflectionLogRoute(projectId, milestoneId))
                },
            )
        }

        // ── PJ-04 · Task Detail ───────────────────────────────────────────────
        // Back → PJ-03, a plain pop. Submit Work / view review both push forward; neither
        // ever pops PJ-04 itself, so it stays the stable anchor every later step in this
        // workflow returns to.
        composable(
            route = Routes.STUDENT_TASK_DETAIL,
            arguments = listOf(
                navArgument(PROJECT_ID_ARG) { type = NavType.StringType },
                navArgument(TASK_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            val taskId = backStackEntry.arguments?.getString(TASK_ID_ARG).orEmpty()
            TaskDetailScreen(
                projectId = projectId,
                taskId = taskId,
                onBack = { navController.popBackStack() },
                onOpenComposer = { navController.navigate(Routes.studentSubmissionComposerRoute(projectId, taskId)) },
                onOpenReview = { navController.navigate(Routes.studentProjectReviewRoute(projectId, taskId)) },
            )
        }

        // ── PJ-05 · Submission Composer ─────────────────────────────────────────
        // Back → PJ-04 (a plain pop; the screen itself saves the draft first — see
        // SubmissionComposerScreen's own doc comment). A successful submit pops back down to
        // PJ-04 before pushing PJ-06, so repeated resubmit cycles never pile up duplicate
        // composer/review entries on the stack.
        composable(
            route = Routes.STUDENT_SUBMISSION_COMPOSER,
            arguments = listOf(
                navArgument(PROJECT_ID_ARG) { type = NavType.StringType },
                navArgument(TASK_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            val taskId = backStackEntry.arguments?.getString(TASK_ID_ARG).orEmpty()
            SubmissionComposerScreen(
                projectId = projectId,
                taskId = taskId,
                onBack = { navController.popBackStack() },
                onSubmitted = {
                    navController.navigate(Routes.studentProjectReviewRoute(projectId, taskId)) {
                        popUpTo(Routes.studentTaskDetailRoute(projectId, taskId)) { inclusive = false }
                        launchSingleTop = true
                    }
                },
            )
        }

        // ── PJ-06 · AI Review & Rubric ───────────────────────────────────────────
        // Back → PJ-04, a plain pop; it never resubmits or re-requests a review (getReview()
        // is only ever called from PJ-06's own load(), which a back navigation does not
        // trigger). Resubmit drops back to PJ-04 before pushing PJ-05, same anchor rule as
        // the composer above. Continue pops the whole task workflow back to PJ-03.
        composable(
            route = Routes.STUDENT_PROJECT_REVIEW,
            arguments = listOf(
                navArgument(PROJECT_ID_ARG) { type = NavType.StringType },
                navArgument(TASK_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            val taskId = backStackEntry.arguments?.getString(TASK_ID_ARG).orEmpty()
            ProjectReviewScreen(
                projectId = projectId,
                taskId = taskId,
                onBack = { navController.popBackStack() },
                onResubmit = {
                    navController.navigate(Routes.studentSubmissionComposerRoute(projectId, taskId)) {
                        popUpTo(Routes.studentTaskDetailRoute(projectId, taskId)) { inclusive = false }
                        launchSingleTop = true
                    }
                },
                onContinueProject = {
                    navController.popBackStack(Routes.studentMilestoneBoardRoute(projectId), inclusive = false)
                },
                onOpenPeerReview = { navController.navigate(Routes.STUDENT_PEER_REVIEW) },
            )
        }

        // ── PJ-07 · Peer Review ───────────────────────────────────────────────────
        // No arguments — this slice's one deterministic assignment. Back → wherever it was
        // opened from (PJ-06's contextual action), a plain pop; nothing here resubmits or
        // duplicates a review on the way back.
        composable(Routes.STUDENT_PEER_REVIEW) {
            PeerReviewScreen(onBack = { navController.popBackStack() })
        }

        // ── PJ-08 · Team Workspace ──────────────────────────────────────────────────
        // Back → PJ-03 (a plain pop), reached only from PJ-03's own Team-mode top-bar action.
        composable(
            route = Routes.STUDENT_TEAM_WORKSPACE,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            TeamWorkspaceScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
            )
        }

        // ── PJ-09 · Reflection Log ─────────────────────────────────────────────────
        // Back → PJ-03 (a plain pop), reached only from a reachable milestone's own contextual
        // action there.
        composable(
            route = Routes.STUDENT_REFLECTION_LOG,
            arguments = listOf(
                navArgument(PROJECT_ID_ARG) { type = NavType.StringType },
                navArgument(MILESTONE_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            val milestoneId = backStackEntry.arguments?.getString(MILESTONE_ID_ARG).orEmpty()
            ReflectionLogScreen(
                projectId = projectId,
                milestoneId = milestoneId,
                onBack = { navController.popBackStack() },
            )
        }

        // ── PJ-10 · Project Portfolio ────────────────────────────────────────────────
        // No arguments — the one showcase. Back → PJ-01, a plain pop.
        composable(Routes.STUDENT_PORTFOLIO) {
            PortfolioScreen(
                onBack = { navController.popBackStack() },
                onOpenShowcaseDetail = { projectId ->
                    navController.navigate(Routes.studentProjectShowcaseDetailRoute(projectId))
                },
            )
        }

        // ── PJ-10 · Project Showcase Detail ──────────────────────────────────────────
        // Back → the portfolio, a plain pop.
        composable(
            route = Routes.STUDENT_PROJECT_SHOWCASE_DETAIL,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            ProjectShowcaseDetailScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
                onOpenCertificate = { pid -> navController.navigate(Routes.studentProjectCertificateRoute(pid)) },
            )
        }

        // ── PJ-11 · Project Certificate ──────────────────────────────────────────────
        // Back → the showcase detail, a plain pop. "Verify" pushes the actual public A-12
        // route with this certificate's own code — the same screen anyone else would land on.
        composable(
            route = Routes.STUDENT_PROJECT_CERTIFICATE,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            ProjectCertificateScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
                onVerify = { code -> navController.navigate(Routes.certificateVerifyRoute(code)) },
            )
        }

        // ── PJ-12 · Materials & Safety Sheet ─────────────────────────────────────────
        // Back → PJ-02, a plain pop. Only ever reached for a Physical project.
        composable(
            route = Routes.STUDENT_MATERIALS_SAFETY,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            MaterialsSafetyScreen(
                projectId = projectId,
                onBack = { navController.popBackStack() },
            )
        }
    }
}

/** Resolves the one [TutorChatViewModel] shared by ST-04 and ST-05, graph-scoped.
 *  [initialPrompt] only matters on the instance's first creation — see the ViewModel's own
 *  doc comment — so ST-05 (which never passes one) safely resolves the same already-primed
 *  instance ST-04 created. */
@Composable
private fun tutorChatViewModel(
    navController: NavHostController,
    backStackEntry: NavBackStackEntry,
    lessonId: String,
    initialPrompt: String? = null,
): TutorChatViewModel {
    val parentEntry = remember(backStackEntry) {
        navController.getBackStackEntry(Routes.TUTOR_GRAPH)
    }
    return koinViewModel(viewModelStoreOwner = parentEntry, parameters = { parametersOf(lessonId, initialPrompt) })
}

/**
 * Phase 3 — Teacher (18 screens). TC-02 Dashboard and TC-03 Courses are real this slice;
 * Students/Projects/Me stay the honest placeholders they always were, zero change to their
 * call sites, same [RoleShell] `overrides` mechanism ST-01/PJ-01 already established.
 *
 * [tabNavController] is created here (not left to RoleShell's own default) purely so the
 * Dashboard override's "Courses Snapshot" can switch to the Courses tab the exact same way
 * [com.rork.eduspark.ui.components.nav.RoleTabBar]'s own tap handler already does — no change
 * to RoleShell itself, since `tabNavController` was already an exposed parameter.
 */
private const val TEACHER_OPEN_TAB = "teacher_open_tab"

private fun NavGraphBuilder.teacherGraph(navController: NavHostController) {
    navigation(startDestination = Routes.TEACHER_DASHBOARD, route = Routes.TEACHER_GRAPH) {
        composable(Routes.TEACHER_DASHBOARD) { shellEntry ->
            val tabNavController = rememberNavController()
            val requestedTab by shellEntry.savedStateHandle
                .getStateFlow(TEACHER_OPEN_TAB, "")
                .collectAsStateWithLifecycle()
            LaunchedEffect(requestedTab) {
                if (requestedTab.isBlank()) return@LaunchedEffect
                tabNavController.navigate(requestedTab) {
                    popUpTo(TeacherTabs.first().route) { saveState = true }
                    launchSingleTop = true
                    restoreState = true
                }
                shellEntry.savedStateHandle[TEACHER_OPEN_TAB] = ""
            }
            val messagesBadgeViewModel = koinViewModel<MessagesBadgeViewModel>()
            val unreadMessages by messagesBadgeViewModel.unreadCount.collectAsStateWithLifecycle()
            val drawerViewModel = koinViewModel<StudentNavigationDrawerViewModel>()
            val drawerState by drawerViewModel.state.collectAsStateWithLifecycle()
            LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
                drawerViewModel.refreshTeacherIdentity()
            }
            RoleShell(
                tabs = TeacherTabs,
                tabNavController = tabNavController,
                unreadMessages = unreadMessages,
                onOpenMessages = {
                    navController.navigate(Routes.MESSAGES) {
                        launchSingleTop = true
                    }
                },
                homeRoute = Routes.TEACHER_DASHBOARD,
                homeLabelRes = R.string.tab_teacher_dashboard,
                drawerUser = drawerState.user?.let { user ->
                    RoleDrawerUser(
                        displayName = drawerState.teacherDisplayName ?: user.displayName,
                        email = user.email,
                    )
                },
                drawerSections = TeacherDrawerSections,
                onOpenDrawerDestination = { route -> navController.navigate(route) },
                onConfirmSignOut = {
                    drawerViewModel.signOut {
                        navController.navigate(Routes.ROLE_SELECT) {
                            popUpTo(Routes.TEACHER_GRAPH) { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                },
                isSigningOut = drawerState.isSigningOut,
                screenIdFor = { route ->
                    when (route) {
                        Routes.TEACHER_DASHBOARD -> "TC-02 · Teacher Dashboard"
                        Routes.TEACHER_COURSES -> "TC-03 · Courses List"
                        Routes.TEACHER_STUDENTS -> "TC-12 · Students List"
                        Routes.TEACHER_QUIZZES -> "TC-10 · Quiz Builder"
                        Routes.TEACHER_ME -> "TC-16 · Teacher Account"
                        else -> "TC-16 · Teacher Account"
                    }
                },
                phaseFor = { "Phase 3" },
                overrides = mapOf<String, @Composable () -> Unit>(
                    Routes.TEACHER_DASHBOARD to {
                        TeacherDashboardScreen(
                            onOpenCourses = {
                                tabNavController.navigate(Routes.TEACHER_COURSES) {
                                    popUpTo(TeacherTabs.first().route) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            onOpenLessonProcessing = { courseId, lessonId ->
                                navController.navigate(Routes.teacherLessonProcessingRoute(courseId, lessonId))
                            },
                            onOpenVoiceProfile = { navController.navigate(Routes.TEACHER_VOICE_PROFILE) },
                            onOpenQuizzes = {
                                tabNavController.navigate(Routes.TEACHER_QUIZZES) {
                                    popUpTo(TeacherTabs.first().route) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            onOpenGrades = { navController.navigate(Routes.TEACHER_GRADES) },
                            onOpenAnalytics = { navController.navigate(Routes.TEACHER_ANALYTICS) },
                            onOpenStudents = {
                                tabNavController.navigate(Routes.TEACHER_STUDENTS) {
                                    popUpTo(TeacherTabs.first().route) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            onOpenMessages = { navController.navigate(Routes.MESSAGES) },
                        )
                    },
                    Routes.TEACHER_COURSES to {
                        TeacherCoursesScreen(
                            onOpenCourse = { courseId -> navController.navigate(Routes.teacherCourseDetailRoute(courseId)) },
                        )
                    },
                    Routes.TEACHER_STUDENTS to {
                        TeacherStudentsScreen(
                            onOpenStudentDetail = { studentId -> navController.navigate(Routes.teacherStudentDetailRoute(studentId)) },
                        )
                    },
                    Routes.TEACHER_QUIZZES to {
                        TeacherQuizListScreen(
                            onOpenEditor = { quizId -> navController.navigate(Routes.teacherQuizEditorRoute(quizId)) },
                            onOpenResults = { quizId -> navController.navigate(Routes.teacherQuizResultsRoute(quizId)) },
                        )
                    },
                    Routes.TEACHER_ME to {
                        TeacherAccountScreen(
                            onOpenProfile = { navController.navigate(Routes.TEACHER_PROFILE_EDIT) },
                            onOpenVoice = { navController.navigate(Routes.TEACHER_VOICE_PROFILE) },
                            onOpenTeachingPage = { navController.navigate(Routes.TEACHER_LIVE_PREVIEW) },
                            onLogout = {
                                drawerViewModel.signOut {
                                    navController.navigate(Routes.ROLE_SELECT) {
                                        popUpTo(Routes.TEACHER_GRAPH) { inclusive = true }
                                        launchSingleTop = true
                                    }
                                }
                            },
                        )
                    },
                ),
            )
        }

        // ── TC-04 · Course Detail ────────────────────────────────────────────
        composable(
            route = Routes.TEACHER_COURSE_DETAIL,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            TeacherCourseDetailScreen(
                courseId = courseId,
                onBack = { navController.popBackStack() },
                onAddLesson = { navController.navigate(Routes.teacherLessonUploadRoute(courseId)) },
                onOpenProcessingLesson = { lessonId ->
                    navController.navigate(Routes.teacherLessonProcessingRoute(courseId, lessonId))
                },
                onOpenLessonEditor = { lessonId ->
                    navController.navigate(Routes.teacherLessonEditorRoute(courseId, lessonId))
                },
                onOpenLessonPreview = { lessonId ->
                    navController.navigate(Routes.teacherLessonPreviewRoute(courseId, lessonId))
                },
                onOpenStudents = {
                    navController.getBackStackEntry(Routes.TEACHER_DASHBOARD)
                        .savedStateHandle[TEACHER_OPEN_TAB] = Routes.TEACHER_STUDENTS
                    navController.popBackStack()
                },
                onOpenStudent = { studentId ->
                    navController.navigate(Routes.teacherStudentDetailRoute(studentId))
                },
            )
        }

        // ── TC-05 · Lesson Upload ────────────────────────────────────────────
        composable(
            route = Routes.TEACHER_LESSON_UPLOAD,
            arguments = listOf(navArgument(COURSE_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            TeacherLessonUploadScreen(
                courseId = courseId,
                onBack = { navController.popBackStack() },
                onUploaded = { lessonId ->
                    // TC-05 itself is popped on the way to TC-06 — same "the finished composer
                    // never sits behind the next screen" shape PJ-05 → PJ-06 already uses.
                    navController.navigate(Routes.teacherLessonProcessingRoute(courseId, lessonId)) {
                        popUpTo(Routes.teacherCourseDetailRoute(courseId)) { inclusive = false }
                        launchSingleTop = true
                    }
                },
            )
        }

        // ── TC-06 · Lesson Processing Status ─────────────────────────────────
        composable(
            route = Routes.TEACHER_LESSON_PROCESSING,
            arguments = listOf(
                navArgument(COURSE_ID_ARG) { type = NavType.StringType },
                navArgument(LESSON_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
            TeacherLessonProcessingScreen(
                courseId = courseId,
                lessonId = lessonId,
                onBack = { navController.popBackStack() },
                onOpenPreview = { previewLessonId ->
                    navController.navigate(Routes.teacherLessonPreviewRoute(courseId, previewLessonId))
                },
            )
        }

        // ── TC-07 · Lesson Editor ─────────────────────────────────────────────
        composable(
            route = Routes.TEACHER_LESSON_EDITOR,
            arguments = listOf(
                navArgument(COURSE_ID_ARG) { type = NavType.StringType },
                navArgument(LESSON_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
            TeacherLessonEditorScreen(
                courseId = courseId,
                lessonId = lessonId,
                onBack = { navController.popBackStack() },
                onOpenPreview = { previewLessonId -> navController.navigate(Routes.teacherLessonPreviewRoute(courseId, previewLessonId)) },
                onPublished = { publishedLessonId ->
                    // Same "the finished screen never sits behind the next one" shape TC-05 → TC-06 already uses.
                    navController.navigate(Routes.teacherLessonPreviewRoute(courseId, publishedLessonId)) {
                        popUpTo(Routes.teacherCourseDetailRoute(courseId)) { inclusive = false }
                        launchSingleTop = true
                    }
                },
            )
        }

        // ── TC-08 · Lesson Preview ────────────────────────────────────────────
        composable(
            route = Routes.TEACHER_LESSON_PREVIEW,
            arguments = listOf(
                navArgument(COURSE_ID_ARG) { type = NavType.StringType },
                navArgument(LESSON_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val courseId = backStackEntry.arguments?.getString(COURSE_ID_ARG).orEmpty()
            val lessonId = backStackEntry.arguments?.getString(LESSON_ID_ARG).orEmpty()
            TeacherLessonPreviewScreen(
                courseId = courseId,
                lessonId = lessonId,
                onBack = { navController.popBackStack() },
                onEdit = { editLessonId ->
                    navController.navigate(Routes.teacherLessonEditorRoute(courseId, editLessonId))
                },
            )
        }

        // ── TC-09 · Voice Profile — Account hub is the canonical entry. ──
        composable(Routes.TEACHER_VOICE_PROFILE) {
            TeacherVoiceProfileScreen(onBack = { navController.popBackStack() })
        }

        composable(Routes.TEACHER_PROFILE_EDIT) {
            TeacherProfileScreen(
                onBack = { navController.popBackStack() },
                onSaved = { navController.popBackStack() },
            )
        }

        // ── TC-10 · Quiz Builder — quiz management root, also reached from TC-02's Dashboard. ──
        composable(Routes.TEACHER_QUIZZES) {
            TeacherQuizListScreen(
                onBack = { navController.popBackStack() },
                onOpenEditor = { quizId -> navController.navigate(Routes.teacherQuizEditorRoute(quizId)) },
                onOpenResults = { quizId -> navController.navigate(Routes.teacherQuizResultsRoute(quizId)) },
            )
        }

        composable(
            route = Routes.TEACHER_QUIZ_EDITOR,
            arguments = listOf(navArgument(QUIZ_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val quizId = backStackEntry.arguments?.getString(QUIZ_ID_ARG).orEmpty()
            TeacherQuizEditorScreen(quizId = quizId, onBack = { navController.popBackStack() })
        }

        // ── TC-11 · Quiz Results — reached only from a Published quiz's own Results action. ──
        composable(
            route = Routes.TEACHER_QUIZ_RESULTS,
            arguments = listOf(navArgument(QUIZ_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val quizId = backStackEntry.arguments?.getString(QUIZ_ID_ARG).orEmpty()
            TeacherQuizResultsScreen(
                quizId = quizId,
                onBack = { navController.popBackStack() },
                onOpenEditor = { navController.navigate(Routes.teacherQuizEditorRoute(quizId)) },
                onOpenEssayGrade = { studentId, questionId ->
                    navController.navigate(Routes.teacherQuizEssayGradeRoute(quizId, studentId, questionId))
                },
            )
        }

        composable(
            route = Routes.TEACHER_QUIZ_ESSAY_GRADE,
            arguments = listOf(
                navArgument(QUIZ_ID_ARG) { type = NavType.StringType },
                navArgument(TEACHER_STUDENT_ID_ARG) { type = NavType.StringType },
                navArgument(ESSAY_QUESTION_ID_ARG) { type = NavType.StringType },
            ),
        ) { backStackEntry ->
            val quizId = backStackEntry.arguments?.getString(QUIZ_ID_ARG).orEmpty()
            val studentId = backStackEntry.arguments?.getString(TEACHER_STUDENT_ID_ARG).orEmpty()
            val questionId = backStackEntry.arguments?.getString(ESSAY_QUESTION_ID_ARG).orEmpty()
            TeacherEssayGradeScreen(
                quizId = quizId,
                studentId = studentId,
                questionId = questionId,
                onBack = { navController.popBackStack() },
                onOpenNext = { nextStudentId, nextQuestionId ->
                    navController.navigate(Routes.teacherQuizEssayGradeRoute(quizId, nextStudentId, nextQuestionId)) {
                        popUpTo(backStackEntry.destination.id) { inclusive = true }
                    }
                },
            )
        }

        // ── TC-13 · Student Profile — Teacher View — reached from TC-12's student row tap or TC-15's at-risk list. ──
        composable(
            route = Routes.TEACHER_STUDENT_DETAIL,
            arguments = listOf(navArgument(TEACHER_STUDENT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val studentId = backStackEntry.arguments?.getString(TEACHER_STUDENT_ID_ARG).orEmpty()
            TeacherStudentProfileScreen(
                studentId = studentId,
                onBack = { navController.popBackStack() },
                onOpenParentNote = { noteStudentId ->
                    navController.navigate(Routes.teacherParentNoteRoute(noteStudentId))
                },
                onOpenParentChat = { threadId ->
                    navController.navigate(Routes.messageThreadRoute(threadId))
                },
            )
        }

        composable(
            route = Routes.TEACHER_PARENT_NOTE,
            arguments = listOf(navArgument(TEACHER_STUDENT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val studentId = backStackEntry.arguments?.getString(TEACHER_STUDENT_ID_ARG).orEmpty()
            TeacherParentNoteScreen(
                studentId = studentId,
                onBack = { navController.popBackStack() },
            )
        }

        // ── TC-14 · Grades — also reached from TC-02's Dashboard. ──
        composable(Routes.TEACHER_GRADES) {
            TeacherGradebookScreen(onBack = { navController.popBackStack() })
        }

        // ── TC-15 · Teacher Analytics — also reached from TC-02's Dashboard. ──
        composable(Routes.TEACHER_ANALYTICS) {
            TeacherAnalyticsScreen(
                onBack = { navController.popBackStack() },
                onOpenCourse = { courseId -> navController.navigate(Routes.teacherCourseDetailRoute(courseId)) },
                onOpenQuizResults = { quizId -> navController.navigate(Routes.teacherQuizResultsRoute(quizId)) },
                onOpenStudentDetail = { studentId -> navController.navigate(Routes.teacherStudentDetailRoute(studentId)) },
            )
        }

        // ── TC-16 · Teaching Page — reached from the Account hub. ──
        composable(Routes.TEACHER_LIVE_PREVIEW) {
            TeacherProfilePreviewScreen(onBack = { navController.popBackStack() })
        }

        // ── TC-17 · Project Editor — reached from the Teacher "Projects" tab's list/create action. ──
        composable(
            route = Routes.TEACHER_PROJECT_EDITOR,
            arguments = listOf(navArgument(PROJECT_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getString(PROJECT_ID_ARG).orEmpty()
            TeacherProjectEditorScreen(projectId = projectId, onBack = { navController.popBackStack() })
        }

        // ── TC-18 · Project Review Queue — reached from TC-17. ──
        composable(Routes.TEACHER_REVIEW_QUEUE) {
            TeacherReviewQueueScreen(
                onBack = { navController.popBackStack() },
                onOpenSubmission = { submissionId -> navController.navigate(Routes.teacherReviewDetailRoute(submissionId)) },
            )
        }

        composable(
            route = Routes.TEACHER_REVIEW_DETAIL,
            arguments = listOf(navArgument(SUBMISSION_ID_ARG) { type = NavType.StringType }),
        ) { backStackEntry ->
            val submissionId = backStackEntry.arguments?.getString(SUBMISSION_ID_ARG).orEmpty()
            TeacherReviewDetailScreen(submissionId = submissionId, onBack = { navController.popBackStack() })
        }
    }
}

/** Phase 4 — Parent (14 screens). */
private fun NavGraphBuilder.parentGraph() {
    navigation(startDestination = Routes.PARENT_HOME, route = Routes.PARENT_GRAPH) {
        composable(Routes.PARENT_HOME) {
            RoleShell(
                tabs = ParentTabs,
                screenIdFor = { route ->
                    when (route) {
                        Routes.PARENT_HOME -> "PR-02 · Parent Home"
                        Routes.PARENT_PROGRESS -> "PR-04 · Performance"
                        Routes.PARENT_REPORTS -> "PR-10 · Reports"
                        Routes.PARENT_MESSAGES -> "X-02 · Conversation Thread"
                        else -> "PR-13 · Parent Notifications"
                    }
                },
                phaseFor = { "Phase 4" },
            )
        }
    }
}

private fun NavGraphBuilder.placeholder(
    route: String,
    screenId: String,
    phase: String,
    backendPending: Boolean = false,
) {
    composable(route) {
        PlaceholderScreen(screenId = screenId, phase = phase, backendPending = backendPending)
    }
}
