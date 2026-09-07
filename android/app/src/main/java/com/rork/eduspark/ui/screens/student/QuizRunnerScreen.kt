package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizOrigin
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.matchesQuizAnswer
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.progress.HorizontalSpine
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-06 · Quiz Runner / ST-08 · Remedial Quiz / ST-09 · Manual Quiz Runner — one shell.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [Quiz.origin] and [Quiz.isRemedial] are the only two switches this screen branches on —
 * there is no second quiz engine for the remedial or manual cases. AI marking follows
 * origin exactly: [AiMarker] renders only for [QuizOrigin.AiLesson]; a manual quiz gets a
 * plain teacher-attribution row and nothing else, matching the trust contract in
 * [com.rork.eduspark.ui.components.ai.AiComponents.kt] — a human wrote it, so it stays
 * unmarked.
 */
@Composable
fun QuizRunnerScreen(
    quizId: String,
    onBack: () -> Unit,
    onSubmitted: (quizId: String) -> Unit,
    onRemedialBackToResults: () -> Unit,
    onRemedialBackToLesson: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: QuizRunnerViewModel = koinViewModel(parameters = { parametersOf(quizId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val quiz = (state.result as? UiState.Content)?.data

    LaunchedEffect(state.submittedResult, quiz?.isRemedial) {
        val result = state.submittedResult
        if (result != null && quiz?.isRemedial == false) {
            onSubmitted(quizId)
        }
    }

    EduScaffold(
        title = quiz?.title.orEmpty(),
        onBack = onBack,
        // Approved design (QuizRunner.dc.html): the timer sits in the top bar, not buried
        // in the content header — a glance at the bar is enough, no scrolling required.
        actions = {
            state.timeRemainingSeconds?.let { seconds -> TimerPill(secondsRemaining = seconds) }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { loadedQuiz ->
            val completedResult = state.submittedResult
            if (loadedQuiz.isRemedial && completedResult != null) {
                RemedialCompletion(
                    quiz = loadedQuiz,
                    correctCount = completedResult.correctCount,
                    totalCount = completedResult.totalCount,
                    onBackToResults = onRemedialBackToResults,
                    onBackToLesson = { onRemedialBackToLesson(loadedQuiz.lessonId) },
                    onRetry = viewModel::retryAttempt,
                )
            } else {
                QuizRunnerContent(quiz = loadedQuiz, state = state, viewModel = viewModel)
            }
        }
    }
}

@Composable
private fun QuizRunnerContent(quiz: Quiz, state: QuizRunnerUiState, viewModel: QuizRunnerViewModel) {
    val question = quiz.questions.getOrNull(state.currentIndex) ?: return
    val isLastQuestion = state.currentIndex == quiz.questions.lastIndex
    val isRevealed = state.revealedFeedbackFor == question.id

    Column(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
        ) {
            QuizHeader(quiz = quiz, state = state)
            QuizQuestionCard(
                quiz = quiz,
                question = question,
                questionIndex = state.currentIndex,
                questionTotal = quiz.questions.size,
                state = state,
                isRevealed = isRevealed,
                onRevealHint = viewModel::revealHint,
                onSelect = viewModel::selectOption,
                onTypeChange = viewModel::updateDraft,
            )
        }

        QuizBottomBar(
            canGoPrevious = state.currentIndex > 0,
            isRevealed = isRevealed,
            isLastQuestion = isLastQuestion,
            isSubmitting = state.isSubmitting,
            onPrevious = viewModel::previous,
            onNext = viewModel::next,
            onContinue = viewModel::continueAfterFeedback,
        )
    }
}

@Composable
private fun QuizHeader(quiz: Quiz, state: QuizRunnerUiState) {
    val colors = EduTheme.colors
    EduCard(
        borderColor = if (quiz.isRemedial) colors.primary.copy(alpha = 0.28f) else colors.border,
        modifier = Modifier.padding(bottom = Spacing.sm),
    ) {
        when {
            quiz.isRemedial -> Text(
                text = stringResource(R.string.st08_practice_banner),
                style = EduTheme.typography.caption,
                color = colors.primary,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
            quiz.origin == QuizOrigin.AiLesson -> AiMarker(modifier = Modifier.padding(bottom = Spacing.xs))
            quiz.origin == QuizOrigin.TeacherManual -> Row(
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
        }

        Text(
            text = quiz.lessonTitle,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
        )
        Text(
            text = quiz.title,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
        )

        HorizontalSpine(
            total = quiz.questions.size,
            currentIndex = state.currentIndex,
            contentDescription = stringResource(R.string.st06_question_of, numeral(state.currentIndex + 1), numeral(quiz.questions.size)),
        )
    }
}

@Composable
private fun QuizQuestionCard(
    quiz: Quiz,
    question: QuizQuestion,
    questionIndex: Int,
    questionTotal: Int,
    state: QuizRunnerUiState,
    isRevealed: Boolean,
    onRevealHint: () -> Unit,
    onSelect: (String) -> Unit,
    onTypeChange: (String) -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        borderColor = if (isRevealed) {
            if (state.draftResponse.matchesQuizAnswer(question.correctAnswer)) colors.success else colors.danger
        } else {
            colors.primary.copy(alpha = 0.22f)
        },
    ) {
        SubjectVisual(
            courseId = quiz.lessonId.substringBefore("-"),
            compact = true,
            fillWidth = false,
            modifier = Modifier
                .padding(bottom = Spacing.md)
                .size(96.dp)
                .align(Alignment.CenterHorizontally),
        )
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(40.dp)
                    .background(colors.primary, RoundedCornerShape(Radius.sm)),
            ) {
                Text(
                    text = numeral(questionIndex + 1),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st06_question_of, numeral(questionIndex + 1), numeral(questionTotal)),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.primary,
                )
                Text(
                    text = question.prompt,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        if (quiz.isRemedial && question.hint != null) {
            HintRow(hint = question.hint, revealed = state.hintRevealed, onReveal = onRevealHint)
        }

        AnswerArea(
            question = question,
            draftResponse = state.draftResponse,
            isRevealed = isRevealed,
            showValidation = state.showValidation,
            onSelect = onSelect,
            onTypeChange = onTypeChange,
            modifier = Modifier.padding(top = Spacing.md),
        )

        if (state.showValidation) {
            Text(
                text = stringResource(R.string.st06_validation_required),
                style = EduTheme.typography.caption,
                color = colors.danger,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        if (isRevealed) {
            FeedbackExplanation(quiz = quiz, question = question, response = state.draftResponse)
        }

        if (state.submitError != null) {
            Text(
                text = stringResource(R.string.st06_submit_error),
                style = EduTheme.typography.caption,
                color = colors.danger,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
    }
}

/** Approved design's `.timerpill` — top-bar chip, not content-header text. */
@Composable
private fun TimerPill(secondsRemaining: Int) {
    val colors = EduTheme.colors
    val isLow = secondsRemaining <= 30
    val minutes = secondsRemaining / 60
    val seconds = secondsRemaining % 60
    val timeLabel = "%d:%02d".format(minutes, seconds)
    val tint = if (isLow) colors.danger else colors.textSecondary

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier
            .background(if (isLow) colors.danger.copy(alpha = 0.1f) else colors.neutralAlpha100, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.sm, vertical = Spacing.xxs),
    ) {
        Icon(Icons.Filled.Timer, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.iconSm))
        Text(text = numeral(timeLabel), style = EduTheme.typography.mono.copy(fontWeight = FontWeight.Bold), color = tint)
    }
}

@Composable
private fun HintRow(hint: String, revealed: Boolean, onReveal: () -> Unit) {
    val colors = EduTheme.colors
    if (revealed) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.background, RoundedCornerShape(Radius.sm))
                .padding(Spacing.card)
                .padding(bottom = Spacing.md),
        ) {
            Icon(Icons.Filled.Lightbulb, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconSm))
            Text(text = hint, style = EduTheme.typography.caption, color = colors.textPrimary)
        }
    } else {
        GhostButton(
            text = stringResource(R.string.st08_show_hint),
            onClick = onReveal,
            leadingIcon = Icons.Filled.Lightbulb,
            modifier = Modifier.padding(bottom = Spacing.sm),
        )
    }
}

@Composable
private fun AnswerArea(
    question: QuizQuestion,
    draftResponse: String,
    isRevealed: Boolean,
    showValidation: Boolean,
    onSelect: (String) -> Unit,
    onTypeChange: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    when (question.type) {
        QuestionType.MultipleChoice, QuestionType.TrueFalse -> Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = modifier,
        ) {
            question.options.forEachIndexed { index, option ->
                OptionRow(
                    option = option,
                    optionIndex = index,
                    isSelected = option.id == draftResponse,
                    isRevealed = isRevealed,
                    isCorrectOption = option.id == question.correctAnswer,
                    onClick = { onSelect(option.id) },
                )
            }
        }

        QuestionType.GapFill -> EduTextField(
            value = draftResponse,
            onValueChange = onTypeChange,
            label = stringResource(R.string.st06_answer_placeholder_gap),
            enabled = !isRevealed,
            errorText = if (showValidation) " " else null,
            showErrorText = false,
            keyboardType = KeyboardType.Text,
            imeAction = ImeAction.Done,
            modifier = modifier,
        )

        QuestionType.ShortAnswer -> EduTextField(
            value = draftResponse,
            onValueChange = onTypeChange,
            label = stringResource(R.string.st06_answer_placeholder_short),
            enabled = !isRevealed,
            errorText = if (showValidation) " " else null,
            showErrorText = false,
            singleLine = false,
            keyboardType = KeyboardType.Text,
            imeAction = ImeAction.Default,
            modifier = modifier,
        )
    }
}

@Composable
private fun OptionRow(
    option: QuizOption,
    optionIndex: Int,
    isSelected: Boolean,
    isRevealed: Boolean,
    isCorrectOption: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val showAsCorrect = isRevealed && isCorrectOption
    val showAsWrongPick = isRevealed && isSelected && !isCorrectOption

    val container = when {
        showAsCorrect -> colors.success.copy(alpha = 0.12f)
        showAsWrongPick -> colors.danger.copy(alpha = 0.1f)
        isSelected -> colors.primaryContainer
        else -> colors.surface
    }
    val border = when {
        showAsCorrect -> colors.success
        showAsWrongPick -> colors.danger
        isSelected -> colors.primary
        else -> colors.border
    }
    val shape = RoundedCornerShape(Radius.sm)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(container, shape)
            .border(Sizing.hairline, border, shape)
            .then(if (isRevealed) Modifier else Modifier.eduClickable(onClickLabel = option.text, onClick = onClick))
            .padding(horizontal = Spacing.card, vertical = Spacing.sm),
    ) {
        OptionLetter(index = optionIndex, selected = isSelected, tint = border)
        Text(
            text = option.text,
            style = EduTheme.typography.bodyLg,
            color = colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
        when {
            showAsCorrect -> Icon(Icons.Filled.CheckCircle, contentDescription = stringResource(R.string.st06_correct), tint = colors.success, modifier = Modifier.size(Sizing.icon))
            showAsWrongPick -> Icon(Icons.Filled.Cancel, contentDescription = stringResource(R.string.st06_incorrect), tint = colors.danger, modifier = Modifier.size(Sizing.icon))
        }
    }
}

/** Test-2SY's option letter block translated to Compose. */
@Composable
private fun OptionLetter(index: Int, selected: Boolean, tint: Color) {
    val colors = EduTheme.colors
    val letters = listOf("A", "B", "C", "D", "E", "F")
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(32.dp)
            .background(if (selected) tint else colors.primaryContainer, RoundedCornerShape(Radius.sm))
            .border(Sizing.hairline, if (selected) tint else colors.border, RoundedCornerShape(Radius.sm)),
    ) {
        Text(
            text = letters.getOrElse(index) { numeral(index + 1) },
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
            color = if (selected) colors.surface else colors.primary,
        )
    }
}

