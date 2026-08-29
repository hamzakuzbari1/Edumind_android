package com.rork.eduspark.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navigation
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.ThemeMode
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.FeatureAvailability
import com.rork.eduspark.ui.screens.PlaceholderScreen
import com.rork.eduspark.ui.screens.auth.LoginScreen
import com.rork.eduspark.ui.screens.auth.RegisterScreen
import com.rork.eduspark.ui.screens.auth.RoleSelectScreen
import com.rork.eduspark.ui.screens.auth.SplashDecision
import com.rork.eduspark.ui.screens.auth.SplashScreen
import com.rork.eduspark.ui.screens.auth.SplashViewModel
import com.rork.eduspark.ui.screens.auth.ValueCarouselScreen
import com.rork.eduspark.ui.screens.auth.ValueCarouselViewModel
import com.rork.eduspark.ui.screens.foundation.FoundationScreen
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * The application navigation graph.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Four graphs, matching the Screen Inventory:
 *   • auth    — A-01…A-13, the Phase 0 entry funnel
 *   • student — Phase 1 + 2, five tabs
 *   • teacher — Phase 3, five tabs
 *   • parent  — Phase 4, five tabs
 *
 * plus A-12 Certificate Verification, which sits OUTSIDE every graph because it is public,
 * deep-linked and must render with no session at all.
 *
 * **Built so far: A-01 → A-07 — the entry funnel and the three register forks.** Everything
 * past A-07 still renders an honest [PlaceholderScreen] naming its screen ID and phase. The foundation gallery stays
 * registered at [Routes.FOUNDATION] as a development surface, but it is no longer the start
 * destination — the app now opens on the real splash.
 */
