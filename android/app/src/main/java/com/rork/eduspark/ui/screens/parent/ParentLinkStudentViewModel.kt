package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentLinkStudentData(
    val linkedStudents: List<ParentLinkedStudent>,
)

data class ParentLinkStudentUiState(
    val result: UiState<ParentLinkStudentData> = UiState.Loading,
    val isOnline: Boolean = true,
    val code: String = "",
    val isSubmitting: Boolean = false,
    val invalidCode: Boolean = false,
    val linkedStudentName: String? = null,
)

class ParentLinkStudentViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentLinkStudentUiState())
    val state: StateFlow<ParentLinkStudentUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(linkedStudents = students)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    fun updateCode(value: String) {
        _state.update {
            it.copy(
                code = value.uppercase(),
                invalidCode = false,
                linkedStudentName = null,
            )
        }
    }

    fun submit() {
        val code = state.value.code.trim()
        if (state.value.isSubmitting) return
        if (code.isBlank()) {
            _state.update { it.copy(invalidCode = true, linkedStudentName = null) }
            return
        }

        _state.update { it.copy(isSubmitting = true, invalidCode = false, linkedStudentName = null) }
        viewModelScope.launch {
            when (val result = parentRepository.linkStudent(code)) {
                is AppResult.Success -> _state.update {
                    it.copy(
                        isSubmitting = false,
                        invalidCode = false,
                        linkedStudentName = result.data.displayName,
                    )
                }

                is AppResult.Failure -> _state.update {
                    it.copy(
                        isSubmitting = false,
                        invalidCode = true,
                        linkedStudentName = null,
                    )
                }
            }
        }
    }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val students = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> _state.update {
                    it.copy(result = UiState.Content(ParentLinkStudentData(students.data)))
                }

                is AppResult.Failure -> _state.update {
                    it.copy(result = UiState.Failure(students.error))
                }
            }
        }
    }
}

