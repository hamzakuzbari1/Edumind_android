package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.Canvas
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
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DateRangePicker
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportStatus
import com.rork.eduspark.data.model.ParentReportSummaryType
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

@Composable
fun ParentReportsScreen(
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentReportsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentReportsSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentReportsContent(
            data = data,
            onSelectStudent = viewModel::selectStudent,
            onSelectPeriod = viewModel::selectPeriod,
            onConfirmCustomDateRange = viewModel::confirmCustomDateRange,
            onExportReport = viewModel::exportReport,
            onOpenLinkStudent = onOpenLinkStudent,
        )
    }
}

@Composable
private fun ParentReportsContent(
    data: ParentReportsData,
    onSelectStudent: (String) -> Unit,
    onSelectPeriod: (ParentReportPeriod) -> Unit,
    onConfirmCustomDateRange: (ParentReportDateRange) -> Unit,
    onExportReport: () -> Unit,
    onOpenLinkStudent: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentReportsEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    val selectedStudent = data.linkedStudents.firstOrNull { it.id == data.selectedStudentId }
        ?: data.linkedStudents.first()
    var showCustomRangePicker by rememberSaveable { mutableStateOf(false) }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentReportsStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }
        item {
            ParentReportsPeriodSelector(
                selectedPeriod = data.selectedPeriod,
                onSelectPeriod = onSelectPeriod,
            )
        }

        val snapshot = data.snapshot
        if (snapshot == null) {
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else {
            item { ParentReportOverviewCard(snapshot = snapshot) }
            item {
                ParentReportsActions(
                    exportState = data.exportState,
                    onExportReport = onExportReport,
                    onOpenCustomRangePicker = { showCustomRangePicker = true },
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr09_summary_title)) }
            item { ParentReportSummaryCard(snapshot = snapshot) }
            if (data.exportState == ParentReportExportState.Ready) {
                item { ParentReportExportReadyCard(snapshot = snapshot) }
            }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }

    if (showCustomRangePicker) {
        ParentCustomDateRangeDialog(
            initialRange = data.customDateRange,
            onConfirm = { dateRange ->
                showCustomRangePicker = false
                onConfirmCustomDateRange(dateRange)
            },
            onDismiss = { showCustomRangePicker = false },
        )
    }
}

@Composable
private fun ParentReportsEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentReportIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr09_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr09_empty_body),
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
private fun ParentReportsStudentCard(
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
                Text(
                    text = stringResource(
                        R.string.pr_linked_student_grade_section,
                        selectedStudent.gradeLabel,
                        selectedStudent.sectionLabel,
                    ),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            StatusPill(
                label = stringResource(R.string.pr09_report_status_ready),
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
private fun ParentReportsPeriodSelector(
    selectedPeriod: ParentReportPeriod,
    onSelectPeriod: (ParentReportPeriod) -> Unit,
) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        items(ParentReportPeriod.entries, key = { it.name }) { period ->
            EduChip(
                label = parentReportPeriodLabel(period),
                selected = period == selectedPeriod,
                onClick = { onSelectPeriod(period) },
            )
        }
    }
}

@Composable
private fun ParentReportOverviewCard(snapshot: ParentReportsSnapshot) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            ParentReportIconBadge(
                icon = Icons.Filled.Assessment,
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr09_report_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = parentReportDateRange(snapshot),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            StatusPill(
                label = parentReportStatusLabel(snapshot.summary.status),
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.14f),
            )
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            ParentReportMetricTile(
                value = stringResource(R.string.pr02_percent_value, numeral(snapshot.academicAveragePercent)),
                label = stringResource(R.string.pr09_metric_average),
                modifier = Modifier.weight(1f),
            )
            ParentReportMetricTile(
                value = numeral(snapshot.completedLessons),
                label = stringResource(R.string.pr09_metric_lessons),
                modifier = Modifier.weight(1f),
            )
            ParentReportMetricTile(
                value = stringResource(
                    R.string.pr02_hours_value,
                    numeral(String.format(Locale.US, "%.1f", snapshot.studyHours)),
                ),
                label = stringResource(R.string.pr09_metric_study),
                modifier = Modifier.weight(1f),
            )
        }

        val trendDescription = parentReportTrendDescription(snapshot.period)
        ParentReportTrendChart(
            values = snapshot.trendScores,
            modifier = Modifier
                .fillMaxWidth()
                .height(140.dp)
                .padding(top = Spacing.md)
                .semantics {
                    contentDescription = trendDescription
                },
        )
    }
}

