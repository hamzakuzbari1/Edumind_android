package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonDetail
import com.rork.eduspark.data.model.LessonMediaType
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.QuizRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-03 · Lesson Player.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One shell, three media surfaces — the screen picks which one to render from
 * [LessonDetail.mediaTypes] (video first, then PDF, then audio-only), but every surface
 * shares this same playback/position state rather than each owning its own.
 *
 * "Remember position within the current mock session" (ST-03's PDF requirement) is exactly
 * what living in the ViewModel rather than the composable gives for free — the state
 * survives a configuration change and returning from ST-04/ST-05, and resets only when this
 * ViewModel is actually cleared (leaving the lesson for good).
 */
data class LessonPlayerUiState(
    val result: UiState<LessonDetail> = UiState.Loading,
    val isOnline: Boolean = true,
    val quizSession: LessonQuizSession? = null,
    val isRefreshingSession: Boolean = false,
    val downloadState: DownloadState = DownloadState.NotDownloaded,
    val downloadProgress: Float = 0f,
    // PDF
    val currentPage: Int = 1,
    val isZoomed: Boolean = false,
    // Video / audio
    val isPlaying: Boolean = false,
    val positionFraction: Float = 0f,
    val playbackSpeed: Float = 1f,
    val captionsOn: Boolean = false,
)

enum class DownloadState { NotDownloaded, Downloading, Downloaded }

data class LessonQuizSession(
    val quiz: Quiz,
    val answeredCount: Int,
    val totalCount: Int,
    val correctCount: Int? = null,
    val result: QuizResult? = null,
    val isCompleted: Boolean = false,
) {
    val wrongCount: Int? get() = correctCount?.let { (totalCount - it).coerceAtLeast(0) }
}

/**
 * ST-03's completion-verification sheet — only checks Android can actually verify frontend-only.
 * [contentEngaged] reads the exact same page/position state the player surfaces already tracks;
 * [quizCompleted] is meaningless (and ignored via [allMet]) when the lesson has no [quizRequired].
 * Test-2SY's real backend checks more than this (time-on-page thresholds, AI chat interaction
 * counts) — this mock deliberately doesn't fabricate signals Android has no data for.
 */
data class LessonCompletionChecklist(
    val contentEngaged: Boolean,
    val quizRequired: Boolean,
    val quizCompleted: Boolean,
) {
    val allMet: Boolean get() = contentEngaged && (!quizRequired || quizCompleted)
}

class LessonPlayerViewModel(
    private val lessonId: String,
    private val learningRepository: LearningRepository,
    private val quizRepository: QuizRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(LessonPlayerUiState())
    val state: StateFlow<LessonPlayerUiState> = _state.asStateFlow()

    private var playbackJob: Job? = null
    private var downloadJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading, quizSession = null) }
        viewModelScope.launch {
            when (val result = learningRepository.getLesson(lessonId)) {
                is AppResult.Success -> {
                    val lesson = result.data
                    _state.update {
                        it.copy(
                            result = UiState.Content(lesson),
                            currentPage = lesson.initialPage(),
                            positionFraction = lesson.videoProgress.coerceIn(0f, 1f),
                        )
                    }
                    learningRepository.recordLessonStarted(lessonId, lesson.mediaTypes)
                    refreshQuizSession(result.data)
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun refreshSession() {
        val lesson = (_state.value.result as? UiState.Content)?.data ?: return
        viewModelScope.launch { refreshQuizSession(lesson) }
    }

    private suspend fun refreshQuizSession(lesson: LessonDetail) {
        val quizId = lesson.quizId
        if (quizId == null) {
            _state.update { it.copy(quizSession = null, isRefreshingSession = false) }
            return
        }

        _state.update { it.copy(isRefreshingSession = true) }
        when (val quizResult = quizRepository.getQuiz(quizId)) {
            is AppResult.Success -> {
                val quiz = quizResult.data
                val attempt = quizRepository.getAttempt(quizId)
                val completedResult = if (attempt.isCompleted) {
                    (quizRepository.getResult(quizId) as? AppResult.Success)?.data
                } else {
                    null
                }
                _state.update {
                    it.copy(
                        quizSession = LessonQuizSession(
                            quiz = quiz,
                            answeredCount = attempt.answers.size,
                            totalCount = quiz.questions.size,
                            correctCount = completedResult?.correctCount,
                            result = completedResult,
                            isCompleted = attempt.isCompleted,
                        ),
                        isRefreshingSession = false,
                    )
                }
            }
            is AppResult.Failure -> _state.update { it.copy(quizSession = null, isRefreshingSession = false) }
        }
    }

    fun startDownload() {
        if (_state.value.downloadState != DownloadState.NotDownloaded) return
        downloadJob = viewModelScope.launch {
            _state.update { it.copy(downloadState = DownloadState.Downloading, downloadProgress = 0f) }
            val steps = 10
            repeat(steps) { index ->
                kotlinx.coroutines.delay(180L)
                _state.update { it.copy(downloadProgress = (index + 1) / steps.toFloat()) }
            }
            _state.update { it.copy(downloadState = DownloadState.Downloaded) }
        }
    }

    fun previousPage() {
        _state.update { it.copy(currentPage = (it.currentPage - 1).coerceAtLeast(1)) }
        persistCurrentProgress(pdfOpened = true)
    }

    fun nextPage() {
        val pageCount = (_state.value.result as? UiState.Content)?.data?.pageCount ?: return
        _state.update { it.copy(currentPage = (it.currentPage + 1).coerceAtMost(pageCount.coerceAtLeast(1))) }
        persistCurrentProgress(pdfOpened = true)
    }

    fun toggleZoom() = _state.update { it.copy(isZoomed = !it.isZoomed) }

    fun togglePlayback() {
        if (_state.value.isPlaying) {
            playbackJob?.cancel()
            _state.update { it.copy(isPlaying = false) }
        } else {
            if (_state.value.positionFraction >= 1f) _state.update { it.copy(positionFraction = 0f) }
            _state.update { it.copy(isPlaying = true) }
            playbackJob = viewModelScope.launch {
                var tick = 0
                while (isActive && _state.value.positionFraction < 1f) {
                    kotlinx.coroutines.delay(400L)
                    val speed = _state.value.playbackSpeed
                    _state.update { it.copy(positionFraction = (it.positionFraction + 0.02f * speed).coerceAtMost(1f)) }
                    tick += 1
                    if (tick % 5 == 0 || _state.value.positionFraction >= 1f) {
                        persistCurrentProgress()
                    }
                }
                _state.update { it.copy(isPlaying = false) }
            }
        }
    }

    fun seekTo(fraction: Float) {
        _state.update { it.copy(positionFraction = fraction.coerceIn(0f, 1f)) }
        persistCurrentProgress()
    }

    fun cyclePlaybackSpeed() {
        val speeds = listOf(1f, 1.25f, 1.5f, 2f)
        val next = speeds.getOrElse(speeds.indexOf(_state.value.playbackSpeed) + 1) { speeds.first() }
        _state.update { it.copy(playbackSpeed = next) }
    }

    fun toggleCaptions() = _state.update { it.copy(captionsOn = !it.captionsOn) }

    /**
     * There is still no lesson-completion write endpoint in the Source Audit to call, so this
     * stays a local mutation — but it now also writes through [LearningRepository.markLessonCompleted],
     * the shared hot state Course Detail and Home both read, instead of only updating this
     * screen's own [UiState.Content] the way it used to.
     */
    fun markComplete() {
        val content = _state.value.result as? UiState.Content ?: return
        _state.update { it.copy(result = content.copy(data = content.data.copy(isCompleted = true))) }
        viewModelScope.launch { learningRepository.markLessonCompleted(lessonId) }
    }

    private fun persistCurrentProgress(pdfOpened: Boolean? = null) {
        val s = _state.value
        val lesson = (s.result as? UiState.Content)?.data ?: return
        val video = if (LessonMediaType.Video in lesson.mediaTypes) s.positionFraction else null
        val pdf = if (LessonMediaType.Pdf in lesson.mediaTypes && lesson.pageCount > 0) {
            (s.currentPage.toFloat() / lesson.pageCount.toFloat()).coerceIn(0f, 1f)
        } else {
            null
        }
        viewModelScope.launch {
            learningRepository.updateLessonProgress(
                lessonId = lessonId,
                videoProgress = video,
                pdfProgress = pdf,
                pdfOpened = pdfOpened,
            )
        }
    }

    /** Computed fresh on demand (not cached in [state]) — the quiz may have been completed on
     *  a different screen since this ViewModel was created, and [QuizRepository.getAttempt]
     *  is cheap/synchronous, so there is no reason to risk a stale cached answer here. */
    fun buildCompletionChecklist(): LessonCompletionChecklist {
        val s = _state.value
        val lesson = (s.result as? UiState.Content)?.data
        val contentEngaged = s.currentPage > 1 || s.positionFraction > 0f
        val quizId = lesson?.quizId
        val quizCompleted = quizId != null && quizRepository.getAttempt(quizId).isCompleted
        return LessonCompletionChecklist(
            contentEngaged = contentEngaged,
            quizRequired = quizId != null,
            quizCompleted = quizCompleted,
        )
    }

    override fun onCleared() {
        playbackJob?.cancel()
        downloadJob?.cancel()
    }
}

private fun LessonDetail.initialPage(): Int {
    if (pageCount <= 1) return 1
    val fromProgress = (pdfProgress.coerceIn(0f, 1f) * pageCount).toInt().coerceAtLeast(1)
    return fromProgress.coerceAtMost(pageCount)
}
