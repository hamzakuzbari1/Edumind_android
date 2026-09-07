package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayCircleFilled
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectMilestone
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.ProjectTaskStatus
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.progress.SpineRow
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-03 · Milestone Board — the Progress Spine as the whole screen.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Not a decorative progress widget above a list — [SpineRow] rows, rendered individually so
 * the board can virtualise, ARE the information architecture. Each bead's
 * [SpineNodeState] is [milestoneSpineState] — always derived from the milestone's own tasks,
 * the same rule PJ-02's preview uses, so a milestone can never disagree with its own tasks.
 * The current milestone is expanded by default. A task tap is gated by [ProjectTask.status]:
 * only [ProjectTaskStatus.Current] and [ProjectTaskStatus.Completed] open PJ-04 — a
 * [ProjectTaskStatus.Blocked] tap stays on this screen and shows [BlockedTaskDialog] instead
 * (reusing [ProjectTask.blockerLabel], never a fabricated prerequisite flow), and
 * [ProjectTaskStatus.Upcoming] is a no-op, since PJ-04 has nothing honest to show for a task
 * that hasn't been reached yet.
 *
 * Two small contextual actions were added for PJ-08/PJ-09, deliberately not a redesign of this
 * screen: a top-bar "Team Workspace" icon appears only for [ProjectMode.Team] projects (Solo
 * projects like the water-alarm fixture never show it), and each expanded, reachable milestone
 * (Completed or Current — never Locked) gets one small "Reflection" text action below its
 * tasks. Neither adds a card, a section, or a second primary action.
 */
@Composable
fun MilestoneBoardScreen(
    projectId: String,
    onBack: () -> Unit,
    onOpenTask: (taskId: String) -> Unit,
    onOpenTeamWorkspace: () -> Unit,
    onOpenReflection: (milestoneId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MilestoneBoardViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var blockedTask by remember { mutableStateOf<ProjectTask?>(null) }
    val data = (state.result as? UiState.Content)?.data

    EduScaffold(
        title = stringResource(R.string.pj03_title),
        onBack = onBack,
        actions = {
            if (data?.projectMode == ProjectMode.Team) {
                EduIconButton(
                    icon = Icons.Filled.Groups,
                    contentDescription = stringResource(R.string.pj08_title),
                    onClick = onOpenTeamWorkspace,
                )
            }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { MilestoneBoardSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { content ->
            MilestoneBoardContent(
                projectTitle = content.projectTitle,
                milestones = content.activeProject.milestones,
                expandedMilestoneId = state.expandedMilestoneId,
                onToggleMilestone = viewModel::toggleMilestoneExpanded,
                onTaskTap = { task ->
                    when (task.status) {
                        ProjectTaskStatus.Blocked -> blockedTask = task
                        ProjectTaskStatus.Upcoming -> Unit
                        ProjectTaskStatus.Current, ProjectTaskStatus.Completed -> onOpenTask(task.id)
                    }
                },
                onOpenReflection = onOpenReflection,
            )
        }
    }

    blockedTask?.let { task ->
        BlockedTaskDialog(task = task, onDismiss = { blockedTask = null })
    }
}

/** A [ProjectTaskStatus.Blocked] tap's only surface — dismiss/understand only, no invented prerequisite action. */
@Composable
private fun BlockedTaskDialog(task: ProjectTask, onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(text = task.title, style = EduTheme.typography.title, color = colors.textPrimary)
        },
        text = {
            Text(
                text = task.blockerLabel ?: stringResource(R.string.pj03_blocked_generic),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
            )
        },
        confirmButton = {
            PrimaryButton(text = stringResource(R.string.pj03_blocked_dismiss), onClick = onDismiss)
        },
        containerColor = colors.surface,
        titleContentColor = colors.textPrimary,
        textContentColor = colors.textSecondary,
    )
}

@Composable
private fun MilestoneBoardContent(
    projectTitle: String,
    milestones: List<ProjectMilestone>,
    expandedMilestoneId: String?,
    onToggleMilestone: (String) -> Unit,
    onTaskTap: (ProjectTask) -> Unit,
    onOpenReflection: (milestoneId: String) -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(
                text = projectTitle,
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.md),
            )
        }

        itemsIndexed(milestones, key = { _, milestone -> milestone.id }) { index, milestone ->
            val nodeState = milestoneSpineState(milestone)
            val isExpanded = if (expandedMilestoneId != null) {
                milestone.id == expandedMilestoneId
            } else {
                nodeState == SpineNodeState.Current
            }

            SpineRow(
                node = SpineNode(id = milestone.id, state = nodeState),
                isFirst = index == 0,
                isLast = index == milestones.lastIndex,
                accessibilityLabel = milestone.title,
                modifier = Modifier.eduClickable(onClickLabel = milestone.title) { onToggleMilestone(milestone.id) },
            ) {
                MilestoneRowContent(
                    milestone = milestone,
                    nodeState = nodeState,
                    isExpanded = isExpanded,
                    onTaskTap = onTaskTap,
                    onOpenReflection = { onOpenReflection(milestone.id) },
                )
            }
        }
    }
}

