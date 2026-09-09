package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentLessonProgressFilter
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentLessonProgressData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val selectedFilter: ParentLessonProgressFilter,
    val snapshot: ParentLessonProgressSnapshot?,
)

data class ParentLessonProgressUiState(
    val result: UiState<ParentLessonProgressData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentLessonProgressViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentLessonProgressUiState())
    val state: StateFlow<ParentLessonProgressUiState> = _state.asStateFlow()

    private var lessonsJob: Job? = null

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

        _state.update {
            it.copy(result = UiState.Content(data.copy(selectedStudentId = studentId, snapshot = null)))
        }
        loadLessons(studentId)
    }

    fun selectFilter(filter: ParentLessonProgressFilter) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedFilter == filter) return

        _state.update {
            it.copy(result = UiState.Content(data.copy(selectedFilter = filter)))
        }
    }

    private fun load() {
        lessonsJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = studentsResult.data.firstOrNull()?.id
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentLessonProgressData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    selectedFilter = ParentLessonProgressFilter.All,
                                    snapshot = null,
                                )
                            )
                        )
                    }
                    selectedStudentId?.let { loadLessons(it) }
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
        val keepSnapshot = selectedStudentId != null && selectedStudentId == current.selectedStudentId

        _state.update {
            it.copy(
                result = UiState.Content(
                    current.copy(
                        linkedStudents = students,
                        selectedStudentId = selectedStudentId,
                        snapshot = if (keepSnapshot) current.snapshot else null,
                    )
                )
            )
        }

        if (selectedStudentId != null && !keepSnapshot) {
            loadLessons(selectedStudentId)
        }
    }

    private fun loadLessons(studentId: String) {
        lessonsJob?.cancel()
        lessonsJob = viewModelScope.launch {
            when (val result = parentRepository.getLessonProgress(studentId)) {
                is AppResult.Success -> _state.update { current ->
                    val content = current.result as? UiState.Content ?: return@update current
                    if (content.data.selectedStudentId != studentId) {
                        current
                    } else {
                        current.copy(result = UiState.Content(content.data.copy(snapshot = result.data)))
                    }
                }

                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }
}
