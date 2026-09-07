package com.rork.eduspark.ui.screens.student

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarViewWeek
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.EventNote
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.CommitmentSchedule
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.PlannerPriority
import com.rork.eduspark.data.model.RoutineBuildMessage
import com.rork.eduspark.data.model.RoutineBuildStep
import com.rork.eduspark.data.model.RoutineBuilderAnswers
import com.rork.eduspark.data.model.RoutineDayDraft
import com.rork.eduspark.data.model.RoutineDraft
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.RoutineSuggestion
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.progress.HorizontalSpine
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-12 · Routine Builder.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Six questions, one per screen, plus a review step — the exact shape of onboarding's SO-04
 * ("five questions, one per screen, never a form wall"), not a chat. That is the deliberate
 * difference from ST-11 Planner AI Chat: this collects recurring *structure* through a fixed
 * sequence of quick replies; ST-11 adjusts specific *sessions* through free-text conversation.
 * No aiAccent marking anywhere here — every question and every answer is the student's own
 * structure, not AI-generated content.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun RoutineBuilderScreen(
    onBack: () -> Unit,
    onComplete: () -> Unit,
    onOpenExamCapture: () -> Unit = {},
    modifier: Modifier = Modifier,
    viewModel: RoutineBuilderViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var questionIndex by rememberSaveable { mutableIntStateOf(0) }

    LaunchedEffect(state.confirmedRoutine) {
        if (state.confirmedRoutine != null) onComplete()
    }

    val goBack: () -> Unit = {
        when (state.step) {
            RoutineBuildStep.SuggestionReview, RoutineBuildStep.FinalWeek -> viewModel.editDraft()
            RoutineBuildStep.AiBuild -> {
                questionIndex = TOTAL_STEPS - 1
                viewModel.returnToOnboarding()
            }
            RoutineBuildStep.Onboarding -> if (questionIndex > 0) questionIndex-- else onBack()
        }
    }
    BackHandler(onBack = goBack)

    EduScaffold(title = stringResource(R.string.st12_title), onBack = goBack, modifier = modifier) { _ ->
        when (state.step) {
            RoutineBuildStep.Onboarding -> RoutineOnboardingContent(
                questionIndex = questionIndex,
                state = state,
                onQuestionIndexChange = { questionIndex = it },
                viewModel = viewModel,
            )

            RoutineBuildStep.AiBuild -> RoutineAiBuildContent(
                draft = state.draft,
                input = state.draftInput,
                reviewFailed = state.reviewFailed,
                onInputChange = viewModel::updateDraftInput,
                onSend = viewModel::sendDraftAdjustment,
                onConfirmDay = viewModel::confirmDraftDay,
                onReview = viewModel::reviewDraft,
                onOpenExamCapture = onOpenExamCapture,
            )

            RoutineBuildStep.SuggestionReview -> RoutineSuggestionReviewContent(
                draft = state.draft,
                isConfirming = state.isConfirming,
                confirmFailed = state.confirmFailed,
                onSetSuggestion = viewModel::setSuggestion,
                onEditSchedule = viewModel::editDraft,
                onFinalize = viewModel::finalizeRoutine,
            )

            RoutineBuildStep.FinalWeek -> RoutineAiBuildContent(
                draft = state.draft,
                input = state.draftInput,
                reviewFailed = false,
                onInputChange = viewModel::updateDraftInput,
                onSend = viewModel::sendDraftAdjustment,
                onConfirmDay = viewModel::confirmDraftDay,
                onReview = viewModel::reviewDraft,
                onOpenExamCapture = onOpenExamCapture,
            )
        }
    }
}

