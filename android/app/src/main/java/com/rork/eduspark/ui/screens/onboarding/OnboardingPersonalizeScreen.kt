package com.rork.eduspark.ui.screens.onboarding

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.SimpleDate
import com.rork.eduspark.data.model.StudyHoursPerDay
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.SubjectOption
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-04 · Onboarding: Personalize
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "Five questions, one per screen — never a form wall." The outer Progress Spine stays at
 * 4/4 the whole time (this is still step 4 of 4); [questionIndex] is purely local paging
 * state with its own dot row, matching the PDF's "the spine still reads 4/4 outside".
 *
 * Every question accepts "not sure yet" as answered — none of them block on a specific
 * pick, only on *an* answer existing (see `*Done` in OnboardingViewModel).
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun OnboardingPersonalizeScreen(
    onBack: () -> Unit,
    onContinue: () -> Unit,
    viewModel: OnboardingViewModel,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var questionIndex by remember { mutableIntStateOf(0) }
    val selectedSubjects = (state.availableSubjects as? UiState.Content)
        ?.data
        ?.filter { it.id in state.subjectIds }
        .orEmpty()

    val goBack: () -> Unit = { if (questionIndex > 0) questionIndex-- else onBack() }
    BackHandler { goBack() }

    OnboardingStepScaffold(step = 4, onBack = goBack) {
        Text(
            text = stringResource(R.string.so04_question_label, questionIndex + 1, TOTAL_QUESTIONS),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
        DotRow(total = TOTAL_QUESTIONS, currentIndex = questionIndex, modifier = Modifier.padding(top = Spacing.xs))

        Spacer(modifier = Modifier.height(Spacing.section))

        when (questionIndex) {
            0 -> StudyHoursQuestion(
                selected = state.answers.studyHours,
                onSelect = { viewModel.setStudyHours(it); questionIndex++ },
            )

            1 -> SubjectPickQuestion(
                titleRes = R.string.so04_q2_title,
                bodyRes = R.string.so04_q2_body,
                subjects = selectedSubjects,
                selectedId = state.answers.strongestSubjectId,
                notSure = state.answers.strongestNotSure,
                onSelectSubject = { viewModel.selectStrongestSubject(it); questionIndex++ },
                onNotSure = { viewModel.selectStrongestNotSure(); questionIndex++ },
            )

            2 -> SubjectPickQuestion(
                titleRes = R.string.so04_q3_title,
                bodyRes = R.string.so04_q3_body,
                subjects = selectedSubjects,
                selectedId = state.answers.weakestSubjectId,
                notSure = state.answers.weakestNotSure,
                onSelectSubject = { viewModel.selectWeakestSubject(it); questionIndex++ },
                onNotSure = { viewModel.selectWeakestNotSure(); questionIndex++ },
            )

            3 -> ExamDateQuestion(
                selected = state.answers.examDate,
                notSure = state.answers.examDateNotSure,
                onSelectDate = { viewModel.setExamDate(it) },
                onNotSure = { viewModel.setExamDateNotSure(); questionIndex++ },
                onNext = { questionIndex++ },
            )

            else -> StudyTimeQuestion(
                selected = state.answers.studyTime,
                onSelect = { viewModel.setStudyTime(it) },
                onBuildPlan = onContinue,
            )
        }
    }
}

private const val TOTAL_QUESTIONS = 5

@Composable
private fun QuestionHeader(titleRes: Int, bodyRes: Int) {
    Text(text = stringResource(titleRes), style = EduTheme.typography.titleLg, color = EduTheme.colors.textPrimary)
    Text(
        text = stringResource(bodyRes),
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.section),
    )
}

@Composable
private fun DotRow(total: Int, currentIndex: Int, modifier: Modifier = Modifier) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs), modifier = modifier) {
        repeat(total) { index ->
            Box(
                modifier = Modifier
                    .size(if (index == currentIndex) 8.dp else 6.dp)
                    .background(
                        if (index <= currentIndex) EduTheme.colors.zaytoun else EduTheme.colors.hajar300,
                        CircleShape,
                    ),
            )
        }
    }
}

