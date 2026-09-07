package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-10 · Quiz setup (PDF 15) + question editor (PDF 16).
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Same [TeacherQuizEditorViewModel] / repository as before — two visual phases, not a second
 * create flow. Duration, pass mark, and single-attempt write into the existing [TeacherQuiz]
 * mock fields.
 */
@Composable
fun TeacherQuizEditorScreen(
    quizId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherQuizEditorViewModel = koinViewModel(parameters = { parametersOf(quizId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val title = when {
        state.showAiImport -> stringResource(R.string.tc10_ai_import_title)
        state.phase == TeacherQuizEditorPhase.Questions -> stringResource(R.string.tc10_question_title)
        else -> stringResource(R.string.tc10_setup_title)
    }

    EduScaffold(
        title = title,
        onBack = {
            when {
                state.showAiImport -> viewModel.closeAiImport()
                state.phase == TeacherQuizEditorPhase.Questions -> viewModel.goToSetup()
                else -> onBack()
            }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherQuizEditorSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { quiz ->
            if (state.showAiImport) {
                AiImportContent(
                    candidates = state.aiCandidates,
                    reviewStatus = state.aiReviewStatus,
                    isLoading = state.isLoadingAiCandidates,
                    onReview = viewModel::reviewAiCandidate,
                )
            } else if (state.phase == TeacherQuizEditorPhase.Questions) {
                TeacherQuestionEditorContent(quiz = quiz, state = state, viewModel = viewModel)
            } else {
                TeacherQuizSetupContent(quiz = quiz, state = state, viewModel = viewModel)
            }
        }

        if (state.showPublishBlocked) {
            ConfirmDialog(
                title = stringResource(R.string.tc10_publish_blocked_title),
                body = publishBlockedBody(quizOrNull(state)),
                confirmLabel = stringResource(R.string.common_done),
                onConfirm = viewModel::dismissPublishBlocked,
                onDismiss = viewModel::dismissPublishBlocked,
            )
        }
    }
}

private fun quizOrNull(state: TeacherQuizEditorUiState): TeacherQuiz? = (state.result as? UiState.Content)?.data

@Composable
private fun publishBlockedBody(quiz: TeacherQuiz?): String {
    if (quiz == null) return ""
    val reasons = buildList {
        if (quiz.title.isBlank()) add(stringResource(R.string.tc10_gate_title))
        if (quiz.questions.isEmpty()) add(stringResource(R.string.tc10_gate_questions))
        if (quiz.questions.any { it.question.prompt.isBlank() }) add(stringResource(R.string.tc10_gate_prompts))
        if (quiz.questions.any { it.points <= 0 }) add(stringResource(R.string.tc10_gate_points))
    }
    return reasons.joinToString(separator = "\n") { "• $it" }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherQuizSetupContent(quiz: TeacherQuiz, state: TeacherQuizEditorUiState, viewModel: TeacherQuizEditorViewModel) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(stringResource(R.string.tc10_field_title), style = EduTheme.typography.caption, color = colors.textSecondary)
            EduTextField(
                value = state.titleDraft,
                onValueChange = viewModel::updateTitleDraft,
                label = "",
                placeholder = stringResource(R.string.tc10_quiz_title_label),
                labelPlacement = FieldLabelPlacement.Above,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
            )
            Text(stringResource(R.string.tc10_field_description), style = EduTheme.typography.caption, color = colors.textSecondary)
            EduTextField(
                value = state.instructionsDraft,
                onValueChange = viewModel::updateInstructionsDraft,
                label = "",
                placeholder = stringResource(R.string.tc10_quiz_instructions_label),
                singleLine = false,
                labelPlacement = FieldLabelPlacement.Above,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )
            Text(stringResource(R.string.tc10_duration_label), style = EduTheme.typography.caption, color = colors.textSecondary)
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            ) {
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_duration_15),
                    selected = state.durationMinutes == 15,
                    onClick = { viewModel.updateDurationMinutes(15) },
                )
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_duration_30),
                    selected = state.durationMinutes == 30,
                    onClick = { viewModel.updateDurationMinutes(30) },
                )
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_duration_unlimited),
                    selected = state.durationMinutes == null,
                    onClick = { viewModel.updateDurationMinutes(null) },
                )
            }
            Text(stringResource(R.string.tc10_pass_mark_label), style = EduTheme.typography.caption, color = colors.textSecondary)
            EduTextField(
                value = if (state.passMarkDraft.isBlank()) "" else "${state.passMarkDraft}%",
                onValueChange = viewModel::updatePassMarkDraft,
                label = "",
                placeholder = stringResource(R.string.tc10_pass_mark_placeholder),
                keyboardType = KeyboardType.Number,
                labelPlacement = FieldLabelPlacement.Above,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )
            EduCard(modifier = Modifier.padding(bottom = Spacing.md)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = stringResource(R.string.tc10_single_attempt),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                        color = colors.textPrimary,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = state.singleAttempt,
                        onCheckedChange = viewModel::updateSingleAttempt,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = colors.onPrimary,
                            checkedTrackColor = colors.primary,
                        ),
                    )
                }
            }
            EduCard(modifier = Modifier.padding(bottom = Spacing.md)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = stringResource(R.string.tc10_publish_after_save),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                        color = colors.textPrimary,
                    )
                    StatusPill(
                        label = teacherQuizStatusLabel(quiz.status),
                        contentColor = if (quiz.status == TeacherQuizStatus.Published) colors.success else colors.warning,
                        containerColor = (if (quiz.status == TeacherQuizStatus.Published) colors.success else colors.warning).copy(alpha = 0.14f),
                    )
                }
            }
            PrimaryButton(
                text = stringResource(R.string.tc10_save_continue),
                onClick = viewModel::continueToQuestions,
                isLoading = state.isSavingMetadata,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun TeacherQuestionEditorContent(quiz: TeacherQuiz, state: TeacherQuizEditorUiState, viewModel: TeacherQuizEditorViewModel) {
    val colors = EduTheme.colors
    val current = quiz.questions.firstOrNull { it.question.id == state.expandedQuestionId } ?: quiz.questions.firstOrNull()

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(bottom = Spacing.sm)) {
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_type_multiple_choice),
                    selected = current?.question?.type == QuestionType.MultipleChoice,
                    onClick = { if (current?.question?.type != QuestionType.MultipleChoice) viewModel.addQuestion(QuestionType.MultipleChoice) },
                )
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_type_true_false),
                    selected = current?.question?.type == QuestionType.TrueFalse,
                    onClick = { if (current?.question?.type != QuestionType.TrueFalse) viewModel.addQuestion(QuestionType.TrueFalse) },
                )
                QuestionTypeChip(
                    label = stringResource(R.string.tc10_type_essay),
                    selected = current?.question?.type == QuestionType.ShortAnswer,
                    onClick = { if (current?.question?.type != QuestionType.ShortAnswer) viewModel.addQuestion(QuestionType.ShortAnswer) },
                )
            }
            if (quiz.questions.size > 1) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(bottom = Spacing.sm),
                ) {
                    quiz.questions.forEachIndexed { index, row ->
                        QuestionTypeChip(
                            label = numeral(index + 1),
                            selected = row.question.id == current?.question?.id,
                            onClick = { viewModel.selectQuestion(row.question.id) },
                        )
                    }
                }
            }
        }

        if (current == null) {
            item {
                Text(
                    text = stringResource(R.string.tc10_no_questions),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        } else {
            item {
                QuestionEditorForm(
                    row = current,
                    isSaving = state.savingQuestionId == current.question.id,
                    onDraftChange = { transform -> viewModel.updateQuestionDraft(current.question.id, transform) },
                    onPointsChange = { viewModel.updateQuestionPoints(current.question.id, it) },
                    onAddOption = { viewModel.addOption(current.question.id) },
                    onRemoveOption = { viewModel.removeOption(current.question.id, it) },
                    onSave = { viewModel.saveQuestionEdit(current.question.id) },
                    onDelete = { viewModel.deleteQuestion(current.question.id) },
                )
            }
        }

        item {
            if (!state.canPublish) {
                Text(
                    text = stringResource(R.string.tc10_publish_gate_hint),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.tc10_publish),
                onClick = viewModel::publish,
                isLoading = state.isPublishing,
                enabled = state.canPublish,
                modifier = Modifier.fillMaxWidth(),
            )
            GhostButton(
                text = stringResource(R.string.tc10_ai_import_action),
                onClick = viewModel::openAiImport,
                leadingIcon = Icons.Filled.AutoAwesome,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }
    }
}

@Composable
private fun QuestionTypeChip(label: String, selected: Boolean, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.pill)
    Text(
        text = label,
        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
        color = if (selected) colors.primary else colors.textPrimary,
        modifier = Modifier
            .background(if (selected) colors.primaryContainer else colors.surface, shape)
            .border(Sizing.hairline, if (selected) colors.primary else colors.border, shape)
            .eduClickable(role = Role.RadioButton, onClick = onClick)
            .semantics { this.selected = selected }
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    )
}

