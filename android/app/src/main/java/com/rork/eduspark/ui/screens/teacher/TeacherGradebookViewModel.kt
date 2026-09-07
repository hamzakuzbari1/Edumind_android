package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.GradePublicationStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherGradeEntry
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-14 · Grades.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A gradebook per course — distinct from TC-11 (which stays quiz-specific analytics). Reached
 * from a TC-02 Dashboard link, the same "no natural tab fits, so link from Dashboard" pattern
 * TC-09/TC-10/TC-15 already use.
 *
 * [TeacherGradeRow.quizComponentPercent] is never teacher-entered or persisted — it is derived
 * fresh, every load, from the SAME [TeacherRepository.getQuizzes]/[TeacherRepository.getQuizAttempts]
 * data TC-11 reads (Published quizzes in this course only, points-weighted, averaged only over
 * quizzes the student actually submitted). Only [TeacherGradeEntry.courseworkScore] is
 * teacher-entered; [TeacherGradeRow.overallPercent] is a weighted blend of the two — see
 * [computeOverallPercent] — never a third, independently-typed number.
 */
data class TeacherGradeRow(
    val student: TeacherStudentSummary,
    val entry: TeacherGradeEntry,
    val quizComponentPercent: Int?,
    val overallPercent: Int?,
)

data class TeacherGradebookScreenData(
    val courses: List<TeacherCourseSummary>,
    val selectedCourseId: String,
    val rows: List<TeacherGradeRow>,
)

data class TeacherGradebookUiState(
    val result: UiState<TeacherGradebookScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val editingStudentId: String? = null,
    val scoreDraft: String = "",
    val commentDraft: String = "",
    val hasValidationError: Boolean = false,
    val showBulkPublishConfirm: Boolean = false,
)

/** Fixed, documented weights — 60% coursework / 40% quiz component when both exist; 100% of whichever one exists alone. */
private const val COURSEWORK_WEIGHT = 0.6f
private const val QUIZ_WEIGHT = 0.4f

fun computeOverallPercent(courseworkScore: Int?, quizComponentPercent: Int?): Int? = when {
    courseworkScore != null && quizComponentPercent != null ->
        (courseworkScore * COURSEWORK_WEIGHT + quizComponentPercent * QUIZ_WEIGHT).roundToInt()
    courseworkScore != null -> courseworkScore
    quizComponentPercent != null -> quizComponentPercent
    else -> null
}

class TeacherGradebookViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherGradebookUiState())
    val state: StateFlow<TeacherGradebookUiState> = _state.asStateFlow()

    private var selectedCourseId: String? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun selectCourse(courseId: String) {
        selectedCourseId = courseId
        load()
    }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val teacherId = authRepository.session.first()?.id
            if (teacherId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            val coursesResult = teacherRepository.getCourses(teacherId)
            val courses = (coursesResult as? AppResult.Success)?.data.orEmpty()
            if (courses.isEmpty()) {
                _state.update { it.copy(result = UiState.Failure((coursesResult as? AppResult.Failure)?.error ?: AppError.NotFound)) }
                return@launch
            }
            val courseId = selectedCourseId ?: courses.first().id
            selectedCourseId = courseId

            val studentsResult = teacherRepository.getStudents(teacherId)
            val students = (studentsResult as? AppResult.Success)?.data.orEmpty().filter { it.courseId == courseId }

            val quizzesResult = teacherRepository.getQuizzes(teacherId)
            val publishedQuizzesInCourse = (quizzesResult as? AppResult.Success)?.data.orEmpty()
                .filter { it.courseId == courseId && it.status == TeacherQuizStatus.Published }
            val attemptsByQuiz = publishedQuizzesInCourse.associate { quiz ->
                quiz.id to ((teacherRepository.getQuizAttempts(quiz.id) as? AppResult.Success)?.data.orEmpty())
            }

            val gradebookResult = teacherRepository.getGradebook(courseId)
            val entries = (gradebookResult as? AppResult.Success)?.data.orEmpty().associateBy { it.studentId }

            val rows = students.map { student ->
                val entry = entries[student.studentId] ?: TeacherGradeEntry(studentId = student.studentId, courseId = courseId)
                val submittedPercents = publishedQuizzesInCourse.mapNotNull { quiz ->
                    val attempt = attemptsByQuiz[quiz.id]?.firstOrNull { it.studentId == student.studentId }
                    if (attempt != null && attempt.status == TeacherQuizAttemptStatus.Completed && quiz.totalPoints > 0) {
                        val earned = quiz.questions.filter { attempt.answers[it.question.id] == true }.sumOf { it.points }
                        (earned * 100) / quiz.totalPoints
                    } else {
                        null
                    }
                }
                val quizComponentPercent = if (submittedPercents.isEmpty()) null else submittedPercents.sum() / submittedPercents.size
                TeacherGradeRow(
                    student = student,
                    entry = entry,
                    quizComponentPercent = quizComponentPercent,
                    overallPercent = computeOverallPercent(entry.courseworkScore, quizComponentPercent),
                )
            }

            _state.update {
                it.copy(result = UiState.Content(TeacherGradebookScreenData(courses = courses, selectedCourseId = courseId, rows = rows)))
            }
        }
    }

    fun openEditor(row: TeacherGradeRow) = _state.update {
        it.copy(
            editingStudentId = row.student.studentId,
            scoreDraft = row.entry.courseworkScore?.toString().orEmpty(),
            commentDraft = row.entry.comment,
            hasValidationError = false,
        )
    }

    fun dismissEditor() = _state.update { it.copy(editingStudentId = null, scoreDraft = "", commentDraft = "", hasValidationError = false) }

    fun updateScoreDraft(value: String) = _state.update { it.copy(scoreDraft = value, hasValidationError = false) }

    fun updateCommentDraft(value: String) = _state.update { it.copy(commentDraft = value) }

    /** Explicit validation — never silently clamps an out-of-range value. */
    fun saveEntry() {
        val current = _state.value
        val studentId = current.editingStudentId ?: return
        val courseId = selectedCourseId ?: return
        val trimmed = current.scoreDraft.trim()
        val score = if (trimmed.isEmpty()) null else trimmed.toIntOrNull()
        if (trimmed.isNotEmpty() && (score == null || score < 0 || score > 100)) {
            _state.update { it.copy(hasValidationError = true) }
            return
        }
        viewModelScope.launch {
            teacherRepository.saveGradeEntry(studentId, courseId, score, current.commentDraft.trim())
            dismissEditor()
            load()
        }
    }

    fun publishOne(studentId: String) {
        val courseId = selectedCourseId ?: return
        viewModelScope.launch {
            teacherRepository.publishGrade(studentId, courseId)
            load()
        }
    }

    fun requestBulkPublish() = _state.update { it.copy(showBulkPublishConfirm = true) }

    fun dismissBulkPublishConfirm() = _state.update { it.copy(showBulkPublishConfirm = false) }

    fun confirmBulkPublish() {
        val courseId = selectedCourseId ?: return
        _state.update { it.copy(showBulkPublishConfirm = false) }
        viewModelScope.launch {
            teacherRepository.publishCourseGrades(courseId)
            load()
        }
    }
}
