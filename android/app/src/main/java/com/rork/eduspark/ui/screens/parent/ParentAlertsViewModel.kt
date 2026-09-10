package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentAlertPreference
import com.rork.eduspark.data.model.ParentAlertPreferenceCategory
import com.rork.eduspark.data.model.ParentAlertsSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentAlertsData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val snapshot: ParentAlertsSnapshot?,
)

data class ParentAlertsUiState(
    val result: UiState<ParentAlertsData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentAlertsViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentAlertsUiState())
    val state: StateFlow<ParentAlertsUiState> = _state.asStateFlow()

    private var alertsJob: Job? = null

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
        loadAlerts(studentId)
    }

    fun markAlertRead(alertId: String) {
        _state.update { current ->
            val content = current.result as? UiState.Content ?: return@update current
            val snapshot = content.data.snapshot ?: return@update current
            current.copy(
                result = UiState.Content(
                    content.data.copy(
                        snapshot = snapshot.copy(
                            alerts = snapshot.alerts.map { alert ->
                                if (alert.id == alertId) alert.copy(isUnread = false) else alert
                            },
                        ),
                    ),
                ),
            )
        }
    }

    fun markAllRead() {
        _state.update { current ->
            val content = current.result as? UiState.Content ?: return@update current
            val snapshot = content.data.snapshot ?: return@update current
            current.copy(
                result = UiState.Content(
                    content.data.copy(
                        snapshot = snapshot.copy(
                            alerts = snapshot.alerts.map { it.copy(isUnread = false) },
                        ),
                    ),
                ),
            )
        }
    }

    fun setPreferenceEnabled(category: ParentAlertPreferenceCategory, enabled: Boolean) {
        _state.update { current ->
            val content = current.result as? UiState.Content ?: return@update current
            val snapshot = content.data.snapshot ?: return@update current
            current.copy(
                result = UiState.Content(
                    content.data.copy(
                        snapshot = snapshot.copy(
                            preferences = snapshot.preferences.map { preference ->
                                if (preference.category == category) {
                                    preference.copy(enabled = enabled)
                                } else {
                                    preference
                                }
                            },
                        ),
                    ),
                ),
            )
        }
    }

    private fun load() {
        alertsJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = studentsResult.data.firstOrNull()?.id
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentAlertsData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    snapshot = null,
                                ),
                            ),
                        )
                    }
                    selectedStudentId?.let(::loadAlerts)
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
                    ),
                ),
            )
        }

        if (selectedStudentId != null && !keepSnapshot) {
            loadAlerts(selectedStudentId)
        }
    }

    private fun loadAlerts(studentId: String) {
        alertsJob?.cancel()
        alertsJob = viewModelScope.launch {
            when (val result = parentRepository.getAlertsSnapshot(studentId)) {
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
