package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyItemScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.zIndex
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.SafetySeverity
import com.rork.eduspark.data.model.TeacherProject
import com.rork.eduspark.data.model.TeacherProjectMaterial
import com.rork.eduspark.data.model.TeacherProjectMediaKind
import com.rork.eduspark.data.model.TeacherProjectMilestone
import com.rork.eduspark.data.model.TeacherProjectRubricCriterion
import com.rork.eduspark.data.model.TeacherProjectSafetyNote
import com.rork.eduspark.data.model.TeacherProjectStatus
import com.rork.eduspark.data.model.TeacherProjectTask
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.nav.SegmentedControl
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.screens.student.projectMediumLabel
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf
import kotlin.math.roundToInt

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-17 · Project Authoring — the project editor.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Structured hierarchy: Metadata → Milestones (with nested tasks) → Rubric → Materials & Safety
 * (only for [ProjectMedium.Physical]) → Media → Publish — never a flat desktop-style form.
 * Milestone reorder reuses the exact dependency-free drag primitive TC-04/TC-10 already proved
 * (long-press the handle, vertical delta only, commit on release); tasks — nested one level
 * deeper inside an already-scrolling list — reorder via up/down instead of a second drag layer.
 * Rubric weights are always shown next to a running total, colored red until it reads exactly
 * 100 — never silently normalized.
 */