@Composable
private fun ParentReportMetricTile(
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
            .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.md))
            .padding(horizontal = Spacing.xs, vertical = Spacing.sm),
    ) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            maxLines = 1,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ParentReportTrendChart(values: List<Int>, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val lineColor = colors.primary
    val baselineColor = colors.border

    Canvas(modifier = modifier) {
        if (values.size < 2) return@Canvas
        val min = values.minOrNull() ?: 0
        val max = values.maxOrNull() ?: 100
        val range = (max - min).coerceAtLeast(1)
        val horizontalPadding = 12.dp.toPx()
        val verticalPadding = 18.dp.toPx()
        val chartWidth = size.width - horizontalPadding * 2
        val chartHeight = size.height - verticalPadding * 2

        drawLine(
            color = baselineColor,
            start = Offset(horizontalPadding, size.height - verticalPadding),
            end = Offset(size.width - horizontalPadding, size.height - verticalPadding),
            strokeWidth = Sizing.hairline.toPx(),
        )

        val points = values.mapIndexed { index, value ->
            val x = horizontalPadding + chartWidth * (index / (values.lastIndex).toFloat())
            val y = verticalPadding + chartHeight * (1f - ((value - min) / range.toFloat()))
            Offset(x, y)
        }
        points.zipWithNext().forEach { (start, end) ->
            drawLine(
                color = lineColor,
                start = start,
                end = end,
                strokeWidth = 6.dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
    }
}

@Composable
private fun ParentReportsActions(
    exportState: ParentReportExportState,
    onExportReport: () -> Unit,
    onOpenCustomRangePicker: () -> Unit,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        PrimaryButton(
            text = if (exportState == ParentReportExportState.Ready) {
                stringResource(R.string.pr09_export_ready_action)
            } else {
                stringResource(R.string.pr09_export_action)
            },
            onClick = onExportReport,
            leadingIcon = Icons.Filled.Download,
            modifier = Modifier.weight(1f),
        )
        SecondaryButton(
            text = stringResource(R.string.pr09_select_period_action),
            onClick = onOpenCustomRangePicker,
            leadingIcon = Icons.Filled.Tune,
            modifier = Modifier.weight(1f),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ParentCustomDateRangeDialog(
    initialRange: ParentReportDateRange?,
    onConfirm: (ParentReportDateRange) -> Unit,
    onDismiss: () -> Unit,
) {
    val pickerState = androidx.compose.material3.rememberDateRangePickerState(
        initialSelectedStartDateMillis = initialRange?.startDateMillis,
        initialSelectedEndDateMillis = initialRange?.endDateMillis,
    )
    val startDateMillis = pickerState.selectedStartDateMillis
    val endDateMillis = pickerState.selectedEndDateMillis

    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            PrimaryButton(
                text = stringResource(R.string.common_confirm),
                onClick = {
                    if (startDateMillis != null && endDateMillis != null) {
                        onConfirm(
                            ParentReportDateRange(
                                startDateMillis = startDateMillis,
                                endDateMillis = endDateMillis,
                            ),
                        )
                    }
                },
                enabled = startDateMillis != null && endDateMillis != null,
            )
        },
        dismissButton = {
            GhostButton(
                text = stringResource(R.string.common_cancel),
                onClick = onDismiss,
            )
        },
    ) {
        DateRangePicker(
            state = pickerState,
            title = {
                Text(
                    text = stringResource(R.string.pr09_custom_range_title),
                    style = EduTheme.typography.title,
                    color = EduTheme.colors.textPrimary,
                    modifier = Modifier.padding(horizontal = Spacing.md, vertical = Spacing.sm),
                )
            },
            showModeToggle = false,
        )
    }
}

@Composable
private fun ParentReportSummaryCard(snapshot: ParentReportsSnapshot) {
    EduCard {
        Text(
            text = parentReportSummaryBody(snapshot.summary.type),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textSecondary,
        )
    }
}

@Composable
private fun ParentReportExportReadyCard(snapshot: ParentReportsSnapshot) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.success.copy(alpha = 0.10f),
        borderColor = colors.success.copy(alpha = 0.32f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(
                imageVector = Icons.Filled.Check,
                contentDescription = null,
                tint = colors.success,
                modifier = Modifier.size(Sizing.iconLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr09_export_ready_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr09_export_ready_body, parentReportPeriodLabel(snapshot.period)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun ParentReportIconBadge(
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
private fun parentReportPeriodLabel(period: ParentReportPeriod): String = when (period) {
    ParentReportPeriod.Last7Days -> stringResource(R.string.pr09_period_7_days)
    ParentReportPeriod.Last30Days -> stringResource(R.string.pr09_period_30_days)
    ParentReportPeriod.Term -> stringResource(R.string.pr09_period_term)
    ParentReportPeriod.Custom -> stringResource(R.string.pr09_period_custom)
}

@Composable
private fun parentReportDateRange(snapshot: ParentReportsSnapshot): String = when (snapshot.period) {
    ParentReportPeriod.Last7Days -> stringResource(R.string.pr09_range_7_days)
    ParentReportPeriod.Last30Days -> stringResource(R.string.pr09_range_30_days)
    ParentReportPeriod.Term -> stringResource(R.string.pr09_range_term)
    ParentReportPeriod.Custom -> snapshot.dateRange?.let { range ->
        stringResource(
            R.string.pr09_custom_range_format,
            numeral(formatReportDate(range.startDateMillis)),
            numeral(formatReportDate(range.endDateMillis)),
        )
    } ?: stringResource(R.string.pr09_range_custom)
}

@Composable
private fun parentReportStatusLabel(status: ParentReportStatus): String = when (status) {
    ParentReportStatus.Ready -> stringResource(R.string.pr09_report_status_ready)
}

@Composable
private fun parentReportSummaryBody(type: ParentReportSummaryType): String = when (type) {
    ParentReportSummaryType.ImprovedAverageAndLessons -> stringResource(R.string.pr09_summary_body)
}

@Composable
private fun parentReportTrendDescription(period: ParentReportPeriod): String =
    stringResource(R.string.pr09_trend_chart_a11y, parentReportPeriodLabel(period))

private fun formatReportDate(millis: Long): String {
    val formatter = SimpleDateFormat("MMM d, yyyy", Locale.getDefault())
    formatter.timeZone = TimeZone.getTimeZone("UTC")
    return formatter.format(Date(millis))
}

@Composable
private fun ParentReportsSkeleton() {
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
