package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.repository.TeacherLessonSelectedFile
import com.rork.eduspark.data.repository.TeacherLessonUploadKind
import com.rork.eduspark.data.repository.TeacherLessonUploadRepository
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
 * [TeacherLessonUploadFormState] (source kind, selected device file or video link, title, order, AI
 * options) is a local draft exactly like TC-01's own step drafts — nothing reaches the
 * repository until [submitUpload]. The three-step Teacher chrome (details → content → review)
 * is presentation only; [submitUpload] sends a real selected file through
 * [TeacherLessonUploadRepository]. Existing mock ticking is kept only for compatibility with a
 * mock upload repository.
 *
 * [TeacherLessonSourceKind.VideoLink] has no dedicated repository field — it reuses
 * [LessonContentType.Video] and stores the typed URL as a lightweight compatibility draft
 * at submit time. AI option toggles stay on the form (and still reach startLessonUpload) but
 * default on so the approved Teacher flow can hide the configuration panel without skipping
 * tutor/quiz stages.
 */
enum class TeacherLessonSourceKind { Video, VideoLink, Pdf, Homework, Audio }

data class TeacherLessonUploadFormState(
    val sourceKind: TeacherLessonSourceKind = TeacherLessonSourceKind.Video,
    val contentType: LessonContentType = LessonContentType.Video,
    val selectedFile: TeacherLessonSelectedFile? = null,
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
    /** Non-null while upload feedback is visible; real uploads complete as soon as the backend accepts the multipart request. */
    val activeUpload: TeacherLessonUploadDraft? = null,
    val uploadError: String? = null,
    val showCancelConfirm: Boolean = false,
) {
    /** True when the primary bottom action may run for the current step. */
    val primaryActionEnabled: Boolean
        get() = when (step) {
            1 -> form.title.isNotBlank()
            2 -> hasTeacherSource(form)
            else -> canSaveLesson(form)
        }

    /** Human-readable reason Save/Next is blocked; null when the action is allowed. */
    val primaryActionBlockedReason: String?
        get() {
            val selected = form.selectedFile
            return when {
                step == 1 && form.title.isBlank() -> "أدخل عنوان الدرس للمتابعة"
                step >= 2 && form.sourceKind != TeacherLessonSourceKind.VideoLink && selected == null ->
                    "اختر ملفاً حقيقياً للمتابعة"
                step >= 2 && form.sourceKind != TeacherLessonSourceKind.VideoLink &&
                    selected != null && selected.bytes.isEmpty() ->
                    "الملف المحدد فارغ. اختر ملفاً آخر"
                step >= 2 && form.sourceKind == TeacherLessonSourceKind.VideoLink && form.videoLink.isBlank() ->
                    "أدخل رابط الفيديو للمتابعة"
                step >= 3 && form.title.isBlank() -> "أدخل عنوان الدرس قبل الحفظ"
                else -> null
            }
        }
}

sealed interface TeacherLessonUploadEvent {
    data class Uploaded(val lessonId: String) : TeacherLessonUploadEvent
}

