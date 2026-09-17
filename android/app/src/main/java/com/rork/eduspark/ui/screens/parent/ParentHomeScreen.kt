package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import java.util.Locale

@Composable
fun ParentHomeScreen(
    onOpenLinkStudent: () -> Unit,
    onOpenPlanner: () -> Unit,
    onOpenAlerts: () -> Unit,
    onOpenAiInsights: () -> Unit,
    onOpenNotes: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentHomeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentHomeSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentHomeContent(
            data = data,
            onSelectStudent = viewModel::selectStudent,
            onOpenLinkStudent = onOpenLinkStudent,
            onOpenPlanner = onOpenPlanner,
            onOpenAlerts = onOpenAlerts,
            onOpenAiInsights = onOpenAiInsights,
            onOpenNotes = onOpenNotes,
        )
    }
}

@Composable
private fun ParentHomeContent(
    data: ParentHomeData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
    onOpenPlanner: () -> Unit,
    onOpenAlerts: () -> Unit,
    onOpenAiInsights: () -> Unit,
    onOpenNotes: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentHomeEmptyState(onOpenLinkStudent = onOpenLinkStudent)
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
            ParentCurrentStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }

        val dashboard = data.dashboard
        if (dashboard == null) {
            item { SkeletonCard() }
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else {
            item { ParentTodaySummaryCard(student = selectedStudent, dashboard = dashboard) }
            item {
                ParentAiInsightCard(
                    insightText = dashboard.latestInsightText,
                    onOpenAiInsights = onOpenAiInsights,
                )
            }
            item { ParentQuickSummaryGrid(dashboard = dashboard) }
            item { ParentPlannerPreviewCard(dashboard = dashboard, onOpenPlanner = onOpenPlanner) }
            dashboard.latestTeacherNote?.let { note ->
                item { ParentTeacherNotePreviewCard(note = note, onOpenNotes = onOpenNotes) }
            }
            item { ParentAttentionCard(dashboard = dashboard, onOpenAlerts = onOpenAlerts) }
            item { ParentRecentActivitiesCard(activities = dashboard.recentActivities) }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentHomeEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr02_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr02_empty_body),
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
private fun ParentCurrentStudentCard(
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
                selectedStudent.lastActivityLabel?.takeIf { it.isNotBlank() }?.let { lastActivity ->
                    Text(
                        text = lastActivity,
                        style = EduTheme.typography.caption,
                        color = colors.textTertiary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            StatusPill(
                label = selectedStudent.statusLabel.ifBlank { stringResource(R.string.pr02_student_active) },
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.14f),
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
private fun ParentTodaySummaryCard(
    student: ParentLinkedStudent,
    dashboard: ParentDashboardSnapshot,
) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary,
    ) {
        Text(
            text = stringResource(R.string.pr02_today_summary_label),
            style = EduTheme.typography.caption,
            color = colors.onPrimary.copy(alpha = 0.82f),
        )
        Text(
            text = stringResource(R.string.pr02_today_summary_title, student.displayName),
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.onPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(
            text = stringResource(R.string.pr02_today_summary_body),
            style = EduTheme.typography.body,
            color = colors.onPrimary.copy(alpha = 0.86f),
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            ParentHeroStat(
                value = stringResource(
                    R.string.pr02_hours_value,
                    numeral(String.format(Locale.US, "%.1f", dashboard.studyHoursThisWeek)),
                ),
                label = stringResource(R.string.pr02_study_time_label),
                modifier = Modifier.weight(1f),
            )
            ParentHeroStat(
                value = if (dashboard.hasAcademicData) {
                    stringResource(R.string.pr02_percent_value, numeral(dashboard.academicAveragePercent))
                } else {
                    stringResource(R.string.pr_no_data_short)
                },
                label = stringResource(R.string.pr02_test_average_label),
                modifier = Modifier.weight(1f),
            )
            ParentHeroStat(
                value = stringResource(R.string.pr02_percent_value, numeral(dashboard.lessonProgressPercent)),
                label = stringResource(R.string.pr02_lesson_progress_label),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentHeroStat(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .heightIn(min = Sizing.avatarLg)
            .background(colors.onPrimary.copy(alpha = 0.10f), RoundedCornerShape(Radius.sm))
            .border(Sizing.hairline, colors.onPrimary.copy(alpha = 0.18f), RoundedCornerShape(Radius.sm))
            .padding(horizontal = Spacing.xs, vertical = Spacing.sm),
    ) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.onPrimary,
            maxLines = 1,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.onPrimary.copy(alpha = 0.76f),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ParentAiInsightCard(
    insightText: String?,
    onOpenAiInsights: () -> Unit,
) {
    val colors = EduTheme.colors
    val body = insightText?.takeIf { it.isNotBlank() }
        ?: stringResource(R.string.pr02_ai_empty)
    EduCard(
        onClick = onOpenAiInsights,
        onClickLabel = stringResource(R.string.pr08_open_ai_insights),
        borderColor = colors.aiAccent.copy(alpha = 0.34f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentIconBadge(
                icon = Icons.Filled.AutoAwesome,
                contentColor = colors.aiAccent,
                containerColor = colors.aiAccentContainer,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr02_ai_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = body,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun ParentQuickSummaryGrid(dashboard: ParentDashboardSnapshot) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            ParentSummaryTile(
                icon = Icons.Filled.Insights,
                title = stringResource(R.string.pr02_performance_title),
                body = stringResource(R.string.pr02_performance_body),
                value = if (dashboard.hasAcademicData) {
                    stringResource(R.string.pr02_percent_value, numeral(dashboard.academicAveragePercent))
                } else {
                    stringResource(R.string.pr_no_data_short)
                },
                modifier = Modifier.weight(1f),
            )
            ParentSummaryTile(
                icon = Icons.Filled.Schedule,
                title = stringResource(R.string.pr02_attendance_title),
                body = stringResource(R.string.pr02_attendance_body),
                value = if (dashboard.hasAttendanceData) {
                    stringResource(R.string.pr02_percent_value, numeral(dashboard.attendancePercent))
                } else {
                    stringResource(R.string.pr_no_data_short)
                },
                modifier = Modifier.weight(1f),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            ParentSummaryTile(
                icon = Icons.AutoMirrored.Filled.MenuBook,
                title = stringResource(R.string.pr02_lessons_title),
                body = stringResource(R.string.pr02_lessons_body),
                value = stringResource(R.string.pr02_percent_value, numeral(dashboard.lessonProgressPercent)),
                modifier = Modifier.weight(1f),
            )
            ParentSummaryTile(
                icon = Icons.Filled.Assessment,
                title = stringResource(R.string.pr02_reports_title),
                body = stringResource(R.string.pr02_reports_body),
                value = stringResource(R.string.pr02_reports_value),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentSummaryTile(
    icon: ImageVector,
    title: String,
    body: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier.heightIn(min = Sizing.avatarLg + Spacing.lg)) {
        ParentIconBadge(
            icon = icon,
            contentColor = colors.primary,
            containerColor = colors.primaryContainer,
        )
        Text(
            text = title,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Text(
            text = body,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.primary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentPlannerPreviewCard(
    dashboard: ParentDashboardSnapshot,
    onOpenPlanner: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard {
        ListRow(
            title = stringResource(R.string.pr02_planner_title),
            supporting = stringResource(R.string.pr02_planner_body, numeral(dashboard.plannerItemsDue)),
            leading = Icons.Filled.CalendarToday,
            leadingTint = colors.primary,
            showChevron = true,
            onClick = onOpenPlanner,
            trailingContent = {
                StatusPill(
                    label = stringResource(R.string.pr02_planner_status),
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
            },
        )
    }
}

@Composable
private fun ParentTeacherNotePreviewCard(
    note: ParentNote,
    onOpenNotes: () -> Unit,
) {
    val colors = EduTheme.colors
    val from = listOfNotNull(
        note.teacherName.takeIf { it.isNotBlank() },
        note.categoryLabel.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    val body = note.description.ifBlank { note.title }
    val meta = listOfNotNull(
        note.createdLabel.takeIf { it.isNotBlank() },
        note.statusLabel.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    EduCard(
        onClick = onOpenNotes,
        onClickLabel = stringResource(R.string.pr02_teacher_note_open),
        borderColor = colors.primary.copy(alpha = 0.28f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentIconBadge(
                icon = Icons.AutoMirrored.Filled.MenuBook,
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.parent_notes_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                if (from.isNotBlank()) {
                    Text(
                        text = from,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
        if (body.isNotBlank()) {
            Text(
                text = body,
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
        if (meta.isNotBlank()) {
            Text(
                text = meta,
                style = EduTheme.typography.caption,
                color = colors.textTertiary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        Text(
            text = stringResource(R.string.pr02_teacher_note_open),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = colors.primary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun ParentAttentionCard(
    dashboard: ParentDashboardSnapshot,
    onOpenAlerts: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        onClick = onOpenAlerts,
        onClickLabel = stringResource(R.string.pr11_open_alerts),
        containerColor = colors.highlightContainer,
        borderColor = colors.warning.copy(alpha = 0.28f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(
                imageVector = Icons.Filled.WarningAmber,
                contentDescription = null,
                tint = colors.warning,
                modifier = Modifier.size(Sizing.iconLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr02_attention_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr02_attention_body, numeral(dashboard.alertCount)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun ParentRecentActivitiesCard(activities: List<ParentActivity>) {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = stringResource(R.string.pr02_recent_activity_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        if (activities.isEmpty()) {
            Text(
                text = stringResource(R.string.pr02_recent_activity_empty),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            return@EduCard
        }
        activities.forEachIndexed { index, activity ->
            ParentRecentActivityRow(activity = activity)
            if (index != activities.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentRecentActivityRow(activity: ParentActivity) {
    val colors = EduTheme.colors
    ListRow(
        title = activity.title,
        supporting = listOfNotNull(
            activity.description?.takeIf { it.isNotBlank() },
            activity.relativeTime.takeIf { it.isNotBlank() },
        ).joinToString(" · "),
        leading = Icons.Filled.Assessment,
        leadingTint = colors.primary,
    )
}

@Composable
private fun ParentIconBadge(
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

private data class ParentActivityUi(
    val title: String,
    val body: String,
    val icon: ImageVector,
    val tint: Color,
)

@Composable
private fun ParentHomeSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
