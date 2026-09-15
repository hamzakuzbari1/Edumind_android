package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentSubjectTeacher
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import com.rork.eduspark.data.repository.ParentRepository
import com.rork.eduspark.ui.screens.messaging.messagingParticipantIdOrNull
import com.rork.eduspark.ui.screens.messaging.messagingRoleOrNull
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentSubjectsTeachersData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val query: String,
    val snapshot: ParentSubjectsTeachersSnapshot?,
)

data class ParentSubjectsTeachersUiState(
    val result: UiState<ParentSubjectsTeachersData> = UiState.Loading,
    val isOnline: Boolean = true,
)

sealed interface ParentSubjectsTeachersEvent {
    data class OpenThread(val threadId: String) : ParentSubjectsTeachersEvent
}

class ParentSubjectsTeachersViewModel(
    private val authRepository: AuthRepository,
    private val parentRepository: ParentRepository,
    private val messagingRepository: MessagingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentSubjectsTeachersUiState())
    val state: StateFlow<ParentSubjectsTeachersUiState> = _state.asStateFlow()

    private val _events = Channel<ParentSubjectsTeachersEvent>(Channel.BUFFERED)
    val events: Flow<ParentSubjectsTeachersEvent> = _events.receiveAsFlow()

    private var subjectsJob: Job? = null

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
        loadSubjectsTeachers(studentId)
    }

    fun updateQuery(query: String) {
        val content = state.value.result as? UiState.Content ?: return
        _state.update {
            it.copy(result = UiState.Content(content.data.copy(query = query)))
        }
    }

    fun openTeacherMessage(item: ParentSubjectTeacher) {
        val content = state.value.result as? UiState.Content ?: return
        val selectedStudentId = content.data.selectedStudentId ?: return
        val isAllowedTeacher = content.data.snapshot?.items.orEmpty().any { subjectTeacher ->
            subjectTeacher.id == item.id &&
                subjectTeacher.teacher.id == item.teacher.id &&
                subjectTeacher.id.startsWith("$selectedStudentId-")
        }
        if (!isAllowedTeacher) return

        viewModelScope.launch {
            val session = authRepository.session.first()
            val viewerId = session?.messagingParticipantIdOrNull() ?: return@launch
            if (session.messagingRoleOrNull() != MessageParticipantRole.Parent) return@launch
            when (val result = messagingRepository.openOrCreateThread(
                viewerId = viewerId,
                viewerRole = MessageParticipantRole.Parent,
                contactId = item.teacher.id,
            )) {
                is AppResult.Success -> _events.send(ParentSubjectsTeachersEvent.OpenThread(result.data.id))
                is AppResult.Failure -> Unit
            }
        }
    }

    private fun load() {
        subjectsJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = studentsResult.data.firstOrNull()?.id
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentSubjectsTeachersData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    query = "",
                                    snapshot = null,
                                )
                            )
                        )
                    }
                    selectedStudentId?.let { loadSubjectsTeachers(it) }
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
            loadSubjectsTeachers(selectedStudentId)
        }
    }

    private fun loadSubjectsTeachers(studentId: String) {
        subjectsJob?.cancel()
        subjectsJob = viewModelScope.launch {
            when (val result = parentRepository.getSubjectsTeachers(studentId)) {
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
