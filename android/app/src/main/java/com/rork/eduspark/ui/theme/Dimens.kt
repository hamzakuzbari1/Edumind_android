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

    /** Screen gutter — 20pt. */
    val gutter = 20.dp

    /** Section gap — 24pt. */
    val section = 24.dp
    val lg = 32.dp
    val xl = 40.dp

    /** Card padding — 16pt. */
    val card = 16.dp
}

/** Corner radii — Design System §5. Cards `md`, sheets `lg` (top corners), buttons `pill`. */
object Radius {
    val sm = 12.dp
    val md = 18.dp
    val lg = 26.dp
    val pill = 999.dp
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
