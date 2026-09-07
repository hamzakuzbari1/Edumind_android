package com.rork.eduspark.ui.components.nav

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import com.rork.eduspark.ui.navigation.TabDestination
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing

/**
 * The per-role bottom tab bar — five tabs maximum, anything else lives one level deeper
 * (Screen Inventory · Navigation shells).
 *
 * Messages and Notifications are deliberately NOT tabs: they sit in the TopBar of every
 * root screen with badge counts, which keeps the five slots for the learning surfaces.
 *
 * Labels are always shown. Icon-only tabs are a literacy and accessibility risk for the
 * parent audience (35–60, low tech-confidence, "clarity over density").
 */
@Composable
fun RoleTabBar(
    tabs: List<TabDestination>,
    currentRoute: String?,
    onTabSelected: (TabDestination) -> Unit,
    modifier: Modifier = Modifier,
) {
    NavigationBar(
        containerColor = EduTheme.colors.surface,
        contentColor = EduTheme.colors.textPrimary,
        tonalElevation = Sizing.hairline * 0, // Elevation is tint + hairline, never a shadow.
        modifier = modifier.height(Sizing.tabBarHeight + Sizing.touchTarget / 2),
    ) {
        tabs.forEach { tab ->
            val selected = currentRoute == tab.route
            val label = stringResource(tab.labelRes)

            NavigationBarItem(
                selected = selected,
                onClick = { onTabSelected(tab) },
                icon = {
                    Icon(
                        imageVector = if (selected) tab.selectedIcon else tab.icon,
                        contentDescription = null,
                        modifier = Modifier.size(Sizing.iconLg),
                    )
                },
                label = {
                    Text(
                        text = label,
                        style = EduTheme.typography.caption,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
                alwaysShowLabel = true,
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = EduTheme.colors.primary,
                    selectedTextColor = EduTheme.colors.primary,
                    indicatorColor = EduTheme.colors.primaryContainer,
                    unselectedIconColor = EduTheme.colors.textSecondary,
                    unselectedTextColor = EduTheme.colors.textSecondary,
                ),
            )
        }
    }
}
