package com.rork.eduspark.ui.navigation

import androidx.annotation.StringRes
import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.activity.compose.BackHandler
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.nav.BadgedTopBarAction
import com.rork.eduspark.ui.components.nav.RoleTabBar
import com.rork.eduspark.ui.components.scaffold.EduRootScaffold
import com.rork.eduspark.ui.screens.PlaceholderScreen
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.launch

data class RoleDrawerUser(
    val displayName: String,
    val email: String,
)

data class RoleDrawerDestination(
    val route: String,
    @param:StringRes val labelRes: Int,
    val icon: ImageVector,
)

data class RoleDrawerSection(
    val destinations: List<RoleDrawerDestination>,
)

/**
 * The per-role tab shell.
 *
 * One shell serves all three roles because the *structure* is identical — five tabs, a
 * TopBar carrying Messages and Notifications with badge counts, and a nested NavHost so
 * each tab keeps its own back stack. Only the tab list differs.
 *
 * Messages and Notifications live in the TopBar rather than costing a tab slot
 * (Screen Inventory · Navigation shells).
 *
 * @param overrides real content for a tab route, keyed by [TabDestination.route]. A tab
 * with no entry here still renders the honest [PlaceholderScreen] it always has — this is
 * how ST-01 becomes real while Courses/Projects/English/Me (and every Teacher/Parent tab)
 * stay exactly as they were, with zero change to their call sites.
 */
