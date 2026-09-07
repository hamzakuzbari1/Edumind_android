package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectMaterial
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.model.ProjectShowcaseSample
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-02 · Project Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Follows the Screen Inventory hierarchy literally: hero (deliverable) → skills → materials →
 * time/difficulty → milestone preview (Progress Spine) → showcase → primary action. The hero
 * always leads with [Project.deliverable], never [Project.title] or [Project.description] —
 * the outcome, not the lesson topic.
 */
@Composable
fun ProjectDetailScreen(
    projectId: String,
    onBack: () -> Unit,
    onOpenMilestoneBoard: (projectId: String) -> Unit,
    onOpenMaterialsSafety: (projectId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProjectDetailViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is ProjectDetailEvent.NavigateToMilestoneBoard -> onOpenMilestoneBoard(event.projectId)
            }
        }
    }

    EduScaffold(title = stringResource(R.string.pj02_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ProjectDetailSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ProjectDetailContent(
                data = data,
                isStarting = state.isStarting,
                onToggleMaterial = viewModel::toggleMaterial,
                onPrimaryAction = viewModel::onPrimaryAction,
                onOpenMaterialsSafety = { onOpenMaterialsSafety(projectId) },
            )
        }
    }

    if (state.showTeamBoundary) {
        ConfirmDialog(
            title = stringResource(R.string.pj02_team_boundary_title),
            body = stringResource(R.string.pj02_team_boundary_body),
            confirmLabel = stringResource(R.string.common_close),
            onConfirm = viewModel::dismissTeamBoundary,
            onDismiss = viewModel::dismissTeamBoundary,
        )
    }
}

@Composable
private fun ProjectDetailContent(
    data: ProjectDetailScreenData,
    isStarting: Boolean,
    onToggleMaterial: (String, Boolean) -> Unit,
    onPrimaryAction: () -> Unit,
    onOpenMaterialsSafety: () -> Unit,
) {
    val project = data.project

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item { HeroSection(project) }
        item { SkillsSection(project.skills) }
        item {
            MaterialsSection(project.materials, data.checkedMaterialIds, onToggleMaterial)
            // PJ-12 — only a Physical project has a materials/safety sheet worth opening;
            // absent entirely for Digital ones, never a link to an empty screen.
            if (project.medium == ProjectMedium.Physical) {
                SecondaryButton(
                    text = stringResource(R.string.pj12_open_from_project),
                    onClick = onOpenMaterialsSafety,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }
        item { TimeDifficultySection(project) }
        item { MilestonePreviewSection(project) }
        item { ShowcaseSection(project.showcaseSamples) }
        item { PrimaryActionSection(project, data.activeProject, isStarting, onPrimaryAction) }
    }
}

@Composable
private fun HeroSection(project: Project) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        Text(project.subjectTitle, style = EduTheme.typography.caption, color = colors.primary)
        Text(
            text = project.deliverable,
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(
            text = project.description,
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            PillTag(icon = if (project.mode == ProjectMode.Solo) Icons.Filled.Person else Icons.Filled.Groups, label = projectModeLabel(project.mode))
            PillTag(label = projectMediumLabel(project.medium))
        }
    }
}

@Composable
private fun SkillsSection(skills: List<String>) {
    if (skills.isEmpty()) return
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        SectionHeader(title = stringResource(R.string.pj02_skills_section))
        Column {
            skills.forEach { skill ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(vertical = Spacing.xxs)) {
                    Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = EduTheme.colors.primary, modifier = Modifier.size(Sizing.iconSm))
                    Text(skill, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
                }
            }
        }
    }
}

@Composable
private fun MaterialsSection(materials: List<ProjectMaterial>, checkedIds: Set<String>, onToggle: (String, Boolean) -> Unit) {
    if (materials.isEmpty()) return
    val colors = EduTheme.colors
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        SectionHeader(title = stringResource(R.string.pj02_materials_section))
        Text(
            text = stringResource(R.string.pj02_materials_hint),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(bottom = Spacing.xs),
        )
        EduCard {
            materials.forEachIndexed { index, material ->
                val checked = material.id in checkedIds
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = Spacing.xxs),
                ) {
                    Checkbox(
                        checked = checked,
                        onCheckedChange = { onToggle(material.id, it) },
                        colors = CheckboxDefaults.colors(checkedColor = colors.primary, checkmarkColor = colors.onPrimary),
                    )
                    Text(
                        text = material.label,
                        style = EduTheme.typography.body,
                        color = if (checked) colors.textSecondary else colors.textPrimary,
                    )
                }
            }
        }
    }
}

@Composable
private fun TimeDifficultySection(project: Project) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.section),
        modifier = Modifier.padding(bottom = Spacing.section),
    ) {
        Column {
            Text(stringResource(R.string.pj02_time_label), style = EduTheme.typography.caption, color = colors.textSecondary)
            Text(project.estimatedDurationLabel, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        }
        Column {
            Text(stringResource(R.string.pj02_difficulty_label), style = EduTheme.typography.caption, color = colors.textSecondary)
            Text(projectDifficultyLabel(project.difficulty), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        }
    }
}

@Composable
private fun MilestonePreviewSection(project: Project) {
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        SectionHeader(title = stringResource(R.string.pj02_milestones_section))
        val nodes = project.milestones.map { SpineNode(id = it.id, state = milestoneSpineState(it)) }
        ProgressSpine(nodes = nodes) { index, _ ->
            Text(
                text = project.milestones[index].title,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(start = Spacing.xs, end = Spacing.xs, top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun ShowcaseSection(samples: List<ProjectShowcaseSample>) {
    if (samples.isEmpty()) return
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        SectionHeader(title = stringResource(R.string.pj02_showcase_section))
        samples.forEach { sample ->
            EduCard {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatar)
                            .background(EduTheme.colors.neutralAlpha100, CircleShape),
                    ) {
                        Icon(Icons.Filled.PhotoLibrary, contentDescription = null, tint = EduTheme.colors.textSecondary)
                    }
                    Text(sample.caption, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun PrimaryActionSection(project: Project, activeProject: ActiveProject?, isStarting: Boolean, onClick: () -> Unit) {
    val label = when {
        activeProject != null -> stringResource(R.string.pj02_continue_project)
        project.mode == ProjectMode.Solo -> stringResource(R.string.pj02_start_project)
        else -> stringResource(R.string.pj02_join_team)
    }
    PrimaryButton(
        text = label,
        onClick = onClick,
        isLoading = isStarting,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun PillTag(label: String, icon: ImageVector? = null) {
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

@Composable
private fun ProjectDetailSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}

