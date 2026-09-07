package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ExplanationLength
import com.rork.eduspark.data.model.LearningGoal
import com.rork.eduspark.data.model.LearningInterest
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Learning Preferences — extends ST-22 · Student Profile.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A persistent, always-editable profile preference, not a one-time onboarding answer — see
 * [LearningPreferences]'s own doc comment for why this deliberately does not reuse
 * [com.rork.eduspark.ui.screens.onboarding.OnboardingViewModel]'s SO-04 study-habits wizard.
 * Draft edits live only in this screen's own [UiState.Content] until [save] confirms them
 * through [ProfileRepository.updateLearningPreferences] — same "edit locally, commit on
 * explicit save" shape as [StudentProfileViewModel.saveProfile].
 */
data class LearningPreferencesUiState(
    val result: UiState<LearningPreferences> = UiState.Loading,
    val isOnline: Boolean = true,
    val isSaving: Boolean = false,
    /** Set true once [save] confirms — the screen pops back on it, then this never matters again. */
    val saved: Boolean = false,
)

class LearningPreferencesViewModel(
    private val profileRepository: ProfileRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(LearningPreferencesUiState())
    val state: StateFlow<LearningPreferencesUiState> = _state.asStateFlow()

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
            when (val result = profileRepository.getLearningPreferences()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun selectGoal(goal: LearningGoal) = updateDraft { it.copy(goal = goal) }

    fun selectExplanationLength(length: ExplanationLength) = updateDraft { it.copy(explanationLength = length) }

    fun toggleInterest(interest: LearningInterest) = updateDraft {
        it.copy(interests = if (interest in it.interests) it.interests - interest else it.interests + interest)
    }

    private fun updateDraft(transform: (LearningPreferences) -> LearningPreferences) {
        val current = (_state.value.result as? UiState.Content)?.data ?: return
        _state.update { it.copy(result = UiState.Content(transform(current))) }
    }

    fun save() {
        val draft = (_state.value.result as? UiState.Content)?.data ?: return
        if (_state.value.isSaving) return
        _state.update { it.copy(isSaving = true) }
        viewModelScope.launch {
            when (profileRepository.updateLearningPreferences(draft)) {
                is AppResult.Success -> _state.update { it.copy(isSaving = false, saved = true) }
                is AppResult.Failure -> _state.update { it.copy(isSaving = false) }
            }
        }
    }
}