@Composable
fun TeacherProjectEditorScreen(
    projectId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherProjectEditorViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val project = (state.result as? UiState.Content)?.data

    EduScaffold(title = project?.title?.ifBlank { stringResource(R.string.tc17_untitled_project) } ?: stringResource(R.string.tc17_editor_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherProjectEditorSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherProjectEditorContent(project = data, state = state, viewModel = viewModel)
        }
    }

    if (state.showMilestoneEditor) MilestoneEditorDialog(state, viewModel)
    if (state.showTaskEditor) TaskEditorDialog(state, viewModel)
    if (state.showCriterionEditor) CriterionEditorDialog(state, viewModel)
    if (state.showMaterialEditor) MaterialEditorDialog(state, viewModel)
    if (state.showSafetyEditor) SafetyEditorDialog(state, viewModel)
    if (state.showMediaEditor) MediaEditorDialog(state, viewModel)
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherProjectEditorContent(project: TeacherProject, state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors

    var orderedIds by remember(project.milestones.map { it.id }) { mutableStateOf(project.milestones.map { it.id }) }
    val milestonesById = remember(project.milestones) { project.milestones.associateBy { it.id } }
    var draggingId by remember { mutableStateOf<String?>(null) }
    var dragDeltaPx by remember { mutableFloatStateOf(0f) }
    val rowHeightsPx = remember { mutableStateMapOf<String, Int>() }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        // ── Metadata ──────────────────────────────────────────────────────
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                Text(project.courseTitle, style = EduTheme.typography.caption, color = colors.zaytoun)
                Text("·", style = EduTheme.typography.caption, color = colors.textMuted)
                StatusPill(
                    label = teacherProjectStatusLabel(project.status),
                    contentColor = if (project.status == TeacherProjectStatus.Published) colors.success else colors.textMuted,
                    containerColor = (if (project.status == TeacherProjectStatus.Published) colors.success else colors.textMuted).copy(alpha = 0.14f),
                )
            }
            Text(
                text = stringResource(if (state.hasUnsavedMetadata) R.string.tc16_unsaved else R.string.tc16_all_saved),
                style = EduTheme.typography.caption,
                color = if (state.hasUnsavedMetadata) colors.warning else colors.success,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.section),
            )

            SectionHeader(title = stringResource(R.string.tc17_metadata_section))
            EduCard {
                EduTextField(value = state.titleDraft, onValueChange = viewModel::updateTitleDraft, label = stringResource(R.string.tc17_title_label), modifier = Modifier.padding(bottom = Spacing.sm))
                EduTextField(value = state.deliverableDraft, onValueChange = viewModel::updateDeliverableDraft, label = stringResource(R.string.tc17_deliverable_label), singleLine = false, modifier = Modifier.padding(bottom = Spacing.sm))
                EduTextField(value = state.descriptionDraft, onValueChange = viewModel::updateDescriptionDraft, label = stringResource(R.string.tc17_description_label), singleLine = false, modifier = Modifier.padding(bottom = Spacing.sm))
                EduTextField(
                    value = state.teamSizeDraft, onValueChange = viewModel::updateTeamSizeDraft, label = stringResource(R.string.tc17_team_size_label),
                    keyboardType = KeyboardType.Number, modifier = Modifier.padding(bottom = Spacing.sm),
                )
                Text(stringResource(R.string.tc17_medium_label), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.xxs))
                SegmentedControl(
                    options = listOf(ProjectMedium.Digital, ProjectMedium.Physical),
                    selected = state.mediumDraft, onSelect = viewModel::updateMediumDraft,
                    labelOf = { projectMediumLabel(it) },
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
                PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveMetadata, isLoading = state.isSavingMetadata, enabled = state.hasUnsavedMetadata, modifier = Modifier.fillMaxWidth())
            }
        }

        // ── Milestones ────────────────────────────────────────────────────
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(top = Spacing.section)) {
                SectionHeader(title = stringResource(R.string.tc17_milestones_section), modifier = Modifier.weight(1f))
            }
            GhostButton(text = stringResource(R.string.tc17_add_milestone), onClick = viewModel::openAddMilestone, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(bottom = Spacing.sm))
        }
        if (project.milestones.isEmpty()) {
            item { Text(stringResource(R.string.tc17_no_milestones), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.sm)) }
        } else {
            items(orderedIds, key = { it }) { id ->
                val milestone = milestonesById[id] ?: return@items
                MilestoneCard(
                    milestone = milestone,
                    isDragging = id == draggingId,
                    dragOffsetPx = if (id == draggingId) dragDeltaPx else 0f,
                    onMeasuredHeight = { px -> rowHeightsPx[id] = px },
                    onEdit = { viewModel.openEditMilestone(milestone) },
                    onDelete = { viewModel.deleteMilestone(id) },
                    onAddTask = { viewModel.openAddTask(id) },
                    onEditTask = { task -> viewModel.openEditTask(id, task) },
                    onDeleteTask = { taskId -> viewModel.deleteTask(id, taskId) },
                    onMoveTask = { taskId, delta -> viewModel.moveTask(id, taskId, delta) },
                    dragHandleModifier = Modifier.dragHandlePointerInput(
                        id = id,
                        onDragStart = { draggingId = id; dragDeltaPx = 0f },
                        onDragDelta = { deltaY -> dragDeltaPx += deltaY },
                        onDragEnd = {
                            val fromIndex = orderedIds.indexOf(id)
                            val rowHeight = rowHeightsPx[id]?.takeIf { it > 0 } ?: 1
                            val steps = (dragDeltaPx / rowHeight).roundToInt()
                            val toIndex = (fromIndex + steps).coerceIn(0, orderedIds.lastIndex)
                            if (toIndex != fromIndex) {
                                orderedIds = orderedIds.toMutableList().also { it.add(toIndex, it.removeAt(fromIndex)) }
                                viewModel.reorderMilestones(orderedIds)
                            }
                            draggingId = null
                            dragDeltaPx = 0f
                        },
                        onDragCancel = { draggingId = null; dragDeltaPx = 0f },
                    ),
                )
            }
        }

        // ── Rubric ────────────────────────────────────────────────────────
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(top = Spacing.section)) {
                SectionHeader(title = stringResource(R.string.tc17_rubric_section), modifier = Modifier.weight(1f))
                Text(
                    text = stringResource(R.string.tc17_rubric_total, numeral(project.rubricWeightTotal)),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = if (project.rubric.isNotEmpty() && project.rubricWeightTotal == 100) colors.success else colors.danger,
                )
            }
            GhostButton(text = stringResource(R.string.tc17_add_criterion), onClick = viewModel::openAddCriterion, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(bottom = Spacing.sm))
        }
        if (project.rubric.isEmpty()) {
            item { Text(stringResource(R.string.tc17_no_rubric), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.sm)) }
        } else {
            items(project.rubric, key = { it.id }) { criterion ->
                CriterionRow(criterion, onEdit = { viewModel.openEditCriterion(criterion) }, onDelete = { viewModel.deleteCriterion(criterion.id) })
            }
        }

        // ── Materials & Safety — Physical projects only ──────────────────
        if (project.medium == ProjectMedium.Physical) {
            item {
                SectionHeader(title = stringResource(R.string.tc17_materials_section), modifier = Modifier.padding(top = Spacing.section))
                GhostButton(text = stringResource(R.string.tc17_add_material), onClick = viewModel::openAddMaterial, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(bottom = Spacing.sm))
            }
            items(project.materials, key = { it.id }) { material -> MaterialRow(material, onDelete = { viewModel.deleteMaterial(material.id) }) }
            item {
                SectionHeader(title = stringResource(R.string.tc17_safety_section))
                GhostButton(text = stringResource(R.string.tc17_add_safety_note), onClick = viewModel::openAddSafetyNote, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(bottom = Spacing.sm))
            }
            items(project.safetyNotes, key = { it.id }) { note -> SafetyNoteRow(note, onDelete = { viewModel.deleteSafetyNote(note.id) }) }
        }

        // ── Media ─────────────────────────────────────────────────────────
        item {
            SectionHeader(title = stringResource(R.string.tc17_media_section), modifier = Modifier.padding(top = Spacing.section))
            GhostButton(text = stringResource(R.string.tc17_add_media), onClick = viewModel::openAddMedia, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(bottom = Spacing.sm))
        }
        if (project.media.isEmpty()) {
            item { Text(stringResource(R.string.tc17_no_media), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.sm)) }
        } else {
            item {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs), verticalArrangement = Arrangement.spacedBy(Spacing.xxs), modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.sm)) {
                    project.media.forEach { item ->
                        StatusPill(
                            label = "${teacherProjectMediaKindLabel(item.kind)} · ${item.label}",
                            contentColor = colors.zaytoun, containerColor = colors.zaytounSoft,
                        )
                    }
                }
            }
        }

        // ── Publish ───────────────────────────────────────────────────────
        item {
            SectionHeader(title = stringResource(R.string.tc17_publish_section))
            if (project.status == TeacherProjectStatus.Published) {
                Text(stringResource(R.string.tc17_already_published), style = EduTheme.typography.body, color = colors.success, modifier = Modifier.padding(bottom = Spacing.xl))
            } else {
                val canPublish = viewModel.canPublish(project)
                if (!canPublish) {
                    Text(publishBlockedBody(project), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.sm))
                }
                if (state.publishError) {
                    Text(stringResource(R.string.tc17_publish_failed), style = EduTheme.typography.caption, color = colors.danger, modifier = Modifier.padding(bottom = Spacing.sm))
                }
                PrimaryButton(
                    text = stringResource(R.string.tc17_publish), onClick = viewModel::publish,
                    isLoading = state.isPublishing, enabled = canPublish,
                    modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xl),
                )
            }
        }
    }
}

