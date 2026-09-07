package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduColors
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-11 · Quiz Results — PDF page 17.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Attempt count, average, and pending-essay count are derived from the same
 * [TeacherQuizAttempt] list. Pending rows open the existing essay-grading destination.
 */
@Composable
fun TeacherQuizResultsScreen(
    quizId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    onOpenEditor: (() -> Unit)? = null,
    onOpenEssayGrade: ((studentId: String, questionId: String) -> Unit)? = null,
    viewModel: TeacherQuizResultsViewModel = koinViewModel(parameters = { parametersOf(quizId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    EduScaffold(
        title = stringResource(R.string.tc11_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherQuizResultsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherQuizResultsContent(
                data = data,
                onSelectAttempt = { result ->
                    val pendingQuestionId = result.pendingQuestionId
                    if (result.hasPendingEssay && pendingQuestionId != null && onOpenEssayGrade != null) {
                        onOpenEssayGrade(result.attempt.studentId, pendingQuestionId)
                    } else if (result.attempt.essayResponses.isNotEmpty() && onOpenEssayGrade != null) {
                        val questionId = result.attempt.essayResponses.keys.first()
                        onOpenEssayGrade(result.attempt.studentId, questionId)
                    } else {
                        viewModel.selectAttempt(result.attempt.studentId)
                    }
                },
                onOpenFirstEssay = {
                    val studentId = data.firstPendingStudentId
                    val questionId = data.firstPendingQuestionId
                    if (studentId != null && questionId != null) onOpenEssayGrade?.invoke(studentId, questionId)
                },
                onOpenEditor = onOpenEditor,
            )

            val selected = data.results.firstOrNull { it.attempt.studentId == state.selectedAttemptId }
            if (selected != null) {
                AttemptDetailDialog(result = selected, data = data, onDismiss = viewModel::dismissAttemptDetail)
            }
        }
    }
}

@Composable
private fun TeacherQuizResultsContent(
    data: TeacherQuizResultsScreenData,
    onSelectAttempt: (TeacherQuizAttemptResult) -> Unit,
    onOpenFirstEssay: () -> Unit,
    onOpenEditor: (() -> Unit)?,
) {
    val colors = EduTheme.colors
    val scoredCount = data.results.count { it.scorePercent != null }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (data.pendingStudentCount > 0) {
            item {
                Text(
                    text = stringResource(R.string.tc11_pending_students, numeral(data.pendingStudentCount)),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
            }
        }

        item {
            EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
                Row(
                    horizontalArrangement = Arrangement.SpaceEvenly,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    ResultStat(
                        value = numeral(data.attemptsCount),
                        label = stringResource(R.string.tc11_stat_attempts),
                    )
                    if (scoredCount > 0) {
                        ResultStat(
                            value = stringResource(R.string.progress_percent, data.classAveragePercent),
                            label = stringResource(R.string.tc11_stat_average),
                        )
                    }
                    if (data.pendingEssayCount > 0) {
                        ResultStat(
                            value = numeral(data.pendingEssayCount),
                            label = stringResource(R.string.tc11_stat_pending),
                            valueColor = colors.danger,
                        )
                    }
                }
            }
        }

        if (data.results.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc11_not_submitted),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                )
            }
        } else {
            items(data.results, key = { it.attempt.studentId }) { result ->
                StudentResultRow(
                    result = result,
                    onClick = { onSelectAttempt(result) },
                )
            }
        }

        if (data.pendingEssayCount > 0) {
            item {
                PrimaryButton(
                    text = stringResource(R.string.tc11_open_first_essay),
                    onClick = onOpenFirstEssay,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        }

        if (onOpenEditor != null) {
            item {
                GhostButton(
                    text = stringResource(R.string.tc10_edit_quiz),
                    onClick = onOpenEditor,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        }
    }
}

@Composable
private fun ResultStat(value: String, label: String, valueColor: Color = EduTheme.colors.textPrimary) {
    val colors = EduTheme.colors
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = valueColor)
        Text(label, style = EduTheme.typography.caption, color = colors.textSecondary)
    }
}

@Composable
private fun StudentResultRow(result: TeacherQuizAttemptResult, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val attempt = result.attempt
    val isNotSubmitted = attempt.status == TeacherQuizAttemptStatus.NotSubmitted
    val initial = attempt.studentName.trim().firstOrNull()?.toString().orEmpty()

    EduCard(
        onClick = onClick,
        borderColor = if (result.hasPendingEssay) colors.danger else colors.border,
        modifier = Modifier.padding(bottom = Spacing.xs),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarSm)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = initial,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = attempt.studentName,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = when {
                        isNotSubmitted -> stringResource(R.string.tc11_not_submitted)
                        result.hasPendingEssay -> stringResource(R.string.tc11_essay_pending)
                        else -> stringResource(R.string.progress_percent, result.scorePercent ?: result.percentage)
                    },
                    style = EduTheme.typography.caption,
                    color = when {
                        isNotSubmitted -> colors.textSecondary
                        result.hasPendingEssay -> colors.danger
                        else -> resultColor(result.scorePercent ?: result.percentage, colors)
                    },
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            when {
                result.hasPendingEssay -> StatusPill(
                    label = stringResource(R.string.tc11_grade_action),
                    contentColor = colors.danger,
                    containerColor = colors.danger.copy(alpha = 0.14f),
                )
                isNotSubmitted -> StatusPill(
                    label = stringResource(R.string.tc11_not_submitted),
                    contentColor = colors.warning,
                    containerColor = colors.warning.copy(alpha = 0.14f),
                )
            }
        }
    }
}

@Composable
private fun resultColor(percentage: Int, colors: EduColors): Color = when {
    percentage < 50 -> colors.danger
    percentage < 70 -> colors.warning
    else -> colors.success
}

@Composable
private fun AttemptDetailDialog(result: TeacherQuizAttemptResult, data: TeacherQuizResultsScreenData, onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(result.attempt.studentName, style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                if (result.scorePercent != null) {
                    Text(
                        text = stringResource(R.string.progress_percent, result.scorePercent),
                        style = EduTheme.typography.body,
                        color = colors.textPrimary,
                        modifier = Modifier.padding(bottom = Spacing.sm),
                    )
                }
                data.questionStats.forEach { stat ->
                    val essay = result.attempt.essayResponses[stat.question.question.id]
                    val wasCorrect = result.attempt.answers[stat.question.question.id]
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                        modifier = Modifier.padding(bottom = Spacing.xxs),
                    ) {
                        Text(
                            text = stringResource(R.string.tc11_question_number, numeral(stat.orderNumber)),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                            modifier = Modifier.width(56.dp),
                        )
                        Text(
                            text = when {
                                essay?.pending == true -> stringResource(R.string.tc11_essay_pending)
                                wasCorrect == true -> stringResource(R.string.tc11_answer_correct)
                                wasCorrect == false -> stringResource(R.string.tc11_answer_incorrect)
                                else -> stringResource(R.string.tc11_answer_unanswered)
                            },
                            style = EduTheme.typography.caption,
                            color = when {
                                essay?.pending == true -> colors.danger
                                wasCorrect == true -> colors.success
                                wasCorrect == false -> colors.danger
                                else -> colors.textSecondary
                            },
                        )
                    }
                }
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_done), onClick = onDismiss) },
        containerColor = colors.surface,
        titleContentColor = colors.textPrimary,
        textContentColor = colors.textSecondary,
    )
}

@Composable
private fun TeacherQuizResultsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
