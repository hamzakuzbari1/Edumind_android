package com.rork.eduspark.ui.components.ai

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.LocalReducedMotion
import com.rork.eduspark.ui.theme.Motion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * AI surfaces — and the aiAccent trust contract (formerly "jouri").
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The rule (unchanged; only the colour and field name moved — old rose `jouri` has no
 * successor in the new reference, which reuses cyan for AI/insight content instead, see
 * the approved Part 1 §9 decision): anything the AI generated — a tutor reply, an AI hint,
 * a generated quiz, an AI project review — carries an aiAccent hairline or dot. Human-
 * authored content (a teacher's lesson, a parent's note) never does. This is a trust
 * contract with parents, not a style choice.
 *
 * [AiMessageBubble] is therefore the ONLY bubble that may carry aiAccent. A teacher-authored
 * quiz (ST-09) or a parent note (PR-12) uses the plain card, deliberately unmarked.
 *
 * Source Audit note that shapes this component set: **the tutor does not stream.**
 * The backend returns one complete JSON reply after 5–30+ seconds. So the waiting state is
 * an honest [AiTypingIndicator] with a cancel affordance — never a fake token-by-token
 * reveal, which would imply a capability the platform does not have.
 */

/** AI-authored message. aiAccent hairline + aiAccent sparkle mark, always. */
@Composable
fun AiMessageBubble(
    text: String,
    modifier: Modifier = Modifier,
    footer: @Composable (() -> Unit)? = null,
) {
    val aiLabel = stringResource(R.string.a11y_ai_generated)
    val shape = RoundedCornerShape(Radius.md)

    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier
            .fillMaxWidth()
            .semantics { contentDescription = "$aiLabel. $text" },
    ) {
        Icon(
            imageVector = Icons.Filled.AutoAwesome,
            contentDescription = null,
            tint = EduTheme.colors.aiAccent,
            modifier = Modifier
                .padding(top = Spacing.xs)
                .size(Sizing.icon),
        )
        Column(
            modifier = Modifier
                .weight(1f)
                .background(EduTheme.colors.surface, shape)
                .border(Sizing.hairline, EduTheme.colors.aiAccent, shape)
                .padding(Spacing.card),
        ) {
            Text(
                text = text,
                // Reading-heavy surface → body-lg, with the taller Arabic leading.
                style = EduTheme.typography.bodyLg,
                color = EduTheme.colors.textPrimary,
            )
            if (footer != null) {
                Box(modifier = Modifier.padding(top = Spacing.xs)) { footer() }
            }
        }
    }
}

/** Student-authored message. Primary-tinted, never aiAccent-marked. */
@Composable
fun UserMessageBubble(
    text: String,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(Radius.md)
    Row(
        horizontalArrangement = Arrangement.End,
        modifier = modifier.fillMaxWidth(),
    ) {
        Box(modifier = Modifier.width(Spacing.lg))
        Text(
            text = text,
            style = EduTheme.typography.bodyLg,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier
                .background(EduTheme.colors.primaryContainer, shape)
                .padding(Spacing.card),
        )
    }
}

/**
 * Honest waiting indicator for a non-streaming backend.
 *
 * Three dots fading in sequence; under reduced motion it becomes a static row plus the
 * label, and the label is a polite live region so TalkBack announces that a reply is
 * being prepared rather than leaving silence for half a minute.
 */
@Composable
fun AiTypingIndicator(
    modifier: Modifier = Modifier,
) {
    val reduced = LocalReducedMotion.current
    val label = stringResource(R.string.ai_thinking)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier
            .fillMaxWidth()
            .semantics {
                liveRegion = LiveRegionMode.Polite
                contentDescription = label
            },
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
            repeat(3) { index -> TypingDot(index = index, animate = !reduced) }
        }
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
    }
}

@Composable
private fun TypingDot(index: Int, animate: Boolean) {
    val alpha = if (animate) {
        val transition = rememberInfiniteTransition(label = "typing")
        val value by transition.animateFloat(
            initialValue = 0.3f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = Motion.XP_FLIGHT_MS * 2, delayMillis = index * 120),
                repeatMode = RepeatMode.Reverse,
            ),
            label = "typingDot$index",
        )
        value
    } else {
        0.6f
    }

    Box(
        modifier = Modifier
            .size(6.dp)
            .alpha(alpha)
            .background(EduTheme.colors.aiAccent, RoundedCornerShape(Radius.pill))
    )
}

/**
 * Disclosure footer shown at the end of any AI-generated surface.
 *
 * Required wherever the AI produces something a parent might read as authoritative:
 * tutor replies, generated quizzes, project reviews, parent insight cards.
 */
@Composable
fun AiDisclosureFooter(modifier: Modifier = Modifier) {
    Text(
        text = stringResource(R.string.ai_disclosure),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textSecondary,
        modifier = modifier
            .fillMaxWidth()
            .padding(top = Spacing.xs),
    )
}

/**
 * Small aiAccent dot for compact surfaces — an insight card header, a generated quiz row.
 * Use where a full bubble would be too heavy but the provenance still has to be visible.
 */
@Composable
fun AiMarker(modifier: Modifier = Modifier) {
    val label = stringResource(R.string.a11y_ai_generated)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier.semantics { contentDescription = label },
    ) {
        Box(
            modifier = Modifier
                .size(Spacing.xs)
                .background(EduTheme.colors.aiAccent, RoundedCornerShape(Radius.pill))
        )
        Text(
            text = stringResource(R.string.ai_label),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.aiAccent,
        )
    }
}
