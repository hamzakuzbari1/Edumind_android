package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-05 · Lesson Upload.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherLessonUploadFormState] (source kind, mock file or video link, title, order, AI
 * options) is a local draft exactly like TC-01's own step drafts — nothing reaches the
 * repository until [submitUpload]. The three-step Teacher chrome (details → content → review)
 * is presentation only; [submitUpload] still calls the same [TeacherRepository.startLessonUpload]
 * contract. From that point on, [activeUpload] mirrors the repository's
 * [TeacherLessonUploadDraft] record, never a private copy — see that model's own doc comment
 * for why. This ViewModel only drives the clock ([tickingJob], a plain `delay` loop calling
 * [TeacherRepository.advanceLessonUpload]); the repository is what remembers where the upload
 * got to. So if this screen is left mid-upload and a new [TeacherLessonUploadViewModel]
 * instance is created later, [load] simply reads whatever [TeacherRepository.getUploadDraft]
 * already has and restarts ticking from there.
 *
 * [TeacherLessonSourceKind.VideoLink] has no dedicated repository field — it reuses
 * [LessonContentType.Video] and stores the typed URL as [TeacherLessonUploadFormState.mockFileName]
 * at submit time. AI option toggles stay on the form (and still reach startLessonUpload) but
 * default on so the approved Teacher flow can hide the configuration panel without skipping
 * tutor/quiz stages.
 */
enum class TeacherLessonSourceKind { Video, VideoLink, Pdf }

data class TeacherLessonUploadFormState(
    val sourceKind: TeacherLessonSourceKind = TeacherLessonSourceKind.Video,
    val contentType: LessonContentType = LessonContentType.Video,
    val mockFileName: String? = null,
    val mockFileBytes: Long = 0L,
    val videoLink: String = "",
    val title: String = "",
    val order: Int = 1,
    val generateQuiz: Boolean = true,
    val generateNarration: Boolean = true,
    val indexForTutor: Boolean = true,
)

data class TeacherLessonUploadScreenData(
    val defaultOrder: Int,
    val maxOrder: Int,
)

data class TeacherLessonUploadUiState(
    val result: UiState<TeacherLessonUploadScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val form: TeacherLessonUploadFormState = TeacherLessonUploadFormState(),
    /** 1 = details, 2 = teacher content, 3 = review. Local chrome only — not a navigation destination. */
    val step: Int = 1,
    val showValidationError: Boolean = false,
    val isStartingUpload: Boolean = false,
    /** Non-null exactly while a mock upload for this course is in flight (or paused) — see the class doc comment for why this mirrors, not owns, repository state. */
    val activeUpload: TeacherLessonUploadDraft? = null,
    val showCancelConfirm: Boolean = false,
)

sealed interface TeacherLessonUploadEvent {
    data class Uploaded(val lessonId: String) : TeacherLessonUploadEvent
}

