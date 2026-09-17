package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentProgressData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val performance: ParentPerformanceSnapshot?,
)

data class ParentProgressUiState(
    val result: UiState<ParentProgressData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentProgressViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentProgressUiState())
    val state: StateFlow<ParentProgressUiState> = _state.asStateFlow()

    private var performanceJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                applyStudents(students)
            }
        }
        load()
    }

    fun retry() = load()

    fun selectStudent(studentId: String) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedStudentId == studentId || data.linkedStudents.none { it.id == studentId }) return

        viewModelScope.launch { parentRepository.selectStudent(studentId) }

        _state.update {
            it.copy(result = UiState.Content(data.copy(selectedStudentId = studentId, performance = null)))
        }
        loadPerformance(studentId)
    }

    private fun load() {
        performanceJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = parentRepository.initialSelectedStudentId(studentsResult.data)
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentProgressData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    performance = null,
                                )
                            )
                        )
                    }
                    selectedStudentId?.let(::loadPerformance)
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
        val keepPerformance = selectedStudentId != null && selectedStudentId == current.selectedStudentId

        _state.update {
            it.copy(
                result = UiState.Content(
                    current.copy(
                        linkedStudents = students,
                        selectedStudentId = selectedStudentId,
                        performance = if (keepPerformance) current.performance else null,
                    )
                )
            )
        }

        if (selectedStudentId != null && !keepPerformance) {
            loadPerformance(selectedStudentId)
        }
    }

    private fun loadPerformance(studentId: String) {
        performanceJob?.cancel()
        performanceJob = viewModelScope.launch {
            when (val result = parentRepository.getPerformanceSnapshot(studentId)) {
                is AppResult.Success -> _state.update { current ->
                    val content = current.result as? UiState.Content ?: return@update current
                    if (content.data.selectedStudentId != studentId) {
                        current
                    } else {
                        current.copy(result = UiState.Content(content.data.copy(performance = result.data)))
                    }
                }

                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }
}
