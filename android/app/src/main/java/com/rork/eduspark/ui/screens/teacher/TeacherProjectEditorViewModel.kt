package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.SafetySeverity
import com.rork.eduspark.data.model.TeacherProject
import com.rork.eduspark.data.model.TeacherProjectMaterial
import com.rork.eduspark.data.model.TeacherProjectMediaItem
import com.rork.eduspark.data.model.TeacherProjectMediaKind
import com.rork.eduspark.data.model.TeacherProjectMilestone
import com.rork.eduspark.data.model.TeacherProjectRubricCriterion
import com.rork.eduspark.data.model.TeacherProjectSafetyNote
import com.rork.eduspark.data.model.TeacherProjectTask
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-17 · Project Authoring — the project editor.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Metadata is a local draft with an explicit Save ([hasUnsavedMetadata], the same dirty-state
 * shape TC-10/TC-16 already use). Every other section — milestones/tasks, rubric, materials/
 * safety, media — is a set of discrete list actions that persist immediately through their own
 * full-list-replace [TeacherRepository] call, the exact "whole list, order reassigned from
 * position" convention [TeacherQuizEditorViewModel] already established for quiz questions.
 * Publish re-validates server-side — see [TeacherRepository.publishTeacherProject]'s own doc
 * comment — this ViewModel's own [canPublish] only mirrors that gate so the button can disable
 * itself honestly, never the other way around.
 */
data class TeacherProjectEditorUiState(
    val result: UiState<TeacherProject> = UiState.Loading,
    val isOnline: Boolean = true,

    val titleDraft: String = "",
    val descriptionDraft: String = "",
    val deliverableDraft: String = "",
    val teamSizeDraft: String = "1",
    val mediumDraft: ProjectMedium = ProjectMedium.Digital,
    val hasUnsavedMetadata: Boolean = false,
    val isSavingMetadata: Boolean = false,

    val showMilestoneEditor: Boolean = false,
    val editingMilestoneId: String? = null,
    val milestoneTitleDraft: String = "",
    val milestoneDescriptionDraft: String = "",
    val milestoneContextDraft: String = "",

    val showTaskEditor: Boolean = false,
    val taskEditorMilestoneId: String? = null,
    val editingTaskId: String? = null,
    val taskTitleDraft: String = "",
    val taskDescriptionDraft: String = "",

    val showCriterionEditor: Boolean = false,
    val editingCriterionId: String? = null,
    val criterionTitleDraft: String = "",
    val criterionDescriptionDraft: String = "",
    val criterionWeightDraft: String = "",

    val showMaterialEditor: Boolean = false,
    val materialLabelDraft: String = "",
    val materialQuantityDraft: String = "",

    val showSafetyEditor: Boolean = false,
    val safetyTextDraft: String = "",
    val safetySeverityDraft: SafetySeverity = SafetySeverity.Caution,

    val showMediaEditor: Boolean = false,
    val mediaKindDraft: TeacherProjectMediaKind = TeacherProjectMediaKind.Image,
    val mediaLabelDraft: String = "",

    val isPublishing: Boolean = false,
    val publishError: Boolean = false,
)

