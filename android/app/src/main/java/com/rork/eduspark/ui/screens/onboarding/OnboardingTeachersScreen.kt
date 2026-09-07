package com.rork.eduspark.ui.screens.onboarding

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
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
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.surface.SkeletonBlock
import com.rork.eduspark.ui.components.surface.SkeletonCircle
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-03 · Onboarding: Teachers
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One horizontally-scrolling row per chosen subject, one teacher selected per row. Reuses
 * [SkeletonBlock]/[SkeletonCircle] for the loading state (A-14's primitives, composed into a
 * card-shaped skeleton here rather than a new component) and [UiState] for per-subject
 * loading/content/error — teacher data is genuinely server-driven (Source Audit §2), so it
 * is fetched through [OnboardingRepository], not baked into the screen.
 *
 * The intro-voice control is visual only, per this slice's scope — it toggles a play/pause
 * icon locally and plays nothing. No audio, no backend.
 */
@Composable
fun OnboardingTeachersScreen(
    onBack: () -> Unit,
    onContinue: () -> Unit,
    viewModel: OnboardingViewModel,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showValidation by remember { mutableStateOf(false) }

    BackHandler { onBack() }

    LaunchedEffect(Unit) { viewModel.loadTeachersIfNeeded() }

    OnboardingStepScaffold(
        step = 3,
        onBack = onBack,
        bottomBar = {
            if (showValidation && !state.canContinueFromTeachers) {
                Text(
                    text = stringResource(R.string.so03_error_teachers),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.so03_continue),
                onClick = { if (state.canContinueFromTeachers) onContinue() else showValidation = true },
                modifier = Modifier.fillMaxWidth(),
            )
        },
    ) {
        Text(
            text = stringResource(R.string.so03_title),
            style = EduTheme.typography.titleLg,
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.so03_body),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        state.subjectIds.forEach { subjectId ->
            val subjectLabel = OnboardingCatalog.byId(subjectId)?.labelRes?.let { stringResource(it) } ?: subjectId

            Text(
                text = subjectLabel,
                style = EduTheme.typography.title,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.section, bottom = Spacing.sm),
            )

            when (val teachers = state.teachersBySubject[subjectId] ?: UiState.Loading) {
                is UiState.Loading -> TeacherRowSkeleton()

                is UiState.Content -> Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                ) {
                    teachers.data.forEach { teacher ->
                        TeacherCard(
                            teacher = teacher,
                            selected = state.selectedTeacherIdBySubject[subjectId] == teacher.id,
                            onClick = { viewModel.selectTeacher(subjectId, teacher.id) },
                        )
                    }
                }

                is UiState.Empty -> Text(
                    text = stringResource(R.string.state_empty_default_body),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                )

                is UiState.Failure -> TeacherRowError(onRetry = { viewModel.retryTeachers(subjectId) })
            }
        }
    }
}

@Composable
private fun TeacherRowSkeleton() {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        repeat(2) {
            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .width(TeacherCardWidth)
                    .background(EduTheme.colors.surface, RoundedCornerShape(Radius.md))
                    .border(Sizing.hairline, EduTheme.colors.border, RoundedCornerShape(Radius.md))
                    .padding(Spacing.card),
            ) {
                SkeletonCircle(size = Sizing.avatar)
                SkeletonBlock(widthFraction = 0.8f, height = 16.dp)
                SkeletonBlock(widthFraction = 0.5f, height = 12.dp)
            }
        }
    }
}

@Composable
private fun TeacherRowError(onRetry: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Icon(
            imageVector = Icons.Filled.ErrorOutline,
            contentDescription = null,
            tint = EduTheme.colors.danger,
            modifier = Modifier.size(Sizing.icon),
        )
        Text(
            text = stringResource(R.string.state_error_network_body),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.weight(1f),
        )
        SecondaryButton(text = stringResource(R.string.common_retry), onClick = onRetry)
    }
}

private val TeacherCardWidth = 220.dp

@Composable
private fun TeacherCard(
    teacher: OnboardingTeacher,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    var isPlayingIntro by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .width(TeacherCardWidth)
            .background(colors.surface, shape)
            .border(
                width = if (selected) Sizing.hairline * 2 else Sizing.hairline,
                color = if (selected) colors.zaytoun else colors.border,
                shape = shape,
            )
            .eduClickable(onClickLabel = teacher.name, onClick = onClick)
            .padding(Spacing.card),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.zaytounSoft, CircleShape),
            ) {
                Text(
                    text = teacher.name.take(1),
                    style = EduTheme.typography.title,
                    color = colors.zaytoun,
                )
            }
            if (selected) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = colors.zaytoun,
                    modifier = Modifier.size(Sizing.icon),
                )
            }
        }

        Text(
            text = teacher.name,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(
            text = pluralStringResource(R.plurals.so03_years_teaching, teacher.yearsTeaching, teacher.yearsTeaching),
            style = EduTheme.typography.caption,
            color = colors.textMuted,
        )

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            modifier = Modifier.padding(top = Spacing.xxs),
        ) {
            Icon(
                imageVector = Icons.Filled.Star,
                contentDescription = null,
                tint = colors.barq,
                modifier = Modifier.size(Sizing.iconSm),
            )
            Text(text = numeral("%.1f".format(teacher.rating)), style = EduTheme.typography.caption, color = colors.textPrimary)
            Text(
                text = pluralStringResource(R.plurals.so03_students_count, teacher.studentCount, teacher.studentCount),
                style = EduTheme.typography.caption,
                color = colors.textMuted,
            )
        }

        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        ) {
            EduIconButton(
                icon = if (isPlayingIntro) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                contentDescription = stringResource(
                    if (isPlayingIntro) R.string.a11y_so03_pause_intro else R.string.a11y_so03_play_intro
                ),
                tint = colors.zaytoun,
                onClick = { isPlayingIntro = !isPlayingIntro },
            )
            Text(
                text = numeral("0:%02d".format(teacher.introClipSeconds)),
                style = EduTheme.typography.mono,
                color = colors.textMuted,
            )
            Spacer(modifier = Modifier.weight(1f))
            Column(horizontalAlignment = Alignment.End) {
                Text(text = stringResource(R.string.so03_per_session), style = EduTheme.typography.caption, color = colors.textMuted)
                Text(
                    text = teacher.priceLabel,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.zaytoun,
                )
            }
        }
    }
}
