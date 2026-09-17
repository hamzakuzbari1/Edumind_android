package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentAlert
import com.rork.eduspark.data.model.ParentAlertPreference
import com.rork.eduspark.data.model.ParentAlertPreferenceKey
import com.rork.eduspark.data.model.ParentAlertSeverity
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentAlertsScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentAlertsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr11_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentAlertsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentAlertsContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onOpenLinkStudent = onOpenLinkStudent,
                onMarkAlertRead = viewModel::markAlertRead,
                onMarkAllRead = viewModel::markAllRead,
                onPreferenceChange = viewModel::setPreferenceEnabled,
            )
        }
    }
}

@Composable
private fun ParentAlertsContent(
    data: ParentAlertsData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
    onMarkAlertRead: (String) -> Unit,
    onMarkAllRead: () -> Unit,
    onPreferenceChange: (ParentAlertPreferenceKey, Boolean) -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentAlertsEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    val selectedStudent = data.linkedStudents.firstOrNull { it.id == data.selectedStudentId }
        ?: data.linkedStudents.first()

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentAlertsStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }

        val snapshot = data.snapshot
        if (snapshot == null) {
            item { SkeletonCard() }
            item { SkeletonListItem() }
            item { SkeletonCard() }
        } else {
            item {
                ParentAlertsListCard(
                    snapshot = snapshot,
                    onMarkAlertRead = onMarkAlertRead,
                    onMarkAllRead = onMarkAllRead,
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr11_settings_title)) }
            item {
                ParentAlertPreferencesCard(
                    preferences = snapshot.preferences,
                    onPreferenceChange = onPreferenceChange,
                )
            }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentAlertsEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentAlertsIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr11_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr11_empty_body),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                PrimaryButton(
                    text = stringResource(R.string.pr02_empty_action),
                    onClick = onOpenLinkStudent,
                    leadingIcon = Icons.Filled.Link,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        }
    }
}

