package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.Icon
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
import com.rork.eduspark.data.model.ParentAttendanceConsistencyWeek
import com.rork.eduspark.data.model.ParentAttendanceMonthWeek
import com.rork.eduspark.data.model.ParentAttendanceStatusBreakdown
import com.rork.eduspark.data.model.ParentAttendanceStudyTimeSnapshot
import com.rork.eduspark.data.model.ParentDailyStudyTime
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentMonthlyStudyWeek
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.progress.ProgressRing
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
import java.util.Locale

@Composable
fun ParentAttendanceStudyTimeScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentAttendanceStudyTimeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr04_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentAttendanceStudyTimeSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentAttendanceStudyTimeContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentAttendanceStudyTimeContent(
    data: ParentAttendanceStudyTimeData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentAttendanceEmptyState(onOpenLinkStudent = onOpenLinkStudent)
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
            ParentAttendanceStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }
        val snapshot = data.snapshot
        if (snapshot == null) {
            item { SkeletonCard() }
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else if (!snapshot.hasData) {
            item { ParentAttendanceNoDataCard() }
        } else {
            item { ParentAttendanceSummaryCards(snapshot = snapshot) }
            item {
                if (snapshot.dailyStudyMinutes.isNotEmpty()) {
                    ParentWeeklyActivityCard(days = snapshot.dailyStudyMinutes)
                } else {
                    EduCard {
                        Text(
                            text = stringResource(R.string.pr04_week_activity),
                            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                            color = EduTheme.colors.textPrimary,
                        )
                        ParentEmptyCaption(
                            stringResource(R.string.pr04_week_activity_empty),
                            modifier = Modifier.padding(top = Spacing.sm),
                        )
                    }
                }
            }
            item {
                ParentStudyTimeAveragesCard(
                    averages = snapshot.studyTimeAverages,
                    weeklyComparisonPercent = snapshot.weeklyComparisonPercent,
                    monthlyComparisonPercent = snapshot.monthlyComparisonPercent,
                )
            }
            if (snapshot.monthlyStudyWeeks.isNotEmpty()) {
                item { SectionHeader(title = stringResource(R.string.pr04_monthly_study)) }
                item { ParentMonthlyStudyCard(weeks = snapshot.monthlyStudyWeeks) }
            }
            item { SectionHeader(title = stringResource(R.string.pr04_monthly_overview)) }
            item { ParentMonthlyOverviewCard(weeks = snapshot.monthlyAttendance) }
            item { SectionHeader(title = stringResource(R.string.pr04_consistency_weeks)) }
            item { ParentConsistencyWeeksCard(weeks = snapshot.consistencyWeeks) }
            item { SectionHeader(title = stringResource(R.string.pr04_status_breakdown)) }
            item { ParentAttendanceStatusCard(breakdown = snapshot.statusBreakdown) }
            item { SectionHeader(title = stringResource(R.string.pr04_ai_insights)) }
            item { ParentAttendanceAiInsightsCard(insights = snapshot.aiInsights) }
            item { SectionHeader(title = stringResource(R.string.pr04_login_history)) }
            item {
                ParentLoginSessionsCard(
                    sessions = snapshot.loginSessions,
                    emptyText = stringResource(R.string.pr04_login_history_empty),
                )
            }
            item { ParentAttendanceIndicatorsCard(snapshot = snapshot) }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentAttendanceEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentAttendanceIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr04_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr04_empty_body),
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
private fun ParentAttendanceStudentCard(
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
            StatusPill(
                label = stringResource(R.string.pr04_read_only),
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
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
private fun ParentAttendanceNoDataCard() {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = stringResource(R.string.pr04_no_data_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        ParentEmptyCaption(
            text = stringResource(R.string.pr04_no_data_body),
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentAttendanceSummaryCards(snapshot: ParentAttendanceStudyTimeSnapshot) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        ParentRingMetricCard(
            progress = snapshot.studyHours / 8f,
            value = stringResource(
                R.string.pr04_hours_value,
                numeral(String.format(Locale.US, "%.1f", snapshot.studyHours)),
            ),
            label = stringResource(R.string.pr04_study_time),
            tint = EduTheme.colors.aiAccent,
            modifier = Modifier.weight(1f),
        )
        ParentRingMetricCard(
            progress = snapshot.attendancePercent / 100f,
            value = stringResource(R.string.pr02_percent_value, numeral(snapshot.attendancePercent)),
            label = stringResource(R.string.pr04_attendance_commitment),
            tint = EduTheme.colors.primary,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentRingMetricCard(
    progress: Float,
    value: String,
    label: String,
    tint: Color,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier.heightIn(min = Sizing.heroBadge + Spacing.lg)) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            ProgressRing(
                progress = progress.coerceIn(0f, 1f),
                size = Sizing.heroRing,
                showLabel = false,
                tint = tint,
            )
            Text(
                text = value,
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                maxLines = 1,
            )
        }
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentWeeklyActivityCard(days: List<ParentDailyStudyTime>) {
    val colors = EduTheme.colors
    val maxMinutes = days.maxOfOrNull { it.minutes }?.coerceAtLeast(1) ?: 1
    EduCard {
        Text(
            text = stringResource(R.string.pr04_week_activity),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            verticalAlignment = Alignment.Bottom,
            modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.heroBadge + Spacing.lg)
                .padding(top = Spacing.md),
        ) {
            days.forEach { day ->
                ParentStudyDayBar(
                    day = day,
                    maxMinutes = maxMinutes,
                    modifier = Modifier.weight(1f),
                )
            }
        }
        Text(
            text = stringResource(R.string.pr04_week_activity_body),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentStudyDayBar(
    day: ParentDailyStudyTime,
    maxMinutes: Int,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val label = stringResource(
        R.string.pr04_day_minutes_a11y,
        day.dayLabel,
        numeral(day.minutes),
    )
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom,
        modifier = modifier
            .fillMaxHeight()
            .semantics { contentDescription = label },
    ) {
        Box(
            contentAlignment = Alignment.BottomCenter,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxHeight((day.minutes.toFloat() / maxMinutes).coerceIn(0.12f, 1f))
                    .background(
                        if (day.isToday) colors.primary else colors.primary.copy(alpha = 0.78f),
                        RoundedCornerShape(topStart = Radius.sm, topEnd = Radius.sm),
                    ),
            )
        }
        Text(
            text = day.dayLabel,
            style = EduTheme.typography.caption,
            color = if (day.isToday) colors.primary else colors.textTertiary,
            maxLines = 1,
        )
    }
}

@Composable
private fun ParentAttendanceIndicatorsCard(snapshot: ParentAttendanceStudyTimeSnapshot) {
    val colors = EduTheme.colors
    EduCard {
        ListRow(
            title = stringResource(R.string.pr04_regular_sessions),
            supporting = stringResource(R.string.pr04_active_days, numeral(snapshot.activeDays)),
            leading = Icons.Filled.Check,
            leadingTint = colors.success,
            trailingContent = {
                if (snapshot.consistencyPercent > 0) {
                    StatusPill(
                        label = stringResource(R.string.pr02_percent_value, numeral(snapshot.consistencyPercent)),
                        contentColor = colors.success,
                        containerColor = colors.success.copy(alpha = 0.14f),
                    )
                } else {
                    Text(
                        text = stringResource(R.string.pr_no_data_short),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            },
        )
        EduDivider()
        ListRow(
            title = stringResource(R.string.pr04_average_session),
            supporting = stringResource(R.string.pr04_average_session_body),
            leading = Icons.Filled.Timer,
            leadingTint = colors.aiAccent,
            trailingContent = {
                Text(
                    text = if (snapshot.averageSessionMinutes > 0) {
                        stringResource(R.string.pr04_minutes_value, numeral(snapshot.averageSessionMinutes))
                    } else {
                        stringResource(R.string.pr_no_data_short)
                    },
                    style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textSecondary,
                )
            },
        )
    }
}

@Composable
private fun ParentMonthlyStudyCard(weeks: List<ParentMonthlyStudyWeek>) {
    EduCard {
        ParentLabeledBarChart(
            values = weeks.map { week ->
                stringResource(R.string.pr04_week_index, numeral(week.weekIndex)) to week.minutes.toFloat()
            },
            contentDescription = stringResource(R.string.pr04_monthly_study_a11y),
        )
    }
}

@Composable
private fun ParentMonthlyOverviewCard(weeks: List<ParentAttendanceMonthWeek>) {
    EduCard {
        if (weeks.isEmpty()) {
            ParentEmptyCaption(stringResource(R.string.pr04_monthly_overview_empty))
            return@EduCard
        }
        weeks.forEachIndexed { index, week ->
            ListRow(
                title = week.label.ifBlank { stringResource(R.string.pr04_week_index, numeral(index + 1)) },
                supporting = stringResource(
                    R.string.pr04_month_week_supporting,
                    numeral(week.presentDays),
                    numeral(week.partialDays),
                    numeral(week.absentDays),
                ),
                trailingContent = {
                    Text(
                        text = stringResource(R.string.pr02_percent_value, numeral(week.consistencyPercent)),
                        style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                        color = EduTheme.colors.textSecondary,
                    )
                },
            )
            if (index != weeks.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentConsistencyWeeksCard(weeks: List<ParentAttendanceConsistencyWeek>) {
    EduCard {
        if (weeks.isEmpty()) {
            ParentEmptyCaption(stringResource(R.string.pr04_consistency_weeks_empty))
            return@EduCard
        }
        ParentLabeledBarChart(
            values = weeks.map { week -> week.label to week.consistencyPercent.toFloat() },
            contentDescription = stringResource(R.string.pr04_consistency_weeks_a11y),
        )
        weeks.forEach { week ->
            Text(
                text = stringResource(
                    R.string.pr04_consistency_week_supporting,
                    week.label,
                    numeral(week.presentDays),
                    numeral(week.totalDays),
                    numeral(week.consistencyPercent),
                ),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun ParentAttendanceStatusCard(breakdown: ParentAttendanceStatusBreakdown) {
    if (!breakdown.hasValues) {
        EduCard { ParentEmptyCaption(stringResource(R.string.pr04_status_empty)) }
        return
    }
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        ParentStatusTile(
            label = stringResource(R.string.pr04_status_present),
            value = numeral(breakdown.presentDays),
            modifier = Modifier.weight(1f),
        )
        ParentStatusTile(
            label = stringResource(R.string.pr04_status_partial),
            value = numeral(breakdown.partialDays),
            modifier = Modifier.weight(1f),
        )
        ParentStatusTile(
            label = stringResource(R.string.pr04_status_absent),
            value = numeral(breakdown.absentDays),
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentStatusTile(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun ParentAttendanceAiInsightsCard(insights: List<String>) {
    EduCard {
        if (insights.isEmpty()) {
            ParentEmptyCaption(stringResource(R.string.pr04_ai_insights_empty))
            return@EduCard
        }
        insights.forEachIndexed { index, line ->
            Text(
                text = line,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = if (index == 0) Modifier else Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun ParentAttendanceIconBadge(
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
private fun ParentAttendanceStudyTimeSkeleton() {
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
