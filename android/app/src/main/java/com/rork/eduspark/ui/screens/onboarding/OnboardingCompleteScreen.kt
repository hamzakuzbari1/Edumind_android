package com.rork.eduspark.ui.screens.onboarding

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.OnboardingAnswers
import com.rork.eduspark.data.model.StudyHoursPerDay
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.Track
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-05 · Onboarding: Complete
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "The payoff, not a fifth step — so the spine is gone." No [OnboardingStepScaffold] here on
 * purpose. `+50 XP` is one of the design system's sanctioned `barq` moments (celebration),
 * built from the existing [StatusPill] rather than a new badge component.
 *
 * The primary action calls the canonical completion endpoint and only leaves this graph
 * after /auth/me confirms that onboarding is complete.
 */
@Composable
fun OnboardingCompleteScreen(
    onChangeGrade: () -> Unit,
    onChangeSubjects: () -> Unit,
    onChangeTeachers: () -> Unit,
    onChangeStudy: () -> Unit,
    onStart: () -> Unit,
    viewModel: OnboardingViewModel,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // The payoff screen does not step backward — consumed, not delegated to onBack.
    BackHandler {}

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                OnboardingEvent.Completed -> onStart()
                else -> Unit
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = Spacing.gutter),
    ) {
        Spacer(modifier = Modifier.height(Spacing.section))

        CelebrationHeader(name = state.studentName)

        Spacer(modifier = Modifier.height(Spacing.section))

        SummaryCard(
            state = state,
            onChangeGrade = onChangeGrade,
            onChangeSubjects = onChangeSubjects,
            onChangeTeachers = onChangeTeachers,
            onChangeStudy = onChangeStudy,
        )

        Text(
            text = stringResource(R.string.so05_footer_note),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )

        Spacer(modifier = Modifier.height(Spacing.section))

        if (state.completionFailed) {
            Text(
                text = stringResource(R.string.state_error_unknown_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.danger,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }

        PrimaryButton(
            text = stringResource(R.string.so05_cta),
            onClick = viewModel::completeOnboarding,
            isLoading = state.isCompleting,
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(modifier = Modifier.height(Spacing.section))
    }
}

@Composable
private fun CelebrationHeader(name: String) {
    val colors = EduTheme.colors
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(72.dp)
                .background(colors.barq.copy(alpha = if (colors.isDark) 0.25f else 0.15f), CircleShape),
        ) {
            Icon(
                imageVector = Icons.Filled.CheckCircle,
                contentDescription = null,
                tint = colors.barq,
                modifier = Modifier.size(40.dp),
            )
        }

        Text(
            text = stringResource(R.string.so05_celebration_title, name),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.md),
        )
        Text(
            text = stringResource(R.string.so05_celebration_body),
            style = EduTheme.typography.body,
            color = colors.textMuted,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        StatusPill(
            label = stringResource(R.string.so05_xp_earned),
            contentColor = colors.onBarq,
            containerColor = colors.barq,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun SummaryCard(
    state: OnboardingUiState,
    onChangeGrade: () -> Unit,
    onChangeSubjects: () -> Unit,
    onChangeTeachers: () -> Unit,
    onChangeStudy: () -> Unit,
) {
    EduCard {
        Text(
            text = stringResource(R.string.so05_summary_title),
            style = EduTheme.typography.title,
            color = EduTheme.colors.textPrimary,
        )

        SummaryRow(R.string.so05_field_grade, gradeSummary(state.grade, state.track), onChangeGrade)
        EduDivider()
        SummaryRow(R.string.so05_field_subjects, subjectsSummary(state), onChangeSubjects)
        EduDivider()
        SummaryRow(R.string.so05_field_teachers, teachersSummary(state), onChangeTeachers)
        EduDivider()
        SummaryRow(R.string.so05_field_study, studySummary(state.answers), onChangeStudy)
        EduDivider()
        SummaryRow(R.string.so05_field_exam, examSummary(state.answers), onChangeStudy)
    }
}

@Composable
private fun SummaryRow(labelRes: Int, value: String, onChange: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.sm),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = stringResource(labelRes), style = EduTheme.typography.caption, color = EduTheme.colors.textMuted)
            Text(
                text = value,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        GhostButton(text = stringResource(R.string.a08_change_email_action), onClick = onChange)
    }
}

@Composable
private fun gradeSummary(grade: Grade?, track: Track?): String {
    val gradeLabel = when (grade) {
        Grade.Grade10 -> stringResource(R.string.a07_grade_10)
        Grade.Grade11 -> stringResource(R.string.a07_grade_11)
        Grade.Baccalaureate -> stringResource(R.string.a07_grade_12)
        null -> ""
    }
    return if (track != null) {
        val trackLabel = stringResource(if (track == Track.Science) R.string.so01_track_science else R.string.so01_track_literary)
        stringResource(R.string.so05_grade_track_format, gradeLabel, trackLabel)
    } else {
        gradeLabel
    }
}

@Composable
private fun subjectsSummary(state: OnboardingUiState): String {
    val subjects = (state.availableSubjects as? UiState.Content)?.data.orEmpty()
    return subjects.filter { it.id in state.subjectIds }.joinToString(", ") { it.name }
}

@Composable
private fun teachersSummary(state: OnboardingUiState): String {
    val lines = state.subjectIds.mapNotNull { subjectId ->
        val teacherId = state.selectedTeacherIdBySubject[subjectId] ?: return@mapNotNull null
        val teachersState = state.teachersBySubject[subjectId]
        val teachers = if (teachersState is UiState.Content) teachersState.data else emptyList()
        val teacherName = teachers.firstOrNull { it.id == teacherId }?.name ?: return@mapNotNull null
        val subjectLabel = (state.availableSubjects as? UiState.Content)
            ?.data
            ?.firstOrNull { it.id == subjectId }
            ?.name
            ?: subjectId
        "$teacherName · $subjectLabel"
    }
    return lines.joinToString("\n")
}

@Composable
private fun studySummary(answers: OnboardingAnswers): String {
    val hoursLabel = when (answers.studyHours) {
        StudyHoursPerDay.ThirtyMinutes -> stringResource(R.string.so04_hours_30min)
        StudyHoursPerDay.OneHour -> stringResource(R.string.so04_hours_1h)
        StudyHoursPerDay.TwoHours -> stringResource(R.string.so04_hours_2h)
        StudyHoursPerDay.ThreePlusHours -> stringResource(R.string.so04_hours_3h_plus)
        null -> stringResource(R.string.so04_not_sure_yet)
    }
    val timeLabel = when (answers.studyTime) {
        StudyTimeOfDay.EarlyMorning -> stringResource(R.string.so04_time_morning)
        StudyTimeOfDay.Afternoon -> stringResource(R.string.so04_time_afternoon)
        StudyTimeOfDay.Evening -> stringResource(R.string.so04_time_evening)
        StudyTimeOfDay.LateNight -> stringResource(R.string.so04_time_late)
        null -> stringResource(R.string.so04_not_sure_yet)
    }
    return stringResource(R.string.so05_study_summary, hoursLabel, timeLabel)
}

@Composable
private fun examSummary(answers: OnboardingAnswers): String {
    val date = answers.examDate ?: return stringResource(R.string.so05_exam_not_sure)
    val days = daysUntil(date).coerceAtLeast(0)
    return pluralStringResource(R.plurals.so04_exam_days_until, days, days)
}
