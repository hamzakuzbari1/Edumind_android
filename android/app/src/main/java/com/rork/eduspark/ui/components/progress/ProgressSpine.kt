package com.rork.eduspark.ui.components.progress

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.spineFillSpec

/**
 * ══════════════════════════════════════════════════════════════════════════
 * THE PROGRESS SPINE (المسار) — Design System §2, the app's signature element.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A single continuous vertical rail along the **leading edge** of the screen — the right
 * edge in Arabic, the left in English — with lessons, milestones and project stages as
 * beads on it.
 *
 * It is not decoration; it is the app's information architecture made visible, and it is
 * the same object on a course page (ST-02), a language learning path (LN-07) and a project
 * milestone board (PJ-03). It is the one thing a user should be able to describe when
 * asked what EduSpark looks like.
 *
 * Bead vocabulary:
 *  • [SpineNodeState.Completed] — filled zaytoun, solid rail between beads.
 *  • [SpineNodeState.Current]   — larger, highlight ring, gentle pulse (off under reduced motion).
 *  • [SpineNodeState.Locked]    — hollow bead, hairline rail.
 *
 * Hard rules encoded here:
 *  • **One spine per screen, maximum.** Screens without sequence — settings, messages,
 *    profile — have no spine at all.
 *  • Leading-edge placement is automatic: the composable is a [Row] whose first child is
 *    the rail, so Compose puts it on the correct side per locale with no branching.
 *  • Each row exposes a single merged accessibility node ("Lesson 3, completed"), so a
 *    TalkBack user hears the state rather than swiping past decorative graphics.
 */
enum class SpineNodeState { Completed, Current, Locked }

/** One bead and the content beside it. */
data class SpineNode(
    val id: String,
    val state: SpineNodeState,
)

/**
 * Renders one spine row: the rail segment + bead on the leading edge, then [content].
 *
 * Rows are rendered individually (rather than the whole spine drawing itself) so that
 * spines can live inside a `LazyColumn` and stay virtualised on long courses — a course
 * with 60 lessons must not compose 60 rows at once on a 2GB device.
 *
 * @param isFirst hides the rail above the bead for the first row.
 * @param isLast hides the rail below the bead for the last row.
 */
@Composable
fun SpineRow(
    node: SpineNode,
    isFirst: Boolean,
    isLast: Boolean,
    modifier: Modifier = Modifier,
    accessibilityLabel: String? = null,
    content: @Composable () -> Unit,
) {
    val stateLabel = when (node.state) {
        SpineNodeState.Completed -> stringResource(R.string.a11y_spine_completed)
        SpineNodeState.Current -> stringResource(R.string.a11y_spine_current)
        SpineNodeState.Locked -> stringResource(R.string.a11y_spine_locked)
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            // IntrinsicSize.Min lets the rail stretch to exactly the height of the row's
            // content, which is what makes the spine continuous across rows of any height.
            .height(IntrinsicSize.Min)
            .semantics {
                if (accessibilityLabel != null) {
                    contentDescription = "$accessibilityLabel, $stateLabel"
                }
            },
    ) {
        SpineRail(
            state = node.state,
            isFirst = isFirst,
            isLast = isLast,
            modifier = Modifier
                .width(Sizing.spineGutter)
                .fillMaxHeight(),
        )
        Box(modifier = Modifier.padding(bottom = Spacing.sm).fillMaxWidth()) {
            content()
        }
    }
}

/**
 * The rail + bead column. Drawn on a [Canvas] rather than composed from shapes so the
 * whole spine costs one draw call per row on the device floor.
 */
