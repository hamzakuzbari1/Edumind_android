package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.model.SubjectProgress
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.ProfileRepository
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-22 · Student Profile.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Quick stats reuse [LearningRepository.getStudentHome] directly — the exact same
 * [GamificationSnapshot]/[SubjectProgress] data ST-01/ST-15 already show — so level, streak
 * and course progress are never modelled a second time here. [ProfileRepository.profile] and
 * [ProfileRepository.linkedParents] are both collected as hot flows so an edit or a revoke is
 * reflected the moment the repository confirms it, no manual reload needed.
 */
data class ProfileScreenData(
    val profile: StudentProfile,
    val email: String,
    val gamification: GamificationSnapshot,
    val subjects: List<SubjectProgress>,
    val linkedParents: List<LinkedParent>,
    val learningPreferences: LearningPreferences,
)

data class StudentProfileUiState(
    val result: UiState<ProfileScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val showEditSheet: Boolean = false,
    val isSavingEdit: Boolean = false,
    val pendingRevokeParentId: String? = null,
    val isRevoking: Boolean = false,
)

class StudentProfileViewModel(
    private val profileRepository: ProfileRepository,
    private val learningRepository: LearningRepository,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(StudentProfileUiState())
    val state: StateFlow<StudentProfileUiState> = _state.asStateFlow()

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
        viewModelScope.launch {
            profileRepository.learningPreferences.collect { preferences ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(learningPreferences = preferences)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val profileResult = profileRepository.getProfile()
            val homeResult = learningRepository.getStudentHome()
            val preferencesResult = profileRepository.getLearningPreferences()
            val email = authRepository.session.first()?.email.orEmpty()
            if (profileResult is AppResult.Success && homeResult is AppResult.Success && preferencesResult is AppResult.Success) {
                val parents = (profileRepository.getLinkedParents() as? AppResult.Success)?.data ?: emptyList()
                _state.update {
                    it.copy(
                        result = UiState.Content(
                            ProfileScreenData(
                                profile = profileResult.data,
                                email = email,
                                gamification = homeResult.data.gamification,
                                subjects = homeResult.data.subjects,
                                linkedParents = parents,
                                learningPreferences = preferencesResult.data,
                            )
                        )
                    )
                }
            } else {
                val error = (profileResult as? AppResult.Failure)?.error
                    ?: (homeResult as? AppResult.Failure)?.error
                    ?: (preferencesResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun openEditSheet() = _state.update { it.copy(showEditSheet = true) }

    fun dismissEditSheet() = _state.update { it.copy(showEditSheet = false) }

    fun saveProfile(displayName: String, grade: Grade, school: String) {
        if (_state.value.isSavingEdit) return
        _state.update { it.copy(isSavingEdit = true) }
        viewModelScope.launch {
            when (profileRepository.updateProfile(displayName, grade, school)) {
                // Reflected by the profile flow collector above — same convention as
                // PlannerViewModel's own loadWeekPlan() call.
                is AppResult.Success -> _state.update { it.copy(isSavingEdit = false, showEditSheet = false) }
                is AppResult.Failure -> _state.update { it.copy(isSavingEdit = false) }
            }
        }
    }

    /** Revoke always asks first — this only opens the confirmation, it never removes anything itself. */
    fun requestRevokeParent(parentId: String) = _state.update { it.copy(pendingRevokeParentId = parentId) }

    fun cancelRevokeParent() = _state.update { it.copy(pendingRevokeParentId = null) }

    fun confirmRevokeParent() {
        val parentId = _state.value.pendingRevokeParentId ?: return
        _state.update { it.copy(isRevoking = true) }
        viewModelScope.launch {
            profileRepository.revokeLinkedParent(parentId)
            _state.update { it.copy(isRevoking = false, pendingRevokeParentId = null) }
        }
    }
}
