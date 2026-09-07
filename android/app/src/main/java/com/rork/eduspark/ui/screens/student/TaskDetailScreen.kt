package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.TaskHint
import com.rork.eduspark.data.model.TaskWorkflowStatus
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.foundation.shape.RoundedCornerShape
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-04 · Task Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A persistent bottom action bar outside the scrollable content — required for long-form,
 * paginated task content per the Screen Inventory. The CTA's label and action both derive
 * from [ProjectTask.workflowStatus]; only "Start task" ever calls [TaskDetailViewModel.startTask].
 * Hints reveal one at a time via [TaskDetailViewModel.revealNextHint] — never all at once, and
 * the XP cost shown is informational only (see [TaskHint]'s own doc comment for why nothing
 * here deducts real XP).
 */
@Composable
fun TaskDetailScreen(
    projectId: String,
    taskId: String,
    onBack: () -> Unit,
    onOpenComposer: (taskId: String) -> Unit,
    onOpenReview: (taskId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TaskDetailViewModel = koinViewModel(parameters = { parametersOf(projectId, taskId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.pj04_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TaskDetailSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            Column(modifier = Modifier.fillMaxSize()) {
                TaskDetailContent(
                    data = data,
                    revealedHintIds = state.revealedHintIds,
                    onRevealHint = viewModel::revealNextHint,
                    modifier = Modifier.weight(1f),
                )
                TaskDetailActionBar(
                    task = data.task,
                    isStarting = state.isStarting,
                    onStart = viewModel::startTask,
                    onOpenComposer = { onOpenComposer(taskId) },
                    onOpenReview = { onOpenReview(taskId) },
                )
            }
        }
    }
}

@Composable
private fun TaskDetailContent(
    data: TaskDetailScreenData,
    revealedHintIds: Set<String>,
    onRevealHint: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val task = data.task
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            Text(
                text = stringResource(R.string.pj04_context_format, data.projectTitle, data.milestoneTitle),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
            Text(
                text = task.title,
                style = EduTheme.typography.brandTitle,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            StatusPill(
                label = workflowStatusLabel(task.workflowStatus),
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            if (task.objective != null) {
                Text(
                    text = task.objective,
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        if (task.instructions.isNotEmpty()) {
            item {
                SectionHeader(title = stringResource(R.string.pj04_instructions_section))
                EduCard {
                    task.instructions.forEachIndexed { index, step ->
                        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(vertical = Spacing.xxs)) {
                            Text(stringResource(R.string.pj04_step_number, numeral(index + 1)), style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.primary)
                            Text(step, style = EduTheme.typography.body, color = colors.textPrimary)
                        }
                    }
                }
            }
        }

        if (task.safetyNote != null) {
            item { SafetyCallout(task.safetyNote) }
        }

        if (task.whatGoodLooksLike.isNotEmpty()) {
            item {
                SectionHeader(title = stringResource(R.string.pj04_good_example_section))
                EduCard {
                    task.whatGoodLooksLike.forEach { point ->
                        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(vertical = Spacing.xxs)) {
                            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.iconSm))
                            Text(point, style = EduTheme.typography.body, color = colors.textPrimary)
                        }
                    }
                }
            }
        }

        if (task.hints.isNotEmpty()) {
            item {
                SectionHeader(title = stringResource(R.string.pj04_hints_section))
                HintsSection(hints = task.hints, revealedHintIds = revealedHintIds, onRevealHint = onRevealHint)
            }
        }
    }
}

@Composable
private fun SafetyCallout(note: String) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.warning.copy(alpha = 0.12f), RoundedCornerShape(Radius.md))
            .padding(Spacing.card)
            .padding(bottom = Spacing.section),
    ) {
        Icon(Icons.Filled.WarningAmber, contentDescription = null, tint = colors.warning, modifier = Modifier.size(Sizing.icon))
        Text(note, style = EduTheme.typography.body, color = colors.textPrimary)
    }
}

@Composable
private fun HintsSection(hints: List<TaskHint>, revealedHintIds: Set<String>, onRevealHint: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        hints.forEachIndexed { index, hint ->
            if (hint.id in revealedHintIds) {
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(vertical = Spacing.xxs)) {
                    Icon(Icons.Filled.Lightbulb, contentDescription = null, tint = colors.warning, modifier = Modifier.size(Sizing.iconSm))
                    Text(hint.text, style = EduTheme.typography.body, color = colors.textPrimary)
                }
            }
        }
        val nextHint = hints.firstOrNull { it.id !in revealedHintIds }
        if (nextHint != null) {
            SecondaryButton(
                text = stringResource(R.string.pj04_reveal_hint, numeral(nextHint.xpCost)),
                onClick = onRevealHint,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun TaskDetailActionBar(
    task: ProjectTask,
    isStarting: Boolean,
    onStart: () -> Unit,
    onOpenComposer: () -> Unit,
    onOpenReview: () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(Spacing.gutter),
    ) {
        when (task.workflowStatus) {
            null, TaskWorkflowStatus.NotStarted -> PrimaryButton(
                text = stringResource(R.string.pj04_start_task),
                onClick = onStart,
                isLoading = isStarting,
                modifier = Modifier.fillMaxWidth(),
            )
            TaskWorkflowStatus.InProgress -> PrimaryButton(
                text = stringResource(R.string.pj04_continue_task),
                onClick = onOpenComposer,
                modifier = Modifier.fillMaxWidth(),
            )
            TaskWorkflowStatus.ReadyToSubmit -> PrimaryButton(
                text = stringResource(R.string.pj04_submit_work),
                onClick = onOpenComposer,
                modifier = Modifier.fillMaxWidth(),
            )
            TaskWorkflowStatus.Submitted -> PrimaryButton(
                text = stringResource(R.string.pj04_view_review_status),
                onClick = onOpenReview,
                modifier = Modifier.fillMaxWidth(),
            )
            TaskWorkflowStatus.Reviewed -> PrimaryButton(
                text = stringResource(R.string.pj04_view_review),
                onClick = onOpenReview,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun workflowStatusLabel(status: TaskWorkflowStatus?): String = when (status) {
    null, TaskWorkflowStatus.NotStarted -> stringResource(R.string.pj04_status_not_started)
    TaskWorkflowStatus.InProgress -> stringResource(R.string.pj04_status_in_progress)
    TaskWorkflowStatus.ReadyToSubmit -> stringResource(R.string.pj04_status_ready)
    TaskWorkflowStatus.Submitted -> stringResource(R.string.pj04_status_submitted)
    TaskWorkflowStatus.Reviewed -> stringResource(R.string.pj04_status_reviewed)
}

@Composable
private fun TaskDetailSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}

