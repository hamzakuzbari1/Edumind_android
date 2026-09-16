package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherProfessionalDocument
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.remote.media.MediaUrlResolver
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherSetupRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Teacher Edit Profile + Teaching Page share this ViewModel class (separate Koin instances).
 * Identity, bio (headline), grades, and subjects read/write the same Teacher Setup record.
 */
data class TeacherProfileScreenData(
    val displayName: String,
    val email: String,
    val headline: String,
    val subjectsGrades: TeacherSubjectsGrades,
    val qualifications: List<TeacherQualification>,
    val professionalDocuments: List<TeacherProfessionalDocument> = emptyList(),
    val photoUrl: String? = null,
)

data class TeacherProfileUiState(
    val result: UiState<TeacherProfileScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val nameDraft: String = "",
    val email: String = "",
    val bioDraft: String = "",
    val gradesDraft: Set<Grade> = emptySet(),
    val subjectIdsDraft: Set<String> = emptySet(),
    val avatarUrl: String? = null,
    /** Immediate local preview (`content://…`) while upload is in flight or pending. */
    val localPreviewUri: String? = null,
    val isSaving: Boolean = false,
    val isUploadingPhoto: Boolean = false,
    val isResolvingDocument: Boolean = false,
)

sealed interface TeacherProfileEvent {
    data object Saved : TeacherProfileEvent
    data class PhotoUploadFailed(val error: AppError) : TeacherProfileEvent
    data class OpenExternalDocument(val url: String) : TeacherProfileEvent
    data class DocumentOpenFailed(val error: AppError) : TeacherProfileEvent
}