@Composable
private fun MilestoneRowContent(
    milestone: ProjectMilestone,
    nodeState: SpineNodeState,
    isExpanded: Boolean,
    onTaskTap: (ProjectTask) -> Unit,
    onOpenReflection: () -> Unit,
) {
    val colors = EduTheme.colors

    Column(modifier = Modifier.padding(start = Spacing.sm, end = Spacing.xs)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = milestone.title,
                style = if (nodeState == SpineNodeState.Current) {
                    EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold)
                } else {
                    EduTheme.typography.body
                },
                color = if (nodeState == SpineNodeState.Locked) colors.textSecondary else colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            Icon(
                imageVector = if (isExpanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                contentDescription = null,
                tint = colors.textSecondary,
                modifier = Modifier.size(Sizing.iconSm),
            )
        }

        if (nodeState == SpineNodeState.Locked) {
            Text(
                text = stringResource(R.string.pj03_locked_hint),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }

        if (isExpanded) {
            Column(modifier = Modifier.padding(top = Spacing.xs)) {
                milestone.tasks.forEach { task -> TaskRow(task = task, onTap = { onTaskTap(task) }) }
                // PJ-09 — only for a milestone the student has actually reached; reflecting on
                // one still Locked has nothing to reflect on yet.
                if (nodeState != SpineNodeState.Locked) {
                    GhostButton(
                        text = stringResource(R.string.pj09_open_from_milestone),
                        onClick = onOpenReflection,
                        leadingIcon = Icons.Filled.Mic,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }
    }
}

@Composable
private fun TaskRow(task: ProjectTask, onTap: () -> Unit) {
    val colors = EduTheme.colors
    val icon = when (task.status) {
        ProjectTaskStatus.Completed -> Icons.Filled.CheckCircle
        ProjectTaskStatus.Current -> Icons.Filled.PlayCircleFilled
        ProjectTaskStatus.Blocked -> Icons.Filled.ErrorOutline
        ProjectTaskStatus.Upcoming -> Icons.Filled.RadioButtonUnchecked
    }
    val tint = when (task.status) {
        ProjectTaskStatus.Completed -> colors.success
        ProjectTaskStatus.Current -> colors.primary
        ProjectTaskStatus.Blocked -> colors.danger
        ProjectTaskStatus.Upcoming -> colors.textSecondary
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .eduClickable(onClickLabel = task.title, onClick = onTap)
            .padding(vertical = Spacing.xs),
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.iconSm))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = task.title,
                style = EduTheme.typography.body,
                color = if (task.status == ProjectTaskStatus.Upcoming) colors.textSecondary else colors.textPrimary,
            )
            if (task.status == ProjectTaskStatus.Blocked && task.blockerLabel != null) {
                Text(
                    text = task.blockerLabel,
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun MilestoneBoardSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        repeat(4) { SkeletonListItem() }
    }
}