class TeacherLessonUploadViewModel(
    private val courseId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherLessonUploadUiState())
    val state: StateFlow<TeacherLessonUploadUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherLessonUploadEvent>(Channel.BUFFERED)
    val events: Flow<TeacherLessonUploadEvent> = _events.receiveAsFlow()

    private var tickingJob: Job? = null

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
            val lessonsResult = teacherRepository.getLessons(courseId)
            if (lessonsResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((lessonsResult as AppResult.Failure).error)) }
                return@launch
            }
            val defaultOrder = lessonsResult.data.size + 1
            _state.update {
                it.copy(
                    result = UiState.Content(TeacherLessonUploadScreenData(defaultOrder = defaultOrder, maxOrder = defaultOrder)),
                    form = it.form.copy(order = defaultOrder),
                )
            }

            when (val draftResult = teacherRepository.getUploadDraft(courseId)) {
                is AppResult.Success -> {
                    val draft = draftResult.data ?: return@launch
                    _state.update { it.copy(activeUpload = draft) }
                    when (draft.stage) {
                        LessonUploadStage.Uploading, LessonUploadStage.Preparing -> startTicking()
                        LessonUploadStage.Completed -> draft.createdLessonId?.let { lessonId ->
                            _events.send(TeacherLessonUploadEvent.Uploaded(lessonId))
                        }
                        LessonUploadStage.Paused -> Unit
                    }
                }
                is AppResult.Failure -> Unit
            }
        }
    }

    fun selectSourceKind(kind: TeacherLessonSourceKind) {
        if (kind == _state.value.form.sourceKind) return
        val contentType = if (kind == TeacherLessonSourceKind.Pdf) LessonContentType.Pdf else LessonContentType.Video
        _state.update {
            it.copy(
                form = it.form.copy(
                    sourceKind = kind,
                    contentType = contentType,
                    mockFileName = null,
                    mockFileBytes = 0L,
                    videoLink = if (kind == TeacherLessonSourceKind.VideoLink) it.form.videoLink else "",
                ),
                showValidationError = false,
            )
        }
    }

    /** Kept so existing callers still map Pdf/Video onto the one-source selector. */
    fun selectContentType(type: LessonContentType) {
        selectSourceKind(
            if (type == LessonContentType.Pdf) TeacherLessonSourceKind.Pdf else TeacherLessonSourceKind.Video,
        )
    }

    /** Also used for "Replace" — same deterministic fixture per content type, an honest MOCK label, never a real file. */
    fun selectMockFile() {
        val kind = _state.value.form.sourceKind
        if (kind == TeacherLessonSourceKind.VideoLink) return
        val (name, bytes) = when (kind) {
            TeacherLessonSourceKind.Pdf -> MOCK_PDF_NAME to MOCK_PDF_BYTES
            TeacherLessonSourceKind.Video, TeacherLessonSourceKind.VideoLink -> MOCK_VIDEO_NAME to MOCK_VIDEO_BYTES
        }
        _state.update { it.copy(form = it.form.copy(mockFileName = name, mockFileBytes = bytes), showValidationError = false) }
    }

    fun removeMockFile() = _state.update { it.copy(form = it.form.copy(mockFileName = null, mockFileBytes = 0L)) }

    fun updateVideoLink(link: String) = _state.update {
        it.copy(form = it.form.copy(videoLink = link), showValidationError = false)
    }

    fun updateTitle(title: String) = _state.update { it.copy(form = it.form.copy(title = title), showValidationError = false) }

    fun updateOrder(order: Int) {
        val maxOrder = (_state.value.result as? UiState.Content)?.data?.maxOrder ?: return
        _state.update { it.copy(form = it.form.copy(order = order.coerceIn(1, maxOrder))) }
    }

    /** Underlying AI flags stay writable so the existing startLessonUpload contract is unchanged. */
    fun toggleGenerateQuiz() = _state.update { it.copy(form = it.form.copy(generateQuiz = !it.form.generateQuiz)) }
    fun toggleGenerateNarration() = _state.update { it.copy(form = it.form.copy(generateNarration = !it.form.generateNarration)) }
    fun toggleIndexForTutor() = _state.update { it.copy(form = it.form.copy(indexForTutor = !it.form.indexForTutor)) }

    /** @return true when this screen consumed Back as a step-back; false when the host should pop. */
    fun consumeBack(): Boolean {
        if (_state.value.activeUpload != null) return false
        val step = _state.value.step
        if (step > 1) {
            _state.update { it.copy(step = step - 1, showValidationError = false) }
            return true
        }
        return false
    }

    fun goNext() {
        val current = _state.value
        when (current.step) {
            1 -> {
                if (current.form.title.isBlank()) {
                    _state.update { it.copy(showValidationError = true) }
                    return
                }
                _state.update { it.copy(step = 2, showValidationError = false) }
            }
            2 -> {
                if (!hasTeacherSource(current.form)) {
                    _state.update { it.copy(showValidationError = true) }
                    return
                }
                _state.update { it.copy(step = 3, showValidationError = false) }
            }
            else -> submitUpload()
        }
    }

    fun submitUpload() {
        val current = _state.value
        if (current.isStartingUpload || current.activeUpload != null) return
        val form = current.form
        val resolvedName = resolvedSubmitFileName(form)
        val resolvedBytes = resolvedSubmitBytes(form)
        if (resolvedName == null || form.title.isBlank()) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        _state.update { it.copy(isStartingUpload = true, showValidationError = false) }
        viewModelScope.launch {
            val result = teacherRepository.startLessonUpload(
                courseId = courseId,
                contentType = form.contentType,
                mockFileName = resolvedName,
                mockTotalBytes = resolvedBytes,
                title = form.title,
                order = form.order,
                generateQuiz = form.generateQuiz,
                generateNarration = form.generateNarration,
                indexForTutor = form.indexForTutor,
            )
            if (result is AppResult.Success) {
                _state.update { it.copy(activeUpload = result.data, isStartingUpload = false) }
                startTicking()
            } else {
                _state.update { it.copy(isStartingUpload = false) }
            }
        }
    }

    fun pauseUpload() {
        tickingJob?.cancel()
        viewModelScope.launch {
            val result = teacherRepository.pauseLessonUpload(courseId)
            if (result is AppResult.Success) _state.update { it.copy(activeUpload = result.data) }
        }
    }

    fun resumeUpload() {
        viewModelScope.launch {
            val result = teacherRepository.resumeLessonUpload(courseId)
            if (result is AppResult.Success) {
                _state.update { it.copy(activeUpload = result.data) }
                startTicking()
            }
        }
    }

    fun requestCancelUpload() = _state.update { it.copy(showCancelConfirm = true) }
    fun dismissCancelUpload() = _state.update { it.copy(showCancelConfirm = false) }

    /** Discards the in-flight draft — no lesson exists yet at any point before Completed, so there is nothing left behind to clean up. */
    fun confirmCancelUpload() {
        tickingJob?.cancel()
        viewModelScope.launch {
            teacherRepository.cancelLessonUpload(courseId)
            _state.update { it.copy(activeUpload = null, showCancelConfirm = false) }
        }
    }

    private fun startTicking() {
        tickingJob?.cancel()
        tickingJob = viewModelScope.launch {
            while (isActive) {
                val current = _state.value.activeUpload ?: break
                if (current.stage != LessonUploadStage.Uploading && current.stage != LessonUploadStage.Preparing) break
                delay(TICK_DELAY_MS)
                when (val result = teacherRepository.advanceLessonUpload(courseId)) {
                    is AppResult.Success -> {
                        _state.update { it.copy(activeUpload = result.data) }
                        if (result.data.stage == LessonUploadStage.Completed) {
                            result.data.createdLessonId?.let { lessonId ->
                                _events.send(TeacherLessonUploadEvent.Uploaded(lessonId))
                            }
                            break
                        }
                    }
                    is AppResult.Failure -> break
                }
            }
        }
    }

    override fun onCleared() {
        tickingJob?.cancel()
        super.onCleared()
    }

    private fun hasTeacherSource(form: TeacherLessonUploadFormState): Boolean = when (form.sourceKind) {
        TeacherLessonSourceKind.Video, TeacherLessonSourceKind.Pdf -> form.mockFileName != null
        TeacherLessonSourceKind.VideoLink -> form.videoLink.isNotBlank()
    }

    private fun resolvedSubmitFileName(form: TeacherLessonUploadFormState): String? = when (form.sourceKind) {
        TeacherLessonSourceKind.VideoLink -> form.videoLink.trim().takeIf { it.isNotEmpty() }
        TeacherLessonSourceKind.Video, TeacherLessonSourceKind.Pdf -> form.mockFileName
    }

    private fun resolvedSubmitBytes(form: TeacherLessonUploadFormState): Long = when (form.sourceKind) {
        TeacherLessonSourceKind.VideoLink -> MOCK_VIDEO_BYTES
        TeacherLessonSourceKind.Video, TeacherLessonSourceKind.Pdf -> form.mockFileBytes
    }

    private companion object {
        const val TICK_DELAY_MS = 450L
        const val MOCK_PDF_NAME = "physics_unit_4.pdf"
        const val MOCK_PDF_BYTES = 3_400_000L
        const val MOCK_VIDEO_NAME = "chain_rule_lesson.mp4"
        const val MOCK_VIDEO_BYTES = 42_800_000L
    }
}
