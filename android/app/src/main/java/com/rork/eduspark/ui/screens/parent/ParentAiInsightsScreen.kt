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
import com.rork.eduspark.data.model.ParentAiInsightsSnapshot
import com.rork.eduspark.data.model.ParentAiSummary
import com.rork.eduspark.data.model.ParentAiSummaryType
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentStudyBehaviorBestTime
import com.rork.eduspark.data.model.ParentStudyBehaviorInsight
import com.rork.eduspark.data.model.ParentStudyBehaviorInterruptions
import com.rork.eduspark.data.model.ParentSubjectInsight
import com.rork.eduspark.data.model.ParentSubjectInsightObservation
import com.rork.eduspark.data.model.ParentSubjectInsightStatus
import com.rork.eduspark.data.model.ParentSubjectKind
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
        } else {
            item { ParentAiExecutiveSummaryCard(summary = snapshot.summary) }
            item { SectionHeader(title = stringResource(R.string.pr08_subject_analysis)) }
            item { ParentAiSubjectAnalysisCard(snapshot.subjectInsights) }
            item { SectionHeader(title = stringResource(R.string.pr08_study_behavior)) }
            item { ParentAiStudyBehaviorCard(snapshot.behavior) }
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
private fun ParentAiExecutiveSummaryCard(summary: ParentAiSummary) {
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
        Text(
            text = parentAiSummaryBody(summary.type),
            style = EduTheme.typography.body,
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        AiDisclosureFooter(modifier = Modifier.padding(top = Spacing.sm))
    }
}

@Composable
private fun ParentAiSubjectAnalysisCard(insights: List<ParentSubjectInsight>) {
    EduCard {
        insights.forEachIndexed { index, insight ->
            ParentAiSubjectInsightRow(insight = insight)
            if (index != insights.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentAiSubjectInsightRow(insight: ParentSubjectInsight) {
    val statusColor = parentAiSubjectStatusColor(insight.status)
    val subject = parentAiSubjectLabel(insight.subject)
    val status = parentAiSubjectStatusLabel(insight.status)
    val observation = parentAiSubjectObservation(insight.observation)
    val description = stringResource(R.string.pr08_subject_row_a11y, subject, status, observation)

    ListRow(
        title = subject,
        supporting = observation,
        leading = parentAiSubjectStatusIcon(insight.status),
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
                label = stringResource(R.string.pr08_behavior_best_time),
                value = parentAiBestTimeLabel(behavior.bestTime),
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_average_session),
                value = stringResource(R.string.pr08_minutes_value, numeral(behavior.averageSessionMinutes)),
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_consistency),
                value = stringResource(
                    R.string.pr08_days_fraction,
                    numeral(behavior.consistencyDays),
                    numeral(behavior.consistencyTotalDays),
                ),
                modifier = Modifier.weight(1f),
            )
            ParentAiBehaviorTile(
                label = stringResource(R.string.pr08_behavior_interruptions),
                value = parentAiInterruptionsLabel(behavior.interruptions),
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
private fun parentAiSummaryBody(type: ParentAiSummaryType): String = when (type) {
    ParentAiSummaryType.StableWithAlgebraSupport -> stringResource(R.string.pr08_summary_body)
}

@Composable
private fun parentAiSubjectLabel(subject: ParentSubjectKind): String = when (subject) {
    ParentSubjectKind.Mathematics -> stringResource(R.string.pr03_subject_math)
    ParentSubjectKind.Science -> stringResource(R.string.pr03_subject_science)
    ParentSubjectKind.Arabic -> stringResource(R.string.pr03_subject_arabic)
}

@Composable
private fun parentAiSubjectStatusLabel(status: ParentSubjectInsightStatus): String = when (status) {
    ParentSubjectInsightStatus.Strength -> stringResource(R.string.pr08_subject_status_strength)
    ParentSubjectInsightStatus.FollowUp -> stringResource(R.string.pr08_subject_status_follow_up)
}

@Composable
private fun parentAiSubjectObservation(observation: ParentSubjectInsightObservation): String = when (observation) {
    ParentSubjectInsightObservation.PositiveStableTrend -> stringResource(R.string.pr08_subject_observation_science)
    ParentSubjectInsightObservation.RepeatedAlgebraMistakes -> stringResource(R.string.pr08_subject_observation_math)
}

@Composable
private fun parentAiBestTimeLabel(bestTime: ParentStudyBehaviorBestTime): String = when (bestTime) {
    ParentStudyBehaviorBestTime.Afternoon -> stringResource(R.string.pr08_best_time_afternoon)
}

@Composable
private fun parentAiInterruptionsLabel(interruptions: ParentStudyBehaviorInterruptions): String = when (interruptions) {
    ParentStudyBehaviorInterruptions.Low -> stringResource(R.string.pr08_interruptions_low)
}

@Composable
private fun parentAiSubjectStatusColor(status: ParentSubjectInsightStatus): Color {
    val colors = EduTheme.colors
    return when (status) {
        ParentSubjectInsightStatus.Strength -> colors.success
        ParentSubjectInsightStatus.FollowUp -> colors.warning
    }
}

private fun parentAiSubjectStatusIcon(status: ParentSubjectInsightStatus): ImageVector = when (status) {
    ParentSubjectInsightStatus.Strength -> Icons.Filled.TrendingUp
    ParentSubjectInsightStatus.FollowUp -> Icons.Filled.WarningAmber
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
