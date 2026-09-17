package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherActivityItem
import com.rork.eduspark.data.model.TeacherPrivateNote
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.data.model.TeacherStudentAttendance
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
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
 * TC-13 · Student Profile — Teacher View.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Header/status/flags reuse [TeacherStudentSummary] verbatim (the exact same row TC-12 already
 * loaded, re-fetched by id via [TeacherRepository.getStudent] — never recomputed). Quiz history
 * reuses TC-10/TC-11's own [TeacherQuiz]/[TeacherQuizAttempt] data: this ViewModel calls the
 * same [TeacherRepository.getQuizzes]/[TeacherRepository.getQuizAttempts] TC-10/TC-11 already
 * call, filters to this student's course and only Published quizzes (a student never sees a
 * Draft one), and scores each attempt the identical points-weighted way
 * [TeacherQuizResultsViewModel] does — never a second, possibly-disagreeing formula.
 */
data class TeacherStudentQuizHistoryEntry(
    val quiz: TeacherQuiz,
    val attempt: TeacherQuizAttempt?,
    /** Null exactly when [attempt] is null or [TeacherQuizAttemptStatus.NotSubmitted] — an honest "Not Submitted" state, never a fabricated zero. */
    val scorePercent: Int?,
)

data class TeacherStudentProfileScreenData(
    val student: TeacherStudentSummary,
    val completedWorkCount: Int,
    val outstandingWorkCount: Int,
    val quizHistory: List<TeacherStudentQuizHistoryEntry>,
    val attendance: TeacherStudentAttendance,
    val activity: List<TeacherActivityItem>,
    val privateNotes: List<TeacherPrivateNote>,
)

data class TeacherStudentProfileUiState(
    val result: UiState<TeacherStudentProfileScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val showNoteEditor: Boolean = false,
    val editingNoteId: String? = null,
    val noteDraftText: String = "",
    val showParentNoteDialog: Boolean = false,
    val parentNoteDraft: String = "",
    val parentNoteSent: Boolean = false,
    val showMessageDialog: Boolean = false,
    val messageDraft: String = "",
    val messageSent: Boolean = false,
    val showNoParentThread: Boolean = false,
)

sealed interface TeacherStudentProfileEvent {
    data class OpenParentChat(val threadId: String) : TeacherStudentProfileEvent
}

