package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Teacher Account hub — reads the same [TeacherIdentityInfo] / [TeacherSubjectsGrades]
 * record Teacher Setup and Edit Profile already save. No second profile model.
 */
data class TeacherAccountScreenData(
    val identity: TeacherIdentityInfo,
    val subjectsGrades: TeacherSubjectsGrades,
)

data class TeacherAccountUiState(
    val result: UiState<TeacherAccountScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class TeacherAccountViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherAccountUiState())
    val state: StateFlow<TeacherAccountUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        if (_state.value.result !is UiState.Content) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            val teacherId = authRepository.session.first()?.id
            if (teacherId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            when (val setupResult = teacherRepository.getSetupState(teacherId)) {
                is AppResult.Success -> _state.update {
                    it.copy(
                        result = UiState.Content(
                            TeacherAccountScreenData(
                                identity = setupResult.data.identity,
                                subjectsGrades = setupResult.data.subjectsGrades,
                            )
                        )
                    )
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(setupResult.error)) }
            }
        }
    }
}
