package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.data.repository.CertificateRepository
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-11 · Project Certificate.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reuses the SAME two abstractions A-12 already resolves through — [ProjectRepository.getCertificateCode]
 * only tells this screen which code belongs to [projectId] (null means no certificate yet, i.e.
 * the project isn't [com.rork.eduspark.data.model.isFullyCompleted]); [CertificateRepository.verify]
 * is what actually resolves that code to a [CertificateVerification] record — no parallel
 * verification model or repository was created for this slice. [showExportDialog] is purely
 * local UI state for the honest MOCK image-export acknowledgement — see
 * [ProjectCertificateScreen]'s own doc comment for the real-vs-MOCK boundary.
 */
data class ProjectCertificateScreenData(
    val certificate: CertificateVerification,
    val code: String,
)

data class ProjectCertificateUiState(
    val result: UiState<ProjectCertificateScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val showExportDialog: Boolean = false,
)

class ProjectCertificateViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    private val certificateRepository: CertificateRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ProjectCertificateUiState())
    val state: StateFlow<ProjectCertificateUiState> = _state.asStateFlow()

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
            val code = (projectRepository.getCertificateCode(projectId) as? AppResult.Success)?.data
            if (code == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            when (val certResult = certificateRepository.verify(code)) {
                is AppResult.Success -> _state.update {
                    it.copy(result = UiState.Content(ProjectCertificateScreenData(certResult.data, code)))
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(certResult.error)) }
            }
        }
    }

    fun openExportDialog() = _state.update { it.copy(showExportDialog = true) }
    fun dismissExportDialog() = _state.update { it.copy(showExportDialog = false) }
}