class TeacherProfileViewModel(
    private val authRepository: AuthRepository,
    private val teacherSetupRepository: TeacherSetupRepository,
    private val mediaUrlResolver: MediaUrlResolver,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherProfileUiState())
    val state: StateFlow<TeacherProfileUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherProfileEvent>(Channel.BUFFERED)
    val events: Flow<TeacherProfileEvent> = _events.receiveAsFlow()

    private var teacherId: String = ""
    private var draftsSeeded = false
    private var documentResolveJob: Job? = null

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
            val session = authRepository.session.first()
            val resolvedId = session?.id
            if (resolvedId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            teacherId = resolvedId
            when (val setupResult = teacherSetupRepository.getSetupState(teacherId)) {
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(setupResult.error)) }
                is AppResult.Success -> {
                    val setup = setupResult.data
                    val photoUrl = setup.identity.photoUrl
                    _state.update { current ->
                        val withDrafts = if (!draftsSeeded) {
                            draftsSeeded = true
                            current.copy(
                                nameDraft = session.displayName,
                                email = session.email,
                                bioDraft = setup.identity.headline,
                                gradesDraft = setup.subjectsGrades.grades,
                                subjectIdsDraft = setup.subjectsGrades.subjectIds,
                                avatarUrl = photoUrl,
                            )
                        } else {
                            current.copy(avatarUrl = photoUrl)
                        }
                        withDrafts.copy(
                            localPreviewUri = null,
                            result = UiState.Content(
                                TeacherProfileScreenData(
                                    displayName = session.displayName,
                                    email = session.email,
                                    headline = setup.identity.headline,
                                    subjectsGrades = setup.subjectsGrades,
                                    qualifications = setup.qualifications,
                                    professionalDocuments = setup.professionalDocuments,
                                    photoUrl = photoUrl,
                                ),
                            ),
                        )
                    }
                }
            }
        }
    }

    fun updateNameDraft(value: String) = _state.update { it.copy(nameDraft = value) }

    fun updateBioDraft(value: String) = _state.update { it.copy(bioDraft = value) }

    fun toggleGrade(grade: Grade) = _state.update {
        val updated = if (grade in it.gradesDraft) it.gradesDraft - grade else it.gradesDraft + grade
        it.copy(gradesDraft = updated)
    }

    fun toggleSubject(subjectId: String) = _state.update {
        val updated = if (subjectId in it.subjectIdsDraft) it.subjectIdsDraft - subjectId else it.subjectIdsDraft + subjectId
        it.copy(subjectIdsDraft = updated)
    }

    fun onLocalPhotoPreview(uriString: String) {
        _state.update {
            it.copy(localPreviewUri = uriString, isUploadingPhoto = false)
        }
    }

    fun uploadSelectedPhoto(bytes: ByteArray, filename: String, mimeType: String) {
        if (teacherId.isBlank() || _state.value.isUploadingPhoto) return
        if (bytes.isEmpty()) {
            _state.update { it.copy(localPreviewUri = null) }
            viewModelScope.launch { _events.send(TeacherProfileEvent.PhotoUploadFailed(AppError.Domain("empty_avatar_file"))) }
            return
        }
        _state.update { it.copy(isUploadingPhoto = true) }
        viewModelScope.launch {
            when (
                val result = teacherSetupRepository.uploadAvatar(
                    teacherId = teacherId,
                    bytes = bytes,
                    filename = filename,
                    mimeType = mimeType,
                )
            ) {
                is AppResult.Success -> {
                    val photoUrl = result.data.identity.photoUrl
                    _state.update { current ->
                        val data = (current.result as? UiState.Content)?.data
                        current.copy(
                            isUploadingPhoto = false,
                            localPreviewUri = null,
                            avatarUrl = photoUrl,
                            result = if (data != null) {
                                UiState.Content(data.copy(photoUrl = photoUrl))
                            } else {
                                current.result
                            },
                        )
                    }
                }
                is AppResult.Failure -> {
                    // Keep prior remote avatar; drop failed local preview so UI stays stable.
                    _state.update { it.copy(isUploadingPhoto = false, localPreviewUri = null) }
                    _events.send(TeacherProfileEvent.PhotoUploadFailed(result.error))
                }
            }
        }
    }

    fun onPhotoReadFailed() {
        _state.update { it.copy(localPreviewUri = null, isUploadingPhoto = false) }
        viewModelScope.launch {
            _events.send(TeacherProfileEvent.PhotoUploadFailed(AppError.Domain("avatar_read_failed")))
        }
    }

    /** Resolve private/legacy/public document ref at open time — never cache signed URLs. */
    fun openProfessionalDocument(documentId: String) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val doc = data.professionalDocuments.firstOrNull { it.id == documentId } ?: return
        documentResolveJob?.cancel()
        documentResolveJob = viewModelScope.launch {
            _state.update { it.copy(isResolvingDocument = true) }
            when (val resolved = mediaUrlResolver.resolve(doc.fileUrl)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isResolvingDocument = false) }
                    _events.send(TeacherProfileEvent.OpenExternalDocument(resolved.data.url))
                }
                is AppResult.Failure -> {
                    _state.update { it.copy(isResolvingDocument = false) }
                    _events.send(TeacherProfileEvent.DocumentOpenFailed(resolved.error))
                }
            }
        }
    }

    fun saveProfile() {
        val draft = _state.value
        if (draft.nameDraft.isBlank() || draft.isSaving) return
        _state.update { it.copy(isSaving = true) }
        viewModelScope.launch {
            val currentIdentity = (teacherSetupRepository.getSetupState(teacherId) as? AppResult.Success)?.data?.identity
            if (currentIdentity == null) {
                _state.update { it.copy(isSaving = false) }
                return@launch
            }
            val identityResult = teacherSetupRepository.saveIdentity(
                teacherId,
                currentIdentity.copy(
                    displayName = draft.nameDraft.trim(),
                    headline = draft.bioDraft.trim(),
                ),
            )
            val subjectsResult = teacherSetupRepository.saveSubjectsGrades(
                teacherId,
                TeacherSubjectsGrades(
                    subjectIds = draft.subjectIdsDraft,
                    grades = draft.gradesDraft,
                ),
            )
            _state.update { it.copy(isSaving = false) }
            if (identityResult is AppResult.Success && subjectsResult is AppResult.Success) {
                val photoUrl = identityResult.data.identity.photoUrl
                _state.update { it.copy(avatarUrl = photoUrl ?: it.avatarUrl) }
                _events.send(TeacherProfileEvent.Saved)
            }
        }
    }

    override fun onCleared() {
        documentResolveJob?.cancel()
    }
}