@Composable
fun RoleShell(
    tabs: List<TabDestination>,
    modifier: Modifier = Modifier,
    unreadMessages: Int = 0,
    unreadNotifications: Int = 0,
    onOpenMessages: () -> Unit = {},
    onOpenNotifications: () -> Unit = {},
    drawerUser: RoleDrawerUser? = null,
    drawerSections: List<RoleDrawerSection> = emptyList(),
    onOpenDrawerDestination: (String) -> Unit = {},
    onConfirmSignOut: () -> Unit = {},
    isSigningOut: Boolean = false,
    homeRoute: String? = null,
    homeLabelRes: Int? = null,
    tabNavController: NavHostController = rememberNavController(),
    screenIdFor: (String) -> String,
    phaseFor: (String) -> String,
    backendPendingFor: (String) -> Boolean = { false },
    overrides: Map<String, @Composable () -> Unit> = emptyMap(),
) {
    val backStackEntry by tabNavController.currentBackStackEntryAsState()
    val startRoute = homeRoute ?: tabs.first().route
    val currentRoute = backStackEntry?.destination?.route ?: startRoute
    val isStudentTab = StudentTabs.any { it.route == currentRoute }
    val isTeacherTab = TeacherTabs.any { it.route == currentRoute }
    val currentTab = tabs.firstOrNull { it.route == currentRoute }
    val titleRes = currentTab?.labelRes ?: homeLabelRes ?: tabs.first().labelRes
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showSignOutConfirm by rememberSaveable { mutableStateOf(false) }
    val tabRoutes = tabs.map { it.route }.toSet()
    val canOpenDrawer = drawerSections.isNotEmpty()

    BackHandler(enabled = canOpenDrawer && drawerState.isOpen) {
        scope.launch { drawerState.close() }
    }

    if (showSignOutConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.drawer_logout_confirm_title),
            body = stringResource(R.string.drawer_logout_confirm_body),
            confirmLabel = stringResource(R.string.drawer_logout),
            onConfirm = {
                showSignOutConfirm = false
                onConfirmSignOut()
            },
            onDismiss = { showSignOutConfirm = false },
            isDestructive = true,
        )
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = canOpenDrawer,
        drawerContent = {
            if (canOpenDrawer) {
                StudentDrawerSheet(
                    user = drawerUser,
                    sections = drawerSections,
                    currentRoute = currentRoute,
                    homeRoute = homeRoute,
                    tabRoutes = tabRoutes,
                    isSigningOut = isSigningOut,
                    onSelect = { destination ->
                        scope.launch {
                            drawerState.close()
                            if (destination.route == homeRoute || destination.route in tabRoutes) {
                                tabNavController.navigate(destination.route) {
                                    popUpTo(startRoute) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            } else {
                                onOpenDrawerDestination(destination.route)
                            }
                        }
                    },
                    onLogout = {
                        scope.launch { drawerState.close() }
                        showSignOutConfirm = true
                    },
                )
            }
        },
    ) {
        EduRootScaffold(
            title = if (currentRoute == Routes.STUDENT_HOME || currentRoute == Routes.TEACHER_DASHBOARD) {
                stringResource(R.string.st01_brand_wordmark)
            } else {
                stringResource(titleRes)
            },
            showBrandMark = !isStudentTab && !isTeacherTab,
            navigationIcon = if (canOpenDrawer) {
                {
                    EduIconButton(
                        icon = Icons.Filled.Menu,
                        contentDescription = stringResource(
                            if (tabs === TeacherTabs) {
                                R.string.a11y_open_teacher_menu
                            } else {
                                R.string.a11y_open_student_menu
                            },
                        ),
                        onClick = { scope.launch { drawerState.open() } },
                    )
                }
            } else {
                null
            },
            actions = {
                // Messages + Notifications on every root tab shell (Student Home, Teacher, Parent).
                // Nested screens use EduScaffold on the parent nav, so they never inherit this row.
                BadgedTopBarAction(
                    icon = Icons.Filled.Forum,
                    contentDescription = stringResource(R.string.topbar_messages),
                    count = unreadMessages,
                    onClick = onOpenMessages,
                )
                BadgedTopBarAction(
                    icon = Icons.Filled.Notifications,
                    contentDescription = stringResource(R.string.topbar_notifications),
                    count = unreadNotifications,
                    onClick = onOpenNotifications,
                )
            },
            bottomBar = {
                RoleTabBar(
                    tabs = tabs,
                    currentRoute = currentRoute,
                    onTabSelected = { tab ->
                        tabNavController.navigate(tab.route) {
                            // Standard tab behaviour: single instance per tab, state preserved,
                            // and back from any tab returns to the shell's landing route, then exits.
                            popUpTo(startRoute) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                )
            },
            modifier = modifier,
        ) { innerPadding ->
            NavHost(
                navController = tabNavController,
                startDestination = startRoute,
                modifier = Modifier.padding(innerPadding),
            ) {
                (listOfNotNull(homeRoute) + tabs.map { it.route }).distinct().forEach { route ->
                    composable(route) {
                        val override = overrides[route]
                        if (override != null) {
                            override()
                        } else {
                            // Screens are built in their phase; the shell is real today.
                            PlaceholderScreen(
                                screenId = screenIdFor(route),
                                phase = phaseFor(route),
                                backendPending = backendPendingFor(route),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StudentDrawerSheet(
    user: RoleDrawerUser?,
    sections: List<RoleDrawerSection>,
    currentRoute: String,
    homeRoute: String?,
    tabRoutes: Set<String>,
    isSigningOut: Boolean,
    onSelect: (RoleDrawerDestination) -> Unit,
    onLogout: () -> Unit,
) {
    ModalDrawerSheet(
        drawerContainerColor = EduTheme.colors.surface,
        drawerContentColor = EduTheme.colors.textPrimary,
        modifier = Modifier.width(320.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxHeight()
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(Spacing.md),
        ) {
            DrawerUserHeader(user = user)
            Spacer(modifier = Modifier.height(Spacing.sm))
            sections.forEachIndexed { sectionIndex, section ->
                if (sectionIndex > 0) {
                    HorizontalDivider(
                        color = EduTheme.colors.border,
                        modifier = Modifier.padding(vertical = Spacing.sm),
                    )
                }
                section.destinations.forEach { destination ->
                    val selected = destination.route == currentRoute ||
                        (destination.route == homeRoute && currentRoute == homeRoute) ||
                        (destination.route in tabRoutes && destination.route == currentRoute)
                    NavigationDrawerItem(
                        selected = selected,
                        onClick = { onSelect(destination) },
                        icon = {
                            Icon(
                                imageVector = destination.icon,
                                contentDescription = null,
                                modifier = Modifier.size(Sizing.iconLg),
                            )
                        },
                        label = {
                            Text(
                                text = stringResource(destination.labelRes),
                                style = EduTheme.typography.body,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        },
                        colors = NavigationDrawerItemDefaults.colors(
                            selectedContainerColor = EduTheme.colors.primaryContainer,
                            selectedIconColor = EduTheme.colors.primary,
                            selectedTextColor = EduTheme.colors.primary,
                            unselectedIconColor = EduTheme.colors.textSecondary,
                            unselectedTextColor = EduTheme.colors.textPrimary,
                        ),
                    )
                }
            }
            Spacer(modifier = Modifier.height(Spacing.md))
            HorizontalDivider(color = EduTheme.colors.border, modifier = Modifier.padding(vertical = Spacing.sm))
            NavigationDrawerItem(
                selected = false,
                onClick = { if (!isSigningOut) onLogout() },
                icon = {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.Logout,
                        contentDescription = null,
                        tint = EduTheme.colors.danger,
                        modifier = Modifier.size(Sizing.iconLg),
                    )
                },
                label = {
                    Text(
                        text = stringResource(R.string.drawer_logout),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                        color = EduTheme.colors.danger,
                    )
                },
                colors = NavigationDrawerItemDefaults.colors(
                    unselectedContainerColor = EduTheme.colors.surface,
                    unselectedIconColor = EduTheme.colors.danger,
                    unselectedTextColor = EduTheme.colors.danger,
                ),
            )
        }
    }
}

@Composable
private fun DrawerUserHeader(user: RoleDrawerUser?) {
    val displayName = user?.displayName?.takeIf { it.isNotBlank() } ?: stringResource(R.string.app_name)
    val email = user?.email.orEmpty()
    val initial = displayName.take(1)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(48.dp)
                .background(EduTheme.colors.primaryContainer, RoundedCornerShape(Radius.md)),
        ) {
            Text(
                text = initial,
                style = EduTheme.typography.title,
                color = EduTheme.colors.primary,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = displayName,
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (email.isNotBlank()) {
                Text(
                    text = email,
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