@Composable
private fun StudyHoursQuestion(
    selected: StudyHoursPerDay?,
    onSelect: (StudyHoursPerDay) -> Unit,
) {
    QuestionHeader(R.string.so04_q1_title, R.string.so04_q1_body)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        AnswerRow(stringResource(R.string.so04_hours_30min), selected == StudyHoursPerDay.ThirtyMinutes) { onSelect(StudyHoursPerDay.ThirtyMinutes) }
        AnswerRow(stringResource(R.string.so04_hours_1h), selected == StudyHoursPerDay.OneHour) { onSelect(StudyHoursPerDay.OneHour) }
        AnswerRow(stringResource(R.string.so04_hours_2h), selected == StudyHoursPerDay.TwoHours) { onSelect(StudyHoursPerDay.TwoHours) }
        AnswerRow(stringResource(R.string.so04_hours_3h_plus), selected == StudyHoursPerDay.ThreePlusHours) { onSelect(StudyHoursPerDay.ThreePlusHours) }
    }
}

@Composable
private fun SubjectPickQuestion(
    titleRes: Int,
    bodyRes: Int,
    subjects: List<SubjectOption>,
    selectedId: String?,
    notSure: Boolean,
    onSelectSubject: (String) -> Unit,
    onNotSure: () -> Unit,
) {
    QuestionHeader(titleRes, bodyRes)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        subjects.forEach { subject ->
            EduChip(
                label = subject.name,
                selected = selectedId == subject.id,
                onClick = { onSelectSubject(subject.id) },
            )
        }
        EduChip(
            label = stringResource(R.string.so04_not_sure_yet),
            selected = notSure,
            onClick = onNotSure,
        )
    }
}

@Composable
private fun ExamDateQuestion(
    selected: SimpleDate?,
    notSure: Boolean,
    onSelectDate: (SimpleDate) -> Unit,
    onNotSure: () -> Unit,
    onNext: () -> Unit,
) {
    QuestionHeader(R.string.so04_q4_title, R.string.so04_q4_body)
    SimpleDatePicker(selected = selected, onSelect = onSelectDate)

    Spacer(modifier = Modifier.height(Spacing.md))

    EduChip(
        label = stringResource(R.string.so04_exam_date_not_sure),
        selected = notSure,
        onClick = onNotSure,
    )

    if (selected != null) {
        val days = daysUntil(selected).coerceAtLeast(0)
        Text(
            text = pluralStringResource(R.plurals.so04_exam_days_until, days, days),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.zaytoun,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        PrimaryButton(
            text = stringResource(R.string.so04_next),
            onClick = onNext,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun StudyTimeQuestion(
    selected: StudyTimeOfDay?,
    onSelect: (StudyTimeOfDay) -> Unit,
    onBuildPlan: () -> Unit,
) {
    QuestionHeader(R.string.so04_q5_title, R.string.so04_q5_body)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        TimeAnswerRow(R.string.so04_time_morning, R.string.so04_time_morning_hint, selected == StudyTimeOfDay.EarlyMorning) { onSelect(StudyTimeOfDay.EarlyMorning) }
        TimeAnswerRow(R.string.so04_time_afternoon, R.string.so04_time_afternoon_hint, selected == StudyTimeOfDay.Afternoon) { onSelect(StudyTimeOfDay.Afternoon) }
        TimeAnswerRow(R.string.so04_time_evening, R.string.so04_time_evening_hint, selected == StudyTimeOfDay.Evening) { onSelect(StudyTimeOfDay.Evening) }
        TimeAnswerRow(R.string.so04_time_late, R.string.so04_time_late_hint, selected == StudyTimeOfDay.LateNight) { onSelect(StudyTimeOfDay.LateNight) }
    }
    if (selected != null) {
        PrimaryButton(
            text = stringResource(R.string.so04_build_plan),
            onClick = onBuildPlan,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.section),
        )
    }
}

/** A single-line quick-reply answer — the shared shape for SO-04's simplest questions. */
@Composable
private fun AnswerRow(label: String, selected: Boolean, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .background(if (selected) colors.zaytounSoft else colors.surface, shape)
            .border(if (selected) Sizing.hairline * 2 else Sizing.hairline, if (selected) colors.zaytoun else colors.border, shape)
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(horizontal = Spacing.card, vertical = Spacing.sm),
    ) {
        Text(text = label, style = EduTheme.typography.body, color = if (selected) colors.zaytoun else colors.textPrimary)
    }
}

/** A quick-reply row with a title and a supporting hint line — SO-04 Q5's richer chips. */
@Composable
private fun TimeAnswerRow(titleRes: Int, hintRes: Int, selected: Boolean, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    val title = stringResource(titleRes)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (selected) colors.zaytounSoft else colors.surface, shape)
            .border(if (selected) Sizing.hairline * 2 else Sizing.hairline, if (selected) colors.zaytoun else colors.border, shape)
            .eduClickable(onClickLabel = title, onClick = onClick)
            .padding(Spacing.card),
    ) {
        Text(text = title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = if (selected) colors.zaytoun else colors.textPrimary)
        Text(text = stringResource(hintRes), style = EduTheme.typography.caption, color = colors.textMuted)
    }
}

