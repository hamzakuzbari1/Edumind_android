package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ParentRepository
import com.rork.eduspark.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentAccountSummary(
    val displayName: String,
    val email: String,
    val avatarInitial: String,
)

data class ParentMeData(
    val account: ParentAccountSummary,
    val linkedStudents: List<ParentLinkedStudent>,
    val twoFactorEnabled: Boolean,
    val sessions: List<ActiveSession>,
)

data class ParentMeUiState(
    val result: UiState<ParentMeData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ParentMeViewModel(
    private val authRepository: AuthRepository,
    private val parentRepository: ParentRepository,
    private val securityRepository: SecurityRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentMeUiState())
    val state: StateFlow<ParentMeUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(linkedStudents = students)))
                }
            }
        }
        viewModelScope.launch {
            securityRepository.securitySettings.collect { settings ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(twoFactorEnabled = settings.twoFactorEnabled)))
                }
            }
        }
        viewModelScope.launch {
            securityRepository.activeSessions.collect { sessions ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(sessions = sessions)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val session = authRepository.session.first()
            val studentsResult = parentRepository.getLinkedStudents()
            val settingsResult = securityRepository.getSecuritySettings()
            val sessionsResult = securityRepository.getActiveSessions()

            if (session == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.SessionExpired)) }
                return@launch
            }

            if (studentsResult is AppResult.Success && settingsResult is AppResult.Success && sessionsResult is AppResult.Success) {
                _state.update {
                    it.copy(
                        result = UiState.Content(
                            ParentMeData(
                                account = ParentAccountSummary(
                                    displayName = session.displayName,
                                    email = session.email,
                                    avatarInitial = session.displayName.take(1).ifBlank { "P" },
                                ),
                                linkedStudents = studentsResult.data,
                                twoFactorEnabled = settingsResult.data.twoFactorEnabled,
                                sessions = sessionsResult.data,
                            )
                        )
                    )
                }
            } else {
                val error = (studentsResult as? AppResult.Failure)?.error
                    ?: (settingsResult as? AppResult.Failure)?.error
                    ?: (sessionsResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }
}

