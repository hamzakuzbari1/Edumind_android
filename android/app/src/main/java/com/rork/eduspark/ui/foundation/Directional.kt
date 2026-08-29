package com.rork.eduspark.ui.foundation

import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import com.rork.eduspark.ui.theme.EduTheme

/**
 * ══════════════════════════════════════════════════════════════════════════
 * RTL helpers — Design System §6, "non-negotiable".
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Rule 1: `left`/`right` are forbidden; only start/end. Compose resolves start/end from
 * the layout direction automatically, so enforcement is a review rule: never call
 * `Modifier.absolutePadding`, `Alignment.AbsoluteLeft`, or `Arrangement.Absolute.*`.
 *
 * Rule 2: mirror directional icons, and only directional icons.
 */

/**
 * Mirrors a glyph horizontally in RTL.
 *
 * Apply to **directional** icons only: arrows, chevrons, back, send, next, undo/redo.
 * Do NOT apply to clocks, media play/pause, checkmarks, camera, phone or logos —
 * mirroring those is the single most common Arabic-app defect.
 */
@Composable
fun Modifier.mirrorInRtl(): Modifier {
    val isRtl = LocalLayoutDirection.current == LayoutDirection.Rtl
    return if (isRtl) this.scale(scaleX = -1f, scaleY = 1f) else this
}

/**
 * An icon that flips with the reading direction.
 * Use for back/forward/send affordances; use a plain [Icon] for everything else.
 */
@Composable
fun DirectionalIcon(
    imageVector: ImageVector,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    tint: Color = EduTheme.colors.textPrimary,
) {
    Icon(
        imageVector = imageVector,
        contentDescription = contentDescription,
        tint = tint,
        modifier = modifier.mirrorInRtl(),
    )
}

/** +1 in LTR, −1 in RTL. Needed when drawing on a Canvas, where direction is not automatic. */
@Composable
@ReadOnlyComposable
fun directionSign(): Float = if (EduTheme.isRtl) -1f else 1f
