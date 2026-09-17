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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Link
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLessonActivityEvent
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonVerificationItem
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
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
import org.koin.core.parameter.parametersOf

@Composable
fun ParentLessonDetailsScreen(
    lessonId: String,
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentLessonDetailsViewModel = koinViewModel(parameters = { parametersOf(lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr06_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLessonDetailsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentLessonDetailsContent(
                data = data,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentLessonDetailsContent(
    data: ParentLessonDetailsData,
    onOpenLinkStudent: () -> Unit,
) {
    val linkedStudent = data.linkedStudent
    val details = data.details
    if (linkedStudent == null || details == null) {
        ParentLessonDetailsEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item { ParentLessonDetailsStudentCard(student = linkedStudent) }
        item { ParentLessonOverviewCard(details = details) }
        item { ParentLessonMetricsRow(details = details) }
        if (details.checklist.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.pr06_checklist_title)) }
            item { ParentLessonChecklistCard(items = details.checklist) }
        }
        if (details.missingRequirements > 0) {
            item { ParentLessonMissingRequirementsCard(missingRequirements = details.missingRequirements) }
        }
        if (details.timeline.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.pr06_timeline_title)) }
            item { ParentLessonTimelineCard(events = details.timeline) }
        }
        item { Spacer(modifier = Modifier.height(Spacing.section)) }
    }
}

@Composable
private fun ParentLessonDetailsEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentLessonDetailsIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr06_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr06_empty_body),
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
private fun ParentLessonDetailsStudentCard(student: ParentLinkedStudent) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = student.avatarInitial,
                modifier = Modifier.size(Sizing.avatarLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = student.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (student.gradeLabel.isNotBlank()) {
                    Text(
                        text = student.gradeLabel,
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
    }
}

@Composable
private fun ParentLessonOverviewCard(details: ParentLessonDetails) {
    val colors = EduTheme.colors
    val title = details.title
    val subject = details.subjectName.ifBlank { details.courseTitle }
    val status = details.statusLabel.ifBlank {
        stringResource(R.string.pr02_percent_value, numeral(details.completionPercent))
    }
    val progress = details.completionPercent / 100f
    val description = stringResource(
        R.string.pr06_lesson_overview_a11y,
        title,
        subject,
        numeral(details.completionPercent),
    )

    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary,
        modifier = Modifier.semantics { contentDescription = description },
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = listOfNotNull(
                        subject.takeIf { it.isNotBlank() },
                        details.teacherName.takeIf { it.isNotBlank() },
                    ).joinToString(" · "),
                    style = EduTheme.typography.body,
                    color = colors.onPrimary.copy(alpha = 0.82f),
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            StatusPill(
                label = status,
                contentColor = colors.primary,
                containerColor = colors.onPrimary,
            )
        }
        Spacer(modifier = Modifier.height(Spacing.md))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(Spacing.xs)
                .background(colors.onPrimary.copy(alpha = 0.28f), RoundedCornerShape(Radius.pill)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress.coerceIn(0f, 1f))
                    .height(Spacing.xs)
                    .background(colors.onPrimary, RoundedCornerShape(Radius.pill)),
            )
        }
    }
}

@Composable
private fun ParentLessonMetricsRow(details: ParentLessonDetails) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        ParentLessonMetricCard(
            value = stringResource(
                R.string.pr06_pages_value,
                numeral(details.pagesViewed),
                numeral(details.totalPages),
            ),
            label = stringResource(R.string.pr06_pages_viewed),
            modifier = Modifier.weight(1f),
        )
        ParentLessonMetricCard(
            value = stringResource(
                R.string.pr06_requirements_value,
                numeral(details.requirementsCompleted),
                numeral(details.requirementsTotal),
            ),
            label = stringResource(R.string.pr06_requirements),
            modifier = Modifier.weight(1f),
        )
        ParentLessonMetricCard(
            value = stringResource(R.string.pr02_percent_value, numeral(details.quizScorePercent)),
            label = stringResource(R.string.pr06_quiz_score),
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentLessonMetricCard(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(
        contentPadding = PaddingValues(Spacing.sm),
        modifier = modifier,
    ) {
        Text(
            text = value,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun ParentLessonChecklistCard(items: List<ParentLessonVerificationItem>) {
    val colors = EduTheme.colors
    EduCard {
        items.forEachIndexed { index, item ->
            val complete = item.isComplete
            ListRow(
                title = item.label,
                supporting = if (complete) {
                    stringResource(R.string.pr06_check_complete)
                } else {
                    stringResource(R.string.pr06_check_missing)
                },
                leading = if (complete) Icons.Filled.Check else Icons.Filled.WarningAmber,
                leadingTint = if (complete) colors.success else colors.warning,
            )
            if (index != items.lastIndex) {
                EduDivider()
            }
        }
    }
}

@Composable
private fun ParentLessonMissingRequirementsCard(missingRequirements: Int) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.warning.copy(alpha = 0.12f),
        borderColor = colors.warning.copy(alpha = 0.34f),
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentLessonDetailsIconBadge(
                icon = Icons.Filled.WarningAmber,
                contentColor = colors.warning,
                containerColor = colors.warning.copy(alpha = 0.18f),
                modifier = Modifier.size(Sizing.touchTarget),
            )
            Text(
                text = stringResource(R.string.pr06_missing_warning, numeral(missingRequirements)),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentLessonTimelineCard(events: List<ParentLessonActivityEvent>) {
    EduCard {
        ProgressSpine(
            nodes = events.map { SpineNode(id = it.id, state = SpineNodeState.Completed) },
        ) { index, _ ->
            val event = events[index]
            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = if (index == events.lastIndex) 0.dp else Spacing.sm),
            ) {
                Text(
                    text = event.label,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = event.timeLabel,
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
        }
    }
}

@Composable
private fun ParentLessonDetailsIconBadge(
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
private fun ParentLessonDetailsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
        SkeletonListItem()
    }
}