@Composable
private fun RoutineOnboardingContent(
    questionIndex: Int,
    state: RoutineBuilderUiState,
    onQuestionIndexChange: (Int) -> Unit,
    viewModel: RoutineBuilderViewModel,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Text(
            text = stringResource(R.string.st06_question_of, numeral(questionIndex + 1), numeral(TOTAL_STEPS)),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
        HorizontalSpine(
            total = TOTAL_STEPS,
            currentIndex = questionIndex,
            modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.section),
        )

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            when (questionIndex) {
                0 -> WakeTimeQuestion(selected = state.answers.wakeTime, onSelect = { viewModel.setWakeTime(it); onQuestionIndexChange(questionIndex + 1) })
                1 -> SchoolHoursQuestion(selected = state.answers.schoolHoursId, onSelect = { viewModel.setSchoolHours(it); onQuestionIndexChange(questionIndex + 1) })
                2 -> CommitmentsQuestion(
                    selected = state.answers.commitmentIds,
                    schedules = state.answers.commitmentSchedules,
                    onToggle = viewModel::toggleCommitment,
                    onToggleDay = viewModel::toggleCommitmentDay,
                    onSelectStart = viewModel::setCommitmentStartTime,
                    onSelectEnd = viewModel::setCommitmentEndTime,
                    onNext = { onQuestionIndexChange(questionIndex + 1) },
                )
                3 -> StudyWindowsQuestion(
                    selected = state.answers.studyWindowIds,
                    onToggle = viewModel::toggleStudyWindow,
                    onNext = { onQuestionIndexChange(questionIndex + 1) },
                )
                4 -> EnergyPatternQuestion(selected = state.answers.energyPattern, onSelect = { viewModel.setEnergyPattern(it); onQuestionIndexChange(questionIndex + 1) })
                5 -> SleepTimeQuestion(selected = state.answers.sleepTime, onSelect = { viewModel.setSleepTime(it); onQuestionIndexChange(questionIndex + 1) })
                else -> ReviewQuestion(
                    answers = state.answers,
                    isConfirming = state.isConfirming,
                    confirmFailed = state.confirmFailed,
                    onConfirm = viewModel::startAiBuild,
                    onEdit = onQuestionIndexChange,
                )
            }
        }
    }
}

