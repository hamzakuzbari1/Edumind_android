package com.rork.eduspark.ui.screens.student

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ProjectDifficulty
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.ProjectMilestone
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.model.ProjectTaskStatus
import com.rork.eduspark.data.model.isCompleted
import com.rork.eduspark.data.model.isCurrent
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.theme.EduTheme

/**
 * The one place a [ProjectMilestone] becomes a Progress Spine bead — PJ-02's not-started
 * preview and PJ-03's live board both call this, so a milestone can never render differently
 * on the two screens. See [ProjectMilestone]'s own doc comment for why this is derived from
 * tasks rather than a stored status.
 */
fun milestoneSpineState(milestone: ProjectMilestone): SpineNodeState = when {
    milestone.isCompleted -> SpineNodeState.Completed
    milestone.isCurrent -> SpineNodeState.Current
    else -> SpineNodeState.Locked
}

/** Shared label resolution for PJ-01/PJ-02/PJ-03 — one place, so the three screens never drift on wording. */
@Composable
fun projectDifficultyLabel(difficulty: ProjectDifficulty): String = when (difficulty) {
    ProjectDifficulty.Beginner -> stringResource(R.string.pj_difficulty_beginner)
    ProjectDifficulty.Intermediate -> stringResource(R.string.pj_difficulty_intermediate)
    ProjectDifficulty.Advanced -> stringResource(R.string.pj_difficulty_advanced)
}

@Composable
fun projectModeLabel(mode: ProjectMode): String = when (mode) {
    ProjectMode.Solo -> stringResource(R.string.pj_mode_solo)
    ProjectMode.Team -> stringResource(R.string.pj_mode_team)
}

@Composable
fun projectMediumLabel(medium: ProjectMedium): String = when (medium) {
    ProjectMedium.Physical -> stringResource(R.string.pj_medium_physical)
    ProjectMedium.Digital -> stringResource(R.string.pj_medium_digital)
}

/** PJ-08. Same [ProjectTaskStatus] icon/tint mapping [MilestoneBoardScreen]'s own TaskRow uses, shared here so a new screen never invents a second wording. */
@Composable
fun projectTaskStatusLabel(status: ProjectTaskStatus): String = when (status) {
    ProjectTaskStatus.Completed -> stringResource(R.string.pj_task_status_completed)
    ProjectTaskStatus.Current -> stringResource(R.string.pj_task_status_current)
    ProjectTaskStatus.Blocked -> stringResource(R.string.pj_task_status_blocked)
    ProjectTaskStatus.Upcoming -> stringResource(R.string.pj_task_status_upcoming)
}

@Composable
fun projectTaskStatusColor(status: ProjectTaskStatus): Color = when (status) {
    ProjectTaskStatus.Completed -> EduTheme.colors.success
    ProjectTaskStatus.Current -> EduTheme.colors.primary
    ProjectTaskStatus.Blocked -> EduTheme.colors.danger
    ProjectTaskStatus.Upcoming -> EduTheme.colors.textSecondary
}

