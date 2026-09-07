package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectReflection
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-09 · Reflection Log.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * NO real microphone, NO RECORD_AUDIO permission, NO Whisper/STT — [stopRecording] simulates
 * processing with a short fixed delay, then hands back one of a small deterministic transcript
 * set; every third stop deliberately fails, same "reachable by hand, not on the very first
 * try" convention [TutorVoiceScreen] already uses for its own mock transcription failure.
 * [transcript] is freely editable once ready, and [saveReflection] persists through
 * [ProjectRepository.saveReflection] — repository/session state, not view-only, so PJ-10 can
 * read it back later. [recordedDurationSeconds] is raw seconds, not a formatted label — the
 * numeral()-aware "MM:SS" text is composed at the screen layer (numeral() requires a
 * composable context this ViewModel doesn't have) and handed back into [saveReflection].
 */
data class ReflectionLogScreenData(
    val projectTitle: String,
    val milestoneTitle: String,
    val sessionLabel: String?,
    val existingDurationLabel: String?,
)

enum class RecordingState { Idle, Recording, Processing, Ready, Failed }

data class ReflectionLogUiState(
    val result: UiState<ReflectionLogScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val recordingState: RecordingState = RecordingState.Idle,
    val transcript: String = "",
    val elapsedSeconds: Int = 0,
    val recordedDurationSeconds: Int? = null,
    val isSaving: Boolean = false,
)

class ReflectionLogViewModel(
    private val projectId: String,
    private val milestoneId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ReflectionLogUiState())
    val state: StateFlow<ReflectionLogUiState> = _state.asStateFlow()

    private var recordingJob: Job? = null
    private var attemptCount = 0

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val projectResult = projectRepository.getProject(projectId)
            val active = (projectRepository.getActiveProjects() as? AppResult.Success)?.data
                ?.firstOrNull { it.projectId == projectId }
            val milestone = active?.milestones?.firstOrNull { it.id == milestoneId }

            if (projectResult !is AppResult.Success || milestone == null) {
                val error = (projectResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            val existing = (projectRepository.getReflection(projectId, milestoneId) as? AppResult.Success)?.data
            _state.update {
                it.copy(
                    result = UiState.Content(
                        ReflectionLogScreenData(
                            projectTitle = projectResult.data.title,
                            milestoneTitle = milestone.title,
                            sessionLabel = existing?.sessionLabel,
                            existingDurationLabel = existing?.durationLabel,
                        )
                    ),
                    transcript = existing?.transcript.orEmpty(),
                    recordingState = RecordingState.Idle,
                    recordedDurationSeconds = null,
                    elapsedSeconds = 0,
                )
            }
        }
    }

    fun startRecording() {
        if (_state.value.recordingState == RecordingState.Recording) return
        recordingJob?.cancel()
        _state.update { it.copy(recordingState = RecordingState.Recording, elapsedSeconds = 0, transcript = "") }
        recordingJob = viewModelScope.launch {
            while (isActive) {
                delay(1_000)
                _state.update { it.copy(elapsedSeconds = it.elapsedSeconds + 1) }
            }
        }
    }

    fun stopRecording() {
        if (_state.value.recordingState != RecordingState.Recording) return
        recordingJob?.cancel()
        val elapsed = _state.value.elapsedSeconds
        _state.update { it.copy(recordingState = RecordingState.Processing) }
        viewModelScope.launch {
            delay(PROCESSING_DELAY_MS)
            attemptCount += 1
            if (attemptCount % 3 == 0) {
                _state.update { it.copy(recordingState = RecordingState.Failed) }
            } else {
                val transcript = MOCK_TRANSCRIPTS[(attemptCount - 1) % MOCK_TRANSCRIPTS.size]
                _state.update {
                    it.copy(recordingState = RecordingState.Ready, transcript = transcript, recordedDurationSeconds = elapsed)
                }
            }
        }
    }

    fun updateTranscript(text: String) {
        _state.update { it.copy(transcript = text) }
    }

    fun saveReflection(freshDurationLabel: String?) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val transcript = _state.value.transcript.trim()
        if (transcript.isBlank() || _state.value.isSaving) return

        val durationLabel = freshDurationLabel ?: data.existingDurationLabel
        val sessionLabel = data.sessionLabel ?: DEFAULT_SESSION_LABEL
        _state.update { it.copy(isSaving = true) }
        viewModelScope.launch {
            val reflection = ProjectReflection(
                projectId = projectId,
                milestoneId = milestoneId,
                milestoneTitle = data.milestoneTitle,
                projectTitle = data.projectTitle,
                sessionLabel = sessionLabel,
                transcript = transcript,
                durationLabel = durationLabel,
            )
            projectRepository.saveReflection(reflection)
            _state.update {
                it.copy(
                    isSaving = false,
                    recordingState = RecordingState.Idle,
                    recordedDurationSeconds = null,
                    result = UiState.Content(data.copy(sessionLabel = sessionLabel, existingDurationLabel = durationLabel)),
                )
            }
        }
    }

    private companion object {
        const val PROCESSING_DELAY_MS = 900L
        const val DEFAULT_SESSION_LABEL = "جلسة الانعكاس"
        val MOCK_TRANSCRIPTS = listOf(
            "شعرت أن هذه المرحلة كانت واضحة، خصوصاً بعد ما جربت الخطوات بنفسي بدل ما أكتفي بالقراءة.",
            "واجهت صعوبة بسيطة في البداية، لكن بعد إعادة المحاولة فهمت السبب وصلّحت الخطأ.",
            "أهم شيء تعلمته في هذه المرحلة هو أهمية تسجيل الملاحظات أولاً بأول بدل الاعتماد على الذاكرة.",
        )
    }
}
