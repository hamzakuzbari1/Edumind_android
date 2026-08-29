package com.rork.eduspark.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.nav.BadgedTopBarAction
import com.rork.eduspark.ui.components.nav.RoleTabBar
import com.rork.eduspark.ui.components.scaffold.EduRootScaffold
import com.rork.eduspark.ui.screens.PlaceholderScreen

/**
 * The per-role tab shell.
 *
 * One shell serves all three roles because the *structure* is identical — five tabs, a
 * TopBar carrying Messages and Notifications with badge counts, and a nested NavHost so
 * each tab keeps its own back stack. Only the tab list differs.
 *
 * Messages and Notifications live in the TopBar rather than costing a tab slot
 * (Screen Inventory · Navigation shells).
 */
@Composable
fun RoleShell(
    tabs: List<TabDestination>,
    modifier: Modifier = Modifier,
    unreadMessages: Int = 0,
    unreadNotifications: Int = 0,
    tabNavController: NavHostController = rememberNavController(),
    screenIdFor: (String) -> String,
    phaseFor: (String) -> String,
    backendPendingFor: (String) -> Boolean = { false },
) {
    val backStackEntry by tabNavController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route ?: tabs.first().route
    val currentTab = tabs.firstOrNull { it.route == currentRoute } ?: tabs.first()

    EduRootScaffold(
        title = stringResource(currentTab.labelRes),
        actions = {
            BadgedTopBarAction(
                icon = Icons.Filled.Forum,
                contentDescription = stringResource(R.string.topbar_messages),
                count = unreadMessages,
                onClick = { /* X-01 Messages — Phase 6 */ },
            )
            BadgedTopBarAction(
                icon = Icons.Filled.Notifications,
                contentDescription = stringResource(R.string.topbar_notifications),
                count = unreadNotifications,
                onClick = { /* X-04 Notifications Centre — Phase 6 */ },
            )
        },
        bottomBar = {
            RoleTabBar(
                tabs = tabs,
                currentRoute = currentRoute,
                onTabSelected = { tab ->
                    tabNavController.navigate(tab.route) {
                        // Standard tab behaviour: single instance per tab, state preserved,
                        // and back from any tab returns to the first tab, then exits.
                        popUpTo(tabs.first().route) { saveState = true }
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
            startDestination = tabs.first().route,
            modifier = Modifier.padding(innerPadding),
        ) {
            tabs.forEach { tab ->
                composable(tab.route) {
                    // Screens are built in their phase; the shell is real today.
                    PlaceholderScreen(
                        screenId = screenIdFor(tab.route),
                        phase = phaseFor(tab.route),
                        backendPending = backendPendingFor(tab.route),
                    )
                }
            }
        }
    }
}
