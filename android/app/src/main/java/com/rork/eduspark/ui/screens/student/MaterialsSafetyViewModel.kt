package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectMaterial
import com.rork.eduspark.data.model.ProjectSafetyNote
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-12 · Materials & Safety Sheet.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Only ever reached for a [com.rork.eduspark.data.model.ProjectMedium.Physical] project — the
 * gate lives at the navigation entry point (PJ-02/PJ-03 never show the entry action for a
 * Digital project), not a runtime check here. Everything this screen renders — [ProjectMaterial]/
 * [ProjectSafetyNote]/the cost estimate — comes straight from [ProjectRepository.getProject]'s
 * static catalog fixture, and [checkedMaterialIds] reuses PJ-02's own
 * [ProjectRepository.getCheckedMaterials]/[ProjectRepository.setMaterialChecked] verbatim
 * (same "ticked before a project is even started, tracked independently of an ActiveProject"
 * state PJ-02 already established) — nothing here needs live connectivity, so this screen reads
 * correctly whether the shell reports online or offline.
 */
data class MaterialsSafetyScreenData(
    val projectTitle: String,
    val materials: List<ProjectMaterial>,
    val safetyNotes: List<ProjectSafetyNote>,
    val estimatedTotalCostLabel: String?,
    val checkedMaterialIds: Set<String>,
)

data class MaterialsSafetyUiState(
    val result: UiState<MaterialsSafetyScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class MaterialsSafetyViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(MaterialsSafetyUiState())
    val state: StateFlow<MaterialsSafetyUiState> = _state.asStateFlow()

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
            val projectResult = projectRepository.getProject(projectId)
            if (projectResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((projectResult as AppResult.Failure).error)) }
                return@launch
            }
            val checked = (projectRepository.getCheckedMaterials(projectId) as? AppResult.Success)?.data ?: emptySet()
            _state.update {
                it.copy(
                    result = UiState.Content(
                        MaterialsSafetyScreenData(
                            projectTitle = projectResult.data.title,
                            materials = projectResult.data.materials,
                            safetyNotes = projectResult.data.safetyNotes,
                            estimatedTotalCostLabel = projectResult.data.estimatedTotalCostLabel,
                            checkedMaterialIds = checked,
                        )
                    )
                )
            }
        }
    }

    fun toggleMaterial(materialId: String, checked: Boolean) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val updated = if (checked) data.checkedMaterialIds + materialId else data.checkedMaterialIds - materialId
        _state.update { it.copy(result = UiState.Content(data.copy(checkedMaterialIds = updated))) }
        viewModelScope.launch { projectRepository.setMaterialChecked(projectId, materialId, checked) }
    }
}
