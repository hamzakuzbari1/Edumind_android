package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.repository.QuizRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-07 · Quiz Results.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reads the result [QuizRunnerViewModel.submit] already computed and the repository already
 * cached — no separate scoring pass happens here, so results are identical whether you just
 * submitted or navigated back to this screen later.
 */
data class QuizResultsUiState(
    val result: UiState<QuizResult> = UiState.Loading,
    val isOnline: Boolean = true,
    val showOnlyWrong: Boolean = false,
    val isBuildingRemedial: Boolean = false,
    val remedialQuizId: String? = null,
)

class QuizResultsViewModel(
    private val quizId: String,
    private val quizRepository: QuizRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(QuizResultsUiState())
    val state: StateFlow<QuizResultsUiState> = _state.asStateFlow()

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
            when (val result = quizRepository.getResult(quizId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun toggleShowOnlyWrong() = _state.update { it.copy(showOnlyWrong = !it.showOnlyWrong) }

    /** "Practice these again" — builds the remedial quiz, then the screen navigates once [QuizResultsUiState.remedialQuizId] is set. */
    fun startRemedial() {
        if (_state.value.isBuildingRemedial) return
        _state.update { it.copy(isBuildingRemedial = true) }
        viewModelScope.launch {
            when (val result = quizRepository.buildRemedialQuiz(quizId)) {
                is AppResult.Success -> _state.update {
                    it.copy(isBuildingRemedial = false, remedialQuizId = result.data.id)
                }
                is AppResult.Failure -> _state.update { it.copy(isBuildingRemedial = false) }
            }
        }
    }
}
