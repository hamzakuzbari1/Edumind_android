package com.rork.eduspark.ui.navigation

import androidx.annotation.StringRes
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.Assessment
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Insights
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Forum
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
    const val VERIFY_EMAIL = "auth/verify-email"        // A-08
    const val TWO_FACTOR = "auth/two-factor"            // A-09
    const val FORGOT_PASSWORD = "auth/forgot"           // A-10
    const val RESET_PASSWORD = "auth/reset"             // A-11
    const val CERTIFICATE_VERIFY = "certificate/verify" // A-12 (public, deep-linked)
    const val LOCALE_SWITCH = "auth/locale-switch"      // A-13

    // ── Student graph (Phase 1) ───────────────────────────────────────────
    const val STUDENT_GRAPH = "student"
    const val STUDENT_HOME = "student/home"
    const val STUDENT_COURSES = "student/courses"
    const val STUDENT_PROJECTS = "student/projects"
    const val STUDENT_ENGLISH = "student/english"
    const val STUDENT_ME = "student/me"

    // ── Teacher graph (Phase 3) ───────────────────────────────────────────
    const val TEACHER_GRAPH = "teacher"
    const val TEACHER_DASHBOARD = "teacher/dashboard"
    const val TEACHER_COURSES = "teacher/courses"
    const val TEACHER_STUDENTS = "teacher/students"
    const val TEACHER_PROJECTS = "teacher/projects"
    const val TEACHER_ME = "teacher/me"

    // ── Parent graph (Phase 4) ────────────────────────────────────────────
    const val PARENT_GRAPH = "parent"
    const val PARENT_HOME = "parent/home"
    const val PARENT_PROGRESS = "parent/progress"
    const val PARENT_REPORTS = "parent/reports"
    const val PARENT_MESSAGES = "parent/messages"
    const val PARENT_ME = "parent/me"

    // ── Cross-cutting (Phase 6) ───────────────────────────────────────────
    const val MESSAGES = "messages"
    const val NOTIFICATIONS = "notifications"
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

/** Student tabs — الرئيسية · موادي · مشاريعي · الإنجليزية · حسابي */
val StudentTabs: List<TabDestination> = listOf(
    TabDestination(Routes.STUDENT_HOME, R.string.tab_student_home, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.STUDENT_COURSES, R.string.tab_student_courses, Icons.Outlined.AutoStories, Icons.Filled.AutoStories),
    TabDestination(Routes.STUDENT_PROJECTS, R.string.tab_student_projects, Icons.Outlined.Build, Icons.Filled.Build),
    TabDestination(Routes.STUDENT_ENGLISH, R.string.tab_student_english, Icons.Outlined.Language, Icons.Filled.Language),
    TabDestination(Routes.STUDENT_ME, R.string.tab_student_me, Icons.Outlined.Person, Icons.Filled.Person),
)

/** Teacher tabs — لوحتي · موادي · طلابي · مشاريع · حسابي */
val TeacherTabs: List<TabDestination> = listOf(
    TabDestination(Routes.TEACHER_DASHBOARD, R.string.tab_teacher_dashboard, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.TEACHER_COURSES, R.string.tab_teacher_courses, Icons.Outlined.AutoStories, Icons.Filled.AutoStories),
    TabDestination(Routes.TEACHER_STUDENTS, R.string.tab_teacher_students, Icons.Outlined.Groups, Icons.Filled.Groups),
    TabDestination(Routes.TEACHER_PROJECTS, R.string.tab_teacher_projects, Icons.Outlined.Build, Icons.Filled.Build),
    TabDestination(Routes.TEACHER_ME, R.string.tab_teacher_me, Icons.Outlined.Person, Icons.Filled.Person),
)

/** Parent tabs — الرئيسية · التقدم · التقارير · الرسائل · حسابي */
val ParentTabs: List<TabDestination> = listOf(
    TabDestination(Routes.PARENT_HOME, R.string.tab_parent_home, Icons.Outlined.Home, Icons.Filled.Home),
    TabDestination(Routes.PARENT_PROGRESS, R.string.tab_parent_progress, Icons.Outlined.Insights, Icons.Filled.Insights),
    TabDestination(Routes.PARENT_REPORTS, R.string.tab_parent_reports, Icons.Outlined.Assessment, Icons.Filled.Assessment),
    TabDestination(Routes.PARENT_MESSAGES, R.string.tab_parent_messages, Icons.Outlined.Forum, Icons.Filled.Forum),
    TabDestination(Routes.PARENT_ME, R.string.tab_parent_me, Icons.Outlined.Person, Icons.Filled.Person),
)