@Composable
private fun publishBlockedBody(project: TeacherProject): String {
    val reasons = buildList {
        if (project.title.isBlank()) add(stringResource(R.string.tc17_gate_title))
        if (project.deliverable.isBlank()) add(stringResource(R.string.tc17_gate_deliverable))
        if (project.milestones.isEmpty()) add(stringResource(R.string.tc17_gate_milestones))
        if (project.milestones.any { it.title.isBlank() }) add(stringResource(R.string.tc17_gate_milestone_titles))
        if (project.rubric.isEmpty() || project.rubricWeightTotal != 100) add(stringResource(R.string.tc17_gate_rubric_total))
        if (project.medium == ProjectMedium.Physical && project.materials.isEmpty()) add(stringResource(R.string.tc17_gate_materials))
    }
    return reasons.joinToString(separator = "\n") { "• $it" }
}

@Composable
private fun LazyItemScope.MilestoneCard(
    milestone: TeacherProjectMilestone,
    isDragging: Boolean,
    dragOffsetPx: Float,
    onMeasuredHeight: (Int) -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onAddTask: () -> Unit,
    onEditTask: (TeacherProjectTask) -> Unit,
    onDeleteTask: (String) -> Unit,
    onMoveTask: (String, Int) -> Unit,
    dragHandleModifier: Modifier,
) {
    val colors = EduTheme.colors
    var showDeleteConfirm by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .animateItem()
            .zIndex(if (isDragging) 1f else 0f)
            .graphicsLayer { translationY = dragOffsetPx }
            .onGloballyPositioned { coords -> onMeasuredHeight(coords.size.height) }
            .padding(bottom = Spacing.sm),
    ) {
        EduCard {
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                Column(modifier = Modifier.weight(1f)) {
                    if (milestone.contextLabel != null) {
                        Text(milestone.contextLabel, style = EduTheme.typography.caption, color = colors.zaytoun)
                    }
                    Text(
                        text = milestone.title.ifBlank { stringResource(R.string.tc17_untitled_milestone) },
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                    if (milestone.description.isNotBlank()) {
                        Text(milestone.description, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.xxs))
                    }
                }
                DragHandleIcon(dragHandleModifier)
            }

            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.xs)) {
                GhostButton(text = stringResource(R.string.common_edit), onClick = onEdit)
                GhostButton(text = stringResource(R.string.common_delete), onClick = { showDeleteConfirm = true })
            }

            if (milestone.tasks.isNotEmpty()) {
                Column(modifier = Modifier.padding(top = Spacing.sm)) {
                    milestone.tasks.forEachIndexed { index, task ->
                        TaskRow(
                            task = task,
                            canMoveUp = index > 0, canMoveDown = index < milestone.tasks.lastIndex,
                            onEdit = { onEditTask(task) }, onDelete = { onDeleteTask(task.id) },
                            onMoveUp = { onMoveTask(task.id, -1) }, onMoveDown = { onMoveTask(task.id, 1) },
                        )
                    }
                }
            }
            GhostButton(text = stringResource(R.string.tc17_add_task), onClick = onAddTask, leadingIcon = Icons.Filled.Add, modifier = Modifier.padding(top = Spacing.xs))
        }
    }

    if (showDeleteConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.tc17_delete_milestone_title),
            body = stringResource(R.string.tc17_delete_milestone_body),
            confirmLabel = stringResource(R.string.common_delete),
            onConfirm = { showDeleteConfirm = false; onDelete() },
            onDismiss = { showDeleteConfirm = false },
            isDestructive = true,
        )
    }
}

