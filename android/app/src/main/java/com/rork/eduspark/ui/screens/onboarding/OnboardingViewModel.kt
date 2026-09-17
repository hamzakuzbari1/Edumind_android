package com.rork.eduspark.ui.screens.onboarding

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.R
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.OnboardingAnswers
import com.rork.eduspark.data.model.OnboardingSelections
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.SimpleDate
import com.rork.eduspark.data.model.StudentOnboardingStatus
import com.rork.eduspark.data.model.StudyHoursPerDay
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.SubjectOption
import com.rork.eduspark.data.model.Track
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.OnboardingRepository
import java.util.Calendar
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-01 … SO-05 · Student Onboarding — one ViewModel for the whole flow.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Scoped to the `onboarding` nav graph's own back-stack entry (see `onboardingGraph` in
 * AppNavigation), not to any single screen — every SO-0x composable resolves the *same*
 * instance. That is the entire mechanism behind "back navigation with state preservation":
 * nothing is written to disk, there is nothing to resume-from-crash, but moving between
 * SO-01 and SO-03 within one session never loses a selection, because the state never left
 * memory that belongs to one screen.
 *
 * Grade, subject and teacher selections are persisted by the canonical FastAPI onboarding
 * endpoints before navigation advances. The non-contract personalization questions remain
 * local drafts and are never presented as server-owned state.
 */
data class OnboardingUiState(
    val grade: Grade? = null,
    val track: Track? = null,
    val subjectIds: Set<String> = emptySet(),
    val availableSubjects: UiState<List<SubjectOption>> = UiState.Loading,
    val teachersBySubject: Map<String, UiState<List<OnboardingTeacher>>> = emptyMap(),
    val selectedTeacherIdBySubject: Map<String, String> = emptyMap(),
    val answers: OnboardingAnswers = OnboardingAnswers(),
    /** SO-05's celebration addresses the student by name — read from the live session. */
    val studentName: String = "",
    val isOnline: Boolean = true,
    val isRestoring: Boolean = true,
    val statusLoadFailed: Boolean = false,
    val isSavingGrade: Boolean = false,
    val gradeSaveFailed: Boolean = false,
    val isSavingSubjects: Boolean = false,
    val subjectsSaveFailed: Boolean = false,
    val isSavingTeachers: Boolean = false,
    val teachersSaveFailed: Boolean = false,
    val isCompleting: Boolean = false,
    val completionFailed: Boolean = false,
) {
    val canContinueFromGrade: Boolean
        get() = grade != null && (grade != Grade.Baccalaureate || track != null)

    val canContinueFromSubjects: Boolean
        get() = subjectIds.isNotEmpty()

    val canContinueFromTeachers: Boolean
        get() = subjectIds.isNotEmpty() && subjectIds.all { selectedTeacherIdBySubject.containsKey(it) }

    val selections: OnboardingSelections
        get() = OnboardingSelections(grade, track, subjectIds, selectedTeacherIdBySubject, answers)
}

sealed interface OnboardingEvent {
    data object GradeSaved : OnboardingEvent
    data object SubjectsSaved : OnboardingEvent
    data object TeachersSaved : OnboardingEvent

    /** SO-05's primary action succeeded — the caller routes to Student Core from here. */
    data object Completed : OnboardingEvent
}

