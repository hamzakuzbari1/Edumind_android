package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.repository.RoutineRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-13 · Routine Week View.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Same shape as [PlannerViewModel] on purpose — collects [RoutineRepository.routineProfile]
 * continuously rather than fetching once, so Complete/Miss/Undo and a rebuilt routine from
 * ST-12 both show up immediately. [AppError.NotFound] from the initial load means "no
 * routine confirmed yet" — the screen routes that case to ST-12 rather than treating it as a
 * failure.
 */
data class RoutineUiState(
    val result: UiState<RoutineProfile> = UiState.Loading,
    val isOnline: Boolean = true,
    val isFirstTime: Boolean = false,
    val isRenewing: Boolean = false,
    val isDeleting: Boolean = false,
)

class RoutineViewModel(
    private val routineRepository: RoutineRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(RoutineUiState())
    val state: StateFlow<RoutineUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            routineRepository.routineProfile.collect { profile ->
                if (profile != null) _state.update { it.copy(result = UiState.Content(profile), isFirstTime = false) }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val result = routineRepository.loadRoutine()) {
                is AppResult.Success -> Unit // reflected by the flow collector above.
                is AppResult.Failure -> _state.update {
                    // NotFound means "never built one" — an honest empty state routing to
                    // ST-12, not a retryable failure. Any other error stays a real failure.
                    if (result.error == AppError.NotFound) {
                        it.copy(result = UiState.Empty(), isFirstTime = true)
                    } else {
                        it.copy(result = UiState.Failure(result.error), isFirstTime = false)
                    }
                }
            }
        }
    }

    fun completeSlot(slotId: String) = updateStatus(slotId, RoutineSlotStatus.Completed)

    fun missSlot(slotId: String) = updateStatus(slotId, RoutineSlotStatus.Missed)

    fun undoSlot(slotId: String) = updateStatus(slotId, RoutineSlotStatus.Upcoming)

    private fun updateStatus(slotId: String, status: RoutineSlotStatus) {
        viewModelScope.launch { routineRepository.updateSlotStatus(slotId, status) }
    }

    fun acknowledgeRenewal() {
        viewModelScope.launch { routineRepository.acknowledgeRenewal() }
    }

    fun renewWeek() {
        if (_state.value.isRenewing) return
        _state.update { it.copy(isRenewing = true) }
        viewModelScope.launch {
            routineRepository.renewRoutineWeek()
            _state.update { it.copy(isRenewing = false) }
        }
    }

    fun deleteRoutine() {
        if (_state.value.isDeleting) return
        _state.update { it.copy(isDeleting = true) }
        viewModelScope.launch {
            when (routineRepository.deleteRoutine()) {
                is AppResult.Success -> _state.update { it.copy(isDeleting = false, result = UiState.Empty(), isFirstTime = true) }
                is AppResult.Failure -> _state.update { it.copy(isDeleting = false) }
            }
        }
    }
}
