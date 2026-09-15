package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.EmptyReason
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentDashboardUiState(
    val parent: SessionUser? = null,
    val students: List<ParentLinkedStudent> = emptyList(),
    val selectedStudentId: String? = null,
    val result: UiState<ParentDashboard> = UiState.Loading,
    val notes: List<ParentNote> = emptyList(),
    val notesUnreadCount: Int = 0,
    val replyDrafts: Map<String, String> = emptyMap(),
    val acknowledgingNoteId: String? = null,
    val replyingNoteId: String? = null,
    val isOnline: Boolean = true,
)

class ParentDashboardViewModel(
    private val authRepository: AuthRepository,
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentDashboardUiState())
    val state: StateFlow<ParentDashboardUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            authRepository.session.collect { user -> _state.update { it.copy(parent = user) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students -> _state.update { it.copy(students = students) } }
        }
        viewModelScope.launch {
            parentRepository.selectedStudentId.collect { id -> _state.update { it.copy(selectedStudentId = id) } }
        }
        load()
    }

    fun retry() = load()

    fun selectStudent(studentId: String) {
        viewModelScope.launch {
            when (parentRepository.selectStudent(studentId)) {
                is AppResult.Success -> loadChildOverview(studentId)
                is AppResult.Failure -> _state.update {
                    it.copy(
                        result = UiState.Empty(EmptyReason.NoContent),
                        notes = emptyList(),
                        notesUnreadCount = 0,
                        replyDrafts = emptyMap(),
                    )
                }
            }
        }
    }

    fun updateReplyDraft(noteId: String, text: String) {
        _state.update { current ->
            current.copy(replyDrafts = current.replyDrafts + (noteId to text))
        }
    }

    fun acknowledgeNote(noteId: String) {
        if (_state.value.acknowledgingNoteId != null) return
        _state.update { it.copy(acknowledgingNoteId = noteId) }
        viewModelScope.launch {
            when (val result = parentRepository.acknowledgeParentNote(noteId)) {
                is AppResult.Success -> replaceNote(result.data)
                is AppResult.Failure -> Unit
            }
            _state.update { it.copy(acknowledgingNoteId = null) }
        }
    }

    fun markNoteRead(noteId: String) {
        viewModelScope.launch {
            when (val result = parentRepository.markParentNoteRead(noteId)) {
                is AppResult.Success -> replaceNote(result.data)
                is AppResult.Failure -> Unit
            }
        }
    }

    fun replyToNote(noteId: String) {
        val draft = _state.value.replyDrafts[noteId].orEmpty().trim()
        if (draft.isEmpty() || _state.value.replyingNoteId != null) return
        _state.update { it.copy(replyingNoteId = noteId) }
        viewModelScope.launch {
            when (val result = parentRepository.replyToParentNote(noteId, draft)) {
                is AppResult.Success -> {
                    replaceNote(result.data)
                    _state.update { current ->
                        current.copy(replyDrafts = current.replyDrafts - noteId)
                    }
                }
                is AppResult.Failure -> Unit
            }
            _state.update { it.copy(replyingNoteId = null) }
        }
    }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedId = _state.value.selectedStudentId
                        ?.takeIf { selected -> studentsResult.data.any { it.id == selected } }
                        ?: studentsResult.data.firstOrNull()?.id
                    if (selectedId == null) {
                        _state.update {
                            it.copy(
                                result = UiState.Empty(EmptyReason.NoContent),
                                notes = emptyList(),
                                notesUnreadCount = 0,
                            )
                        }
                    } else {
                        loadChildOverview(selectedId)
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(studentsResult.error)) }
            }
        }
    }

    private suspend fun loadChildOverview(studentId: String) {
        _state.update {
            it.copy(
                result = UiState.Loading,
                replyDrafts = emptyMap(),
                acknowledgingNoteId = null,
                replyingNoteId = null,
            )
        }
        when (val overview = parentRepository.getChildOverview(studentId)) {
            is AppResult.Success -> _state.update { it.copy(result = UiState.Content(overview.data)) }
            is AppResult.Failure -> {
                _state.update {
                    it.copy(
                        result = UiState.Failure(overview.error),
                        notes = emptyList(),
                        notesUnreadCount = 0,
                    )
                }
                return
            }
        }
        when (val notes = parentRepository.getParentNotes(studentId)) {
            is AppResult.Success -> _state.update {
                it.copy(
                    notes = notes.data.notes,
                    notesUnreadCount = notes.data.unreadCount,
                )
            }
            is AppResult.Failure -> _state.update {
                it.copy(notes = emptyList(), notesUnreadCount = 0)
            }
        }
    }

    private fun replaceNote(updated: ParentNote) {
        _state.update { current ->
            val notes = current.notes.map { if (it.id == updated.id) updated else it }
            current.copy(
                notes = notes,
                notesUnreadCount = notes.count { !it.isRead },
            )
        }
    }
}