class OnboardingViewModel(
    private val onboardingRepository: OnboardingRepository,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingUiState())
    val state: StateFlow<OnboardingUiState> = _state.asStateFlow()

    private val _events = Channel<OnboardingEvent>(Channel.BUFFERED)
    val events: Flow<OnboardingEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            authRepository.session.collect { session ->
                _state.update { it.copy(studentName = session?.displayName.orEmpty()) }
            }
        }
        loadStatus()
    }

    fun retryStatus() = loadStatus()

    private fun loadStatus() {
        _state.update { it.copy(isRestoring = true, statusLoadFailed = false) }
        viewModelScope.launch {
            when (val result = onboardingRepository.getStatus()) {
                is AppResult.Success -> {
                    applyServerStatus(result.data)
                    _state.update { it.copy(isRestoring = false) }
                    result.data.grade?.let { loadSubjects(it) }
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isRestoring = false, statusLoadFailed = true)
                }
            }
        }
    }

    private fun applyServerStatus(status: StudentOnboardingStatus) {
        _state.update { current ->
            current.copy(
                grade = status.grade ?: current.grade,
                subjectIds = status.selectedSubjectIds,
                selectedTeacherIdBySubject = status.selectedTeacherIdBySubject,
            )
        }
    }

    // ── SO-01 · Grade ─────────────────────────────────────────────────────
    fun selectGrade(grade: Grade) {
        _state.update {
            it.copy(
                grade = grade,
                // A track only means something for the Baccalaureate year; moving off it
                // clears a now-meaningless choice, moving onto it leaves the fork open.
                track = if (grade == Grade.Baccalaureate) it.track else null,
            )
        }
    }

    fun selectTrack(track: Track) {
        _state.update { it.copy(track = track) }
    }

    fun saveGrade() {
        val grade = _state.value.grade ?: return
        if (_state.value.isSavingGrade) return
        _state.update { it.copy(isSavingGrade = true, gradeSaveFailed = false) }
        viewModelScope.launch {
            when (val result = onboardingRepository.saveGrade(grade)) {
                is AppResult.Success -> {
                    applyServerStatus(result.data)
                    loadSubjects(grade)
                    _state.update { it.copy(isSavingGrade = false) }
                    _events.send(OnboardingEvent.GradeSaved)
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isSavingGrade = false, gradeSaveFailed = true)
                }
            }
        }
    }

    // ── SO-02 · Subjects ─────────────────────────────────────────────────
    fun toggleSubject(subjectId: String) {
        _state.update {
            val next = if (subjectId in it.subjectIds) it.subjectIds - subjectId else it.subjectIds + subjectId
            it.copy(
                subjectIds = next,
                // A dropped subject cannot keep a teacher pick — SO-03 must never show a
                // selection for a subject that is no longer part of the path.
                selectedTeacherIdBySubject = it.selectedTeacherIdBySubject.filterKeys { id -> id in next },
            )
        }
    }

    fun loadSubjectsIfNeeded() {
        val grade = _state.value.grade ?: return
        if (_state.value.availableSubjects !is UiState.Content) loadSubjects(grade)
    }

    fun retrySubjects() {
        _state.value.grade?.let(::loadSubjects)
    }

    private fun loadSubjects(grade: Grade) {
        _state.update { it.copy(availableSubjects = UiState.Loading) }
        viewModelScope.launch {
            when (val result = onboardingRepository.getSubjects(grade)) {
                is AppResult.Success -> _state.update {
                    val subjects = if (result.data.isEmpty()) UiState.Empty() else UiState.Content(result.data)
                    it.copy(availableSubjects = subjects)
                }

                is AppResult.Failure -> _state.update {
                    it.copy(availableSubjects = UiState.Failure(result.error))
                }
            }
        }
    }

    fun saveSubjects() {
        val subjectIds = _state.value.subjectIds
        if (subjectIds.isEmpty() || _state.value.isSavingSubjects) return
        _state.update { it.copy(isSavingSubjects = true, subjectsSaveFailed = false) }
        viewModelScope.launch {
            when (val result = onboardingRepository.saveSubjects(subjectIds)) {
                is AppResult.Success -> {
                    applyServerStatus(result.data)
                    _state.update { it.copy(isSavingSubjects = false) }
                    _events.send(OnboardingEvent.SubjectsSaved)
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isSavingSubjects = false, subjectsSaveFailed = true)
                }
            }
        }
    }

    // ── SO-03 · Teachers ─────────────────────────────────────────────────
    /** Fetches teachers for every chosen subject that hasn't already loaded successfully. */
    fun loadTeachersIfNeeded() {
        _state.value.subjectIds.forEach { subjectId ->
            if (_state.value.teachersBySubject[subjectId] !is UiState.Content) loadTeachers(subjectId)
        }
    }

    fun retryTeachers(subjectId: String) = loadTeachers(subjectId)

    private fun loadTeachers(subjectId: String) {
        val grade = _state.value.grade ?: return
        _state.update { it.copy(teachersBySubject = it.teachersBySubject + (subjectId to UiState.Loading)) }
        viewModelScope.launch {
            when (val result = onboardingRepository.getTeachers(subjectId, grade)) {
                is AppResult.Success -> _state.update {
                    val loaded = if (result.data.isEmpty()) UiState.Empty() else UiState.Content(result.data)
                    it.copy(teachersBySubject = it.teachersBySubject + (subjectId to loaded))
                }

                is AppResult.Failure -> _state.update {
                    it.copy(teachersBySubject = it.teachersBySubject + (subjectId to UiState.Failure(result.error)))
                }
            }
        }
    }

    fun selectTeacher(subjectId: String, teacherId: String) {
        _state.update {
            it.copy(selectedTeacherIdBySubject = it.selectedTeacherIdBySubject + (subjectId to teacherId))
        }
    }

    fun saveTeachers() {
        val choices = _state.value.selectedTeacherIdBySubject
        if (!_state.value.canContinueFromTeachers || _state.value.isSavingTeachers) return
        _state.update { it.copy(isSavingTeachers = true, teachersSaveFailed = false) }
        viewModelScope.launch {
            when (val result = onboardingRepository.saveTeachers(choices)) {
                is AppResult.Success -> {
                    applyServerStatus(result.data)
                    _state.update { it.copy(isSavingTeachers = false) }
                    _events.send(OnboardingEvent.TeachersSaved)
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isSavingTeachers = false, teachersSaveFailed = true)
                }
            }
        }
    }

    // ── SO-04 · Personalize ──────────────────────────────────────────────
    fun setStudyHours(hours: StudyHoursPerDay) {
        _state.update { it.copy(answers = it.answers.copy(studyHours = hours)) }
    }

    fun selectStrongestSubject(subjectId: String) {
        _state.update {
            it.copy(answers = it.answers.copy(strongestSubjectId = subjectId, strongestNotSure = false))
        }
    }

    fun selectStrongestNotSure() {
        _state.update { it.copy(answers = it.answers.copy(strongestSubjectId = null, strongestNotSure = true)) }
    }

    fun selectWeakestSubject(subjectId: String) {
        _state.update {
            it.copy(answers = it.answers.copy(weakestSubjectId = subjectId, weakestNotSure = false))
        }
    }

    fun selectWeakestNotSure() {
        _state.update { it.copy(answers = it.answers.copy(weakestSubjectId = null, weakestNotSure = true)) }
    }

    fun setExamDate(date: SimpleDate) {
        _state.update { it.copy(answers = it.answers.copy(examDate = date, examDateNotSure = false)) }
    }

    fun setExamDateNotSure() {
        _state.update { it.copy(answers = it.answers.copy(examDate = null, examDateNotSure = true)) }
    }

    fun setStudyTime(time: StudyTimeOfDay) {
        _state.update { it.copy(answers = it.answers.copy(studyTime = time)) }
    }

    // ── SO-05 · Complete ─────────────────────────────────────────────────
    fun completeOnboarding() {
        if (_state.value.isCompleting) return
        _state.update { it.copy(isCompleting = true, completionFailed = false) }
        viewModelScope.launch {
            when (onboardingRepository.complete()) {
                is AppResult.Success -> when (val restored = authRepository.restoreSession()) {
                    is AppResult.Success -> {
                        if (restored.data?.hasCompletedOnboarding == true) {
                            _state.update { it.copy(isCompleting = false) }
                            _events.send(OnboardingEvent.Completed)
                        } else {
                            _state.update { it.copy(isCompleting = false, completionFailed = true) }
                        }
                    }

                    is AppResult.Failure -> _state.update {
                        it.copy(isCompleting = false, completionFailed = true)
                    }
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isCompleting = false, completionFailed = true)
                }
            }
        }
    }
}

