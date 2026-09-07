package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Workspaces
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectDifficulty
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.ProjectMilestone
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.model.ProjectTaskStatus
import com.rork.eduspark.data.model.isCompleted
import com.rork.eduspark.data.model.isCurrent
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.progress.HorizontalMilestoneBeads
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-01 · Projects Hub — the STUDENT_PROJECTS tab root.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Two sections, per the Screen Inventory: My Projects (already-started, answers "what do I do
 * next?") and Discover (the catalog, filtered locally — see [ProjectsHubViewModel]'s own doc
 * comment for why filtering never touches the repository). No `EduScaffold`: this is a tab
 * root, RoleShell's own chrome wraps it, same convention [StudentHomeScreen]/[StudentProfileScreen] use.
 *
 * PJ-10's one entry point lives in "My Projects"' own [SectionHeader] action slot — a single
 * icon, not a new section or a bottom-nav item, since the showcase is a contextual jump from
 * here, not a third thing this hub is about.
 */
private enum class ProjectsHubMode { Current, Discover }

@Composable
fun ProjectsHubScreen(
    onOpenProjectDetail: (projectId: String) -> Unit,
    onOpenMilestoneBoard: (projectId: String) -> Unit,
    onOpenPortfolio: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProjectsHubViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var mode by rememberSaveable { mutableStateOf(ProjectsHubMode.Current) }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ProjectsHubSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        if (mode == ProjectsHubMode.Discover) {
            Column(modifier = Modifier.fillMaxSize()) {
                GhostButton(
                    text = stringResource(R.string.pj01_my_projects_section),
                    onClick = { mode = ProjectsHubMode.Current },
                    modifier = Modifier.padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
                )
                DiscoverTab(
                    catalog = data.catalog,
                    activeIds = data.activeProjects.map { it.projectId }.toSet(),
                    filters = state.filters,
                    onOpenDiscoverProject = onOpenProjectDetail,
                    onToggleSubject = viewModel::toggleSubjectFilter,
                    onToggleDifficulty = viewModel::toggleDifficultyFilter,
                    onToggleDuration = viewModel::toggleDurationFilter,
                    onToggleMode = viewModel::toggleModeFilter,
                    onToggleMedium = viewModel::toggleMediumFilter,
                    onClearFilters = viewModel::clearFilters,
                    modifier = Modifier.weight(1f),
                )
            }
        } else {
            MyProjectsTab(
                activeProjects = data.activeProjects,
                catalog = data.catalog,
                onOpenActiveProject = onOpenMilestoneBoard,
                onOpenDiscover = { mode = ProjectsHubMode.Discover },
                onOpenShowcase = onOpenPortfolio,
            )
        }
    }
}

