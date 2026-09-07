package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Parent note thread — the existing [TeacherRepository.sendParentNote] list, as a screen.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No category/priority/status fields exist on [TeacherParentNote]; this ViewModel does not
 * invent them. Replies are additional teacher notes via the same send method. There is no
 * parent-reply model in the repository.
 */
data class TeacherParentNoteScreenData(
    val student: TeacherStudentSummary,
    val notes: List<TeacherParentNote>,
)

data class TeacherParentNoteUiState(
    val result: UiState<TeacherParentNoteScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val draft: String = "",
    val isSending: Boolean = false,
)

class TeacherParentNoteViewModel(
    private val studentId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherParentNoteUiState())
    val state: StateFlow<TeacherParentNoteUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun updateDraft(text: String) = _state.update { it.copy(draft = text) }

    private fun load() {
        if (_state.value.result !is UiState.Content) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            val studentResult = teacherRepository.getStudent(studentId)
            val notesResult = teacherRepository.getParentNotes(studentId)
            if (studentResult !is AppResult.Success || notesResult !is AppResult.Success) {
                val error = (studentResult as? AppResult.Failure)?.error
                    ?: (notesResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherParentNoteScreenData(
                            student = studentResult.data,
                            notes = notesResult.data,
                        )
                    )
                )
            }
        }
    }

    fun sendReply() {
        val message = _state.value.draft.trim()
        if (message.isBlank() || _state.value.isSending) return
        _state.update { it.copy(isSending = true) }
        viewModelScope.launch {
            when (val result = teacherRepository.sendParentNote(studentId, message)) {
                is AppResult.Success -> {
                    val current = _state.value.result
                    val notes = if (current is UiState.Content) current.data.notes + result.data else listOf(result.data)
                    if (current is UiState.Content) {
                        _state.update {
                            it.copy(
                                result = UiState.Content(current.data.copy(notes = notes)),
                                draft = "",
                                isSending = false,
                            )
                        }
                    } else {
                        _state.update { it.copy(isSending = false, draft = "") }
                        load()
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(isSending = false) }
            }
        }
    }
}