@Composable
fun AppNavigation(
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    themeMode: ThemeMode = ThemeMode.System,
    onThemeModeChange: (ThemeMode) -> Unit = {},
    numeralSystem: NumeralSystem = NumeralSystem.Western,
    onNumeralSystemChange: (NumeralSystem) -> Unit = {},
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
        studentGraph()
        teacherGraph()
        parentGraph()

        // A-12 — public, no auth, reached by deep link. Deliberately outside every graph.
        composable(Routes.CERTIFICATE_VERIFY) {
            PlaceholderScreen(screenId = "A-12 · Certificate Verification", phase = "Phase 0")
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
                    SplashDecision.Login -> navController.replaceWith(Routes.LOGIN)
                    is SplashDecision.Home -> navController.openRoleShell(decision.role)
                    else -> Unit
                }
            }
        }

        // ── A-02 · Value Carousel ────────────────────────────────────────
        composable(Routes.VALUE_CAROUSEL) {
            val viewModel = koinViewModel<ValueCarouselViewModel>()
            ValueCarouselScreen(
                locale = locale,
                onSelectLocale = onSelectLocale,
                onFinished = {
                    viewModel.markSeen()
                    navController.navigate(Routes.ROLE_SELECT)
                },
            )
        }

        // ── A-03 · Role Select ───────────────────────────────────────────
        composable(Routes.ROLE_SELECT) {
            RoleSelectScreen(
                locale = locale,
                onSelectLocale = onSelectLocale,
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
                onBack = { navController.popBackStack() },
            )
        }

        // ── A-04 · Login ─────────────────────────────────────────────────
        composable(Routes.LOGIN) {
            val canGoBack = navController.previousBackStackEntry != null

            LoginScreen(
                locale = locale,
                onSelectLocale = onSelectLocale,
                onAuthenticated = navController::openRoleShell,
                onTwoFactorRequired = { navController.navigate(Routes.TWO_FACTOR) },
                onVerifyEmail = { navController.navigate(Routes.VERIFY_EMAIL) },
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
        registerDestination(navController, Routes.REGISTER_STUDENT, UserRole.Student, locale, onSelectLocale)
        registerDestination(navController, Routes.REGISTER_PARENT, UserRole.Parent, locale, onSelectLocale)
        registerDestination(navController, Routes.REGISTER_TEACHER, UserRole.Teacher, locale, onSelectLocale)

        // ── Not built yet — A-08 … A-13 ──────────────────────────────────
        placeholder(Routes.VERIFY_EMAIL, "A-08 · Verify Email", "Phase 0")
        placeholder(Routes.TWO_FACTOR, "A-09 · Two-Factor Verify", "Phase 0")
        placeholder(Routes.FORGOT_PASSWORD, "A-10 · Forgot Password", "Phase 0")
        placeholder(Routes.RESET_PASSWORD, "A-11 · Reset Password", "Phase 0")
        placeholder(Routes.LOCALE_SWITCH, "A-13 · Locale Switch Transition", "Phase 0")
    }
}

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
            onRegistered = {
                navController.navigate(Routes.VERIFY_EMAIL) { launchSingleTop = true }
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

/** Signed in: the whole auth graph is dropped so back cannot return to a login form. */
private fun NavHostController.openRoleShell(role: UserRole) {
    val destination = when (role) {
        UserRole.Student -> Routes.STUDENT_GRAPH
        UserRole.Teacher -> Routes.TEACHER_GRAPH
        UserRole.Parent -> Routes.PARENT_GRAPH
    }
    navigate(destination) {
        popUpTo(Routes.AUTH_GRAPH) { inclusive = true }
        launchSingleTop = true
    }
}

/** Runs [onDecision] once per distinct splash decision. */
@Composable
private fun LaunchedDecision(
    decision: SplashDecision,
    onDecision: (SplashDecision) -> Unit,
) {
    androidx.compose.runtime.LaunchedEffect(decision) { onDecision(decision) }
}

/** Phase 1 (Student Core) + Phase 2 (Projects). */
private fun NavGraphBuilder.studentGraph() {
    navigation(startDestination = Routes.STUDENT_HOME, route = Routes.STUDENT_GRAPH) {
        composable(Routes.STUDENT_HOME) {
            RoleShell(
                tabs = StudentTabs,
                screenIdFor = { route ->
                    when (route) {
                        Routes.STUDENT_HOME -> "ST-01 · Student Home"
                        Routes.STUDENT_COURSES -> "ST-02 · Course Detail"
                        Routes.STUDENT_PROJECTS -> "PJ-01 · Projects Hub"
                        Routes.STUDENT_ENGLISH -> "LN-01 · Languages Hub"
                        else -> "ST-22 · Student Profile"
                    }
                },
                phaseFor = { route ->
                    when (route) {
                        Routes.STUDENT_PROJECTS -> "Phase 2"
                        Routes.STUDENT_ENGLISH -> "Phase 5"
                        else -> "Phase 1"
                    }
                },
                // Projects has no backend at all — the shell says so rather than implying one.
                backendPendingFor = { route ->
                    route == Routes.STUDENT_PROJECTS && !FeatureAvailability.PROJECTS_BACKEND_READY
                },
            )
        }
    }
}

/** Phase 3 — Teacher (18 screens). */
private fun NavGraphBuilder.teacherGraph() {
    navigation(startDestination = Routes.TEACHER_DASHBOARD, route = Routes.TEACHER_GRAPH) {
        composable(Routes.TEACHER_DASHBOARD) {
            RoleShell(
                tabs = TeacherTabs,
                screenIdFor = { route ->
                    when (route) {
                        Routes.TEACHER_DASHBOARD -> "TC-02 · Teacher Dashboard"
                        Routes.TEACHER_COURSES -> "TC-03 · Courses List"
                        Routes.TEACHER_STUDENTS -> "TC-12 · Students List"
                        Routes.TEACHER_PROJECTS -> "TC-17 · Project Authoring"
                        else -> "TC-16 · Teacher Profile / CV"
                    }
                },
                phaseFor = { "Phase 3" },
                backendPendingFor = { route ->
                    route == Routes.TEACHER_PROJECTS && !FeatureAvailability.PROJECTS_BACKEND_READY
                },
            )
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