class TeacherLessonUploadViewModel(
    private val courseId: String,
    private val teacherRepository: TeacherRepository,
    private val uploadRepository: TeacherLessonUploadRepository,
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
        val contentType = when (kind) {
            TeacherLessonSourceKind.Pdf,
            TeacherLessonSourceKind.Homework,
            TeacherLessonSourceKind.Audio -> LessonContentType.Pdf
            TeacherLessonSourceKind.Video,
            TeacherLessonSourceKind.VideoLink -> LessonContentType.Video
        }
        _state.update {
            it.copy(
                form = it.form.copy(
                    sourceKind = kind,
                    contentType = contentType,
                    selectedFile = null,
                    videoLink = if (kind == TeacherLessonSourceKind.VideoLink) it.form.videoLink else "",
                ),
                showValidationError = false,
                uploadError = null,
            )
        }
    }

    /** Kept so existing callers still map Pdf/Video onto the one-source selector. */
    fun selectContentType(type: LessonContentType) {
        selectSourceKind(
            if (type == LessonContentType.Pdf) TeacherLessonSourceKind.Pdf else TeacherLessonSourceKind.Video,
        )
    }

    fun selectRealFile(file: TeacherLessonSelectedFile) {
        _state.update {
            it.copy(
                form = it.form.copy(selectedFile = file),
                showValidationError = false,
                uploadError = null,
            )
        }
    }

    fun rejectSelectedFile(reason: String = "تعذر قراءة الملف المحدد") {
        _state.update { it.copy(uploadError = reason, showValidationError = false) }
    }

    fun pickerCancelled() = _state.update { it.copy(uploadError = null) }

    fun removeSelectedFile() = _state.update {
        it.copy(form = it.form.copy(selectedFile = null), uploadError = null)
    }

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
        val selectedFile = form.selectedFile
        if (!canSaveLesson(form)) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        _state.update { it.copy(isStartingUpload = true, showValidationError = false, uploadError = null) }
        viewModelScope.launch {
            try {
                val result = if (form.sourceKind == TeacherLessonSourceKind.VideoLink) {
                    teacherRepository.startLessonUpload(
                        courseId = courseId,
                        contentType = form.contentType,
                        mockFileName = form.videoLink.trim(),
                        mockTotalBytes = LINK_PLACEHOLDER_BYTES,
                        title = form.title,
                        order = form.order,
                        generateQuiz = form.generateQuiz,
                        generateNarration = form.generateNarration,
                        indexForTutor = form.indexForTutor,
                    )
                } else if (selectedFile != null && selectedFile.bytes.isNotEmpty()) {
                    uploadRepository.uploadLessonFile(
                        courseId = courseId,
                        title = form.title.trim(),
                        order = form.order,
                        file = selectedFile,
                        kind = form.sourceKind.toUploadKind(),
                        generateQuiz = form.generateQuiz,
                        generateNarration = form.generateNarration,
                        indexForTutor = form.indexForTutor,
                    )
                } else {
                    AppResult.Failure(com.rork.eduspark.core.result.AppError.Domain("file_required"))
                }
                if (result is AppResult.Success) {
                    _state.update { it.copy(activeUpload = result.data, isStartingUpload = false) }
                    if (result.data.stage == LessonUploadStage.Completed) {
                        result.data.createdLessonId?.let { lessonId ->
                            _events.send(TeacherLessonUploadEvent.Uploaded(lessonId))
                        }
                    } else {
                        startTicking()
                    }
                } else {
                    _state.update {
                        it.copy(
                            isStartingUpload = false,
                            uploadError = (result as AppResult.Failure).error.toUploadMessage(),
                        )
                    }
                }
            } catch (_: Throwable) {
                _state.update {
                    it.copy(
                        isStartingUpload = false,
                        uploadError = "تعذر رفع الملف الحقيقي.",
                    )
                }
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

    private companion object {
        const val TICK_DELAY_MS = 450L
        const val LINK_PLACEHOLDER_BYTES = 1L
    }
}

/** Save requires a non-blank title plus a real selected file (or video link). Never mock attachment fields. */
internal fun canSaveLesson(form: TeacherLessonUploadFormState): Boolean =
    form.title.isNotBlank() && hasTeacherSource(form)

internal fun hasTeacherSource(form: TeacherLessonUploadFormState): Boolean = when (form.sourceKind) {
    TeacherLessonSourceKind.Video,
    TeacherLessonSourceKind.Pdf,
    TeacherLessonSourceKind.Homework,
    TeacherLessonSourceKind.Audio -> form.selectedFile != null && form.selectedFile.bytes.isNotEmpty()
    TeacherLessonSourceKind.VideoLink -> form.videoLink.isNotBlank()
}

private fun TeacherLessonSourceKind.toUploadKind(): TeacherLessonUploadKind = when (this) {
    TeacherLessonSourceKind.Video -> TeacherLessonUploadKind.Video
    TeacherLessonSourceKind.Pdf -> TeacherLessonUploadKind.Pdf
    TeacherLessonSourceKind.Homework -> TeacherLessonUploadKind.Homework
    TeacherLessonSourceKind.Audio -> TeacherLessonUploadKind.Audio
    TeacherLessonSourceKind.VideoLink -> TeacherLessonUploadKind.Video
}

private fun com.rork.eduspark.core.result.AppError.toUploadMessage(): String = when (this) {
    com.rork.eduspark.core.result.AppError.Forbidden -> "لا تملك صلاحية رفع ملف لهذا الدرس."
    com.rork.eduspark.core.result.AppError.Network,
    com.rork.eduspark.core.result.AppError.Offline -> "تعذر الاتصال بالخادم. تحقق من الإنترنت ثم أعد المحاولة."
    com.rork.eduspark.core.result.AppError.Server -> "الخادم لم يقبل الرفع حالياً. أعد المحاولة لاحقاً."
    com.rork.eduspark.core.result.AppError.SessionExpired -> "انتهت الجلسة. سجّل الدخول من جديد."
    is com.rork.eduspark.core.result.AppError.Domain -> when (code) {
        "file_too_large" -> "الملف كبير جداً."
        "unsupported_file_type" -> "نوع الملف غير مدعوم."
        else -> "تعذر رفع الملف الحقيقي."
    }
    is com.rork.eduspark.core.result.AppError.Validation -> "تحقق من نوع الملف وحجمه ثم أعد المحاولة."
    else -> "تعذر رفع الملف الحقيقي."
}
