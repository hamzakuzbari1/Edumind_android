package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentDashboardSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentHomeData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val dashboard: ParentDashboardSnapshot?,
)

data class ParentHomeUiState(
    val result: UiState<ParentHomeData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentHomeViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentHomeUiState())
    val state: StateFlow<ParentHomeUiState> = _state.asStateFlow()

    private var dashboardJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                applyStudents(students)
            }
        }
        viewModelScope.launch {
            parentRepository.unreadAlertCount.collect {
                refreshCurrentDashboard()
            }
        }
        load()
    }

    fun retry() = load()

    fun selectStudent(studentId: String) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedStudentId == studentId || data.linkedStudents.none { it.id == studentId }) return

        _state.update {
            it.copy(result = UiState.Content(data.copy(selectedStudentId = studentId, dashboard = null)))
        }
        loadDashboard(studentId)
    }

    private fun load() {
        dashboardJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = studentsResult.data.firstOrNull()?.id
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentHomeData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    dashboard = null,
                                )
                            )
                        )
                    }
                    selectedStudentId?.let(::loadDashboard)
                }

                is AppResult.Failure -> _state.update {
                    it.copy(result = UiState.Failure(studentsResult.error))
                }
            }
        }
    }

    private fun applyStudents(students: List<ParentLinkedStudent>) {
        val content = state.value.result as? UiState.Content ?: return
        val current = content.data
        val selectedStudentId = current.selectedStudentId
            ?.takeIf { selectedId -> students.any { it.id == selectedId } }
            ?: students.firstOrNull()?.id
        val keepDashboard = selectedStudentId != null && selectedStudentId == current.selectedStudentId

        _state.update {
            it.copy(
                result = UiState.Content(
                    current.copy(
                        linkedStudents = students,
                        selectedStudentId = selectedStudentId,
                        dashboard = if (keepDashboard) current.dashboard else null,
                    )
                )
            )
        }

        if (selectedStudentId != null && !keepDashboard) {
            loadDashboard(selectedStudentId)
        }
    }

    private fun loadDashboard(studentId: String) {
        dashboardJob?.cancel()
        dashboardJob = viewModelScope.launch {
            when (val result = parentRepository.getDashboardSnapshot(studentId)) {
                is AppResult.Success -> _state.update { current ->
                    val content = current.result as? UiState.Content ?: return@update current
                    if (content.data.selectedStudentId != studentId) {
                        current
                    } else {
                        current.copy(result = UiState.Content(content.data.copy(dashboard = result.data)))
                    }
                }

                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun refreshCurrentDashboard() {
        val selectedStudentId = (state.value.result as? UiState.Content)?.data?.selectedStudentId ?: return
        loadDashboard(selectedStudentId)
    }
}
