package com.rork.eduspark.ui.screens.auth

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.ui.components.progress.HorizontalSpine
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.reducedMotionAware
import kotlinx.coroutines.delay

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-13 · Locale Switch Transition
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "The 1-second branded reload when direction flips. Logo + spine sweeping from one edge to
 * the other." (Screen Inventory.) This does not touch the locale system itself —
 * [LocaleController]/`AppCompatDelegate` still own applying the locale and the resulting
 * activity recreation; this screen only supplies the branded frame the app is showing at the
 * moment that recreation happens, via [onComplete], which the caller wires to the real
 * `setLocale`. Reuses [HorizontalSpine] — the app's existing signature progress element —
 * rather than inventing new motion primitives for a screen that exists for about a second.
 *
 * Only screens *switching* locale mid-flow (ValueCarousel, RoleSelect, Login, Register) route
 * through here. A-01's first-run language gate does not — there is no prior direction to
 * flip *from* on first launch, so it applies its choice directly.
 */
@Composable
fun LocaleSwitchScreen(
    target: AppLocale,
    onComplete: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val progress = remember(target) { Animatable(0f) }
    val sweepSpec: AnimationSpec<Float> = reducedMotionAware(tween(SWEEP_MS, easing = LinearOutSlowInEasing))

    LaunchedEffect(target) {
        progress.animateTo(1f, animationSpec = sweepSpec)
        // A minimum dwell even under reduced motion (an instant snap still needs a frame the
        // eye can register as "something branded happened"), never counted as motion itself.
        delay(MIN_HOLD_MS)
        onComplete()
    }

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding()
            .padding(Spacing.gutter),
    ) {
        BrandMark(size = 64.dp)

        Spacer(modifier = Modifier.height(Spacing.lg))

        HorizontalSpine(
            total = SWEEP_SEGMENTS,
            currentIndex = (progress.value * SWEEP_SEGMENTS).toInt(),
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

private const val SWEEP_MS = 700
private const val SWEEP_SEGMENTS = 6
private const val MIN_HOLD_MS = 400L