/**
 * Days between today and [date], via `java.util.Calendar` epoch arithmetic — not `java.time`,
 * which needs core-library desugaring that this module (minSdk 24) does not configure.
 * Shared by SO-04 (the "exam in N days" caption) and SO-05 (the same fact in the summary).
 */
fun daysUntil(date: SimpleDate): Int {
    val target = Calendar.getInstance().apply {
        set(date.year, date.month - 1, date.day, 0, 0, 0)
        set(Calendar.MILLISECOND, 0)
    }
    val today = Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }
    val diffMs = target.timeInMillis - today.timeInMillis
    return (diffMs / (24 * 60 * 60 * 1000)).toInt()
}

val OnboardingAnswers.studyHoursDone: Boolean get() = studyHours != null
val OnboardingAnswers.strongestDone: Boolean get() = strongestSubjectId != null || strongestNotSure
val OnboardingAnswers.weakestDone: Boolean get() = weakestSubjectId != null || weakestNotSure
val OnboardingAnswers.examDateDone: Boolean get() = examDate != null || examDateNotSure
val OnboardingAnswers.studyTimeDone: Boolean get() = studyTime != null

/** A subject's display id + label — the string resource the same vocabulary A-07 already uses. */
data class SubjectDisplay(val id: String, @param:StringRes val labelRes: Int)

/**
 * Curriculum reference data — static, like A-07's own subject/grade lists, because these
 * are catalogue facts, not something a mock latency needs to simulate.
 */
object OnboardingCatalog {
    val Math = SubjectDisplay("math", R.string.a07_subject_math)
    val Physics = SubjectDisplay("physics", R.string.a07_subject_physics)
    val Chemistry = SubjectDisplay("chemistry", R.string.a07_subject_chemistry)
    val Biology = SubjectDisplay("biology", R.string.a07_subject_biology)
    val Arabic = SubjectDisplay("arabic", R.string.a07_subject_arabic)
    val English = SubjectDisplay("english", R.string.a07_subject_english)
    val French = SubjectDisplay("french", R.string.so_subject_french)
    val Philosophy = SubjectDisplay("philosophy", R.string.a07_subject_philosophy)
    val Informatics = SubjectDisplay("informatics", R.string.a07_subject_informatics)

    val All = listOf(Math, Physics, Chemistry, Biology, Arabic, English, French, Philosophy, Informatics)

    fun byId(id: String): SubjectDisplay? = All.firstOrNull { it.id == id }

    /**
     * (group title resource, subjects). Grouping depends on [track]: the PDF's own example
     * only shows the science grouping explicitly (core sciences, then languages/general);
     * the literary grouping is a bounded, consistent extrapolation using A-07's existing
     * subject vocabulary (Arabic moves into the literary core, English/French stay general).
     * Grades 10/11 (no track yet) default to the science grouping as a neutral foundation set.
     */
    fun groupsFor(track: Track?): List<Pair<Int, List<SubjectDisplay>>> = if (track == Track.Literary) {
        listOf(
            R.string.so02_group_literary_core to listOf(Arabic, Philosophy, Informatics),
            R.string.so02_group_languages_general to listOf(English, French),
        )
    } else {
        listOf(
            R.string.so02_group_science_core to listOf(Math, Physics, Chemistry, Biology),
            R.string.so02_group_languages_general to listOf(English, Arabic, French),
        )
    }
}
