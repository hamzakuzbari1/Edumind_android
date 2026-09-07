package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherVoiceProfile
import com.rork.eduspark.data.model.VoiceSampleSourceType
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-09 · Voice Profile.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherRepository] is the only place [TeacherVoiceProfile] lives — every mutator here is a
 * thin suspend call straight through to it, same "ViewModel never keeps a shadow copy" shape
 * every other Teacher screen this phase uses. [togglePreview] is the one purely local,
 * un-persisted piece of state: playback position has no meaning once this screen closes, the
 * same reasoning ST-03's [com.rork.eduspark.ui.screens.student.LessonPlayerViewModel] already
 * applies to its own transient player state.
 */
data class TeacherVoiceProfileUiState(
    val result: UiState<TeacherVoiceProfile> = UiState.Loading,
    val isOnline: Boolean = true,
    val isGenerating: Boolean = false,
    val isPreviewPlaying: Boolean = false,
)

class TeacherVoiceProfileViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherVoiceProfileUiState())
    val state: StateFlow<TeacherVoiceProfileUiState> = _state.asStateFlow()

    private var teacherId: String? = null
    private var previewJob: Job? = null

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
            val id = authRepository.session.first()?.id
            if (id == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            teacherId = id
            applyResult(teacherRepository.getVoiceProfile(id))
        }
    }

    fun setConsent(granted: Boolean) = mutate { teacherRepository.setVoiceConsent(it, granted) }

    fun addRecordedSample() = mutate { teacherRepository.addVoiceSample(it, VoiceSampleSourceType.Recorded) }

    fun addUploadedSample() = mutate { teacherRepository.addVoiceSample(it, VoiceSampleSourceType.Uploaded) }

    fun removeSample(sampleId: String) = mutate { teacherRepository.removeVoiceSample(it, sampleId) }

    fun setNarrationEnabled(enabled: Boolean) = mutate { teacherRepository.setClonedNarrationEnabled(it, enabled) }

    /** Generate and Regenerate are the same call — see [TeacherRepository.generateVoiceProfile]'s own doc comment for the deterministic fail-once-then-succeed rule. */
    fun generateProfile() {
        val id = teacherId ?: return
        if (_state.value.isGenerating) return
        _state.update { it.copy(isGenerating = true) }
        viewModelScope.launch {
            applyResult(teacherRepository.generateVoiceProfile(id), keepGenerating = false)
        }
    }

    fun togglePreview() {
        if (_state.value.isPreviewPlaying) {
            previewJob?.cancel()
            _state.update { it.copy(isPreviewPlaying = false) }
            return
        }
        _state.update { it.copy(isPreviewPlaying = true) }
        previewJob = viewModelScope.launch {
            delay(PREVIEW_DURATION_MS)
            _state.update { it.copy(isPreviewPlaying = false) }
        }
    }

    private fun mutate(call: suspend (String) -> AppResult<TeacherVoiceProfile>) {
        val id = teacherId ?: return
        viewModelScope.launch { applyResult(call(id)) }
    }

    private fun applyResult(result: AppResult<TeacherVoiceProfile>, keepGenerating: Boolean = true) {
        when (result) {
            is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data), isGenerating = if (keepGenerating) it.isGenerating else false) }
            is AppResult.Failure -> _state.update { it.copy(isGenerating = if (keepGenerating) it.isGenerating else false) }
        }
    }

    override fun onCleared() {
        previewJob?.cancel()
        super.onCleared()
    }

    private companion object {
        const val PREVIEW_DURATION_MS = 4000L
    }
}