@Composable
private fun RoutineAiBuildContent(
    draft: RoutineDraft?,
    input: String,
    reviewFailed: Boolean,
    onInputChange: (String) -> Unit,
    onSend: () -> Unit,
    onConfirmDay: (Weekday) -> Unit,
    onReview: () -> Unit,
    onOpenExamCapture: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        EduCard(borderColor = colors.aiAccent) {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.icon))
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = stringResource(R.string.st12_ai_build_title), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                    Text(text = stringResource(R.string.st12_ai_build_body), style = EduTheme.typography.caption, color = colors.textSecondary)
                }
            }
        }

        if (draft == null) {
            Text(text = stringResource(R.string.st12_ai_build_loading), style = EduTheme.typography.body, color = colors.textSecondary)
            return@Column
        }

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            RoutineBuildMetric(stringResource(R.string.st12_days_confirmed), "${draft.confirmedCount}/${draft.totalDays}", modifier = Modifier.weight(1f))
            RoutineBuildMetric(stringResource(R.string.st12_current_day), draft.currentDay.builderShortLabel(), modifier = Modifier.weight(1f))
        }

        EduCard {
            Text(text = stringResource(R.string.st12_ai_chat_title), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
            Text(text = stringResource(R.string.st12_ai_chat_body), style = EduTheme.typography.caption, color = colors.textSecondary)
            Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                draft.messages.forEach { message -> RoutineBuildMessageBubble(message) }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = Spacing.sm)) {
                EduTextField(
                    value = input,
                    onValueChange = onInputChange,
                    label = stringResource(R.string.st12_ai_message_label),
                    placeholder = stringResource(R.string.st12_ai_message_placeholder),
                    modifier = Modifier.weight(1f),
                )
                EduIconButton(
                    icon = Icons.AutoMirrored.Filled.Send,
                    contentDescription = stringResource(R.string.st04_send),
                    onClick = onSend,
                    enabled = input.isNotBlank(),
                    tint = colors.primary,
                )
            }
        }

        EduCard {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.CameraAlt, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = stringResource(R.string.st12_exams_title), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                    Text(text = stringResource(R.string.st12_exams_body), style = EduTheme.typography.caption, color = colors.textSecondary)
                }
            }
            SecondaryButton(
                text = stringResource(R.string.st12_add_exam),
                onClick = onOpenExamCapture,
                leadingIcon = Icons.Filled.CameraAlt,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }

        val currentDraft = draft.dayDrafts.firstOrNull { it.day == draft.currentDay } ?: draft.dayDrafts.firstOrNull()
        if (currentDraft != null) {
            RoutineDayDraftPreview(
                dayDraft = currentDraft,
                onConfirmDay = { onConfirmDay(currentDraft.day) },
            )
        }

        EduCard {
            Text(text = stringResource(R.string.st12_week_progress), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                draft.dayDrafts.forEach { day ->
                    StatusPill(
                        label = if (day.confirmed) {
                            stringResource(R.string.st12_day_confirmed, day.day.builderShortLabel())
                        } else {
                            stringResource(R.string.st12_day_activity_count, day.day.builderShortLabel(), numeral(day.slots.size))
                        },
                        contentColor = if (day.confirmed) colors.success else colors.textSecondary,
                        containerColor = if (day.confirmed) colors.success.copy(alpha = 0.12f) else colors.neutralAlpha100,
                    )
                }
            }
        }

        if (reviewFailed) {
            Text(text = stringResource(R.string.st12_all_days_required), style = EduTheme.typography.caption, color = colors.danger)
        }

        PrimaryButton(
            text = stringResource(R.string.st12_review_ai_suggestions),
            onClick = onReview,
            enabled = draft.readyForReview,
            leadingIcon = Icons.Filled.AutoAwesome,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun RoutineBuildMetric(label: String, value: String, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier) {
        Text(text = value, style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
        Text(text = label, style = EduTheme.typography.caption, color = colors.textSecondary)
    }
}

@Composable
private fun RoutineBuildMessageBubble(message: RoutineBuildMessage) {
    val colors = EduTheme.colors
    val isAi = message.sender == PlannerChatSender.Assistant
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                if (isAi) colors.aiAccentContainer else colors.primaryContainer,
                RoundedCornerShape(Radius.md),
            )
            .border(
                Sizing.hairline,
                if (isAi) colors.aiAccent else colors.primary,
                RoundedCornerShape(Radius.md),
            )
            .padding(Spacing.sm),
    ) {
        Text(
            text = if (isAi) stringResource(R.string.st12_sender_ai) else stringResource(R.string.st12_sender_you),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = if (isAi) colors.aiAccent else colors.primary,
        )
        Text(text = message.text, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
    }
}

