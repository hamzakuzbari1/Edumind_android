package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentLessonDetailsData(
    val linkedStudent: ParentLinkedStudent?,
    val details: ParentLessonDetails?,
)

data class ParentLessonDetailsUiState(
    val result: UiState<ParentLessonDetailsData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentLessonDetailsViewModel(
    private val lessonId: String,
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentLessonDetailsUiState())
    val state: StateFlow<ParentLessonDetailsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                val content = state.value.result as? UiState.Content ?: return@collect
                val currentStudent = content.data.linkedStudent
                if (students.isEmpty()) {
                    _state.update {
                        it.copy(result = UiState.Content(ParentLessonDetailsData(null, null)))
                    }
                } else if (currentStudent != null && students.none { it.id == currentStudent.id }) {
                    load()
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    if (studentsResult.data.isEmpty()) {
                        _state.update {
                            it.copy(result = UiState.Content(ParentLessonDetailsData(null, null)))
                        }
                        return@launch
                    }

                    when (val detailsResult = parentRepository.getLessonDetails(lessonId)) {
                        is AppResult.Success -> {
                            val student = studentsResult.data.firstOrNull {
                                detailsResult.data.lesson.id.startsWith("${it.id}-")
                            } ?: studentsResult.data.first()
                            _state.update {
                                it.copy(
                                    result = UiState.Content(
                                        ParentLessonDetailsData(
                                            linkedStudent = student,
                                            details = detailsResult.data,
                                        )
                                    )
                                )
                            }
                        }

                        is AppResult.Failure -> _state.update {
                            it.copy(result = UiState.Failure(detailsResult.error))
                        }
                    }
                }

                is AppResult.Failure -> _state.update {
                    it.copy(result = UiState.Failure(studentsResult.error))
                }
            }
        }
    }
}
