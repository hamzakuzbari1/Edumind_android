package com.rork.eduspark.ui.theme

import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf

/**
 * Motion tokens — Design System §8.
 *
 * Restrained by default, with exactly three sanctioned moments:
 *  1. **Spine fill** — the rail fills from the previous bead to the current one (400ms
 *     ease-out), then the bead pops (150ms).
 *  2. **XP flight** — the XP chip flies to the tab-bar profile icon (300ms).
 *  3. **Celebration** — confetti + barq wash, for level-up, promotion pass and certificate
 *     issue only. Nowhere else.
 *
 * Everything else is a 150–200ms opacity/transform crossfade. No parallax, no blur, no
 * ambient loops — they cost battery on the device floor.
 *
 * Under reduced motion all three sanctioned moments collapse to instant state changes.
 */
object Motion {
    const val QUICK_MS = 150
    const val STANDARD_MS = 200
    const val XP_FLIGHT_MS = 300
    const val SPINE_FILL_MS = 400
}

/**
 * True when the user has asked the system to remove animations, or has switched the
 * in-app reduce-motion override on. Read it via [rememberReducedMotionSpec] rather
 * than branching by hand in each component.
 */
val LocalReducedMotion = staticCompositionLocalOf { false }

/** Returns [spec], or an instant [snap] when reduced motion is active. */
@Composable
@ReadOnlyComposable
fun <T> reducedMotionAware(spec: AnimationSpec<T>): AnimationSpec<T> =
    if (LocalReducedMotion.current) snap() else spec

@Composable
@ReadOnlyComposable
fun spineFillSpec(): AnimationSpec<Float> =
    reducedMotionAware(tween(Motion.SPINE_FILL_MS, easing = LinearOutSlowInEasing))

@Composable
@ReadOnlyComposable
fun standardSpec(): AnimationSpec<Float> =
    reducedMotionAware(tween(Motion.STANDARD_MS, easing = FastOutSlowInEasing))

@Composable
@ReadOnlyComposable
fun quickSpec(): AnimationSpec<Float> =
    reducedMotionAware(tween(Motion.QUICK_MS, easing = FastOutSlowInEasing))