@Composable
private fun RoutineDayDraftPreview(dayDraft: RoutineDayDraft, onConfirmDay: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(borderColor = if (dayDraft.confirmed) colors.success else colors.border) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.CalendarViewWeek, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
            Column(modifier = Modifier.weight(1f)) {
                Text(text = dayDraft.day.builderShortLabel(), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                Text(text = dayDraft.reasoning, style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            if (dayDraft.confirmed) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.icon))
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            if (dayDraft.slots.isEmpty()) {
                Text(text = stringResource(R.string.st12_day_empty), style = EduTheme.typography.caption, color = colors.textSecondary)
            } else {
                dayDraft.slots.forEach { slot -> RoutineDraftSlotRow(slot) }
            }
        }
        PrimaryButton(
            text = if (dayDraft.confirmed) stringResource(R.string.st12_day_confirmed_button) else stringResource(R.string.st12_confirm_this_day),
            onClick = onConfirmDay,
            enabled = !dayDraft.confirmed,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun RoutineDraftSlotRow(slot: RoutineSlot) {
    val colors = EduTheme.colors
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.Top, modifier = Modifier.fillMaxWidth()) {
        Icon(Icons.Filled.Schedule, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        Column(modifier = Modifier.weight(1f)) {
            Text(text = slot.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
            Text(
                text = if (slot.endTime != null) "${slot.startTime} - ${slot.endTime}" else slot.startTime,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
        StatusPill(
            label = slot.status.routineStatusLabel(),
            contentColor = when (slot.status) {
                RoutineSlotStatus.Completed -> colors.success
                RoutineSlotStatus.Missed -> colors.danger
                RoutineSlotStatus.Upcoming -> colors.textSecondary
            },
            containerColor = colors.neutralAlpha100,
        )
    }
}

@Composable
private fun RoutineSuggestionReviewContent(
    draft: RoutineDraft?,
    isConfirming: Boolean,
    confirmFailed: Boolean,
    onSetSuggestion: (String, Boolean?) -> Unit,
    onEditSchedule: () -> Unit,
    onFinalize: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        EduCard(borderColor = colors.aiAccent) {
            Text(text = stringResource(R.string.st12_ai_review_title), style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
            Text(
                text = draft?.reviewText.orEmpty().ifBlank { stringResource(R.string.st12_ai_review_empty) },
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        draft?.suggestions.orEmpty().forEach { suggestion ->
            RoutineSuggestionCard(suggestion = suggestion, onSetSuggestion = onSetSuggestion)
        }

        EduCard {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.EventNote, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = stringResource(R.string.st12_saved_week_preview), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                    Text(text = stringResource(R.string.st12_saved_week_preview_body), style = EduTheme.typography.caption, color = colors.textSecondary)
                }
            }
        }

        if (confirmFailed) {
            Text(text = stringResource(R.string.st12_confirm_error), style = EduTheme.typography.caption, color = colors.danger)
        }
        SecondaryButton(
            text = stringResource(R.string.st12_edit_schedule),
            onClick = onEditSchedule,
            leadingIcon = Icons.Filled.Schedule,
            modifier = Modifier.fillMaxWidth(),
        )
        PrimaryButton(
            text = stringResource(R.string.st12_finish_routine),
            onClick = onFinalize,
            isLoading = isConfirming,
            leadingIcon = Icons.Filled.CheckCircle,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun RoutineSuggestionCard(suggestion: RoutineSuggestion, onSetSuggestion: (String, Boolean?) -> Unit) {
    val colors = EduTheme.colors
    EduCard(borderColor = suggestion.priority.priorityColor()) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.Top) {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = suggestion.priority.priorityColor(), modifier = Modifier.size(Sizing.icon))
            Column(modifier = Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                    Text(text = suggestion.title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary, modifier = Modifier.weight(1f))
                    StatusPill(
                        label = suggestion.priority.priorityLabel(),
                        contentColor = suggestion.priority.priorityColor(),
                        containerColor = suggestion.priority.priorityColor().copy(alpha = 0.12f),
                    )
                }
                Text(text = suggestion.description, style = EduTheme.typography.body, color = colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                    SecondaryButton(
                        text = if (suggestion.accepted == true) stringResource(R.string.st12_suggestion_accepted) else stringResource(R.string.st12_suggestion_accept),
                        onClick = { onSetSuggestion(suggestion.id, true) },
                        modifier = Modifier.weight(1f),
                    )
                    GhostButton(
                        text = if (suggestion.accepted == false) stringResource(R.string.st12_suggestion_rejected) else stringResource(R.string.st12_suggestion_reject),
                        onClick = { onSetSuggestion(suggestion.id, false) },
                        modifier = Modifier.weight(1f),
                    )
                    GhostButton(text = stringResource(R.string.st12_suggestion_reset), onClick = { onSetSuggestion(suggestion.id, null) })
                }
            }
        }
    }
}

@Composable
private fun RoutineSlotStatus.routineStatusLabel(): String = stringResource(
    when (this) {
        RoutineSlotStatus.Upcoming -> R.string.st13_status_upcoming
        RoutineSlotStatus.Completed -> R.string.st13_status_completed
        RoutineSlotStatus.Missed -> R.string.st13_status_missed
    }
)

@Composable
private fun PlannerPriority.priorityColor() = when (this) {
    PlannerPriority.High -> EduTheme.colors.danger
    PlannerPriority.Medium -> EduTheme.colors.warning
    PlannerPriority.Low -> EduTheme.colors.success
}

@Composable
private fun PlannerPriority.priorityLabel() = stringResource(
    when (this) {
        PlannerPriority.High -> R.string.st12_priority_high
        PlannerPriority.Medium -> R.string.st12_priority_medium
        PlannerPriority.Low -> R.string.st12_priority_low
    }
)

private const val TOTAL_STEPS = 7

private val WAKE_TIME_OPTIONS = listOf("6:00", "6:30", "7:00", "7:30", "8:00")
private val SLEEP_TIME_OPTIONS = listOf("21:00", "21:30", "22:00", "22:30", "23:00")

@Composable
private fun QuestionHeader(titleRes: Int, bodyRes: Int) {
    Text(text = stringResource(titleRes), style = EduTheme.typography.titleLg, color = EduTheme.colors.textPrimary)
    Text(
        text = stringResource(bodyRes),
        style = EduTheme.typography.body,
        color = EduTheme.colors.textSecondary,
        modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.section),
    )
}

@Composable
private fun TimeChipRow(options: List<String>, selected: String?, onSelect: (String) -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        options.forEach { time ->
            EduChip(label = numeral(time), selected = selected == time, onClick = { onSelect(time) })
        }
    }
}

@Composable
private fun WakeTimeQuestion(selected: String?, onSelect: (String) -> Unit) {
    QuestionHeader(R.string.st12_q1_title, R.string.st12_q1_body)
    TimeChipRow(WAKE_TIME_OPTIONS, selected, onSelect)
}

@Composable
private fun SleepTimeQuestion(selected: String?, onSelect: (String) -> Unit) {
    QuestionHeader(R.string.st12_q6_title, R.string.st12_q6_body)
    TimeChipRow(SLEEP_TIME_OPTIONS, selected, onSelect)
}

@Composable
private fun SchoolHoursQuestion(selected: String?, onSelect: (String) -> Unit) {
    QuestionHeader(R.string.st12_q2_title, R.string.st12_q2_body)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        SchoolHoursPresets.forEach { preset ->
            AnswerCard(
                title = stringResource(preset.titleRes),
                hint = stringResource(preset.hintRes),
                selected = selected == preset.id,
                onClick = { onSelect(preset.id) },
            )
        }
    }
}

@Composable
private fun CommitmentsQuestion(
    selected: Set<String>,
    schedules: Map<String, CommitmentSchedule>,
    onToggle: (String) -> Unit,
    onToggleDay: (String, Weekday) -> Unit,
    onSelectStart: (String, String) -> Unit,
    onSelectEnd: (String, String) -> Unit,
    onNext: () -> Unit,
) {
    QuestionHeader(R.string.st12_q3_title, R.string.st12_q3_body)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        CommitmentOptions.forEach { option ->
            EduChip(label = stringResource(option.labelRes), selected = option.id in selected, onClick = { onToggle(option.id) })
        }
    }
    // Approved design's nested detail card (RoutineBuilder.dc.html) — one per selected
    // commitment, additive: days/time are optional, MockRoutineRepository.buildRoutine()
    // falls back to its own defaults for any commitment left uncustomized here.
    CommitmentOptions.filter { it.id in selected }.forEach { option ->
        CommitmentScheduleCard(
            commitmentLabel = stringResource(option.labelRes),
            schedule = schedules[option.id] ?: CommitmentSchedule(),
            onToggleDay = { day -> onToggleDay(option.id, day) },
            onSelectStart = { time -> onSelectStart(option.id, time) },
            onSelectEnd = { time -> onSelectEnd(option.id, time) },
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
    PrimaryButton(
        text = stringResource(R.string.st06_next),
        onClick = onNext,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.section),
    )
}

private val COMMITMENT_TIME_OPTIONS = listOf("15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00")

/** Approved design's nested commitment scheduling card (RoutineBuilder.dc.html's `.detailcard`). */
@Composable
private fun CommitmentScheduleCard(
    commitmentLabel: String,
    schedule: CommitmentSchedule,
    onToggleDay: (Weekday) -> Unit,
    onSelectStart: (String) -> Unit,
    onSelectEnd: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxWidth()
            .background(colors.surface, RoundedCornerShape(Radius.md))
            .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.md))
            .padding(Spacing.card),
    ) {
        Text(
            text = stringResource(R.string.st12_commitment_schedule_days, commitmentLabel),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textSecondary,
        )
        FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs), verticalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
            Weekday.entries.forEach { day ->
                EduChip(label = day.builderShortLabel(), selected = day in schedule.days, onClick = { onToggleDay(day) })
            }
        }
        Text(
            text = stringResource(R.string.st12_commitment_schedule_time),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textSecondary,
        )
        Text(text = stringResource(R.string.st12_commitment_schedule_from), style = EduTheme.typography.caption, color = colors.textSecondary)
        TimeChipRow(COMMITMENT_TIME_OPTIONS, schedule.startTime, onSelectStart)
        Text(text = stringResource(R.string.st12_commitment_schedule_to), style = EduTheme.typography.caption, color = colors.textSecondary)
        TimeChipRow(COMMITMENT_TIME_OPTIONS, schedule.endTime, onSelectEnd)
    }
}