@Composable
private fun TaskRow(task: TeacherProjectTask, canMoveUp: Boolean, canMoveDown: Boolean, onEdit: () -> Unit, onDelete: () -> Unit, onMoveUp: () -> Unit, onMoveDown: () -> Unit) {
    val colors = EduTheme.colors
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs), modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xxs)) {
        Column(modifier = Modifier.weight(1f)) {
            Text(task.title.ifBlank { stringResource(R.string.tc17_untitled_task) }, style = EduTheme.typography.caption, color = colors.textPrimary)
        }
        EduIconButton(icon = Icons.Filled.KeyboardArrowUp, contentDescription = stringResource(R.string.tc17_move_up), enabled = canMoveUp, onClick = onMoveUp)
        EduIconButton(icon = Icons.Filled.KeyboardArrowDown, contentDescription = stringResource(R.string.tc17_move_down), enabled = canMoveDown, onClick = onMoveDown)
        EduIconButton(icon = Icons.Filled.Edit, contentDescription = stringResource(R.string.common_edit), onClick = onEdit)
        EduIconButton(icon = Icons.Filled.Delete, contentDescription = stringResource(R.string.common_delete), onClick = onDelete, tint = colors.danger)
    }
}

@Composable
private fun CriterionRow(criterion: TeacherProjectRubricCriterion, onEdit: () -> Unit, onDelete: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(onClick = onEdit, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                Text(criterion.title.ifBlank { stringResource(R.string.tc17_untitled_criterion) }, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                if (criterion.description.isNotBlank()) {
                    Text(criterion.description, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.xxs))
                }
            }
            StatusPill(label = stringResource(R.string.progress_percent, criterion.weightPercent), contentColor = colors.zaytoun, containerColor = colors.zaytounSoft)
            EduIconButton(icon = Icons.Filled.Delete, contentDescription = stringResource(R.string.common_delete), onClick = onDelete, tint = colors.danger)
        }
    }
}

