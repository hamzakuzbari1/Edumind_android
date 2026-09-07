package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Essay grading — PDF page 18.
 * ══════════════════════════════════════════════════════════════════════════
 */
@Composable
fun TeacherEssayGradeScreen(
    quizId: String,
    studentId: String,
    questionId: String,
    onBack: () -> Unit,
    onOpenNext: (studentId: String, questionId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherEssayGradeViewModel = koinViewModel(parameters = { parametersOf(quizId, studentId, questionId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherEssayGradeEvent.OpenNext -> onOpenNext(event.studentId, event.questionId)
                TeacherEssayGradeEvent.Done -> onBack()
            }
        }
    }

    val title = (state.result as? UiState.Content)?.data?.studentName
        ?: stringResource(R.string.tc11_title)

    EduScaffold(
        title = title,
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherEssayGradeSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherEssayGradeContent(
                data = data,
                selectedMark = state.selectedMark,
                feedbackDraft = state.feedbackDraft,
                isSaving = state.isSaving,
                onSelectMark = viewModel::selectMark,
                onFeedbackChange = viewModel::updateFeedback,
                onSave = viewModel::saveGrade,
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherEssayGradeContent(
    data: TeacherEssayGradeData,
    selectedMark: Int?,
    feedbackDraft: String,
    isSaving: Boolean,
    onSelectMark: (Int) -> Unit,
    onFeedbackChange: (String) -> Unit,
    onSave: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding(),
    ) {
        LazyColumn(
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
            modifier = Modifier.weight(1f),
        ) {
            item {
                Text(
                    text = stringResource(R.string.tc11_essay_meta, numeral(data.questionNumber)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                Text(
                    text = data.questionPrompt,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
                )
                EduCard(modifier = Modifier.padding(bottom = Spacing.md)) {
                    Text(
                        text = data.studentText,
                        style = EduTheme.typography.body,
                        color = colors.textPrimary,
                    )
                }
                Text(
                    text = stringResource(R.string.tc11_score_label),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.md),
                ) {
                    (0..data.maxMark).forEach { mark ->
                        val selected = selectedMark == mark
                        val shape = RoundedCornerShape(Radius.pill)
                        Text(
                            text = numeral(mark),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                            color = if (selected) colors.primary else colors.textPrimary,
                            modifier = Modifier
                                .background(if (selected) colors.primaryContainer else colors.surface, shape)
                                .border(Sizing.hairline, if (selected) colors.primary else colors.border, shape)
                                .eduClickable(role = Role.RadioButton, onClick = { onSelectMark(mark) })
                                .semantics { this.selected = selected }
                                .defaultMinSize(minHeight = Sizing.touchTarget, minWidth = Sizing.touchTarget)
                                .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
                        )
                    }
                }
                Text(
                    text = stringResource(R.string.tc11_feedback_label),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                EduTextField(
                    value = feedbackDraft,
                    onValueChange = onFeedbackChange,
                    label = "",
                    placeholder = stringResource(R.string.tc11_feedback_label),
                    singleLine = false,
                    labelPlacement = FieldLabelPlacement.Above,
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
                )
            }
        }
        PrimaryButton(
            text = stringResource(R.string.tc11_save_grade),
            onClick = onSave,
            isLoading = isSaving,
            enabled = selectedMark != null && !isSaving,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
        )
    }
}

@Composable
private fun TeacherEssayGradeSkeleton() {
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
