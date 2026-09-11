package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentReportsData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val selectedPeriod: ParentReportPeriod,
    val customDateRange: ParentReportDateRange?,
    val snapshot: ParentReportsSnapshot?,
    val exportState: ParentReportExportState,
)

data class ParentReportsUiState(
    val result: UiState<ParentReportsData> = UiState.Loading,
    val isOnline: Boolean = true,
)

enum class ParentReportExportState {
    Idle,
    Ready,
}

class ParentReportsViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentReportsUiState())
    val state: StateFlow<ParentReportsUiState> = _state.asStateFlow()

    private var reportsJob: Job? = null

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
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedStudentId = studentId,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                    ),
                ),
            )
        }
        loadReports(studentId, data.selectedPeriod, data.customDateRange)
    }

    fun selectPeriod(period: ParentReportPeriod) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedPeriod == period) return

        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedPeriod = period,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                    ),
                ),
            )
        }
        data.selectedStudentId?.let { loadReports(it, period, data.customDateRange) }
    }

    fun selectCustomPeriod() = selectPeriod(ParentReportPeriod.Custom)

    fun confirmCustomDateRange(dateRange: ParentReportDateRange) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        val normalizedRange = if (dateRange.startDateMillis <= dateRange.endDateMillis) {
            dateRange
        } else {
            ParentReportDateRange(
                startDateMillis = dateRange.endDateMillis,
                endDateMillis = dateRange.startDateMillis,
            )
        }

        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedPeriod = ParentReportPeriod.Custom,
                        customDateRange = normalizedRange,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                    ),
                ),
            )
        }
        data.selectedStudentId?.let { loadReports(it, ParentReportPeriod.Custom, normalizedRange) }
    }

    fun exportReport() {
        _state.update { current ->
            val content = current.result as? UiState.Content ?: return@update current
            current.copy(
                result = UiState.Content(
                    content.data.copy(exportState = ParentReportExportState.Ready),
                ),
            )
        }
    }

    private fun load() {
        reportsJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = studentsResult.data.firstOrNull()?.id
                    val selectedPeriod = ParentReportPeriod.Last7Days
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentReportsData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    selectedPeriod = selectedPeriod,
                                    customDateRange = null,
                                    snapshot = null,
                                    exportState = ParentReportExportState.Idle,
                                ),
                            ),
                        )
                    }
                    selectedStudentId?.let { loadReports(it, selectedPeriod, customDateRange = null) }
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
                        exportState = if (keepSnapshot) current.exportState else ParentReportExportState.Idle,
                    ),
                ),
            )
        }

        if (selectedStudentId != null && !keepSnapshot) {
            loadReports(selectedStudentId, current.selectedPeriod, current.customDateRange)
        }
    }

    private fun loadReports(
        studentId: String,
        period: ParentReportPeriod,
        customDateRange: ParentReportDateRange?,
    ) {
        reportsJob?.cancel()
        reportsJob = viewModelScope.launch {
            when (val result = parentRepository.getReportsSnapshot(studentId, period, customDateRange)) {
                is AppResult.Success -> _state.update { current ->
                    val content = current.result as? UiState.Content ?: return@update current
                    if (content.data.selectedStudentId != studentId || content.data.selectedPeriod != period) {
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
