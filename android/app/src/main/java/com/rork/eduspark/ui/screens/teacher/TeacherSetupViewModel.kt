package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherSetupStepId
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
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
 * ══════════════════════════════════════════════════════════════════════════
 * TC-01 · Teacher Setup Wizard.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One screen, seven steps — [TeacherSetupScreenData.currentStepId] is transient UI state,
 * never persisted; the RESUMABLE state lives entirely in
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository] (repository/session-level,
 * above this ViewModel's own lifecycle). [load] always recomputes the first genuinely
 * incomplete step from [TeacherSetupState.completedStepIds], so leaving mid-wizard and
 * reopening resumes exactly where the teacher left off with every earlier step's values
 * intact — no separate "resume" call needed.
 *
 * Draft edits ([updateIdentity] etc.) only touch the local [TeacherSetupScreenData.draft];
 * nothing reaches [TeacherRepository] until [saveCurrentStepAndAdvance], which is also the
 * one place required-field validation runs (Identity's display name; Subjects & Grades'
 * "at least one each") — matching [TeacherRepository.finishSetup]'s own defensive check so
 * neither path can silently complete a skipped required step.
 *
 * [finishSetup] calls both [TeacherRepository.finishSetup] (the Teacher-domain completion
 * record) and [AuthRepository.completeOnboarding] (the SAME session flag SO-05 already flips
 * for students) — reusing the one existing "has this role finished its onboarding" field
 * rather than a second parallel one.
 *
 * On first [load], Identity and Subjects & Grades are prefilled from what A-07 Teacher Register
 * already collected — [AppPreferences.teacherIntentSubjects]/[AppPreferences.teacherIntentGrades]
 * (the same on-device store [com.rork.eduspark.ui.screens.auth.RegisterViewModel] wrote to) and
 * the session's own display name — so the teacher is never asked for the same information twice.
 * This only ever prefills the DRAFT; it never adds a step to [TeacherSetupState.completedStepIds]
 * on its own, so those two steps still require an explicit save inside the wizard.
 */
data class TeacherSetupScreenData(
    val draft: TeacherSetupState,
    /** Null once every step has been saved — the review/finish view. */
    val currentStepId: TeacherSetupStepId?,
)

data class TeacherSetupUiState(
    val result: UiState<TeacherSetupScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val isSaving: Boolean = false,
    val isFinishing: Boolean = false,
    val showValidationError: Boolean = false,
)

sealed interface TeacherSetupEvent {
    data object SetupCompleted : TeacherSetupEvent
}

class TeacherSetupViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    private val preferences: AppPreferences,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherSetupUiState())
    val state: StateFlow<TeacherSetupUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherSetupEvent>(Channel.BUFFERED)
    val events: Flow<TeacherSetupEvent> = _events.receiveAsFlow()

    private var teacherId: String? = null

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
            val id = session?.id
            if (id == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            teacherId = id
            when (val result = teacherRepository.getSetupState(id)) {
                is AppResult.Success -> {
                    val prefilled = applyRegistrationPrefill(result.data, session)
                    val firstIncomplete = STEP_ORDER.firstOrNull { it !in prefilled.completedStepIds }
                    _state.update {
                        it.copy(result = UiState.Content(TeacherSetupScreenData(draft = prefilled, currentStepId = firstIncomplete)))
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    /** Prefills the still-blank Identity / Subjects & Grades draft fields from A-07's registration intent — never marks either step complete. */
    private suspend fun applyRegistrationPrefill(state: TeacherSetupState, session: SessionUser): TeacherSetupState {
        var next = state
        if (TeacherSetupStepId.Identity !in state.completedStepIds &&
            state.identity.displayName.isBlank() &&
            session.displayName.isNotBlank()
        ) {
            next = next.copy(identity = next.identity.copy(displayName = session.displayName))
        }
        if (TeacherSetupStepId.SubjectsGrades !in state.completedStepIds &&
            state.subjectsGrades.subjectIds.isEmpty() &&
            state.subjectsGrades.grades.isEmpty()
        ) {
            val subjectIds = preferences.teacherIntentSubjects.first()
            val grades = preferences.teacherIntentGrades.first().mapNotNull(::mapRegistrationGradeId).toSet()
            if (subjectIds.isNotEmpty() || grades.isNotEmpty()) {
                next = next.copy(subjectsGrades = TeacherSubjectsGrades(subjectIds = subjectIds, grades = grades))
            }
        }
        return next
    }

    // ── Draft mutators — local only, nothing saved until saveCurrentStepAndAdvance() ──────
    fun updateIdentity(identity: TeacherIdentityInfo) = updateDraft { it.copy(identity = identity) }
    fun updateSubjectsGrades(subjectsGrades: TeacherSubjectsGrades) = updateDraft { it.copy(subjectsGrades = subjectsGrades) }
    fun updateQualifications(qualifications: List<TeacherQualification>) = updateDraft { it.copy(qualifications = qualifications) }
    fun updateExperience(experience: TeacherExperienceInfo) = updateDraft { it.copy(experience = experience) }
    fun updateDocuments(documents: List<TeacherSetupDocument>) = updateDraft { it.copy(documents = documents) }
    fun updatePricing(pricing: TeacherPricingInfo) = updateDraft { it.copy(pricing = pricing) }
    fun updateVoiceSample(voiceSample: TeacherVoiceSample) = updateDraft { it.copy(voiceSample = voiceSample) }

    private fun updateDraft(transform: (TeacherSetupState) -> TeacherSetupState) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        _state.update { it.copy(result = UiState.Content(data.copy(draft = transform(data.draft))), showValidationError = false) }
    }

    /** Back never re-validates or re-saves — the step being left behind was already saved to reach here. */
    fun goBack() {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val targetIndex = if (data.currentStepId == null) STEP_ORDER.lastIndex else STEP_ORDER.indexOf(data.currentStepId) - 1
        if (targetIndex >= 0) {
            _state.update { it.copy(result = UiState.Content(data.copy(currentStepId = STEP_ORDER[targetIndex])), showValidationError = false) }
        }
    }

    /** Validates the current step's required fields (if any), saves it, and advances — or surfaces an inline validation error. */
    fun saveCurrentStepAndAdvance() {
        val id = teacherId ?: return
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val step = data.currentStepId ?: return
        val draft = data.draft

        if (step == TeacherSetupStepId.Identity && draft.identity.displayName.isBlank()) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        if (step == TeacherSetupStepId.SubjectsGrades &&
            (draft.subjectsGrades.subjectIds.isEmpty() || draft.subjectsGrades.grades.isEmpty())
        ) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        if (_state.value.isSaving) return

        _state.update { it.copy(isSaving = true) }
        viewModelScope.launch {
            val saveResult = when (step) {
                TeacherSetupStepId.Identity -> teacherRepository.saveIdentity(id, draft.identity)
                TeacherSetupStepId.SubjectsGrades -> teacherRepository.saveSubjectsGrades(id, draft.subjectsGrades)
                TeacherSetupStepId.Qualifications -> teacherRepository.saveQualifications(id, draft.qualifications)
                TeacherSetupStepId.Experience -> teacherRepository.saveExperience(id, draft.experience)
                TeacherSetupStepId.Documents -> teacherRepository.saveDocuments(id, draft.documents)
                TeacherSetupStepId.Pricing -> teacherRepository.savePricing(id, draft.pricing)
                TeacherSetupStepId.VoiceSample -> teacherRepository.saveVoiceSample(id, draft.voiceSample)
            }
            if (saveResult is AppResult.Success) {
                val nextStep = STEP_ORDER.getOrNull(STEP_ORDER.indexOf(step) + 1)
                _state.update {
                    it.copy(
                        isSaving = false,
                        result = UiState.Content(TeacherSetupScreenData(draft = saveResult.data, currentStepId = nextStep)),
                    )
                }
            } else {
                _state.update { it.copy(isSaving = false) }
            }
        }
    }

    fun finishSetup() {
        val id = teacherId ?: return
        if (_state.value.isFinishing) return
        _state.update { it.copy(isFinishing = true) }
        viewModelScope.launch {
            when (teacherRepository.finishSetup(id)) {
                is AppResult.Success -> {
                    authRepository.completeOnboarding()
                    _state.update { it.copy(isFinishing = false) }
                    _events.send(TeacherSetupEvent.SetupCompleted)
                }
                is AppResult.Failure -> _state.update { it.copy(isFinishing = false, showValidationError = true) }
            }
        }
    }

    private companion object {
        val STEP_ORDER = TeacherSetupStepId.entries
    }
}

/**
 * Maps A-07 Teacher Register's string grade ids (see
 * [com.rork.eduspark.ui.screens.auth.TeacherGradeOptions]) to TC-01's own typed [Grade] — the
 * one explicit mapping at the registration/setup boundary, so A-07 keeps its simple string ids
 * and TC-01 keeps the [Grade] enum every other Teacher screen already uses, without either side
 * becoming a second source of truth for the other's representation.
 */
private fun mapRegistrationGradeId(id: String): Grade? = when (id) {
    "grade_10" -> Grade.Grade10
    "grade_11" -> Grade.Grade11
    "grade_12" -> Grade.Baccalaureate
    else -> null
}
