package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAttempt
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-11 · Quiz Results.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every summary number ([TeacherQuizResultsScreenData.classAveragePercent], the distribution
 * buckets, each [TeacherQuizQuestionStat.correctRate]) is computed once, here, straight from
 * [TeacherRepository.getQuizAttempts]'s own per-question `answers` — never a second,
 * independently-maintained figure that could silently disagree with the fixture data (the
 * spec's own "average says 72% while individual data says 61%" warning). Read-only throughout:
 * this ViewModel exposes no mutator over quiz content, only [selectAttempt]/[dismissAttemptDetail]
 * for the local, TC-11-only per-student breakdown dialog.
 */
data class TeacherQuizAttemptResult(
    val attempt: TeacherQuizAttempt,
    val scoreEarned: Int,
    val percentage: Int,
    val scorePercent: Int? = null,
    val hasPendingEssay: Boolean = false,
    val pendingQuestionId: String? = null,
)

data class TeacherQuizQuestionStat(
    val question: TeacherQuizQuestion,
    val orderNumber: Int,
    val correctCount: Int,
    val attemptCount: Int,
) {
    val correctRate: Float get() = if (attemptCount == 0) 0f else correctCount.toFloat() / attemptCount
}

data class TeacherQuizResultsScreenData(
    val quiz: TeacherQuiz,
    val results: List<TeacherQuizAttemptResult>,
    val questionStats: List<TeacherQuizQuestionStat>,
    val attemptsCount: Int,
    val submittedCount: Int,
    val classAveragePercent: Int,
    val highestScorePercent: Int,
    val distributionBuckets: List<Pair<IntRange, Int>>,
    val hardestQuestionId: String?,
    val pendingEssayCount: Int = 0,
    val pendingStudentCount: Int = 0,
    val firstPendingStudentId: String? = null,
    val firstPendingQuestionId: String? = null,
)

data class TeacherQuizResultsUiState(
    val result: UiState<TeacherQuizResultsScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val selectedAttemptId: String? = null,
)

class TeacherQuizResultsViewModel(
    private val quizId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherQuizResultsUiState())
    val state: StateFlow<TeacherQuizResultsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        if (_state.value.result !is UiState.Content) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            val quizResult = teacherRepository.getQuiz(quizId)
            val attemptsResult = teacherRepository.getQuizAttempts(quizId)
            if (quizResult !is AppResult.Success || attemptsResult !is AppResult.Success) {
                val error = (quizResult as? AppResult.Failure)?.error ?: (attemptsResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            val analytics = (teacherRepository.getQuizAnalytics(quizId) as? AppResult.Success)?.data
            _state.update {
                it.copy(
                    result = UiState.Content(
                        buildScreenData(
                            quiz = quizResult.data,
                            attempts = attemptsResult.data,
                            serverAverage = analytics?.averageScore,
                            serverHighest = analytics?.highestScore,
                        ),
                    ),
                )
            }
        }
    }

    fun selectAttempt(studentId: String) = _state.update { it.copy(selectedAttemptId = studentId) }
    fun dismissAttemptDetail() = _state.update { it.copy(selectedAttemptId = null) }

    private fun buildScreenData(
        quiz: TeacherQuiz,
        attempts: List<TeacherQuizAttempt>,
        serverAverage: Float? = null,
        serverHighest: Float? = null,
    ): TeacherQuizResultsScreenData {
        val submitted = attempts.filter { it.status == TeacherQuizAttemptStatus.Completed }
        val scored = submitted.filter { !it.hasPendingEssay }

        val results = attempts.map { attempt ->
            val scoreEarned = attempt.earnedPoints(quiz.questions)
            val scorePercent = attempt.scorePercent(quiz)
            TeacherQuizAttemptResult(
                attempt = attempt,
                scoreEarned = scoreEarned,
                percentage = scorePercent ?: 0,
                scorePercent = scorePercent,
                hasPendingEssay = attempt.hasPendingEssay,
                pendingQuestionId = attempt.firstPendingQuestionId(),
            )
        }.sortedWith(
            compareByDescending<TeacherQuizAttemptResult> { it.hasPendingEssay }
                .thenBy { it.attempt.status == TeacherQuizAttemptStatus.NotSubmitted }
                .thenByDescending { it.percentage },
        )

        val questionStats = quiz.questions.mapIndexed { index, question ->
            val correctCount = scored.count { it.answers[question.question.id] == true }
            TeacherQuizQuestionStat(question = question, orderNumber = index + 1, correctCount = correctCount, attemptCount = scored.size)
        }

        val submittedPercentages = results.mapNotNull { it.scorePercent }
        val localAverage = if (submittedPercentages.isEmpty()) 0 else submittedPercentages.sum() / submittedPercentages.size
        val localHighest = submittedPercentages.maxOrNull() ?: 0
        val classAverage = serverAverage?.toInt() ?: localAverage
        val highest = serverHighest?.toInt() ?: localHighest

        val buckets = listOf(0..49, 50..69, 70..84, 85..100).map { range ->
            range to submittedPercentages.count { it in range }
        }

        val hardest = questionStats.filter { it.attemptCount > 0 }.minByOrNull { it.correctRate }?.question?.question?.id
        val pendingStudentCount = results.count { it.hasPendingEssay }
        val firstPending = results.firstOrNull { it.hasPendingEssay }

        return TeacherQuizResultsScreenData(
            quiz = quiz,
            results = results,
            questionStats = questionStats,
            attemptsCount = attempts.size,
            submittedCount = submitted.size,
            classAveragePercent = classAverage,
            highestScorePercent = highest,
            distributionBuckets = buckets,
            hardestQuestionId = hardest,
            pendingEssayCount = attempts.sumOf { it.pendingEssayCount },
            pendingStudentCount = pendingStudentCount,
            firstPendingStudentId = firstPending?.attempt?.studentId,
            firstPendingQuestionId = firstPending?.pendingQuestionId,
        )
    }
}