@Composable
private fun Weekday.builderShortLabel(): String = stringResource(
    when (this) {
        Weekday.Sunday -> R.string.so04_weekday_sun
        Weekday.Monday -> R.string.so04_weekday_mon
        Weekday.Tuesday -> R.string.so04_weekday_tue
        Weekday.Wednesday -> R.string.so04_weekday_wed
        Weekday.Thursday -> R.string.so04_weekday_thu
        Weekday.Friday -> R.string.so04_weekday_fri
        Weekday.Saturday -> R.string.so04_weekday_sat
    }
)

@Composable
private fun StudyWindowsQuestion(selected: Set<String>, onToggle: (String) -> Unit, onNext: () -> Unit) {
    QuestionHeader(R.string.st12_q4_title, R.string.st12_q4_body)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        StudyWindowOptions.forEach { option ->
            EduChip(label = stringResource(option.labelRes), selected = option.id in selected, onClick = { onToggle(option.id) })
        }
    }
    PrimaryButton(
        text = stringResource(R.string.st06_next),
        onClick = onNext,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.section),
    )
}

@Composable
private fun EnergyPatternQuestion(selected: StudyTimeOfDay?, onSelect: (StudyTimeOfDay) -> Unit) {
    QuestionHeader(R.string.st12_q5_title, R.string.st12_q5_body)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        AnswerCard(stringResource(R.string.so04_time_morning), stringResource(R.string.so04_time_morning_hint), selected == StudyTimeOfDay.EarlyMorning) { onSelect(StudyTimeOfDay.EarlyMorning) }
        AnswerCard(stringResource(R.string.so04_time_afternoon), stringResource(R.string.so04_time_afternoon_hint), selected == StudyTimeOfDay.Afternoon) { onSelect(StudyTimeOfDay.Afternoon) }
        AnswerCard(stringResource(R.string.so04_time_evening), stringResource(R.string.so04_time_evening_hint), selected == StudyTimeOfDay.Evening) { onSelect(StudyTimeOfDay.Evening) }
        AnswerCard(stringResource(R.string.so04_time_late), stringResource(R.string.so04_time_late_hint), selected == StudyTimeOfDay.LateNight) { onSelect(StudyTimeOfDay.LateNight) }
    }
}