@Composable
private fun SpineRail(
    state: SpineNodeState,
    isFirst: Boolean,
    isLast: Boolean,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    // Spine fill — 400ms ease-out, collapsed to an instant change under reduced motion.
    val fill by animateFloatAsState(
        targetValue = if (state == SpineNodeState.Locked) 0f else 1f,
        animationSpec = spineFillSpec(),
        label = "spineFill",
    )

    val railActive = colors.primary
    val railInactive = colors.border
    val beadRadius = when (state) {
        SpineNodeState.Current -> Sizing.spineBeadCurrent / 2
        else -> Sizing.spineBead / 2
    }

    Canvas(
        modifier = modifier.clearAndSetSemantics { },
    ) {
        val centerX = size.width / 2f
        val centerY = Sizing.touchTarget.toPx() / 2f
        val railWidth = Sizing.spineRail.toPx()
        val radiusPx = beadRadius.toPx()

        fun railColor(active: Boolean): Color = if (active) railActive else railInactive

        // Rail above the bead — solid when this node has been reached.
        if (!isFirst) {
            drawLine(
                color = railColor(state != SpineNodeState.Locked),
                start = Offset(centerX, 0f),
                end = Offset(centerX, centerY - radiusPx),
                strokeWidth = railWidth,
            )
        }

        // Rail below the bead — solid only once this node is complete.
        if (!isLast) {
            drawLine(
                color = railColor(state == SpineNodeState.Completed),
                start = Offset(centerX, centerY + radiusPx),
                end = Offset(centerX, size.height),
                strokeWidth = railWidth,
            )
        }

        when (state) {
            SpineNodeState.Completed -> drawCircle(
                color = railActive,
                radius = radiusPx * fill.coerceAtLeast(0.6f),
                center = Offset(centerX, centerY),
            )

            SpineNodeState.Current -> {
                drawCircle(
                    color = colors.surface,
                    radius = radiusPx,
                    center = Offset(centerX, centerY),
                )
                // Highlight ring marks "you are here" — one of the few sanctioned highlight usages.
                drawCircle(
                    color = colors.highlight,
                    radius = radiusPx,
                    center = Offset(centerX, centerY),
                    style = Stroke(width = railWidth * 1.5f),
                )
                drawCircle(
                    color = railActive,
                    radius = radiusPx * 0.42f,
                    center = Offset(centerX, centerY),
                )
            }

            SpineNodeState.Locked -> drawCircle(
                color = railInactive,
                radius = radiusPx,
                center = Offset(centerX, centerY),
                style = Stroke(width = railWidth),
            )
        }
    }
}

/**
 * Convenience wrapper for short, non-virtualised spines (onboarding steps, a 4-milestone
 * project board). For long sequences use [SpineRow] inside a `LazyColumn` instead.
 */
@Composable
fun ProgressSpine(
    nodes: List<SpineNode>,
    modifier: Modifier = Modifier,
    rowContent: @Composable (index: Int, node: SpineNode) -> Unit,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        nodes.forEachIndexed { index, node ->
            SpineRow(
                node = node,
                isFirst = index == 0,
                isLast = index == nodes.lastIndex,
            ) {
                rowContent(index, node)
            }
        }
    }
}

/**
 * Horizontal variant used only where a sequence is short and the screen is a runner —
 * the quiz progress strip at the top of ST-06, and the onboarding step indicator.
 * It is the same vocabulary, rotated; it does not replace the vertical spine.
 */
@Composable
fun HorizontalSpine(
    total: Int,
    currentIndex: Int,
    modifier: Modifier = Modifier,
    contentDescription: String? = null,
) {
    val colors = EduTheme.colors
    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(Sizing.spineBead)
            .semantics {
                if (contentDescription != null) this.contentDescription = contentDescription
            },
    ) {
        if (total <= 0) return@Canvas
        val gap = 4.dp.toPx()
        val segmentWidth = (size.width - gap * (total - 1)) / total
        val y = size.height / 2f

        repeat(total) { index ->
            // Start from the leading edge: right in RTL, left in LTR.
            val fromStart = if (layoutDirection == androidx.compose.ui.unit.LayoutDirection.Rtl) {
                size.width - (index + 1) * segmentWidth - index * gap
            } else {
                index * (segmentWidth + gap)
            }
            drawRoundRect(
                // Current and completed segments are both indigo (approved design: ST-06's
                // horizontal strip does not colour-differentiate "current" from "done" — see
                // QuizRunner.dc.html's `.seg.cur{background:#6366F1}`, identical to `.seg.done`).
                // Only the vertical spine's bead ring keeps the amber "current" treatment.
                color = when {
                    index <= currentIndex -> colors.primary
                    else -> colors.border
                },
                topLeft = Offset(fromStart, y - Sizing.spineRail.toPx()),
                size = androidx.compose.ui.geometry.Size(segmentWidth, Sizing.spineRail.toPx() * 2),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(Sizing.spineRail.toPx()),
            )
        }
    }
}