/**
 * A minimal Gregorian month grid — `java.util.Calendar`, not `java.time` (minSdk 24 has no
 * core-library desugaring configured, so `java.time` is unavailable). No Hijri secondary
 * line in this slice — that's documented in the design system as a parent-facing feature,
 * not required here.
 */
@Composable
private fun SimpleDatePicker(
    selected: SimpleDate?,
    onSelect: (SimpleDate) -> Unit,
) {
    val today = remember { Calendar.getInstance() }
    var viewYear by remember { mutableIntStateOf(selected?.year ?: today.get(Calendar.YEAR)) }
    var viewMonth by remember { mutableIntStateOf((selected?.month ?: (today.get(Calendar.MONTH) + 1)) - 1) }

    val cal = remember(viewYear, viewMonth) {
        Calendar.getInstance().apply {
            set(Calendar.YEAR, viewYear)
            set(Calendar.MONTH, viewMonth)
            set(Calendar.DAY_OF_MONTH, 1)
        }
    }
    val daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
    val leadingBlanks = cal.get(Calendar.DAY_OF_WEEK) - Calendar.SUNDAY
    val weekdayLabels = listOf(
        R.string.so04_weekday_sun, R.string.so04_weekday_mon, R.string.so04_weekday_tue,
        R.string.so04_weekday_wed, R.string.so04_weekday_thu, R.string.so04_weekday_fri, R.string.so04_weekday_sat,
    )
    val cells: List<Int?> = List(leadingBlanks) { null } + (1..daysInMonth).toList()
    val padded = cells + List((7 - cells.size % 7) % 7) { null }
    val locale = if (isArabicLocale()) Locale.forLanguageTag("ar") else Locale.ENGLISH
    val monthLabel = remember(viewYear, viewMonth, locale) {
        SimpleDateFormat("MMMM yyyy", locale).format(cal.time)
    }

    Column {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            EduIconButton(
                // AutoMirrored: points toward the leading edge in both directions, same
                // convention as the app's back arrow.
                icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = stringResource(R.string.a11y_so04_prev_month),
                onClick = {
                    if (viewMonth == 0) { viewMonth = 11; viewYear-- } else viewMonth--
                },
            )
            Text(
                text = monthLabel,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = Spacing.xs),
            )
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = stringResource(R.string.a11y_so04_next_month),
                onClick = {
                    if (viewMonth == 11) { viewMonth = 0; viewYear++ } else viewMonth++
                },
            )
        }

        Row(modifier = Modifier.fillMaxWidth()) {
            weekdayLabels.forEach { labelRes ->
                Text(
                    text = stringResource(labelRes),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                    modifier = Modifier.weight(1f),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                )
            }
        }

        padded.chunked(7).forEach { week ->
            Row(modifier = Modifier.fillMaxWidth()) {
                week.forEach { day ->
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .weight(1f)
                            .aspectRatio(1f)
                            .then(
                                if (day != null) {
                                    val isSelected = selected?.year == viewYear &&
                                        selected.month == viewMonth + 1 &&
                                        selected.day == day
                                    Modifier
                                        .padding(2.dp)
                                        .background(
                                            if (isSelected) EduTheme.colors.zaytoun else EduTheme.colors.surface,
                                            CircleShape,
                                        )
                                        .eduClickable(onClickLabel = day.toString()) {
                                            onSelect(SimpleDate(viewYear, viewMonth + 1, day))
                                        }
                                } else {
                                    Modifier
                                },
                            ),
                    ) {
                        if (day != null) {
                            val isSelected = selected?.year == viewYear &&
                                selected.month == viewMonth + 1 &&
                                selected.day == day
                            Text(
                                text = numeral(day.toString()),
                                style = EduTheme.typography.body,
                                color = if (isSelected) EduTheme.colors.onZaytoun else EduTheme.colors.textPrimary,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun isArabicLocale(): Boolean =
    androidx.compose.ui.platform.LocalLayoutDirection.current == androidx.compose.ui.unit.LayoutDirection.Rtl