@Composable
private fun QuestionEditorForm(
    row: TeacherQuizQuestion,
    isSaving: Boolean,
    onDraftChange: ((QuizQuestion) -> QuizQuestion) -> Unit,
    onPointsChange: (Int) -> Unit,
    onAddOption: () -> Unit,
    onRemoveOption: (String) -> Unit,
    onSave: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = EduTheme.colors
    val question = row.question
    val letters = listOf("أ", "ب", "ج", "د", "هـ", "و")

    Text(stringResource(R.string.tc10_prompt_label), style = EduTheme.typography.caption, color = colors.textSecondary)
    EduTextField(
        value = question.prompt,
        onValueChange = { text -> onDraftChange { it.copy(prompt = text) } },
        label = "",
        placeholder = stringResource(R.string.tc10_untitled_question),
        singleLine = false,
        labelPlacement = FieldLabelPlacement.Above,
        modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
    )

    when (question.type) {
        QuestionType.MultipleChoice -> {
            question.options.forEachIndexed { index, option ->
                val selected = question.correctAnswer == option.id
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = Spacing.xs)
                        .background(if (selected) colors.success.copy(alpha = 0.10f) else colors.surface, RoundedCornerShape(Radius.md))
                        .border(Sizing.hairline, if (selected) colors.success else colors.border, RoundedCornerShape(Radius.md))
                        .eduClickable(role = Role.RadioButton, onClick = { onDraftChange { it.copy(correctAnswer = option.id) } })
                        .padding(Spacing.sm),
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.iconLg)
                            .background(if (selected) colors.success else colors.neutralAlpha100, CircleShape),
                    ) {
                        Text(
                            text = letters.getOrElse(index) { "${index + 1}" },
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                            color = if (selected) colors.onPrimary else colors.textPrimary,
                        )
                    }
                    EduTextField(
                        value = option.text,
                        onValueChange = { text ->
                            onDraftChange { q -> q.copy(options = q.options.map { o -> if (o.id == option.id) o.copy(text = text) else o }) }
                        },
                        label = "",
                        modifier = Modifier.weight(1f),
                    )
                    if (question.options.size > 2) {
                        EduIconButton(
                            icon = Icons.Filled.Remove,
                            contentDescription = stringResource(R.string.tc10_remove_option),
                            onClick = { onRemoveOption(option.id) },
                        )
                    }
                }
            }
            GhostButton(
                text = stringResource(R.string.tc10_add_option),
                onClick = onAddOption,
                leadingIcon = Icons.Filled.Add,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }
        QuestionType.TrueFalse -> {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(bottom = Spacing.sm),
            ) {
                question.options.forEach { option ->
                    QuestionTypeChip(
                        label = option.text,
                        selected = question.correctAnswer == option.id,
                        onClick = { onDraftChange { it.copy(correctAnswer = option.id) } },
                    )
                }
            }
        }
        QuestionType.ShortAnswer -> Unit
        QuestionType.GapFill -> {
            EduTextField(
                value = question.correctAnswer,
                onValueChange = { text -> onDraftChange { it.copy(correctAnswer = text) } },
                label = stringResource(R.string.tc10_expected_answer_label),
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }
    }

    Text(stringResource(R.string.tc10_mark_label), style = EduTheme.typography.caption, color = colors.textSecondary)
    PointsStepper(points = row.points, onPointsChange = onPointsChange)

    PrimaryButton(
        text = stringResource(R.string.tc10_save_question),
        onClick = onSave,
        isLoading = isSaving,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.sm, bottom = Spacing.xs),
    )
    GhostButton(text = stringResource(R.string.tc10_delete), onClick = onDelete)
}

