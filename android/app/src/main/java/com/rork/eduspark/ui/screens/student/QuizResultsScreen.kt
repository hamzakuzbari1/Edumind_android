package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.matchesQuizAnswer
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.progress.ProgressRing
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduGroupedSurface
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-07 · Quiz Results.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Explanations carry [AiMarker] only when [QuizResult.quiz]'s origin is
 * [QuizOrigin.AiLesson] — a manual quiz's teacher-authored explanations are never marked,
 * matching the same trust contract [QuizRunnerScreen] already applies.
 */
@Composable
fun QuizResultsScreen(
    quizId: String,
    onBack: () -> Unit,
    onPracticeAgain: (remedialQuizId: String) -> Unit,
    onAskTutorAboutMistake: (lessonId: String, prompt: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: QuizResultsViewModel = koinViewModel(parameters = { parametersOf(quizId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.remedialQuizId) {
        val remedialId = state.remedialQuizId
        if (remedialId != null) onPracticeAgain(remedialId)
    }

    EduScaffold(
        title = stringResource(R.string.st07_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { result ->
            ResultsContent(
                result = result,
                showOnlyWrong = state.showOnlyWrong,
                isBuildingRemedial = state.isBuildingRemedial,
                onBack = onBack,
                onToggleShowOnlyWrong = viewModel::toggleShowOnlyWrong,
                onPracticeAgain = viewModel::startRemedial,
                onAskTutorAboutMistake = { prompt -> onAskTutorAboutMistake(result.quiz.lessonId, prompt) },
            )
        }
    }
}

@Composable
private fun ResultsContent(
    result: QuizResult,
    showOnlyWrong: Boolean,
    isBuildingRemedial: Boolean,
    onBack: () -> Unit,
    onToggleShowOnlyWrong: () -> Unit,
    onPracticeAgain: () -> Unit,
    onAskTutorAboutMistake: (prompt: String) -> Unit,
) {
    val colors = EduTheme.colors
    val quiz = result.quiz
    val hasWrong = result.correctCount < result.totalCount
    var detailsOpen by rememberSaveable { mutableStateOf(false) }
    val questions = if (showOnlyWrong) {
        quiz.questions.filter { q -> !result.attempt.answers[q.id]?.response.matchesQuizAnswer(q.correctAnswer) }
    } else {
        quiz.questions
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ResultHeroCard(result = result)
        }

        item {
            WeakestTopicCard(result = result)
        }

        item {
            ResultFollowUpCard(
                hasWrong = hasWrong,
                showOnlyWrong = showOnlyWrong,
                isBuildingRemedial = isBuildingRemedial,
                onBack = onBack,
                onToggleShowOnlyWrong = {
                    detailsOpen = true
                    onToggleShowOnlyWrong()
                },
                onPracticeAgain = onPracticeAgain,
            )
        }

        if (!detailsOpen) {
            // Mistake review stays reachable from the follow-up actions without filling the main result.
        } else if (questions.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.st07_no_wrong_title),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(vertical = Spacing.md),
                )
            }
        } else {
            item {
                Text(
                    text = stringResource(if (showOnlyWrong) R.string.st07_review_wrong else R.string.st07_show_all),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
            items(questions, key = { it.id }) { question ->
                BreakdownRow(
                    index = quiz.questions.indexOf(question),
                    question = question,
                    response = result.attempt.answers[question.id]?.response,
                    origin = quiz.origin,
                    onAskTutorAboutMistake = onAskTutorAboutMistake,
                )
            }
        }
    }
}

@Composable
private fun WeakestTopicCard(result: QuizResult) {
    val wrongQuestion = result.quiz.questions.firstOrNull { question ->
        !result.attempt.answers[question.id]?.response.matchesQuizAnswer(question.correctAnswer)
    }
    EduCard {
        Text(
            text = stringResource(R.string.st07_weakest_topic),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textSecondary,
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.md),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        ) {
            SubjectVisual(
                courseId = result.quiz.lessonId.substringBefore("-"),
                compact = true,
                modifier = Modifier.weight(0.78f),
            )
            Text(
                text = wrongQuestion?.prompt ?: result.quiz.lessonTitle,
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
                maxLines = 2,
                modifier = Modifier.weight(1f),
            )
        }
        EduGroupedSurface(
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            AiMarker()
            Text(
                text = stringResource(R.string.st07_edumind_recommendation),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.aiAccent,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            Text(
                text = stringResource(R.string.st07_review_minutes),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
private fun ResultHeroCard(result: QuizResult) {
    val colors = EduTheme.colors
    val quiz = result.quiz
    EduCard(borderColor = colors.success.copy(alpha = 0.32f)) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            if (quiz.origin == QuizOrigin.TeacherManual) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                    modifier = Modifier.padding(bottom = Spacing.xs),
                ) {
                    Icon(Icons.Filled.School, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
                    Text(
                        text = stringResource(R.string.st09_teacher_authored, quiz.teacherName),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            } else {
                AiMarker(modifier = Modifier.padding(bottom = Spacing.xs))
            }
            Text(
                text = quiz.lessonTitle,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
            )
            if (result.hasPendingEssay) {
                Text(
                    text = stringResource(R.string.st07_pending_essay),
                    style = EduTheme.typography.body,
                    color = colors.warning,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
            ProgressRing(
                progress = when {
                    result.scorePercent != null -> (result.scorePercent.coerceIn(0, 100)) / 100f
                    result.totalCount == 0 -> 0f
                    else -> result.correctCount / result.totalCount.toFloat()
                },
                size = Sizing.heroBadge,
                tint = colors.success,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = if (result.scorePercent != null) {
                    stringResource(R.string.st07_score_percent, numeral(result.scorePercent))
                } else {
                    stringResource(R.string.st07_correct_count, numeral(result.correctCount), numeral(result.totalCount))
                },
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            ResultXpChip(xp = result.xpEarned, modifier = Modifier.padding(top = Spacing.xs))

            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            ) {
                ResultStat(
                    value = numeral(result.correctCount),
                    label = stringResource(R.string.st07_stat_correct),
                    valueColor = colors.success,
                    modifier = Modifier.weight(1f),
                )
                ResultStat(
                    value = numeral(result.totalCount - result.correctCount),
                    label = stringResource(R.string.st07_stat_wrong),
                    valueColor = colors.danger,
                    modifier = Modifier.weight(1f),
                )
                ResultStat(
                    value = numeral(formatMinutesSeconds(result.timeTakenSeconds)),
                    label = stringResource(R.string.st07_stat_time),
                    valueColor = colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun ResultFollowUpCard(
    hasWrong: Boolean,
    showOnlyWrong: Boolean,
    isBuildingRemedial: Boolean,
    onBack: () -> Unit,
    onToggleShowOnlyWrong: () -> Unit,
    onPracticeAgain: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(borderColor = if (hasWrong) colors.danger.copy(alpha = 0.28f) else colors.success.copy(alpha = 0.28f)) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(
                imageVector = if (hasWrong) Icons.Filled.Lightbulb else Icons.Filled.CheckCircle,
                contentDescription = null,
                tint = if (hasWrong) colors.highlight else colors.success,
                modifier = Modifier.size(Sizing.iconLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(if (hasWrong) R.string.st07_review_wrong else R.string.st07_no_wrong_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(if (hasWrong) R.string.st07_follow_up_mistakes else R.string.st07_follow_up_mastery),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        ) {
            GhostButton(
                text = stringResource(if (showOnlyWrong) R.string.st07_show_all else R.string.st07_review_wrong),
                onClick = onToggleShowOnlyWrong,
                modifier = Modifier.weight(1f),
            )
            if (hasWrong) {
                PrimaryButton(
                    text = stringResource(R.string.st07_practice_again),
                    onClick = onPracticeAgain,
                    isLoading = isBuildingRemedial,
                    modifier = Modifier.weight(1f),
                )
            } else {
                SecondaryButton(
                    text = stringResource(R.string.st08_back_to_lesson),
                    onClick = onBack,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun BreakdownRow(
    index: Int,
    question: QuizQuestion,
    response: String?,
    origin: QuizOrigin,
    onAskTutorAboutMistake: (prompt: String) -> Unit,
) {
    val colors = EduTheme.colors
    val isCorrect = response.matchesQuizAnswer(question.correctAnswer)
    val yourAnswerText = question.options.find { it.id == response }?.text ?: response.orEmpty()
    val correctAnswerText = question.options.find { it.id == question.correctAnswer }?.text ?: question.correctAnswer

    EduCard(borderColor = if (isCorrect) colors.success else colors.danger) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
            Icon(
                imageVector = if (isCorrect) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
                contentDescription = stringResource(if (isCorrect) R.string.st06_correct else R.string.st06_incorrect),
                tint = if (isCorrect) colors.success else colors.danger,
                modifier = Modifier.size(Sizing.iconSm),
            )
            Text(
                text = stringResource(R.string.st07_question_number, numeral(index + 1)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
        Text(
            text = question.prompt,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.xs),
        )
        Text(
            text = stringResource(R.string.st07_your_answer, yourAnswerText.ifBlank { "—" }),
            style = EduTheme.typography.caption,
            color = if (isCorrect) colors.success else colors.danger,
        )
        if (!isCorrect) {
            Text(
                text = stringResource(R.string.st07_correct_answer, correctAnswerText),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            if (origin == QuizOrigin.AiLesson) {
                AiMarker()
            }
            Text(text = question.explanation, style = EduTheme.typography.caption, color = colors.textSecondary)
        }
        if (!isCorrect) {
            val mistakePrompt = stringResource(
                R.string.st07_ask_tutor_mistake_prompt,
                question.prompt,
                yourAnswerText.ifBlank { "—" },
                correctAnswerText,
            )
            GhostButton(
                text = stringResource(R.string.st07_ask_tutor_about_mistake),
                onClick = { onAskTutorAboutMistake(mistakePrompt) },
                leadingIcon = Icons.Filled.School,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

/**
 * Approved-design XP treatment for ST-07 specifically — flame icon + "+N XP" label, on the
 * same highlight pill/border tokens the shared [XpChip][com.rork.eduspark.ui.components.progress.XpChip]
 * already uses. A local composition rather than changing the shared component's API/visible
 * text, which every other XpChip caller (e.g. Achievements) still relies on as a bare number.
 */
@Composable
private fun ResultXpChip(xp: Int, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val label = stringResource(R.string.st07_xp_earned, numeral(xp))
    val shape = RoundedCornerShape(Radius.pill)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .background(colors.highlight.copy(alpha = 0.16f), shape)
            .border(Sizing.hairline, colors.highlight, shape)
            .padding(horizontal = Spacing.sm, vertical = Spacing.xxs),
    ) {
        Icon(Icons.Filled.LocalFireDepartment, contentDescription = null, tint = colors.highlight, modifier = Modifier.size(Sizing.iconSm))
        Text(text = label, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.highlight)
    }
}

/** One cell of the approved design's 3-stat row (correct / wrong / time taken). */
@Composable
private fun ResultStat(value: String, label: String, valueColor: Color, modifier: Modifier = Modifier) {
    EduCard(modifier = modifier, contentPadding = PaddingValues(Spacing.sm)) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(text = value, style = EduTheme.typography.mono.copy(fontWeight = FontWeight.SemiBold), color = valueColor)
            Text(
                text = label,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

/** mm:ss formatting for [QuizResult.timeTakenSeconds], same shape ST-06's timer pill uses. */
private fun formatMinutesSeconds(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%d:%02d".format(minutes, seconds)
}
