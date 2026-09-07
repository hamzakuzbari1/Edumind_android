package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonChunk
import com.rork.eduspark.data.model.TeacherLessonEditorState
import com.rork.eduspark.data.repository.TeacherRepository
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
 * TC-07 · Lesson Editor.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherLessonEditorState] is read from, and every change written straight back to,
 * [TeacherRepository] — the same "no independent copy" discipline every other Teacher screen
 * this phase uses. Text edits (lesson content, a chunk's text) are local-only until their
 * section's explicit Save; Accept/Reject on a generated question or insight, and chunk
 * split/merge, persist immediately — they are already-decided discrete actions, not typing in
 * progress, so there is nothing to "un-save" if the teacher navigates away right after tapping
 * them.
 */
data class TeacherLessonEditorScreenData(
    val lesson: TeacherLesson,
    val courseTitle: String,
)

data class TeacherLessonEditorUiState(
    val result: UiState<TeacherLessonEditorScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val editor: TeacherLessonEditorState = TeacherLessonEditorState(lessonId = "", courseId = ""),
    val hasUnsavedContentEdit: Boolean = false,
    val hasUnsavedChunkEdits: Boolean = false,
    val isSavingContent: Boolean = false,
    val isSavingChunks: Boolean = false,
    val savingQuestionId: String? = null,
    val expandedQuestionId: String? = null,
    val isPublishing: Boolean = false,
    val showPublishBlocked: Boolean = false,
) {
    /** Mirrors the repository's own gate (see [TeacherRepository.submitLessonForPublish]'s doc comment) so TC-07 can show why Publish is disabled without a round trip. */
    val canPublish: Boolean
        get() = editor.extractedText.isNotBlank() &&
            editor.chunks.any { it.text.isNotBlank() } &&
            editor.generatedQuestions.all { it.reviewStatus != AiReviewStatus.Unreviewed } &&
            editor.insights.all { it.reviewStatus != AiReviewStatus.Unreviewed }
}

sealed interface TeacherLessonEditorEvent {
    data object OpenPreview : TeacherLessonEditorEvent
    data object Published : TeacherLessonEditorEvent
}

class TeacherLessonEditorViewModel(
    private val courseId: String,
    private val lessonId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherLessonEditorUiState())
    val state: StateFlow<TeacherLessonEditorUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherLessonEditorEvent>(Channel.BUFFERED)
    val events: Flow<TeacherLessonEditorEvent> = _events.receiveAsFlow()

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
            val lessonResult = teacherRepository.getLesson(courseId, lessonId)
            val courseResult = teacherRepository.getCourse(courseId)
            val editorResult = teacherRepository.getLessonEditorState(courseId, lessonId)
            if (lessonResult !is AppResult.Success || courseResult !is AppResult.Success || editorResult !is AppResult.Success) {
                val error = (lessonResult as? AppResult.Failure)?.error
                    ?: (courseResult as? AppResult.Failure)?.error
                    ?: (editorResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            _state.update {
                it.copy(
                    result = UiState.Content(TeacherLessonEditorScreenData(lessonResult.data, courseResult.data.title)),
                    editor = editorResult.data,
                    hasUnsavedContentEdit = false,
                    hasUnsavedChunkEdits = false,
                )
            }
        }
    }

    // ── 1. Lesson content ────────────────────────────────────────────────────────────────────
    fun updateExtractedText(text: String) =
        _state.update { it.copy(editor = it.editor.copy(extractedText = text), hasUnsavedContentEdit = true) }

    fun saveExtractedText() {
        if (_state.value.isSavingContent) return
        _state.update { it.copy(isSavingContent = true) }
        viewModelScope.launch {
            val result = teacherRepository.saveExtractedText(courseId, lessonId, _state.value.editor.extractedText)
            _state.update {
                if (result is AppResult.Success) it.copy(editor = result.data, hasUnsavedContentEdit = false, isSavingContent = false)
                else it.copy(isSavingContent = false)
            }
        }
    }

    // ── 2. Chunks ─────────────────────────────────────────────────────────────────────────────
    fun updateChunkText(chunkId: String, text: String) = _state.update {
        it.copy(
            editor = it.editor.copy(chunks = it.editor.chunks.map { c -> if (c.id == chunkId) c.copy(text = text) else c }),
            hasUnsavedChunkEdits = true,
        )
    }

    fun saveChunks() = persistChunks(_state.value.editor.chunks, markSaving = true)

    /** Splits [chunkId] at its nearest midpoint space — the deterministic, mobile-friendly "boundary" the spec calls for, never a text-selection tool. */
    fun splitChunk(chunkId: String) {
        val chunks = _state.value.editor.chunks
        val target = chunks.firstOrNull { it.id == chunkId } ?: return
        val text = target.text.trim()
        val midpoint = text.indexOf(' ', startIndex = text.length / 2).takeIf { it != -1 }
            ?: text.lastIndexOf(' ').takeIf { it != -1 }
            ?: return // nothing splittable — a single word chunk stays whole
        val first = text.substring(0, midpoint).trim()
        val second = text.substring(midpoint).trim()
        if (first.isEmpty() || second.isEmpty()) return

        val updated = chunks.flatMap { c ->
            if (c.id == chunkId) {
                listOf(
                    c.copy(text = first),
                    TeacherLessonChunk(id = "$chunkId-${System.currentTimeMillis()}", order = 0, text = second),
                )
            } else {
                listOf(c)
            }
        }
        persistChunks(updated, markSaving = false)
    }

    fun mergeChunkWithPrevious(chunkId: String) {
        val chunks = _state.value.editor.chunks
        val index = chunks.indexOfFirst { it.id == chunkId }
        if (index <= 0) return
        persistChunks(mergeAt(chunks, index - 1), markSaving = false)
    }

    fun mergeChunkWithNext(chunkId: String) {
        val chunks = _state.value.editor.chunks
        val index = chunks.indexOfFirst { it.id == chunkId }
        if (index == -1 || index >= chunks.lastIndex) return
        persistChunks(mergeAt(chunks, index), markSaving = false)
    }

    private fun mergeAt(chunks: List<TeacherLessonChunk>, firstIndex: Int): List<TeacherLessonChunk> {
        val first = chunks[firstIndex]
        val second = chunks[firstIndex + 1]
        val merged = first.copy(text = "${first.text.trim()} ${second.text.trim()}".trim())
        return chunks.toMutableList().apply {
            set(firstIndex, merged)
            removeAt(firstIndex + 1)
        }
    }

    private fun persistChunks(chunks: List<TeacherLessonChunk>, markSaving: Boolean) {
        if (markSaving) _state.update { it.copy(isSavingChunks = true) }
        viewModelScope.launch {
            val result = teacherRepository.saveChunks(courseId, lessonId, chunks)
            _state.update {
                if (result is AppResult.Success) it.copy(editor = result.data, hasUnsavedChunkEdits = false, isSavingChunks = false)
                else it.copy(isSavingChunks = false)
            }
        }
    }

    // ── 3. Generated quiz ─────────────────────────────────────────────────────────────────────
    fun toggleExpandedQuestion(questionId: String) = _state.update {
        it.copy(expandedQuestionId = if (it.expandedQuestionId == questionId) null else questionId)
    }

    fun updateQuestionDraft(questionId: String, transform: (QuizQuestion) -> QuizQuestion) = _state.update {
        it.copy(
            editor = it.editor.copy(
                generatedQuestions = it.editor.generatedQuestions.map { gq ->
                    if (gq.question.id == questionId) gq.copy(question = transform(gq.question)) else gq
                }
            )
        )
    }

    fun saveQuestionEdit(questionId: String) {
        val edited = _state.value.editor.generatedQuestions.firstOrNull { it.question.id == questionId }?.question ?: return
        if (_state.value.savingQuestionId != null) return
        _state.update { it.copy(savingQuestionId = questionId) }
        viewModelScope.launch {
            val result = teacherRepository.saveGeneratedQuestionEdit(courseId, lessonId, questionId, edited)
            _state.update {
                if (result is AppResult.Success) it.copy(editor = result.data, savingQuestionId = null, expandedQuestionId = null)
                else it.copy(savingQuestionId = null)
            }
        }
    }

    fun reviewQuestion(questionId: String, status: AiReviewStatus) {
        viewModelScope.launch {
            val result = teacherRepository.reviewGeneratedQuestion(courseId, lessonId, questionId, status)
            if (result is AppResult.Success) _state.update { it.copy(editor = result.data) }
        }
    }

    // ── 4. AI insights ────────────────────────────────────────────────────────────────────────
    fun reviewInsight(insightId: String, status: AiReviewStatus) {
        viewModelScope.launch {
            val result = teacherRepository.reviewInsight(courseId, lessonId, insightId, status)
            if (result is AppResult.Success) _state.update { it.copy(editor = result.data) }
        }
    }

    // ── 5. Preview / Publish ──────────────────────────────────────────────────────────────────
    fun openPreview() = viewModelScope.launch { _events.send(TeacherLessonEditorEvent.OpenPreview) }

    fun publish() {
        if (_state.value.isPublishing) return
        if (!_state.value.canPublish) {
            _state.update { it.copy(showPublishBlocked = true) }
            return
        }
        _state.update { it.copy(isPublishing = true) }
        viewModelScope.launch {
            when (teacherRepository.submitLessonForPublish(courseId, lessonId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isPublishing = false) }
                    _events.send(TeacherLessonEditorEvent.Published)
                }
                is AppResult.Failure -> _state.update { it.copy(isPublishing = false, showPublishBlocked = true) }
            }
        }
    }

    fun dismissPublishBlocked() = _state.update { it.copy(showPublishBlocked = false) }
}