@Composable
private fun PointsStepper(points: Int, onPointsChange: (Int) -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.padding(bottom = Spacing.xs),
    ) {
        EduIconButton(
            icon = Icons.Filled.Remove,
            contentDescription = stringResource(R.string.tc10_points_decrease),
            enabled = points > 1,
            onClick = { onPointsChange(points - 1) },
        )
        Text(numeral(points), style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold), color = colors.textPrimary)
        EduIconButton(
            icon = Icons.Filled.Add,
            contentDescription = stringResource(R.string.tc10_points_increase),
            onClick = { onPointsChange(points + 1) },
        )
    }
}

@Composable
private fun AiImportContent(
    candidates: List<TeacherQuizQuestion>,
    reviewStatus: Map<String, AiReviewStatus>,
    isLoading: Boolean,
    onReview: (String, AiReviewStatus) -> Unit,
) {
    val colors = EduTheme.colors
    if (isLoading) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            SkeletonCard()
            SkeletonCard()
        }
        return
    }
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(
                text = stringResource(R.string.tc10_ai_import_intro),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.section),
            )
        }
        items(candidates, key = { it.question.id }) { candidate ->
            val status = reviewStatus[candidate.question.id] ?: AiReviewStatus.Unreviewed
            AiCandidateCard(candidate = candidate, status = status, onReview = { newStatus -> onReview(candidate.question.id, newStatus) })
        }
    }
}

@Composable
private fun AiCandidateCard(candidate: TeacherQuizQuestion, status: AiReviewStatus, onReview: (AiReviewStatus) -> Unit) {
    val colors = EduTheme.colors
    val question = candidate.question
    val borderColor = when (status) {
        AiReviewStatus.Unreviewed -> colors.border
        AiReviewStatus.Accepted -> colors.success
        AiReviewStatus.Rejected -> colors.danger
    }

    EduCard(borderColor = borderColor, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            AiMarker(modifier = Modifier.padding(top = Spacing.xxs))
            Column(modifier = Modifier.weight(1f)) {
                Text(questionTypeLabel(question.type), style = EduTheme.typography.caption, color = colors.textSecondary)
                Text(question.prompt, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
            }
            StatusPill(label = aiReviewStatusLabel(status), contentColor = borderColor, containerColor = borderColor.copy(alpha = 0.14f))
        }
        PrimaryButton(
            text = stringResource(R.string.tc07_accept),
            onClick = { onReview(AiReviewStatus.Accepted) },
            enabled = status != AiReviewStatus.Accepted,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun TeacherQuizEditorSkeleton() {
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
