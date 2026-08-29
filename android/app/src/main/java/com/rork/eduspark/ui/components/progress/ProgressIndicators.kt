package com.rork.eduspark.ui.components.progress

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.standardSpec

/**
 * Progress family — Design System §7.
 *
 * `barq` appears here and essentially nowhere else: XP, streaks, achievements and
 * certificates. It is never a button colour. If barq covers more than ~10% of a
 * screen, something is wrong.
 */

/** Per-subject completion ring, used on the subject grid of ST-01 Student Home. */
@Composable
fun ProgressRing(
    progress: Float,
    modifier: Modifier = Modifier,
    size: androidx.compose.ui.unit.Dp = Sizing.progressRing,
    showLabel: Boolean = true,
) {
    val clamped = progress.coerceIn(0f, 1f)
    val animated by animateFloatAsState(
        targetValue = clamped,
        animationSpec = standardSpec(),
        label = "progressRing",
    )
    val colors = EduTheme.colors
    val percentText = stringResource(R.string.progress_percent, (clamped * 100).toInt())

    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(size)
            .semantics {
                progressBarRangeInfo = ProgressBarRangeInfo(clamped, 0f..1f)
                contentDescription = percentText
            },
    ) {
        Canvas(modifier = Modifier.size(size)) {
            val stroke = Sizing.progressRingStroke.toPx()
            drawCircle(
                color = colors.hajar300,
                radius = (this.size.minDimension - stroke) / 2f,
                style = Stroke(width = stroke),
            )
            drawArc(
                color = colors.zaytoun,
                startAngle = -90f,
                sweepAngle = 360f * animated,
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
                topLeft = androidx.compose.ui.geometry.Offset(stroke / 2f, stroke / 2f),
                size = androidx.compose.ui.geometry.Size(
                    this.size.width - stroke,
                    this.size.height - stroke,
                ),
            )
        }
        if (showLabel) {
            Text(
                // Percentages are numeric data → mono face, numeral-preference aware.
                text = numeral((clamped * 100).toInt()),
                style = EduTheme.typography.mono,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.clearAndSetSemantics { },
            )
        }
    }
}

/** XP level bar. The bar itself is zaytoun; the XP value beside it is barq. */
@Composable
fun LevelBar(
    level: Int,
    progressToNextLevel: Float,
    modifier: Modifier = Modifier,
) {
    val clamped = progressToNextLevel.coerceIn(0f, 1f)
    val animated by animateFloatAsState(
        targetValue = clamped,
        animationSpec = standardSpec(),
        label = "levelBar",
    )
    val levelText = stringResource(R.string.progress_level, level)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = levelText,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
        Box(
            modifier = Modifier
                .weight(1f)
                .height(Spacing.xs)
                .background(EduTheme.colors.hajar300, RoundedCornerShape(Radius.pill))
                .semantics {
                    progressBarRangeInfo = ProgressBarRangeInfo(clamped, 0f..1f)
                    contentDescription = levelText
                },
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(animated)
                    .height(Spacing.xs)
                    .background(EduTheme.colors.zaytoun, RoundedCornerShape(Radius.pill))
            )
        }
    }
}

/** XP chip — barq, and the origin of the sanctioned "XP flight" animation. */
@Composable
fun XpChip(
    xp: Int,
    modifier: Modifier = Modifier,
) {
    val label = stringResource(R.string.progress_xp, xp)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .background(
                EduTheme.colors.barq.copy(alpha = 0.16f),
                RoundedCornerShape(Radius.pill),
            )
            .border(
                Sizing.hairline,
                EduTheme.colors.barq,
                RoundedCornerShape(Radius.pill),
            )
            .padding(horizontal = Spacing.xs, vertical = Spacing.xxs)
            .semantics { contentDescription = label },
    ) {
        Text(
            text = numeral(xp),
            style = EduTheme.typography.mono,
            color = EduTheme.colors.barq,
            modifier = Modifier.clearAndSetSemantics { },
        )
    }
}

/**
 * Streak flame. The count uses ICU plurals so Arabic gets all six categories —
 * "يوم واحد" / "يومان" / "3 أيام" / "11 يوماً" are genuinely different strings.
 */
@Composable
fun StreakFlame(
    days: Int,
    modifier: Modifier = Modifier,
) {
    val label = pluralStringResource(R.plurals.progress_streak_days, days, days)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier.semantics { contentDescription = label },
    ) {
        Icon(
            imageVector = Icons.Filled.LocalFireDepartment,
            contentDescription = null,
            tint = if (days > 0) EduTheme.colors.barq else EduTheme.colors.textMuted,
            modifier = Modifier.size(Sizing.icon),
        )
        Text(
            text = numeral(days),
            style = EduTheme.typography.mono,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.clearAndSetSemantics { },
        )
    }
}

/** CEFR level badge for the English module (LN-01, LN-05, certificates). */
@Composable
fun CefrBadge(
    level: String,
    modifier: Modifier = Modifier,
) {
    val label = stringResource(R.string.progress_cefr_level, level)
    Box(
        modifier = modifier
            .background(EduTheme.colors.zaytounSoft, RoundedCornerShape(Radius.sm))
            .border(Sizing.hairline, EduTheme.colors.zaytoun, RoundedCornerShape(Radius.sm))
            .padding(horizontal = Spacing.xs, vertical = Spacing.xxs)
            .semantics { contentDescription = label },
    ) {
        Text(
            text = level,
            style = EduTheme.typography.mono,
            color = EduTheme.colors.zaytoun,
            modifier = Modifier.clearAndSetSemantics { },
        )
    }
}

/** Determinate linear progress used by uploads and lesson processing (TC-05, TC-06). */
@Composable
fun EduLinearProgress(
    progress: Float,
    modifier: Modifier = Modifier,
    contentDescription: String? = null,
) {
    val clamped = progress.coerceIn(0f, 1f)
    val animated by animateFloatAsState(
        targetValue = clamped,
        animationSpec = standardSpec(),
        label = "linearProgress",
    )
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(6.dp)
            .background(EduTheme.colors.hajar300, RoundedCornerShape(Radius.pill))
            .semantics {
                progressBarRangeInfo = ProgressBarRangeInfo(clamped, 0f..1f)
                if (contentDescription != null) this.contentDescription = contentDescription
            },
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(animated)
                .height(6.dp)
                .background(EduTheme.colors.zaytoun, RoundedCornerShape(Radius.pill))
        )
    }
}
