package com.rork.eduspark.ui.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StudentNavigationDrawerState(
    val user: SessionUser? = null,
    val teacherDisplayName: String? = null,
    val isSigningOut: Boolean = false,
)

class StudentNavigationDrawerViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(StudentNavigationDrawerState())
    val state: StateFlow<StudentNavigationDrawerState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.session.collect { user ->
                _state.update { it.copy(user = user) }
                loadTeacherIdentity(user)
            }
        }
    }

    fun refreshTeacherIdentity() {
        viewModelScope.launch {
            loadTeacherIdentity(authRepository.session.first())
        }
    }

    private suspend fun loadTeacherIdentity(user: SessionUser?) {
        if (user?.role != UserRole.Teacher) {
            _state.update { it.copy(teacherDisplayName = null) }
            return
        }
        val name = (teacherRepository.getSetupState(user.id) as? AppResult.Success)
            ?.data?.identity?.displayName?.trim().orEmpty()
        _state.update { it.copy(teacherDisplayName = name.ifBlank { null }) }
    }

    fun signOut(onSignedOut: () -> Unit) {
        if (_state.value.isSigningOut) return
        viewModelScope.launch {
            _state.update { it.copy(isSigningOut = true) }
            authRepository.signOut()
            _state.update { it.copy(isSigningOut = false) }
            onSignedOut()
        }
    }
}