@Composable
private fun AnswerCard(title: String, hint: String, selected: Boolean, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (selected) colors.primaryContainer else colors.surface, shape)
            .border(if (selected) Sizing.hairline * 2 else Sizing.hairline, if (selected) colors.primary else colors.border, shape)
            .eduClickable(onClickLabel = title, onClick = onClick)
            .padding(Spacing.card),
    ) {
        Text(text = title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = if (selected) colors.primary else colors.textPrimary)
        Text(text = hint, style = EduTheme.typography.caption, color = colors.textSecondary)
    }
}

@Composable
private fun ReviewQuestion(
    answers: RoutineBuilderAnswers,
    isConfirming: Boolean,
    confirmFailed: Boolean,
    onConfirm: () -> Unit,
    onEdit: (questionIndex: Int) -> Unit,
) {
    val colors = EduTheme.colors
    Text(text = stringResource(R.string.st12_review_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)

    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.padding(top = Spacing.section),
    ) {
        ReviewRow(stringResource(R.string.st12_review_wake), numeral(answers.wakeTime.orEmpty())) { onEdit(0) }
        ReviewRow(stringResource(R.string.st12_review_school), SchoolHoursPresets.firstOrNull { it.id == answers.schoolHoursId }?.let { stringResource(it.hintRes) }.orEmpty()) { onEdit(1) }
        ReviewRow(
            stringResource(R.string.st12_review_commitments),
            if (answers.commitmentIds.isEmpty()) {
                stringResource(R.string.st12_review_commitments_none)
            } else {
                answers.commitmentIds.mapNotNull { id -> CommitmentOptions.firstOrNull { it.id == id }?.labelRes }
                    .map { stringResource(it) }
                    .joinToString("، ")
            },
        ) { onEdit(2) }
        ReviewRow(
            stringResource(R.string.st12_review_windows),
            if (answers.studyWindowIds.isEmpty()) {
                stringResource(R.string.st12_review_windows_none)
            } else {
                answers.studyWindowIds.mapNotNull { id -> StudyWindowOptions.firstOrNull { it.id == id }?.labelRes }
                    .map { stringResource(it) }
                    .joinToString("، ")
            },
        ) { onEdit(3) }
        ReviewRow(stringResource(R.string.st12_review_energy), answers.energyPattern?.let { energyPatternLabel(it) }.orEmpty()) { onEdit(4) }
        ReviewRow(stringResource(R.string.st12_review_sleep), numeral(answers.sleepTime.orEmpty())) { onEdit(5) }
    }

    if (confirmFailed) {
        Text(
            text = stringResource(R.string.st12_confirm_error),
            style = EduTheme.typography.caption,
            color = colors.danger,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }

    PrimaryButton(
        text = stringResource(R.string.st12_confirm),
        onClick = onConfirm,
        isLoading = isConfirming,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.section),
    )
}