@Composable
private fun FeedbackExplanation(quiz: Quiz, question: QuizQuestion, response: String) {
    val colors = EduTheme.colors
    val isCorrect = response.matchesQuizAnswer(question.correctAnswer)
    val isFreeText = question.type == QuestionType.GapFill || question.type == QuestionType.ShortAnswer

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.sm)
            .background(if (isCorrect) colors.success.copy(alpha = 0.1f) else colors.danger.copy(alpha = 0.1f), RoundedCornerShape(Radius.sm))
            .padding(Spacing.card),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
            Icon(
                imageVector = if (isCorrect) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
                contentDescription = null,
                tint = if (isCorrect) colors.success else colors.danger,
                modifier = Modifier.size(Sizing.iconSm),
            )
            Text(
                text = stringResource(if (isCorrect) R.string.st06_correct else R.string.st06_incorrect),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = if (isCorrect) colors.success else colors.danger,
            )
        }
        if (isFreeText && !isCorrect) {
            Text(
                text = stringResource(R.string.st07_correct_answer, question.correctAnswer),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            if (quiz.origin == QuizOrigin.AiLesson) {
                AiMarker()
            }
            Text(text = question.explanation, style = EduTheme.typography.caption, color = colors.textSecondary)
        }
    }
}

@Composable
private fun QuizBottomBar(
    canGoPrevious: Boolean,
    isRevealed: Boolean,
    isLastQuestion: Boolean,
    isSubmitting: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onContinue: () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        if (canGoPrevious && !isRevealed) {
            SecondaryButton(
                text = stringResource(R.string.st06_previous),
                onClick = onPrevious,
                modifier = Modifier.weight(1f),
            )
        }
        PrimaryButton(
            text = stringResource(
                when {
                    isRevealed -> R.string.st06_continue
                    isLastQuestion -> R.string.st06_submit
                    else -> R.string.st06_next
                }
            ),
            onClick = if (isRevealed) onContinue else onNext,
            isLoading = isSubmitting,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun RemedialCompletion(
    quiz: Quiz,
    correctCount: Int,
    totalCount: Int,
    onBackToResults: () -> Unit,
    onBackToLesson: () -> Unit,
    onRetry: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = Spacing.gutter, vertical = Spacing.section),
    ) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.stateIcon))
        Text(
            text = stringResource(R.string.st08_complete_title),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st08_complete_body, numeral(correctCount), numeral(totalCount)),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
        )
        PrimaryButton(
            text = stringResource(R.string.st08_retry),
            onClick = onRetry,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
        SecondaryButton(
            text = stringResource(R.string.st08_back_to_results),
            onClick = onBackToResults,
            modifier = Modifier.fillMaxWidth(),
        )
        SecondaryButton(
            text = stringResource(R.string.st08_back_to_lesson),
            onClick = onBackToLesson,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