class TeacherProjectEditorViewModel(
    private val projectId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherProjectEditorUiState())
    val state: StateFlow<TeacherProjectEditorUiState> = _state.asStateFlow()

    private var draftsSeeded = false

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val result = teacherRepository.getTeacherProject(projectId)) {
                is AppResult.Success -> {
                    val project = result.data
                    _state.update { current ->
                        val withDrafts = if (!draftsSeeded) {
                            draftsSeeded = true
                            current.copy(
                                titleDraft = project.title, descriptionDraft = project.description,
                                deliverableDraft = project.deliverable, teamSizeDraft = project.teamSize.toString(),
                                mediumDraft = project.medium,
                            )
                        } else current
                        withDrafts.copy(result = UiState.Content(project))
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun currentProject(): TeacherProject? = (_state.value.result as? UiState.Content)?.data

    // ── Metadata ─────────────────────────────────────────────────────────────────────────────

    fun updateTitleDraft(value: String) = _state.update { it.copy(titleDraft = value, hasUnsavedMetadata = true) }
    fun updateDescriptionDraft(value: String) = _state.update { it.copy(descriptionDraft = value, hasUnsavedMetadata = true) }
    fun updateDeliverableDraft(value: String) = _state.update { it.copy(deliverableDraft = value, hasUnsavedMetadata = true) }
    fun updateTeamSizeDraft(value: String) = _state.update { it.copy(teamSizeDraft = value, hasUnsavedMetadata = true) }
    fun updateMediumDraft(medium: ProjectMedium) = _state.update { it.copy(mediumDraft = medium, hasUnsavedMetadata = true) }

    fun saveMetadata() {
        val draft = _state.value
        _state.update { it.copy(isSavingMetadata = true) }
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectMetadata(
                projectId, draft.titleDraft, draft.descriptionDraft, draft.deliverableDraft,
                draft.teamSizeDraft.toIntOrNull()?.coerceAtLeast(1) ?: 1, draft.mediumDraft,
            )
            _state.update { it.copy(hasUnsavedMetadata = false, isSavingMetadata = false) }
            load()
        }
    }

    // ── Milestones ───────────────────────────────────────────────────────────────────────────

    fun openAddMilestone() = _state.update { it.copy(showMilestoneEditor = true, editingMilestoneId = null, milestoneTitleDraft = "", milestoneDescriptionDraft = "", milestoneContextDraft = "") }

    fun openEditMilestone(milestone: TeacherProjectMilestone) = _state.update {
        it.copy(
            showMilestoneEditor = true, editingMilestoneId = milestone.id,
            milestoneTitleDraft = milestone.title, milestoneDescriptionDraft = milestone.description, milestoneContextDraft = milestone.contextLabel.orEmpty(),
        )
    }

    fun updateMilestoneTitleDraft(value: String) = _state.update { it.copy(milestoneTitleDraft = value) }
    fun updateMilestoneDescriptionDraft(value: String) = _state.update { it.copy(milestoneDescriptionDraft = value) }
    fun updateMilestoneContextDraft(value: String) = _state.update { it.copy(milestoneContextDraft = value) }
    fun dismissMilestoneEditor() = _state.update { it.copy(showMilestoneEditor = false, editingMilestoneId = null) }

    fun saveMilestone() {
        val draft = _state.value
        if (draft.milestoneTitleDraft.isBlank()) return
        val project = currentProject() ?: return
        val milestones = project.milestones.toMutableList()
        if (draft.editingMilestoneId != null) {
            val index = milestones.indexOfFirst { it.id == draft.editingMilestoneId }
            if (index != -1) {
                milestones[index] = milestones[index].copy(
                    title = draft.milestoneTitleDraft, description = draft.milestoneDescriptionDraft,
                    contextLabel = draft.milestoneContextDraft.ifBlank { null },
                )
            }
        } else {
            milestones += TeacherProjectMilestone(
                id = "ms-${System.currentTimeMillis()}", order = milestones.size + 1,
                title = draft.milestoneTitleDraft, description = draft.milestoneDescriptionDraft,
                contextLabel = draft.milestoneContextDraft.ifBlank { null },
            )
        }
        persistMilestones(reindex(milestones))
        _state.update { it.copy(showMilestoneEditor = false, editingMilestoneId = null) }
    }

    fun deleteMilestone(milestoneId: String) {
        val project = currentProject() ?: return
        persistMilestones(reindex(project.milestones.filterNot { it.id == milestoneId }))
    }

    fun reorderMilestones(orderedIds: List<String>) {
        val project = currentProject() ?: return
        val byId = project.milestones.associateBy { it.id }
        persistMilestones(orderedIds.mapIndexedNotNull { index, id -> byId[id]?.copy(order = index + 1) })
    }

    // ── Tasks (nested within a milestone) ───────────────────────────────────────────────────

    fun openAddTask(milestoneId: String) = _state.update {
        it.copy(showTaskEditor = true, taskEditorMilestoneId = milestoneId, editingTaskId = null, taskTitleDraft = "", taskDescriptionDraft = "")
    }

    fun openEditTask(milestoneId: String, task: TeacherProjectTask) = _state.update {
        it.copy(showTaskEditor = true, taskEditorMilestoneId = milestoneId, editingTaskId = task.id, taskTitleDraft = task.title, taskDescriptionDraft = task.description)
    }

    fun updateTaskTitleDraft(value: String) = _state.update { it.copy(taskTitleDraft = value) }
    fun updateTaskDescriptionDraft(value: String) = _state.update { it.copy(taskDescriptionDraft = value) }
    fun dismissTaskEditor() = _state.update { it.copy(showTaskEditor = false, taskEditorMilestoneId = null, editingTaskId = null) }

    fun saveTask() {
        val draft = _state.value
        val milestoneId = draft.taskEditorMilestoneId ?: return
        if (draft.taskTitleDraft.isBlank()) return
        val project = currentProject() ?: return
        val milestones = project.milestones.map { milestone ->
            if (milestone.id != milestoneId) return@map milestone
            val tasks = milestone.tasks.toMutableList()
            if (draft.editingTaskId != null) {
                val index = tasks.indexOfFirst { it.id == draft.editingTaskId }
                if (index != -1) tasks[index] = tasks[index].copy(title = draft.taskTitleDraft, description = draft.taskDescriptionDraft)
            } else {
                tasks += TeacherProjectTask(id = "task-${System.currentTimeMillis()}", order = tasks.size + 1, title = draft.taskTitleDraft, description = draft.taskDescriptionDraft)
            }
            milestone.copy(tasks = tasks.mapIndexed { i, t -> t.copy(order = i + 1) })
        }
        persistMilestones(milestones)
        _state.update { it.copy(showTaskEditor = false, taskEditorMilestoneId = null, editingTaskId = null) }
    }

    fun deleteTask(milestoneId: String, taskId: String) {
        val project = currentProject() ?: return
        val milestones = project.milestones.map { milestone ->
            if (milestone.id != milestoneId) milestone
            else milestone.copy(tasks = milestone.tasks.filterNot { it.id == taskId }.mapIndexed { i, t -> t.copy(order = i + 1) })
        }
        persistMilestones(milestones)
    }

    fun moveTask(milestoneId: String, taskId: String, delta: Int) {
        val project = currentProject() ?: return
        val milestones = project.milestones.map { milestone ->
            if (milestone.id != milestoneId) return@map milestone
            val tasks = milestone.tasks.toMutableList()
            val fromIndex = tasks.indexOfFirst { it.id == taskId }
            val toIndex = (fromIndex + delta).coerceIn(0, tasks.lastIndex)
            if (fromIndex == -1 || fromIndex == toIndex) return@map milestone
            tasks.add(toIndex, tasks.removeAt(fromIndex))
            milestone.copy(tasks = tasks.mapIndexed { i, t -> t.copy(order = i + 1) })
        }
        persistMilestones(milestones)
    }

    private fun reindex(milestones: List<TeacherProjectMilestone>) = milestones.mapIndexed { i, m -> m.copy(order = i + 1) }

    private fun persistMilestones(milestones: List<TeacherProjectMilestone>) {
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectMilestones(projectId, milestones)
            load()
        }
    }

    // ── Rubric ───────────────────────────────────────────────────────────────────────────────

    fun openAddCriterion() = _state.update { it.copy(showCriterionEditor = true, editingCriterionId = null, criterionTitleDraft = "", criterionDescriptionDraft = "", criterionWeightDraft = "") }

    fun openEditCriterion(criterion: TeacherProjectRubricCriterion) = _state.update {
        it.copy(
            showCriterionEditor = true, editingCriterionId = criterion.id,
            criterionTitleDraft = criterion.title, criterionDescriptionDraft = criterion.description, criterionWeightDraft = criterion.weightPercent.toString(),
        )
    }

    fun updateCriterionTitleDraft(value: String) = _state.update { it.copy(criterionTitleDraft = value) }
    fun updateCriterionDescriptionDraft(value: String) = _state.update { it.copy(criterionDescriptionDraft = value) }
    fun updateCriterionWeightDraft(value: String) = _state.update { it.copy(criterionWeightDraft = value) }
    fun dismissCriterionEditor() = _state.update { it.copy(showCriterionEditor = false, editingCriterionId = null) }

    fun saveCriterion() {
        val draft = _state.value
        val weight = draft.criterionWeightDraft.toIntOrNull() ?: return
        if (draft.criterionTitleDraft.isBlank() || weight <= 0) return
        val project = currentProject() ?: return
        val rubric = project.rubric.toMutableList()
        if (draft.editingCriterionId != null) {
            val index = rubric.indexOfFirst { it.id == draft.editingCriterionId }
            if (index != -1) rubric[index] = rubric[index].copy(title = draft.criterionTitleDraft, description = draft.criterionDescriptionDraft, weightPercent = weight)
        } else {
            rubric += TeacherProjectRubricCriterion(id = "rc-${System.currentTimeMillis()}", title = draft.criterionTitleDraft, description = draft.criterionDescriptionDraft, weightPercent = weight)
        }
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectRubric(projectId, rubric)
            load()
        }
        _state.update { it.copy(showCriterionEditor = false, editingCriterionId = null) }
    }

    fun deleteCriterion(criterionId: String) {
        val project = currentProject() ?: return
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectRubric(projectId, project.rubric.filterNot { it.id == criterionId })
            load()
        }
    }

    // ── Materials & Safety ──────────────────────────────────────────────────────────────────

    fun openAddMaterial() = _state.update { it.copy(showMaterialEditor = true, materialLabelDraft = "", materialQuantityDraft = "") }
    fun updateMaterialLabelDraft(value: String) = _state.update { it.copy(materialLabelDraft = value) }
    fun updateMaterialQuantityDraft(value: String) = _state.update { it.copy(materialQuantityDraft = value) }
    fun dismissMaterialEditor() = _state.update { it.copy(showMaterialEditor = false) }

    fun saveMaterial() {
        val draft = _state.value
        if (draft.materialLabelDraft.isBlank()) return
        val project = currentProject() ?: return
        val material = TeacherProjectMaterial(id = "mat-${System.currentTimeMillis()}", label = draft.materialLabelDraft, quantityLabel = draft.materialQuantityDraft.ifBlank { null })
        persistMaterials(project.materials + material, project.safetyNotes)
        _state.update { it.copy(showMaterialEditor = false, materialLabelDraft = "", materialQuantityDraft = "") }
    }

    fun deleteMaterial(materialId: String) {
        val project = currentProject() ?: return
        persistMaterials(project.materials.filterNot { it.id == materialId }, project.safetyNotes)
    }

    fun openAddSafetyNote() = _state.update { it.copy(showSafetyEditor = true, safetyTextDraft = "", safetySeverityDraft = SafetySeverity.Caution) }
    fun updateSafetyTextDraft(value: String) = _state.update { it.copy(safetyTextDraft = value) }
    fun updateSafetySeverityDraft(severity: SafetySeverity) = _state.update { it.copy(safetySeverityDraft = severity) }
    fun dismissSafetyEditor() = _state.update { it.copy(showSafetyEditor = false) }

    fun saveSafetyNote() {
        val draft = _state.value
        if (draft.safetyTextDraft.isBlank()) return
        val project = currentProject() ?: return
        val note = TeacherProjectSafetyNote(id = "safety-${System.currentTimeMillis()}", text = draft.safetyTextDraft, severity = draft.safetySeverityDraft)
        persistMaterials(project.materials, project.safetyNotes + note)
        _state.update { it.copy(showSafetyEditor = false, safetyTextDraft = "") }
    }

    fun deleteSafetyNote(safetyId: String) {
        val project = currentProject() ?: return
        persistMaterials(project.materials, project.safetyNotes.filterNot { it.id == safetyId })
    }

    private fun persistMaterials(materials: List<TeacherProjectMaterial>, safetyNotes: List<TeacherProjectSafetyNote>) {
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectMaterials(projectId, materials, safetyNotes)
            load()
        }
    }

    // ── Media (MOCK) ─────────────────────────────────────────────────────────────────────────

    fun openAddMedia() = _state.update { it.copy(showMediaEditor = true, mediaKindDraft = TeacherProjectMediaKind.Image, mediaLabelDraft = "") }
    fun updateMediaKindDraft(kind: TeacherProjectMediaKind) = _state.update { it.copy(mediaKindDraft = kind) }
    fun updateMediaLabelDraft(value: String) = _state.update { it.copy(mediaLabelDraft = value) }
    fun dismissMediaEditor() = _state.update { it.copy(showMediaEditor = false) }

    fun saveMedia() {
        val draft = _state.value
        if (draft.mediaLabelDraft.isBlank()) return
        val project = currentProject() ?: return
        val item = TeacherProjectMediaItem(id = "media-${System.currentTimeMillis()}", kind = draft.mediaKindDraft, label = draft.mediaLabelDraft)
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectMedia(projectId, project.media + item)
            load()
        }
        _state.update { it.copy(showMediaEditor = false, mediaLabelDraft = "") }
    }

    fun deleteMedia(mediaId: String) {
        val project = currentProject() ?: return
        viewModelScope.launch {
            teacherRepository.saveTeacherProjectMedia(projectId, project.media.filterNot { it.id == mediaId })
            load()
        }
    }

    // ── Publish ──────────────────────────────────────────────────────────────────────────────

    /** Mirrors [TeacherRepository]'s own server-side gate for an honest disabled state — never the source of truth; see this file's own doc comment. */
    fun canPublish(project: TeacherProject): Boolean =
        project.title.isNotBlank() &&
            project.deliverable.isNotBlank() &&
            project.teamSize >= 1 &&
            project.milestones.isNotEmpty() &&
            project.milestones.all { it.title.isNotBlank() } &&
            project.milestones.all { m -> m.tasks.all { it.title.isNotBlank() } } &&
            project.rubric.isNotEmpty() &&
            project.rubric.all { it.title.isNotBlank() && it.weightPercent > 0 } &&
            project.rubricWeightTotal == 100 &&
            (project.medium != ProjectMedium.Physical || project.materials.isNotEmpty())

    fun publish() {
        _state.update { it.copy(isPublishing = true, publishError = false) }
        viewModelScope.launch {
            when (teacherRepository.publishTeacherProject(projectId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isPublishing = false) }
                    load()
                }
                is AppResult.Failure -> _state.update { it.copy(isPublishing = false, publishError = true) }
            }
        }
    }
}