@Composable
private fun energyPatternLabel(pattern: StudyTimeOfDay): String = stringResource(
    when (pattern) {
        StudyTimeOfDay.EarlyMorning -> R.string.so04_time_morning
        StudyTimeOfDay.Afternoon -> R.string.so04_time_afternoon
        StudyTimeOfDay.Evening -> R.string.so04_time_evening
        StudyTimeOfDay.LateNight -> R.string.so04_time_late
    }
)

@Composable
private fun ReviewRow(label: String, value: String, onEdit: () -> Unit) {
    val colors = EduTheme.colors
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = label, style = EduTheme.typography.caption, color = colors.textSecondary)
            Text(text = value.ifBlank { "—" }, style = EduTheme.typography.body, color = colors.textPrimary)
        }
        GhostButton(text = stringResource(R.string.st12_edit), onClick = onEdit)
    }
    Spacer(modifier = Modifier.height(Spacing.xxs))
}

private data class SchoolHoursPreset(val id: String, val titleRes: Int, val hintRes: Int)

private val SchoolHoursPresets = listOf(
    SchoolHoursPreset("early", R.string.st12_school_early, R.string.st12_school_early_hint),
    SchoolHoursPreset("standard", R.string.st12_school_standard, R.string.st12_school_standard_hint),
    SchoolHoursPreset("late", R.string.st12_school_late, R.string.st12_school_late_hint),
)

private data class TagOption(val id: String, val labelRes: Int)

private val CommitmentOptions = listOf(
    TagOption("sports", R.string.st12_commitment_sports),
    TagOption("tutoring", R.string.st12_commitment_tutoring),
    TagOption("club", R.string.st12_commitment_club),
    TagOption("volunteer", R.string.st12_commitment_volunteer),
)

private val StudyWindowOptions = listOf(
    TagOption("early_morning", R.string.st12_window_early_morning),
    TagOption("after_school", R.string.st12_window_after_school),
    TagOption("evening", R.string.st12_window_evening),
    TagOption("late_night", R.string.st12_window_late_night),
)
