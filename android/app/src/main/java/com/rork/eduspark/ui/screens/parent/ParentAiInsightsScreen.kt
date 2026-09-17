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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.TrendingUp
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentExecutiveComparisonMetric
import com.rork.eduspark.data.model.ParentExecutiveSubjectAnalysis
import com.rork.eduspark.data.model.ParentExecutiveWeeklySnapshot
import com.rork.eduspark.data.model.ParentInsight
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentStudyBehaviorInsight
import com.rork.eduspark.data.model.ParentSubjectInsight
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.ai.AiDisclosureFooter
import com.rork.eduspark.ui.components.ai.AiMarker
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
import java.util.Locale

@Composable
fun ParentAiInsightsScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentAiInsightsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr08_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentAiInsightsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentAiInsightsContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentAiInsightsContent(
    data: ParentAiInsightsData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentAiInsightsEmptyState(onOpenLinkStudent = onOpenLinkStudent)
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
            ParentAiInsightsStudentCard(
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
        } else if (!snapshot.hasData) {
            item { ParentAiNoDataCard() }
            item { ParentAiPrivacyFooter() }
        } else {
            item { ParentAiWeeklySnapshotCard(snapshot = snapshot.weeklySnapshot) }
            item {
                ParentAiExecutiveSummaryCard(
                    summary = snapshot.summary,
                    summaryLines = snapshot.summaryLines,
                    insights = snapshot.insights,
                )
            }
            item { SectionHeader(title = stringResource(R.string.pr08_subject_analysis)) }
            item {
                ParentAiStrengthWeaknessCard(
                    strength = snapshot.strengthAnalysis,
                    weakness = snapshot.weaknessAnalysis,
                    strongestName = snapshot.weeklySnapshot.strongestSubject,
                    weakestName = snapshot.weeklySnapshot.weakestSubject,
                    subjectInsights = snapshot.subjectInsights,
                )
            }
            snapshot.behavior?.preferredStudyHoursLabel?.takeIf { it.isNotBlank() }?.let { peakHours ->
                item { SectionHeader(title = stringResource(R.string.pr08_peak_hours)) }
                item { ParentAiPeakHoursCard(label = peakHours) }
            }
            if (snapshot.studyTimeAverages.hasValues) {
                item { ParentStudyTimeAveragesCard(averages = snapshot.studyTimeAverages) }
            }
            if (snapshot.periodComparison.isNotEmpty()) {
                item { SectionHeader(title = stringResource(R.string.pr08_period_comparison)) }
                item { ParentAiPeriodComparisonCard(metrics = snapshot.periodComparison, periodLabel = snapshot.periodLabel) }
            }
            item { SectionHeader(title = stringResource(R.string.pr08_risk_alerts)) }
            item { ParentAiInsightListCard(insights = snapshot.riskInsights, emptyText = stringResource(R.string.pr08_risk_empty)) }
            item { SectionHeader(title = stringResource(R.string.pr08_recommendations)) }
            item { ParentAiInsightListCard(insights = snapshot.recommendations, emptyText = stringResource(R.string.pr08_recommendations_empty)) }
            snapshot.behavior?.let { behavior ->
                item { SectionHeader(title = stringResource(R.string.pr08_study_behavior)) }
                item { ParentAiStudyBehaviorCard(behavior) }
            }
            item { ParentAiPrivacyFooter() }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentAiInsightsEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.aiAccent.copy(alpha = 0.34f)) {
                ParentAiIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.aiAccent,
                    containerColor = colors.aiAccentContainer,
                )
                Text(
                    text = stringResource(R.string.pr08_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr08_empty_body),
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
private fun ParentAiInsightsStudentCard(
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
            ParentAiIconBadge(
                icon = Icons.Filled.AutoAwesome,
                contentColor = colors.aiAccent,
                containerColor = colors.aiAccentContainer,
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
private fun ParentAiExecutiveSummaryCard(
    summary: String,
    summaryLines: List<String>,
    insights: List<ParentInsight>,
) {
    val colors = EduTheme.colors
    EduCard(
        borderColor = colors.aiAccent.copy(alpha = 0.44f),
        containerColor = colors.aiAccentContainer.copy(alpha = 0.36f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            AiMarker()
            Text(
                text = stringResource(R.string.pr08_executive_summary),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
        }
        val bullets = summaryLines.ifEmpty { listOfNotNull(summary.takeIf { it.isNotBlank() }) }
        if (bullets.isEmpty()) {
            Text(
                text = stringResource(R.string.pr08_no_insights),
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        } else {
            bullets.forEach { line ->
                Text(
                    text = line,
                    style = EduTheme.typography.body,
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }
        insights.filter { insight -> bullets.none { it.contains(insight.text) } }.forEach { insight ->
            Text(
                text = insight.text,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        AiDisclosureFooter(modifier = Modifier.padding(top = Spacing.sm))
    }
}

@Composable
private fun ParentAiSubjectAnalysisCard(insights: List<ParentSubjectInsight>) {
    EduCard {
        if (insights.isEmpty()) {
            Text(
                text = stringResource(R.string.pr08_no_insights),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
            )
        }
        insights.forEachIndexed { index, insight ->
            ParentAiSubjectInsightRow(insight = insight)
            if (index != insights.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentAiSubjectInsightRow(insight: ParentSubjectInsight) {
    val colors = EduTheme.colors
    val statusColor = if (insight.isStrength) colors.success else colors.warning
    val subject = insight.subjectName
    val status = insight.statusLabel.ifBlank {
        stringResource(
            if (insight.isStrength) R.string.pr08_subject_status_strength else R.string.pr08_subject_status_follow_up,
        )
    }
    val observation = listOfNotNull(
        insight.quizAveragePercent?.let { stringResource(R.string.pr08_subject_quiz_average, numeral(it)) },
        insight.completionPercent?.let { stringResource(R.string.pr08_subject_completion, numeral(it)) },
    ).joinToString(" · ")
    val description = stringResource(R.string.pr08_subject_row_a11y, subject, status, observation)

    ListRow(
        title = subject,
        supporting = observation,
        leading = if (insight.isStrength) Icons.Filled.TrendingUp else Icons.Filled.WarningAmber,
        leadingTint = statusColor,
        trailingContent = {
            StatusPill(
                label = status,
                contentColor = statusColor,
                containerColor = statusColor.copy(alpha = 0.14f),
            )
        },
        modifier = Modifier.semantics { contentDescription = description },
    )
}

@Composable
private fun ParentAiStudyBehaviorCard(behavior: ParentStudyBehaviorInsight) {
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr02_study_time_label),
                value = stringResource(
                    R.string.pr02_hours_value,
                    numeral(String.format(Locale.US, "%.1f", behavior.studyHours)),
                ),
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_average_session),
                value = behavior.averageSessionMinutes?.let {
                    stringResource(R.string.pr08_minutes_value, numeral(it))
                } ?: if (behavior.averageDailyStudyHours > 0f) {
                    stringResource(
                        R.string.pr02_hours_value,
                        numeral(String.format(Locale.US, "%.1f", behavior.averageDailyStudyHours)),
                    )
                } else {
                    stringResource(R.string.pr_no_data_short)
                },
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_consistency),
                value = behavior.consistencyLabel.ifBlank {
                    stringResource(
                        R.string.pr08_days_fraction,
                        numeral(behavior.consistencyDays),
                        numeral(behavior.consistencyTotalDays),
                    )
                },
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_best_time),
                value = behavior.preferredStudyHoursLabel?.takeIf { it.isNotBlank() }
                    ?: stringResource(R.string.pr_no_data_short),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentAiBehaviorTile(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .fillMaxWidth()
            .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.md))
            .padding(horizontal = Spacing.xs, vertical = Spacing.md),
    ) {
        Text(
            text = label,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = value,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun ParentAiPrivacyFooter() {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.aiAccentContainer, RoundedCornerShape(Radius.md))
            .border(Sizing.hairline, colors.aiAccent.copy(alpha = 0.32f), RoundedCornerShape(Radius.md))
            .padding(Spacing.card),
    ) {
        Icon(
            imageVector = Icons.Filled.AutoAwesome,
            contentDescription = null,
            tint = colors.aiAccent,
            modifier = Modifier.size(Sizing.icon),
        )
        Text(
            text = stringResource(R.string.pr08_privacy_footer),
            style = EduTheme.typography.caption,
            color = colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentAiIconBadge(
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
private fun ParentAiInsightsSkeleton() {
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

@Composable
private fun ParentAiNoDataCard() {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = stringResource(R.string.pr08_no_data_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        ParentEmptyCaption(
            text = stringResource(R.string.pr08_no_data_body),
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentAiWeeklySnapshotCard(snapshot: ParentExecutiveWeeklySnapshot) {
    EduCard {
        Text(
            text = stringResource(R.string.pr08_weekly_snapshot),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_lessons_completed),
                value = numeral(snapshot.lessonsCompleted),
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr02_study_time_label),
                value = stringResource(
                    R.string.pr02_hours_value,
                    numeral(String.format(Locale.US, "%.1f", snapshot.studyHours)),
                ),
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_quiz_average),
                value = snapshot.averageQuizScore?.let {
                    stringResource(R.string.pr02_percent_value, numeral(it))
                } ?: stringResource(R.string.pr_no_data_short),
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_planner_adherence),
                value = snapshot.plannerAdherencePercent?.let {
                    stringResource(R.string.pr02_percent_value, numeral(it))
                } ?: stringResource(R.string.pr_no_data_short),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentAiStrengthWeaknessCard(
    strength: ParentExecutiveSubjectAnalysis?,
    weakness: ParentExecutiveSubjectAnalysis?,
    strongestName: String?,
    weakestName: String?,
    subjectInsights: List<ParentSubjectInsight>,
) {
    val hasAnalysis = strength != null || weakness != null ||
        !strongestName.isNullOrBlank() || !weakestName.isNullOrBlank()
    if (!hasAnalysis && subjectInsights.isEmpty()) {
        EduCard { ParentEmptyCaption(stringResource(R.string.pr08_no_insights)) }
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        if (hasAnalysis) {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                ParentAiSubjectFocusCard(
                    title = stringResource(R.string.pr08_strongest_subject),
                    analysis = strength,
                    fallbackName = strongestName,
                    isStrength = true,
                    modifier = Modifier.weight(1f),
                )
                ParentAiSubjectFocusCard(
                    title = stringResource(R.string.pr08_weakest_subject),
                    analysis = weakness,
                    fallbackName = weakestName,
                    isStrength = false,
                    modifier = Modifier.weight(1f),
                )
            }
        }
        if (subjectInsights.isNotEmpty()) {
            ParentAiSubjectAnalysisCard(subjectInsights)
        }
    }
}

@Composable
private fun ParentAiSubjectFocusCard(
    title: String,
    analysis: ParentExecutiveSubjectAnalysis?,
    fallbackName: String?,
    isStrength: Boolean,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val tint = if (isStrength) colors.success else colors.warning
    val name = analysis?.subjectName?.takeIf { it.isNotBlank() } ?: fallbackName
    EduCard(modifier = modifier, borderColor = tint.copy(alpha = 0.32f)) {
        Text(
            text = title,
            style = EduTheme.typography.caption,
            color = tint,
        )
        Text(
            text = name?.takeIf { it.isNotBlank() } ?: stringResource(R.string.pr_no_data_short),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        analysis?.averageScorePercent?.let { score ->
            Text(
                text = stringResource(R.string.pr08_subject_quiz_average, numeral(score)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        analysis?.reasons?.firstOrNull()?.let { reason ->
            Text(
                text = reason,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
private fun ParentAiPeakHoursCard(label: String) {
    EduCard {
        Text(
            text = label,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.pr08_peak_hours_body),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentAiPeriodComparisonCard(
    metrics: List<ParentExecutiveComparisonMetric>,
    periodLabel: String,
) {
    EduCard {
        if (periodLabel.isNotBlank()) {
            Text(
                text = periodLabel,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        metrics.forEachIndexed { index, metric ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = Spacing.xs),
            ) {
                Text(
                    text = metric.label,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = EduTheme.colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = stringResource(
                        R.string.pr09_comparison_values,
                        numeral(String.format(Locale.US, "%.1f", metric.currentValue)),
                        numeral(String.format(Locale.US, "%.1f", metric.previousValue)),
                    ),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
                ParentTrendDelta(percent = metric.changePercent)
            }
            if (index != metrics.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentAiInsightListCard(insights: List<ParentInsight>, emptyText: String) {
    EduCard {
        if (insights.isEmpty()) {
            ParentEmptyCaption(emptyText)
            return@EduCard
        }
        insights.forEachIndexed { index, insight ->
            Text(
                text = insight.text,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = if (index == 0) Modifier else Modifier.padding(top = Spacing.sm),
            )
        }
    }
}
