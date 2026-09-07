package com.rork.eduspark.ui.screens.onboarding

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.Track
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-01 · Onboarding: Grade
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "Picking البكالوريا reveals the branch fork inline instead of pushing another screen,
 * because branch is part of the same decision." (onboarding PDF.) [AnimatedVisibility]
 * handles that inline reveal; nothing about it is a separate screen or route.
 *
 * Follows the house rule from A-04 onward: the primary action stays enabled and validates
 * on press, never a dead grey button — see [showValidation].
 */
@Composable
fun OnboardingGradeScreen(
    onBack: () -> Unit,
    onContinue: () -> Unit,
    viewModel: OnboardingViewModel,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showValidation by remember { mutableStateOf(false) }

    BackHandler { onBack() }

    OnboardingStepScaffold(
        step = 1,
        onBack = onBack,
        bottomBar = {
            if (showValidation && !state.canContinueFromGrade) {
                Text(
                    text = stringResource(
                        if (state.grade == null) R.string.so01_error_grade else R.string.so01_error_track
                    ),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.so01_continue),
                onClick = { if (state.canContinueFromGrade) onContinue() else showValidation = true },
                modifier = Modifier.fillMaxWidth(),
            )
        },
    ) {
        Text(
            text = stringResource(R.string.so01_title),
            style = EduTheme.typography.titleLg,
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.so01_body),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.padding(top = Spacing.section),
        ) {
            GradeCard(
                monogram = "10",
                title = stringResource(R.string.a07_grade_10),
                hint = stringResource(R.string.so01_grade_10_hint),
                selected = state.grade == Grade.Grade10,
                onClick = { viewModel.selectGrade(Grade.Grade10) },
            )
            GradeCard(
                monogram = "11",
                title = stringResource(R.string.a07_grade_11),
                hint = stringResource(R.string.so01_grade_11_hint),
                selected = state.grade == Grade.Grade11,
                onClick = { viewModel.selectGrade(Grade.Grade11) },
            )
            GradeCard(
                monogram = "12",
                title = stringResource(R.string.a07_grade_12),
                hint = stringResource(R.string.so01_grade_12_hint),
                selected = state.grade == Grade.Baccalaureate,
                onClick = { viewModel.selectGrade(Grade.Baccalaureate) },
            )
        }

        AnimatedVisibility(visible = state.grade == Grade.Baccalaureate) {
            Column(modifier = Modifier.padding(top = Spacing.md)) {
                Text(
                    text = stringResource(R.string.so01_track_label),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                ) {
                    EduChip(
                        label = stringResource(R.string.so01_track_science),
                        selected = state.track == Track.Science,
                        onClick = { viewModel.selectTrack(Track.Science) },
                        modifier = Modifier.weight(1f),
                    )
                    EduChip(
                        label = stringResource(R.string.so01_track_literary),
                        selected = state.track == Track.Literary,
                        onClick = { viewModel.selectTrack(Track.Literary) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

/**
 * One grade choice — monogram tile swaps for a checkmark when selected (Design System §3:
 * state is never colour alone), border thickens and tints. Shared visual family with A-03's
 * RoleCard, kept as its own small composable here rather than exporting that one, since the
 * two screens' selection semantics differ (role picking navigates away; grade picking stays
 * on the same screen and can be changed again before Continue).
 */
@Composable
private fun GradeCard(
    monogram: String,
    title: String,
    hint: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface, shape)
            .border(
                width = if (selected) Sizing.hairline * 2 else Sizing.hairline,
                color = if (selected) colors.zaytoun else colors.border,
                shape = shape,
            )
            .eduClickable(onClickLabel = title, onClick = onClick)
            .padding(Spacing.card),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(40.dp)
                .background(colors.zaytounSoft, RoundedCornerShape(Radius.sm)),
        ) {
            if (selected) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = colors.zaytoun,
                    modifier = Modifier.size(Sizing.icon),
                )
            } else {
                Text(text = monogram, style = EduTheme.typography.title, color = colors.zaytoun)
            }
        }

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
            )
            Text(text = hint, style = EduTheme.typography.caption, color = colors.textMuted)
        }
    }
}
