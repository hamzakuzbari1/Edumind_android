package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ExamEntry
import com.rork.eduspark.data.model.OcrConfidence
import com.rork.eduspark.data.repository.ExamRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-14 · Exam Schedule Capture.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [CaptureStage] is deliberately a flat enum, not a route — capture, processing, review and
 * confirm are all one screen, matching "the mock flow should still represent the real user
 * journey accurately" without needing four destinations for a slice that has no real image
 * pipeline behind it yet.
 */
enum class CaptureStage { NoImage, Processing, Reviewing, Confirmed }

data class ExamCaptureUiState(
    val stage: CaptureStage = CaptureStage.NoImage,
    val entries: List<ExamEntry> = emptyList(),
    val error: AppError? = null,
    val isOnline: Boolean = true,
    val isConfirming: Boolean = false,
)

class ExamCaptureViewModel(
    private val examRepository: ExamRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ExamCaptureUiState())
    val state: StateFlow<ExamCaptureUiState> = _state.asStateFlow()

    private var entryCounter = 0

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
    }

    /** "Capture/import" and "OCR" are one mock call — see [ExamRepository.captureSchedule]'s own doc comment. */
    fun capture() {
        _state.update { it.copy(stage = CaptureStage.Processing, error = null) }
        viewModelScope.launch {
            when (val result = examRepository.captureSchedule()) {
                is AppResult.Success -> _state.update {
                    it.copy(stage = CaptureStage.Reviewing, entries = result.data.entries)
                }
                is AppResult.Failure -> _state.update {
                    it.copy(stage = CaptureStage.NoImage, error = result.error)
                }
            }
        }
    }

    fun updateEntry(updated: ExamEntry) {
        _state.update { s -> s.copy(entries = s.entries.map { if (it.id == updated.id) updated else it }) }
    }

    fun removeEntry(id: String) {
        _state.update { s -> s.copy(entries = s.entries.filterNot { it.id == id }) }
    }

    /** Manually added rows are fully trusted — there is no OCR uncertainty to represent. */
    fun addManualEntry() {
        entryCounter += 1
        val entry = ExamEntry(
            id = "manual-$entryCounter",
            subjectId = null,
            subjectTitle = "",
            date = null,
            time = null,
            confidence = OcrConfidence.High,
        )
        _state.update { it.copy(entries = it.entries + entry) }
    }

    fun confirm() {
        if (_state.value.isConfirming) return
        _state.update { it.copy(isConfirming = true, error = null) }
        viewModelScope.launch {
            when (val result = examRepository.confirmSchedule(_state.value.entries)) {
                is AppResult.Success -> _state.update { it.copy(isConfirming = false, stage = CaptureStage.Confirmed) }
                is AppResult.Failure -> _state.update { it.copy(isConfirming = false, error = result.error) }
            }
        }
    }
}