@Composable
private fun MyProjectsTab(
    activeProjects: List<ActiveProject>,
    catalog: List<Project>,
    onOpenActiveProject: (String) -> Unit,
    onOpenDiscover: () -> Unit,
    onOpenShowcase: () -> Unit,
) {
    if (activeProjects.isEmpty()) {
        MessageState(
            icon = Icons.Filled.Build,
            title = stringResource(R.string.pj01_no_active_title),
            body = stringResource(R.string.pj01_no_active_body),
            primaryActionLabel = stringResource(R.string.pj01_discover_section),
            onPrimaryAction = onOpenDiscover,
            modifier = Modifier.fillMaxSize(),
        )
        return
    }

    val current = activeProjects.first()
    val currentProject = catalog.firstOrNull { it.id == current.projectId }
    val others = activeProjects.drop(1).mapNotNull { active ->
        catalog.firstOrNull { it.id == active.projectId }?.let { it to active }
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (currentProject != null) {
            item {
                CurrentProjectHero(project = currentProject, active = current, onClick = { onOpenActiveProject(current.projectId) })
            }
            item {
                Text(
                    text = stringResource(R.string.pj01_milestones_section),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textPrimary,
                )
                EduCard(modifier = Modifier.padding(top = Spacing.xs)) {
                    HubTimeline {
                        current.milestones.forEach { milestone ->
                            val state = when {
                                milestone.isCompleted -> HubTimelineState.Done
                                milestone.isCurrent -> HubTimelineState.Current
                                else -> HubTimelineState.Upcoming
                            }
                            HubTimelineRow(state = state, emphasized = milestone.isCurrent) {
                                Text(
                                    text = milestone.title,
                                    style = EduTheme.typography.body.copy(fontWeight = if (milestone.isCurrent) FontWeight.ExtraBold else FontWeight.SemiBold),
                                    color = if (state == HubTimelineState.Upcoming) EduTheme.colors.textTertiary else EduTheme.colors.textPrimary,
                                )
                            }
                        }
                    }
                }
            }
        }
        if (others.isNotEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.pj01_other_projects),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textTertiary,
                )
                EduCard(modifier = Modifier.padding(top = Spacing.xs), contentPadding = PaddingValues(0.dp)) {
                    others.forEach { (project, active) ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                            modifier = Modifier
                                .fillMaxWidth()
                                .eduClickable(onClickLabel = project.title, onClick = { onOpenActiveProject(active.projectId) })
                                .padding(horizontal = Spacing.card, vertical = Spacing.sm),
                        ) {
                            BioProjectVisual()
                            Text(
                                text = project.title,
                                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                                color = EduTheme.colors.textPrimary,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                GhostButton(
                    text = stringResource(R.string.pj01_discover_section),
                    onClick = onOpenDiscover,
                    modifier = Modifier.weight(1f),
                )
                GhostButton(
                    text = stringResource(R.string.pj01_gallery_tab),
                    onClick = onOpenShowcase,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun CurrentProjectHero(project: Project, active: ActiveProject, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val progress = if (active.totalMilestoneCount == 0) 0f else active.completedMilestoneCount / active.totalMilestoneCount.toFloat()
    EduCard(onClick = onClick, contentPadding = PaddingValues(0.dp)) {
        SolarProjectVisual()
        Column(modifier = Modifier.padding(Spacing.card)) {
            Text(project.title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = colors.textPrimary)
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm, bottom = Spacing.xs),
            ) {
                Text(stringResource(R.string.pj01_progress_label), style = EduTheme.typography.caption, color = colors.textSecondary)
                Text(
                    text = stringResource(R.string.progress_percent, (progress * 100).toInt()),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
            }
            EduLinearProgress(progress = progress)
            Text(
                text = stringResource(R.string.pj01_current_milestone),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = active.currentMilestone?.title ?: project.deliverable,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DiscoverTab(
    catalog: List<Project>,
    activeIds: Set<String>,
    filters: DiscoverFilters,
    onOpenDiscoverProject: (String) -> Unit,
    onToggleSubject: (String) -> Unit,
    onToggleDifficulty: (ProjectDifficulty) -> Unit,
    onToggleDuration: (String) -> Unit,
    onToggleMode: (ProjectMode) -> Unit,
    onToggleMedium: (ProjectMedium) -> Unit,
    onClearFilters: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val discoverable = catalog.filterNot { it.id in activeIds }
    val filtered = discoverable.filter { project ->
        (filters.subjectId == null || project.subjectId == filters.subjectId) &&
            (filters.difficulty == null || project.difficulty == filters.difficulty) &&
            (filters.durationLabel == null || project.estimatedDurationLabel == filters.durationLabel) &&
            (filters.mode == null || project.mode == filters.mode) &&
            (filters.medium == null || project.medium == filters.medium)
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            ) {
                catalog.map { it.subjectId to it.subjectTitle }.distinct().forEach { (id, title) ->
                    EduChip(label = title, selected = filters.subjectId == id, onClick = { onToggleSubject(id) })
                }
                ProjectDifficulty.entries.forEach { difficulty ->
                    EduChip(
                        label = projectDifficultyLabel(difficulty),
                        selected = filters.difficulty == difficulty,
                        onClick = { onToggleDifficulty(difficulty) },
                    )
                }
                catalog.map { it.estimatedDurationLabel }.distinct().forEach { label ->
                    EduChip(label = label, selected = filters.durationLabel == label, onClick = { onToggleDuration(label) })
                }
                ProjectMode.entries.forEach { mode ->
                    EduChip(label = projectModeLabel(mode), selected = filters.mode == mode, onClick = { onToggleMode(mode) })
                }
                ProjectMedium.entries.forEach { medium ->
                    EduChip(label = projectMediumLabel(medium), selected = filters.medium == medium, onClick = { onToggleMedium(medium) })
                }
            }
        }

        if (filtered.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Build,
                    title = stringResource(R.string.pj01_no_discover_results_title),
                    body = stringResource(R.string.pj01_no_discover_results_body),
                    primaryActionLabel = stringResource(R.string.pj01_clear_filters),
                    onPrimaryAction = onClearFilters,
                )
            }
        } else {
            items(filtered, key = { it.id }) { project ->
                DiscoverProjectCard(project = project, onClick = { onOpenDiscoverProject(project.id) })
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        }
    }
}

/**
 * The Gallery tab is a pass-through into the existing, unduplicated PJ-10 Portfolio screen —
 * not a reimplementation of it. A single entry card matches the approved design's 3-tab shell
 * without building a second showcase grid.
 */
@Composable
private fun GalleryTab(onOpenPortfolio: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        EduCard {
            Icon(Icons.Filled.Workspaces, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconLg))
            Text(
                text = stringResource(R.string.pj01_gallery_teaser_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.pj01_gallery_teaser_body),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )
            PrimaryButton(
                text = stringResource(R.string.pj01_gallery_open_action),
                onClick = onOpenPortfolio,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ActiveProjectCard(project: Project, active: ActiveProject, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val nextTask = active.currentMilestone?.tasks?.firstOrNull {
        it.status == ProjectTaskStatus.Current || it.status == ProjectTaskStatus.Blocked
    }

    EduCard(onClick = onClick, borderColor = colors.primary) {
        Text(project.subjectTitle, style = EduTheme.typography.caption, color = colors.primary)
        Text(
            project.title,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(project.deliverable, style = EduTheme.typography.caption, color = colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))

        Text(
            text = stringResource(R.string.pj01_milestone_progress, numeral(active.completedMilestoneCount), numeral(active.totalMilestoneCount)),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        // Approved design's compact horizontal milestone-bead row (ProjectsHub.dc.html),
        // replacing the previous plain linear progress bar.
        HorizontalMilestoneBeads(
            states = active.milestones.map { it.beadState() },
            modifier = Modifier.padding(top = Spacing.xs),
        )

        if (nextTask != null) {
            Text(
                text = stringResource(R.string.pj01_next_action, nextTask.title),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            ProjectModeMediumChip(icon = if (project.mode == ProjectMode.Solo) Icons.Filled.Person else Icons.Filled.Groups, label = projectModeLabel(project.mode))
            ProjectModeMediumChip(icon = Icons.Filled.Build, label = projectMediumLabel(project.medium))
        }
    }
}

@Composable
private fun DiscoverProjectCard(project: Project, onClick: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(onClick = onClick) {
        Text(project.subjectTitle, style = EduTheme.typography.caption, color = colors.primary)
        Text(
            text = project.deliverable,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(project.title, style = EduTheme.typography.caption, color = colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            ProjectModeMediumChip(label = projectDifficultyLabel(project.difficulty))
            ProjectModeMediumChip(label = project.estimatedDurationLabel)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.xs)) {
            ProjectModeMediumChip(icon = if (project.mode == ProjectMode.Solo) Icons.Filled.Person else Icons.Filled.Groups, label = projectModeLabel(project.mode))
            ProjectModeMediumChip(icon = Icons.Filled.Build, label = projectMediumLabel(project.medium))
        }
    }
}

@Composable
private fun ProjectModeMediumChip(label: String, icon: ImageVector? = null) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier
            .background(colors.neutralAlpha100, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.sm, vertical = Spacing.xxs),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        }
        Text(label, style = EduTheme.typography.caption, color = colors.textSecondary)
    }
}

/** [ProjectMilestone]'s state, expressed as [SpineNodeState] for [HorizontalMilestoneBeads]. */
private fun ProjectMilestone.beadState(): SpineNodeState = when {
    isCompleted -> SpineNodeState.Completed
    isCurrent -> SpineNodeState.Current
    else -> SpineNodeState.Locked
}

@Composable
private fun ProjectsHubSkeleton() {
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