@Composable
private fun MaterialRow(material: TeacherProjectMaterial, onDelete: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Column(modifier = Modifier.weight(1f)) {
                Text(material.label, style = EduTheme.typography.body, color = colors.textPrimary)
                if (material.quantityLabel != null) {
                    Text(material.quantityLabel, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.xxs))
                }
            }
            EduIconButton(icon = Icons.Filled.Delete, contentDescription = stringResource(R.string.common_delete), onClick = onDelete, tint = colors.danger)
        }
    }
}

@Composable
private fun SafetyNoteRow(note: TeacherProjectSafetyNote, onDelete: () -> Unit) {
    val colors = EduTheme.colors
    val tint = if (note.severity == SafetySeverity.Important) colors.danger else colors.warning
    EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            StatusPill(label = teacherSafetySeverityLabel(note.severity), contentColor = tint, containerColor = tint.copy(alpha = 0.14f))
            Text(note.text, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.weight(1f))
            EduIconButton(icon = Icons.Filled.Delete, contentDescription = stringResource(R.string.common_delete), onClick = onDelete, tint = colors.danger)
        }
    }
}

@Composable
private fun MilestoneEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissMilestoneEditor,
        title = { Text(stringResource(if (state.editingMilestoneId != null) R.string.tc17_edit_milestone_title else R.string.tc17_add_milestone_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                EduTextField(value = state.milestoneTitleDraft, onValueChange = viewModel::updateMilestoneTitleDraft, label = stringResource(R.string.tc17_title_label))
                EduTextField(value = state.milestoneContextDraft, onValueChange = viewModel::updateMilestoneContextDraft, label = stringResource(R.string.tc17_context_label), modifier = Modifier.padding(top = Spacing.sm))
                EduTextField(value = state.milestoneDescriptionDraft, onValueChange = viewModel::updateMilestoneDescriptionDraft, label = stringResource(R.string.tc17_description_label), singleLine = false, modifier = Modifier.padding(top = Spacing.sm))
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveMilestone, enabled = state.milestoneTitleDraft.isNotBlank()) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissMilestoneEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun TaskEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissTaskEditor,
        title = { Text(stringResource(if (state.editingTaskId != null) R.string.tc17_edit_task_title else R.string.tc17_add_task_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                EduTextField(value = state.taskTitleDraft, onValueChange = viewModel::updateTaskTitleDraft, label = stringResource(R.string.tc17_title_label))
                EduTextField(value = state.taskDescriptionDraft, onValueChange = viewModel::updateTaskDescriptionDraft, label = stringResource(R.string.tc17_description_label), singleLine = false, modifier = Modifier.padding(top = Spacing.sm))
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveTask, enabled = state.taskTitleDraft.isNotBlank()) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissTaskEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun CriterionEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissCriterionEditor,
        title = { Text(stringResource(if (state.editingCriterionId != null) R.string.tc17_edit_criterion_title else R.string.tc17_add_criterion_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                EduTextField(value = state.criterionTitleDraft, onValueChange = viewModel::updateCriterionTitleDraft, label = stringResource(R.string.tc17_title_label))
                EduTextField(value = state.criterionDescriptionDraft, onValueChange = viewModel::updateCriterionDescriptionDraft, label = stringResource(R.string.tc17_description_label), singleLine = false, modifier = Modifier.padding(top = Spacing.sm))
                EduTextField(value = state.criterionWeightDraft, onValueChange = viewModel::updateCriterionWeightDraft, label = stringResource(R.string.tc17_weight_label), keyboardType = KeyboardType.Number, modifier = Modifier.padding(top = Spacing.sm))
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveCriterion, enabled = state.criterionTitleDraft.isNotBlank() && (state.criterionWeightDraft.toIntOrNull() ?: 0) > 0) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissCriterionEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun MaterialEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissMaterialEditor,
        title = { Text(stringResource(R.string.tc17_add_material_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                EduTextField(value = state.materialLabelDraft, onValueChange = viewModel::updateMaterialLabelDraft, label = stringResource(R.string.tc17_material_label))
                EduTextField(value = state.materialQuantityDraft, onValueChange = viewModel::updateMaterialQuantityDraft, label = stringResource(R.string.tc17_material_quantity_label), modifier = Modifier.padding(top = Spacing.sm))
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveMaterial, enabled = state.materialLabelDraft.isNotBlank()) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissMaterialEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun SafetyEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissSafetyEditor,
        title = { Text(stringResource(R.string.tc17_add_safety_note_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(bottom = Spacing.sm)) {
                    EduChip(label = teacherSafetySeverityLabel(SafetySeverity.Caution), selected = state.safetySeverityDraft == SafetySeverity.Caution, onClick = { viewModel.updateSafetySeverityDraft(SafetySeverity.Caution) })
                    EduChip(label = teacherSafetySeverityLabel(SafetySeverity.Important), selected = state.safetySeverityDraft == SafetySeverity.Important, onClick = { viewModel.updateSafetySeverityDraft(SafetySeverity.Important) })
                }
                EduTextField(value = state.safetyTextDraft, onValueChange = viewModel::updateSafetyTextDraft, label = stringResource(R.string.tc17_safety_text_label), singleLine = false)
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::saveSafetyNote, enabled = state.safetyTextDraft.isNotBlank()) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissSafetyEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun MediaEditorDialog(state: TeacherProjectEditorUiState, viewModel: TeacherProjectEditorViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissMediaEditor,
        title = { Text(stringResource(R.string.tc17_add_media_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(bottom = Spacing.sm)) {
                    TeacherProjectMediaKind.entries.forEach { kind ->
                        EduChip(label = teacherProjectMediaKindLabel(kind), selected = state.mediaKindDraft == kind, onClick = { viewModel.updateMediaKindDraft(kind) })
                    }
                }
                EduTextField(value = state.mediaLabelDraft, onValueChange = viewModel::updateMediaLabelDraft, label = stringResource(R.string.tc17_media_label))
                Text(stringResource(R.string.tc17_media_mock_notice), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.xs))
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.tc16_mock_add), onClick = viewModel::saveMedia, enabled = state.mediaLabelDraft.isNotBlank()) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissMediaEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

private fun Modifier.dragHandlePointerInput(
    id: String,
    onDragStart: () -> Unit,
    onDragDelta: (Float) -> Unit,
    onDragEnd: () -> Unit,
    onDragCancel: () -> Unit,
): Modifier = this.pointerInput(id) {
    detectDragGesturesAfterLongPress(
        onDragStart = { onDragStart() },
        onDragEnd = onDragEnd,
        onDragCancel = onDragCancel,
    ) { change, dragAmount ->
        change.consume()
        onDragDelta(dragAmount.y)
    }
}

@Composable
private fun DragHandleIcon(dragHandleModifier: Modifier) {
    val colors = EduTheme.colors
    Icon(
        imageVector = Icons.Filled.DragHandle,
        contentDescription = stringResource(R.string.tc04_reorder_handle),
        tint = colors.textMuted,
        modifier = Modifier
            .size(Sizing.touchTarget)
            .padding(Spacing.xs)
            .then(dragHandleModifier),
    )
}

@Composable
private fun TeacherProjectEditorSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