@Composable
private fun ParentAlertsStudentCard(
    students: List<ParentLinkedStudent>,
    selectedStudent: ParentLinkedStudent,
    onSelectStudent: (String) -> Unit,
) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = selectedStudent.avatarInitial,
                modifier = Modifier.size(Sizing.avatarLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = selectedStudent.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (selectedStudent.gradeLabel.isNotBlank()) {
                    Text(
                        text = selectedStudent.gradeLabel,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
            ParentAlertsIconBadge(
                icon = Icons.Filled.School,
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
                modifier = Modifier.size(Sizing.touchTarget),
            )
        }

        if (students.size > 1) {
            Text(
                text = stringResource(R.string.pr02_student_selector_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(top = Spacing.xs),
            ) {
                items(students, key = { it.id }) { student ->
                    EduChip(
                        label = student.displayName,
                        selected = student.id == selectedStudent.id,
                        onClick = { onSelectStudent(student.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ParentAlertsListCard(
    snapshot: ParentAlertsSnapshot,
    onMarkAlertRead: (String) -> Unit,
    onMarkAllRead: () -> Unit,
) {
    val colors = EduTheme.colors
    val unreadCount = snapshot.alerts.count { it.isUnread }

    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr11_alerts_section),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr11_unread_count, numeral(unreadCount)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            GhostButton(
                text = stringResource(R.string.pr11_mark_all_read),
                onClick = onMarkAllRead,
                enabled = unreadCount > 0,
                leadingIcon = Icons.Filled.Check,
            )
        }

        if (snapshot.alerts.isEmpty()) {
            Text(
                text = stringResource(R.string.pr11_no_alerts),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
        snapshot.alerts.forEachIndexed { index, alert ->
            ParentAlertRow(
                alert = alert,
                onMarkRead = { onMarkAlertRead(alert.id) },
            )
            if (index != snapshot.alerts.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentAlertRow(alert: ParentAlert, onMarkRead: () -> Unit) {
    val colors = EduTheme.colors
    val severityColor = parentAlertSeverityColor(alert.severity)
    val title = alert.title
    val description = alert.body
    val time = alert.timeLabel
    val severity = alert.categoryLabel.ifBlank { parentAlertSeverityLabel(alert.severity) }
    val contentDescription = stringResource(
        R.string.pr11_alert_row_a11y,
        title,
        description,
        time,
        severity,
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.sm)
            .semantics { this.contentDescription = contentDescription },
    ) {
        Box(
            modifier = Modifier
                .size(Sizing.iconSm)
                .background(if (alert.isUnread) colors.primary else colors.border, CircleShape),
        )
        ListRow(
            title = title,
            supporting = description,
            leading = parentAlertIcon(alert.severity),
            leadingTint = severityColor,
            onClick = if (alert.isUnread) onMarkRead else null,
            modifier = Modifier.weight(1f),
            trailingContent = {
                Column(horizontalAlignment = Alignment.End) {
                    StatusPill(
                        label = severity,
                        contentColor = severityColor,
                        containerColor = severityColor.copy(alpha = 0.14f),
                    )
                    Text(
                        text = time,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        maxLines = 1,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            },
        )
    }
}

@Composable
private fun ParentAlertPreferencesCard(
    preferences: List<ParentAlertPreference>,
    onPreferenceChange: (ParentAlertPreferenceKey, Boolean) -> Unit,
) {
    EduCard {
        preferences.forEachIndexed { index, preference ->
            ParentAlertPreferenceRow(
                preference = preference,
                onPreferenceChange = onPreferenceChange,
            )
            if (index != preferences.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentAlertPreferenceRow(
    preference: ParentAlertPreference,
    onPreferenceChange: (ParentAlertPreferenceKey, Boolean) -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.sm),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = parentAlertPreferenceTitle(preference.key),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
            )
            Text(
                text = parentAlertPreferenceBody(preference.key),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        Switch(
            checked = preference.enabled,
            onCheckedChange = { onPreferenceChange(preference.key, it) },
            colors = SwitchDefaults.colors(
                checkedThumbColor = colors.onPrimary,
                checkedTrackColor = colors.primary,
            ),
        )
    }
}

@Composable
private fun ParentAlertsIconBadge(
    icon: ImageVector,
    contentColor: Color,
    containerColor: Color,
    modifier: Modifier = Modifier,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(Sizing.touchTarget)
            .background(containerColor, RoundedCornerShape(Radius.pill)),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = contentColor,
            modifier = Modifier.size(Sizing.icon),
        )
    }
}

@Composable
private fun parentAlertSeverityLabel(severity: ParentAlertSeverity): String = when (severity) {
    ParentAlertSeverity.Important -> stringResource(R.string.pr11_severity_important)
    ParentAlertSeverity.Success -> stringResource(R.string.pr11_severity_success)
    ParentAlertSeverity.Info -> stringResource(R.string.pr11_severity_info)
}

@Composable
private fun parentAlertPreferenceTitle(key: ParentAlertPreferenceKey): String = when (key) {
    ParentAlertPreferenceKey.Login -> stringResource(R.string.pr11_pref_login_title)
    ParentAlertPreferenceKey.Logout -> stringResource(R.string.pr11_pref_logout_title)
    ParentAlertPreferenceKey.Lesson -> stringResource(R.string.pr11_pref_lesson_title)
    ParentAlertPreferenceKey.Quiz -> stringResource(R.string.pr11_pref_quiz_title)
    ParentAlertPreferenceKey.LowScore -> stringResource(R.string.pr11_pref_low_score_title)
    ParentAlertPreferenceKey.Inactivity -> stringResource(R.string.pr11_pref_inactivity_title)
    ParentAlertPreferenceKey.Planner -> stringResource(R.string.pr11_pref_planner_title)
}

@Composable
private fun parentAlertPreferenceBody(key: ParentAlertPreferenceKey): String = when (key) {
    ParentAlertPreferenceKey.Login -> stringResource(R.string.pr11_pref_login_body)
    ParentAlertPreferenceKey.Logout -> stringResource(R.string.pr11_pref_logout_body)
    ParentAlertPreferenceKey.Lesson -> stringResource(R.string.pr11_pref_lesson_body)
    ParentAlertPreferenceKey.Quiz -> stringResource(R.string.pr11_pref_quiz_body)
    ParentAlertPreferenceKey.LowScore -> stringResource(R.string.pr11_pref_low_score_body)
    ParentAlertPreferenceKey.Inactivity -> stringResource(R.string.pr11_pref_inactivity_body)
    ParentAlertPreferenceKey.Planner -> stringResource(R.string.pr11_pref_planner_body)
}

@Composable
private fun parentAlertSeverityColor(severity: ParentAlertSeverity): Color {
    val colors = EduTheme.colors
    return when (severity) {
        ParentAlertSeverity.Important -> colors.warning
        ParentAlertSeverity.Success -> colors.success
        ParentAlertSeverity.Info -> colors.aiAccent
    }
}

private fun parentAlertIcon(severity: ParentAlertSeverity): ImageVector = when (severity) {
    ParentAlertSeverity.Important -> Icons.Filled.WarningAmber
    ParentAlertSeverity.Success -> Icons.Filled.Check
    ParentAlertSeverity.Info -> Icons.Filled.Info
}

@Composable
private fun ParentAlertsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
    }
}
