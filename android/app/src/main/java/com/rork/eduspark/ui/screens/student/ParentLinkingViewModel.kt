package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentLinkingData(
    val profile: StudentProfile,
    val linkedParents: List<LinkedParent>,
)

data class ParentLinkingUiState(
    val result: UiState<ParentLinkingData> = UiState.Loading,
    val isOnline: Boolean = true,
    val pendingRevokeParentId: String? = null,
)

class ParentLinkingViewModel(
    private val profileRepository: ProfileRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentLinkingUiState())
    val state: StateFlow<ParentLinkingUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            profileRepository.profile.collect { profile ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(profile = profile)))
                }
            }
        }
        viewModelScope.launch {
            profileRepository.linkedParents.collect { parents ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(linkedParents = parents)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val profile = profileRepository.getProfile()
            val parents = profileRepository.getLinkedParents()
            if (profile is AppResult.Success && parents is AppResult.Success) {
                _state.update { it.copy(result = UiState.Content(ParentLinkingData(profile.data, parents.data))) }
            } else {
                val error = (profile as? AppResult.Failure)?.error
                    ?: (parents as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun requestRevokeParent(parentId: String) = _state.update { it.copy(pendingRevokeParentId = parentId) }

    fun cancelRevokeParent() = _state.update { it.copy(pendingRevokeParentId = null) }

    fun confirmRevokeParent() {
        val parentId = _state.value.pendingRevokeParentId ?: return
        viewModelScope.launch {
            profileRepository.revokeLinkedParent(parentId)
            _state.update { it.copy(pendingRevokeParentId = null) }
        }
    }
}
