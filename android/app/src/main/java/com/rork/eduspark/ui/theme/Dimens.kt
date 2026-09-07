package com.rork.eduspark.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

/**
 * Layout tokens — Design System §5.
 * 4pt base grid. Every spacing value in the app comes from here; magic numbers are defects.
 */
object Spacing {
    /** 4pt — the grid unit. */
    val grid = 4.dp
    val xxs = 4.dp
    val xs = 8.dp
    val sm = 12.dp
    val md = 16.dp

    /** Screen gutter — 18pt (was 20pt; recalibrated to the new reference's dominant edge padding). */
    val gutter = 18.dp

    /** Section gap — 24pt. */
    val section = 24.dp
    val lg = 32.dp
    val xl = 40.dp

    /** Card padding — 18pt (was 16pt; matches the new reference's dominant card padding). */
    val card = 18.dp
}

/** Corner radii — new identity. Cards `md`, sheets `lg` (top corners), buttons `pill`. */
object Radius {
    val sm = 12.dp
    val md = 18.dp

    /** 22dp (was 26dp) — recalibrated to the new reference's largest non-pill card radius. */
    val lg = 22.dp
    val pill = 999.dp
}

/**
 * Soft coloured shadow — new to this identity. The old system banned shadows outright for
 * low-end-GPU cost; the new reference uses them, but only on primary/floating action
 * affordances (CTA button, FAB, record button), never on ordinary cards or list rows. Keep
 * that scoping when using this token — everything else stays flat (tint + hairline).
 */
object Elevation {
    val action = 8.dp

    /** Alpha applied to the action's own colour for both the ambient and spot shadow. */
    const val actionTint = 0.35f
}

object Sizing {
    /**
     * Minimum touch target — 48×48, always. "Students use this on the bus."
     * Never lower this for visual tidiness; shrink the visual, keep the target.
     */
    val touchTarget = 48.dp

    /** Elevation is expressed as tint + hairline, never as a soft shadow. */
    val hairline = 1.dp

    val iconSm = 16.dp
    val icon = 20.dp
    val iconLg = 24.dp

    /** Illustration-free state glyph (empty / error / offline screens). */
    val stateIcon = 44.dp

    val tabBarHeight = 64.dp
    val topBarHeight = 56.dp

    // Progress Spine geometry — the app's signature element.
    /** Width of the column the spine occupies on the leading edge. */
    val spineGutter = 40.dp
    val spineRail = 2.dp
    val spineBead = 14.dp
    val spineBeadCurrent = 22.dp

    val progressRing = 44.dp
    val progressRingStroke = 4.dp
    val avatarSm = 32.dp
    val avatar = 44.dp

    /**
     * Named "hero" sizes — replaces the ad hoc `Sizing.X * 1.3f/1.4f/1.6f/1.8f/2f` multipliers
     * scattered across celebration/summary screens (ST-05, ST-07, ST-15, ST-20, ST-21, ST-22,
     * PJ-10). Each absorbs one existing cluster of near-identical rendered sizes rather than
     * collapsing every hero element to one size — the three levels preserve the same rough
     * visual hierarchy those screens already had, just from one shared token instead of each
     * screen inventing its own multiplier.
     */
    val avatarLg = 64.dp
    val heroRing = 72.dp
    val heroBadge = 88.dp
}

/**
 * Material 3 shape mapping so built-in M3 components (sheets, menus, dialogs)
 * inherit EduSpark radii instead of Material defaults.
 */
val EduShapes = Shapes(
    extraSmall = RoundedCornerShape(Radius.sm),
    small = RoundedCornerShape(Radius.sm),
    medium = RoundedCornerShape(Radius.md),
    large = RoundedCornerShape(Radius.lg),
    extraLarge = RoundedCornerShape(Radius.lg),
)
