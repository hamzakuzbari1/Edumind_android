package com.rork.eduspark.ui.screens.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.progress.HorizontalSpine
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-01 … SO-04 shared shell — the horizontal Progress Spine at "step X / 4".
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "The Progress Spine turns horizontal across the top and runs 1/4 → 4/4 — same bead
 * vocabulary as the vertical spine." (onboarding PDF.) Reuses [HorizontalSpine] as-is —
 * the same component ST-06's quiz runner and A-13's transition already use — rather than a
 * new progress primitive. SO-05 is the payoff, not a step, so it does not use this shell.
 */
@Composable
fun OnboardingStepScaffold(
    step: Int,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    bottomBar: @Composable ColumnScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding()
            .imePadding(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.topBarHeight)
                .padding(horizontal = Spacing.xs),
        ) {
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(R.string.a11y_back),
                onClick = onBack,
            )
            Box(modifier = Modifier.weight(1f))
            Text(
                text = stringResource(R.string.so_step_label, step, TOTAL_STEPS),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
                modifier = Modifier.padding(end = Spacing.gutter),
            )
        }

        HorizontalSpine(
            total = TOTAL_STEPS,
            currentIndex = step - 1,
            contentDescription = stringResource(R.string.so_step_label, step, TOTAL_STEPS),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter),
        )

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter),
        ) {
            Spacer(modifier = Modifier.height(Spacing.section))
            content()
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter)
                .padding(top = Spacing.sm, bottom = Spacing.md),
            content = bottomBar,
        )
    }
}

private const val TOTAL_STEPS = 4