class TeacherStudentProfileViewModel(
    private val studentId: String,
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    private val messagingRepository: MessagingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherStudentProfileUiState())
    val state: StateFlow<TeacherStudentProfileUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherStudentProfileEvent>(Channel.BUFFERED)
    val events: Flow<TeacherStudentProfileEvent> = _events.receiveAsFlow()

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
            val studentResult = teacherRepository.getStudent(studentId)
            if (studentResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((studentResult as? AppResult.Failure)?.error ?: AppError.NotFound)) }
                return@launch
            }
            val student = studentResult.data
            val teacherId = authRepository.session.first()?.id.orEmpty()

            // getQuizzes is keyed by teacherId, not studentId/courseId — filtered locally to this
            // student's course, the same "load once, filter locally" shape TC-10/TC-11 already use.
            val quizzesResult = teacherRepository.getQuizzes(teacherId)
            val quizzes = (quizzesResult as? AppResult.Success)?.data.orEmpty()
                .filter { it.courseId == student.courseId && it.status == TeacherQuizStatus.Published }

            val quizHistory = quizzes.map { quiz ->
                val attempts = (teacherRepository.getQuizAttempts(quiz.id) as? AppResult.Success)?.data.orEmpty()
                val attempt = attempts.firstOrNull { it.studentId == studentId }
                val scorePercent = if (attempt != null && attempt.status == TeacherQuizAttemptStatus.Completed && quiz.totalPoints > 0) {
                    val earned = quiz.questions.filter { attempt.answers[it.question.id] == true }.sumOf { it.points }
                    (earned * 100) / quiz.totalPoints
                } else {
                    null
                }
                TeacherStudentQuizHistoryEntry(quiz = quiz, attempt = attempt, scorePercent = scorePercent)
            }
            val completedWorkCount = quizHistory.count { it.attempt?.status == TeacherQuizAttemptStatus.Completed }
            val outstandingWorkCount = quizHistory.count { it.attempt?.status != TeacherQuizAttemptStatus.Completed }

            val attendance = (teacherRepository.getStudentAttendance(studentId) as? AppResult.Success)?.data
                ?: TeacherStudentAttendance(studentId = studentId, records = emptyList())
            val activity = (teacherRepository.getStudentActivity(studentId) as? AppResult.Success)?.data.orEmpty()
            val notes = (teacherRepository.getPrivateNotes(studentId) as? AppResult.Success)?.data.orEmpty()

            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherStudentProfileScreenData(
                            student = student,
                            completedWorkCount = completedWorkCount,
                            outstandingWorkCount = outstandingWorkCount,
                            quizHistory = quizHistory,
                            attendance = attendance,
                            activity = activity,
                            privateNotes = notes,
                        )
                    )
                )
            }
        }
    }

    // ── Private notes ────────────────────────────────────────────────────────────────────────

    fun openAddNote() = _state.update { it.copy(showNoteEditor = true, editingNoteId = null, noteDraftText = "") }

    fun openEditNote(note: TeacherPrivateNote) = _state.update { it.copy(showNoteEditor = true, editingNoteId = note.id, noteDraftText = note.text) }

    fun updateNoteDraft(text: String) = _state.update { it.copy(noteDraftText = text) }

    fun dismissNoteEditor() = _state.update { it.copy(showNoteEditor = false, editingNoteId = null, noteDraftText = "") }

    fun saveNote() {
        val draft = _state.value.noteDraftText.trim()
        if (draft.isBlank()) return
        val editingId = _state.value.editingNoteId
        viewModelScope.launch {
            if (editingId != null) {
                teacherRepository.updatePrivateNote(editingId, draft)
            } else {
                teacherRepository.addPrivateNote(studentId, draft)
            }
            val notes = (teacherRepository.getPrivateNotes(studentId) as? AppResult.Success)?.data.orEmpty()
            replaceNotes(notes)
            _state.update { it.copy(showNoteEditor = false, editingNoteId = null, noteDraftText = "") }
        }
    }

    fun deleteNote(noteId: String) {
        viewModelScope.launch {
            teacherRepository.deletePrivateNote(noteId)
            val notes = (teacherRepository.getPrivateNotes(studentId) as? AppResult.Success)?.data.orEmpty()
            replaceNotes(notes)
        }
    }

    private fun replaceNotes(notes: List<TeacherPrivateNote>) {
        val current = _state.value.result
        if (current is UiState.Content) {
            _state.update { it.copy(result = UiState.Content(current.data.copy(privateNotes = notes))) }
        }
    }

    // ── Note to parent — a distinct mock action from private notes ──────────────────────────────

    fun openParentNoteDialog() = _state.update { it.copy(showParentNoteDialog = true, parentNoteDraft = "", parentNoteSent = false) }

    fun updateParentNoteDraft(text: String) = _state.update { it.copy(parentNoteDraft = text) }

    fun dismissParentNoteDialog() = _state.update { it.copy(showParentNoteDialog = false, parentNoteDraft = "", parentNoteSent = false) }

    fun sendParentNote() {
        val message = _state.value.parentNoteDraft.trim()
        if (message.isBlank()) return
        viewModelScope.launch {
            teacherRepository.sendParentNote(studentId, message)
            _state.update { it.copy(parentNoteSent = true) }
        }
    }

    // ── Teacher → student message — an honest mock composer, never a real chat thread ──────────

    fun openMessageDialog() = _state.update { it.copy(showMessageDialog = true, messageDraft = "", messageSent = false) }

    fun updateMessageDraft(text: String) = _state.update { it.copy(messageDraft = text) }

    fun dismissMessageDialog() = _state.update { it.copy(showMessageDialog = false, messageDraft = "", messageSent = false) }

    fun sendStudentMessage() {
        val message = _state.value.messageDraft.trim()
        if (message.isBlank()) return
        viewModelScope.launch {
            val session = authRepository.session.first() ?: return@launch
            val viewerId = session.id
            val threadResult = messagingRepository.openOrCreateThread(
                viewerId = viewerId,
                viewerRole = com.rork.eduspark.data.model.MessageParticipantRole.Teacher,
                contactId = studentId,
            )
            val thread = (threadResult as? AppResult.Success)?.data ?: return@launch
            val sent = messagingRepository.sendMessage(thread.id, viewerId, message)
            if (sent is AppResult.Success) {
                _state.update { it.copy(messageSent = true) }
            }
        }
    }

    fun onMessageParent() {
        viewModelScope.launch {
            val teacherId = authRepository.session.first()?.id ?: return@launch
            when (val result = messagingRepository.getParentThreadForStudent(teacherId, studentId)) {
                is AppResult.Success -> _events.send(TeacherStudentProfileEvent.OpenParentChat(result.data.id))
                is AppResult.Failure -> _state.update { it.copy(showNoParentThread = true) }
            }
        }
    }

    fun dismissNoParentThread() = _state.update { it.copy(showNoParentThread = false) }
}
