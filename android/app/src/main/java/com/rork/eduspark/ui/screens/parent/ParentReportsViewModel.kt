package com.rork.eduspark.ui.screens.parent

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.local.ParentReportExportStore
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentReportDateRange
import com.rork.eduspark.data.model.ParentReportExportFormat
import com.rork.eduspark.data.model.ParentReportPeriod
import com.rork.eduspark.data.model.ParentReportsSnapshot
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentReportsData(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val selectedPeriod: ParentReportPeriod,
    val customDateRange: ParentReportDateRange?,
    val snapshot: ParentReportsSnapshot?,
    val selectedExportFormat: ParentReportExportFormat = ParentReportExportFormat.Pdf,
    val exportState: ParentReportExportState = ParentReportExportState.Idle,
    val exportFilename: String? = null,
    val exportError: AppError? = null,
)

data class ParentReportsUiState(
    val result: UiState<ParentReportsData> = UiState.Loading,
    val isOnline: Boolean = true,
)

enum class ParentReportExportState {
    Idle,
    Exporting,
    Ready,
}

sealed interface ParentReportsEvent {
    data class OpenExport(val uri: Uri, val mimeType: String) : ParentReportsEvent
}

class ParentReportsViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
    private val exportStore: ParentReportExportStore,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentReportsUiState())
    val state: StateFlow<ParentReportsUiState> = _state.asStateFlow()

    private val _events = Channel<ParentReportsEvent>(Channel.BUFFERED)
    val events: Flow<ParentReportsEvent> = _events.receiveAsFlow()

    private var reportsJob: Job? = null
    private var exportJob: Job? = null
    private var exportUri: Uri? = null
    private var exportMimeType: String = ParentReportExportFormat.Pdf.mimeType

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
        clearExport()

        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedStudentId = studentId,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                        exportFilename = null,
                        exportError = null,
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
        clearExport()

        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedPeriod = period,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                        exportFilename = null,
                        exportError = null,
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
        clearExport()

        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedPeriod = ParentReportPeriod.Custom,
                        customDateRange = normalizedRange,
                        snapshot = null,
                        exportState = ParentReportExportState.Idle,
                        exportFilename = null,
                        exportError = null,
                    ),
                ),
            )
        }
        data.selectedStudentId?.let { loadReports(it, ParentReportPeriod.Custom, normalizedRange) }
    }

    fun selectExportFormat(format: ParentReportExportFormat) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedExportFormat == format) return
        if (data.exportState == ParentReportExportState.Ready) {
            clearExport()
        }
        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        selectedExportFormat = format,
                        exportState = ParentReportExportState.Idle,
                        exportFilename = null,
                        exportError = null,
                    ),
                ),
            )
        }
    }

    fun exportReport() {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.exportState == ParentReportExportState.Ready) {
            val uri = exportUri ?: return
            viewModelScope.launch { _events.send(ParentReportsEvent.OpenExport(uri, exportMimeType)) }
            return
        }
        val studentId = data.selectedStudentId ?: return
        if (data.snapshot == null || data.exportState == ParentReportExportState.Exporting) return

        exportJob?.cancel()
        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        exportState = ParentReportExportState.Exporting,
                        exportError = null,
                    ),
                ),
            )
        }
        exportJob = viewModelScope.launch {
            when (
                val result = parentRepository.exportHistoricalReport(
                    studentId = studentId,
                    period = data.selectedPeriod,
                    customDateRange = data.customDateRange,
                    format = data.selectedExportFormat.apiValue,
                )
            ) {
                is AppResult.Success -> {
                    val uri = runCatching { exportStore.save(result.data) }.getOrElse {
                        updateExportFailure(AppError.Unknown)
                        return@launch
                    }
                    exportUri = uri
                    exportMimeType = result.data.mimeType.ifBlank { data.selectedExportFormat.mimeType }
                    _state.update { current ->
                        val latest = current.result as? UiState.Content ?: return@update current
                        if (latest.data.selectedStudentId != studentId) {
                            current
                        } else {
                            current.copy(
                                result = UiState.Content(
                                    latest.data.copy(
                                        exportState = ParentReportExportState.Ready,
                                        exportFilename = result.data.filename,
                                        exportError = null,
                                    ),
                                ),
                            )
                        }
                    }
                    _events.send(ParentReportsEvent.OpenExport(uri, exportMimeType))
                }

                is AppResult.Failure -> updateExportFailure(result.error)
            }
        }
    }

    private fun load() {
        reportsJob?.cancel()
        exportJob?.cancel()
        clearExport()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val studentsResult = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selectedStudentId = parentRepository.initialSelectedStudentId(studentsResult.data)
                    val selectedPeriod = ParentReportPeriod.ThisWeek
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                ParentReportsData(
                                    linkedStudents = studentsResult.data,
                                    selectedStudentId = selectedStudentId,
                                    selectedPeriod = selectedPeriod,
                                    customDateRange = null,
                                    snapshot = null,
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
                        exportFilename = if (keepSnapshot) current.exportFilename else null,
                        exportError = if (keepSnapshot) current.exportError else null,
                    ),
                ),
            )
        }

        if (selectedStudentId != null && !keepSnapshot) {
            clearExport()
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

    private fun updateExportFailure(error: AppError) {
        _state.update { current ->
            val content = current.result as? UiState.Content ?: return@update current
            current.copy(
                result = UiState.Content(
                    content.data.copy(
                        exportState = ParentReportExportState.Idle,
                        exportError = error,
                    ),
                ),
            )
        }
    }

    private fun clearExport() {
        exportJob?.cancel()
        exportUri = null
        exportMimeType = ParentReportExportFormat.Pdf.mimeType
    }
}
