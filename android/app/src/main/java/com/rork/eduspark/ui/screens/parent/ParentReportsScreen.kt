package com.rork.eduspark.ui.screens.parent

import android.content.Intent
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
import androidx.compose.runtime.LaunchedEffect
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentReportComparisonMetric
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportExportFormat
import com.rork.eduspark.data.model.ParentReportMetricKey
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportTrendPoint
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
    val context = LocalContext.current

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is ParentReportsEvent.OpenExport -> {
                    val intent = Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(event.uri, event.mimeType)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    runCatching { context.startActivity(intent) }
                }
            }
        }
    }

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
            onSelectExportFormat = viewModel::selectExportFormat,
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
    onSelectExportFormat: (ParentReportExportFormat) -> Unit,
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
        } else if (!snapshot.hasData) {
            item { ParentReportNoDataCard() }
            item {
                ParentReportsActions(
                    selectedFormat = data.selectedExportFormat,
                    exportState = data.exportState,
                    onSelectExportFormat = onSelectExportFormat,
                    onExportReport = onExportReport,
                    onOpenCustomRangePicker = { showCustomRangePicker = true },
                )
            }
            data.exportError?.let { error ->
                item { ParentReportExportErrorCard(error = error) }
            }
            if (data.exportState == ParentReportExportState.Ready) {
                item { ParentReportExportReadyCard(filename = data.exportFilename, period = data.selectedPeriod) }
            }
        } else {
            item {
                ParentReportOverviewCard(
                    snapshot = snapshot,
                    period = data.selectedPeriod,
                )
            }
            item {
                ParentReportsActions(
                    selectedFormat = data.selectedExportFormat,
                    exportState = data.exportState,
                    onSelectExportFormat = onSelectExportFormat,
                    onExportReport = onExportReport,
                    onOpenCustomRangePicker = { showCustomRangePicker = true },
                )
            }
            data.exportError?.let { error ->
                item { ParentReportExportErrorCard(error = error) }
            }
            item { SectionHeader(title = stringResource(R.string.pr09_summary_title)) }
            item { ParentReportSummaryCard(snapshot = snapshot) }
            item { SectionHeader(title = stringResource(R.string.pr09_lesson_history)) }
            item {
                ParentReportHistoryChartCard(
                    points = snapshot.weeklyLessonHistory,
                    emptyText = stringResource(R.string.pr09_lesson_history_empty),
                    chartDescription = stringResource(R.string.pr09_lesson_history_a11y),
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr09_login_history)) }
            item {
                ParentLoginSessionsCard(
                    sessions = snapshot.loginSessions,
                    emptyText = stringResource(R.string.pr09_login_history_empty),
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr09_planner_history)) }
            item {
                ParentReportHistoryChartCard(
                    points = snapshot.plannerAdherenceHistory,
                    emptyText = stringResource(R.string.pr09_planner_history_empty),
                    chartDescription = stringResource(R.string.pr09_planner_history_a11y),
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr09_missed_tasks)) }
            item {
                ParentReportHistoryChartCard(
                    points = snapshot.missedLateTaskHistory,
                    emptyText = stringResource(R.string.pr09_missed_tasks_empty),
                    chartDescription = stringResource(R.string.pr09_missed_tasks_a11y),
                )
            }
            if (data.exportState == ParentReportExportState.Ready) {
                item { ParentReportExportReadyCard(filename = data.exportFilename, period = data.selectedPeriod) }
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
                if (selectedStudent.gradeLabel.isNotBlank()) {
                    Text(
                        text = selectedStudent.gradeLabel,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
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
private fun ParentReportOverviewCard(
    snapshot: ParentReportsSnapshot,
    period: ParentReportPeriod,
) {
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
                label = snapshot.periodLabel.ifBlank { parentReportPeriodLabel(period) },
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
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

        val trendValues = snapshot.trend.map { it.value }
        if (trendValues.size >= 2) {
            val trendDescription = parentReportTrendDescription(period)
            ParentReportTrendChart(
                values = trendValues,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(140.dp)
                    .padding(top = Spacing.md)
                    .semantics {
                        contentDescription = trendDescription
                    },
            )
        } else {
            ParentEmptyCaption(
                text = stringResource(R.string.pr09_chart_empty),
                modifier = Modifier.padding(top = Spacing.md),
            )
        }
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
private fun ParentReportTrendChart(values: List<Float>, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val lineColor = colors.primary
    val baselineColor = colors.border

    Canvas(modifier = modifier) {
        if (values.size < 2) return@Canvas
        val min = values.minOrNull() ?: 0f
        val max = values.maxOrNull() ?: 100f
        val range = (max - min).coerceAtLeast(1f)
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
            val y = verticalPadding + chartHeight * (1f - ((value - min) / range))
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
    selectedFormat: ParentReportExportFormat,
    exportState: ParentReportExportState,
    onSelectExportFormat: (ParentReportExportFormat) -> Unit,
    onExportReport: () -> Unit,
    onOpenCustomRangePicker: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        Text(
            text = stringResource(R.string.pr09_export_format),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            items(ParentReportExportFormat.entries, key = { it.name }) { format ->
                EduChip(
                    label = parentReportExportFormatLabel(format),
                    selected = format == selectedFormat,
                    onClick = { onSelectExportFormat(format) },
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            PrimaryButton(
                text = if (exportState == ParentReportExportState.Ready) {
                    stringResource(R.string.pr09_export_ready_action)
                } else {
                    stringResource(R.string.pr09_export_action)
                },
                onClick = onExportReport,
                leadingIcon = Icons.Filled.Download,
                isLoading = exportState == ParentReportExportState.Exporting,
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
}

@Composable
private fun ParentReportExportReadyCard(
    filename: String?,
    period: ParentReportPeriod,
) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.success.copy(alpha = 0.10f),
        borderColor = colors.success.copy(alpha = 0.32f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentReportIconBadge(
                icon = Icons.Filled.Check,
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.16f),
            )
            Column {
                Text(
                    text = stringResource(R.string.pr09_export_ready_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(
                        R.string.pr09_export_ready_body,
                        filename?.ifBlank { null } ?: parentReportPeriodLabel(period),
                    ),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun ParentReportExportErrorCard(error: AppError) {
    val colors = EduTheme.colors
    val detail = (error as? AppError.Domain)?.code
    EduCard(
        containerColor = colors.warning.copy(alpha = 0.10f),
        borderColor = colors.warning.copy(alpha = 0.32f),
    ) {
        Text(
            text = stringResource(R.string.pr09_export_failed),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
        )
        if (!detail.isNullOrBlank()) {
            Text(
                text = detail,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
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
    val colors = EduTheme.colors
    EduCard {
        if (snapshot.comparison.isEmpty()) {
            Text(
                text = stringResource(R.string.pr09_summary_empty),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
            )
            return@EduCard
        }
        snapshot.comparison.forEach { metric ->
            ParentReportComparisonRow(metric = metric)
        }
    }
}

@Composable
private fun ParentReportComparisonRow(metric: ParentReportComparisonMetric) {
    val colors = EduTheme.colors
    val change = metric.changePercent
    val changeColor = when {
        change == null -> colors.textSecondary
        change >= 0f -> colors.success
        else -> colors.warning
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
    ) {
        Text(
            text = parentReportMetricLabel(metric.key),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = stringResource(
                R.string.pr09_comparison_values,
                numeral(formatMetricValue(metric.currentValue)),
                numeral(formatMetricValue(metric.previousValue)),
            ),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
        )
        if (change != null) {
            StatusPill(
                label = stringResource(R.string.pr02_percent_value, numeral(formatMetricValue(change))),
                contentColor = changeColor,
                containerColor = changeColor.copy(alpha = 0.14f),
            )
        }
    }
}

private fun formatMetricValue(value: Float): String = String.format(Locale.US, "%.1f", value)

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
    ParentReportPeriod.ThisWeek -> stringResource(R.string.pr09_period_this_week)
    ParentReportPeriod.LastWeek -> stringResource(R.string.pr09_period_last_week)
    ParentReportPeriod.ThisMonth -> stringResource(R.string.pr09_period_this_month)
    ParentReportPeriod.LastMonth -> stringResource(R.string.pr09_period_last_month)
    ParentReportPeriod.Custom -> stringResource(R.string.pr09_period_custom)
}

@Composable
private fun parentReportDateRange(snapshot: ParentReportsSnapshot): String {
    val range = listOf(snapshot.startDate, snapshot.endDate).filter { it.isNotBlank() }
    return if (range.size == 2) {
        stringResource(R.string.pr09_custom_range_format, numeral(range[0]), numeral(range[1]))
    } else {
        snapshot.periodLabel
    }
}

@Composable
private fun parentReportMetricLabel(key: ParentReportMetricKey): String = when (key) {
    ParentReportMetricKey.StudyTime -> stringResource(R.string.pr09_metric_study)
    ParentReportMetricKey.Grades -> stringResource(R.string.pr09_metric_average)
    ParentReportMetricKey.LessonCompletion -> stringResource(R.string.pr09_metric_lessons)
    ParentReportMetricKey.PlannerAdherence -> stringResource(R.string.pr09_metric_planner)
}

@Composable
private fun parentReportExportFormatLabel(format: ParentReportExportFormat): String = when (format) {
    ParentReportExportFormat.Pdf -> stringResource(R.string.pr09_export_pdf)
    ParentReportExportFormat.Csv -> stringResource(R.string.pr09_export_csv)
    ParentReportExportFormat.Xlsx -> stringResource(R.string.pr09_export_xlsx)
}

@Composable
private fun ParentReportNoDataCard() {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = stringResource(R.string.pr09_no_data_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        ParentEmptyCaption(
            text = stringResource(R.string.pr09_no_data_body),
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentReportHistoryChartCard(
    points: List<ParentReportTrendPoint>,
    emptyText: String,
    chartDescription: String,
) {
    EduCard {
        if (points.isEmpty()) {
            ParentEmptyCaption(emptyText)
            return@EduCard
        }
        ParentLabeledBarChart(
            values = points.map { point -> point.label to point.value },
            contentDescription = chartDescription,
        )
    }
}

@Composable
private fun parentReportTrendDescription(period: ParentReportPeriod): String =
    stringResource(R.string.pr09_trend_chart_a11y, parentReportPeriodLabel(period))

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
