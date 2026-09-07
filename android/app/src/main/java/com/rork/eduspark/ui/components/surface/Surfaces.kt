package com.rork.eduspark.ui.components.surface

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.foundation.mirrorInRtl
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Surfaces — Design System §5 and §7.
 *
 * Elevation has exactly two levels and neither uses a shadow:
 *  • Level 1 (cards)  = `surface` on `background` + a 1px `border` hairline.
 *  • Level 2 (sheets) = `surface` + hairline + a 6% scrim behind it.
 *
 * Soft shadows are banned outright — cheap Android GPUs render them badly and it costs
 * frames on the 2–3GB device floor.
 */

/** The app has ONE card. Extend this rather than creating a near-duplicate. */
@Composable
fun EduCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    onClickLabel: String? = null,
    containerColor: Color = EduTheme.colors.surface,
    borderColor: Color = EduTheme.colors.border,
    contentPadding: PaddingValues = PaddingValues(Spacing.card),
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(Radius.md)
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(containerColor, shape)
            .border(BorderStroke(Sizing.hairline, borderColor), shape)
            .then(
                if (onClick != null) {
                    Modifier.eduClickable(onClickLabel = onClickLabel, onClick = onClick)
                } else {
                    Modifier
                }
            )
            .padding(contentPadding),
        content = content,
    )
}

/**
 * [EduCard]'s subtle/grouped sibling — same shape and padding rhythm, but a tint-only
 * treatment (`neutralAlpha100` fill, no hairline) instead of `surface` + border. This is the
 * same "elevation is tint, never a shadow" rule this file's own doc comment already states,
 * applied one step lighter than the primary card's level-1 treatment — not a new visual
 * language, just the existing secondary-surface tint (`neutralAlpha100`) the app already uses
 * for skeletons, disabled buttons and the offline banner, now available as a card shape.
 *
 * Use this for supporting/grouped content sitting *inside* an already-bordered primary
 * surface (a stat summary, a compact history list) so a dense screen does not read as a
 * stack of identically-weighted bordered boxes — never as a replacement for [EduCard] on a
 * screen's actual entities.
 */
@Composable
fun EduGroupedSurface(
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(Spacing.card),
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(Radius.md)
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(EduTheme.colors.neutralAlpha100, shape)
            .padding(contentPadding),
        content = content,
    )
}

/**
 * The app has ONE list row. Height floors at the 48dp touch target; the chevron
 * mirrors in RTL because it is a directional affordance.
 */
@Composable
fun ListRow(
    title: String,
    modifier: Modifier = Modifier,
    supporting: String? = null,
    leading: ImageVector? = null,
    leadingTint: Color = EduTheme.colors.primary,
    trailingContent: @Composable (RowScope.() -> Unit)? = null,
    showChevron: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.eduClickable(onClick = onClick) else Modifier)
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .padding(vertical = Spacing.sm),
    ) {
        if (leading != null) {
            Icon(
                imageVector = leading,
                contentDescription = null,
                tint = leadingTint,
                modifier = Modifier.size(Sizing.iconLg),
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (supporting != null) {
                Text(
                    text = supporting,
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
        trailingContent?.invoke(this)
        if (showChevron) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = EduTheme.colors.textSecondary,
                modifier = Modifier
                    .size(Sizing.icon)
                    .mirrorInRtl(),
            )
        }
    }
}

/** Section heading. Marked as a heading so TalkBack users can jump between sections. */
@Composable
fun SectionHeader(
    title: String,
    modifier: Modifier = Modifier,
    action: @Composable (() -> Unit)? = null,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
            .fillMaxWidth()
            .padding(top = Spacing.section, bottom = Spacing.xs),
    ) {
        Text(
            text = title,
            style = EduTheme.typography.title,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier
                .weight(1f)
                .semantics { heading() },
        )
        action?.invoke()
    }
}

@Composable
fun EduDivider(modifier: Modifier = Modifier) {
    HorizontalDivider(
        thickness = Sizing.hairline,
        color = EduTheme.colors.border,
        modifier = modifier,
    )
}

/**
 * A short, self-contained tag: lesson media type, lesson status, difficulty.
 * Colour never carries state alone (Design System §3) — always pair with a label.
 */
@Composable
fun StatusPill(
    label: String,
    modifier: Modifier = Modifier,
    contentColor: Color = EduTheme.colors.textSecondary,
    containerColor: Color = EduTheme.colors.neutralAlpha100,
    icon: ImageVector? = null,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .background(containerColor, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.xs, vertical = Spacing.xxs),
    ) {
        if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = contentColor,
                modifier = Modifier.size(Sizing.iconSm),
            )
        }
        Text(text = label, style = EduTheme.typography.caption, color = contentColor)
    }
}

/**
 * Skeleton placeholder — skeletons use `neutralAlpha100`.
 *
 * Deliberately a static block, not a shimmer sweep: a continuously animating gradient
 * across a list costs frames and battery on the device floor, and §8 bans ambient loops.
 */
@Composable
fun SkeletonBlock(
    modifier: Modifier = Modifier,
    height: Dp = 16.dp,
    widthFraction: Float = 1f,
    cornerRadius: Dp = Radius.sm,
) {
    Box(
        modifier = modifier
            .fillMaxWidth(widthFraction)
            .height(height)
            .background(EduTheme.colors.neutralAlpha100, RoundedCornerShape(cornerRadius))
    )
}

@Composable
fun SkeletonCircle(size: Dp, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .size(size)
            .background(EduTheme.colors.neutralAlpha100, RoundedCornerShape(Radius.pill))
    )
}

/** Row skeleton with a fixed height, so lists keep `getItemLayout`-style stability. */
@Composable
fun SkeletonListItem(modifier: Modifier = Modifier) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxWidth()
            .height(Sizing.touchTarget + Spacing.md)
            .padding(vertical = Spacing.xs),
    ) {
        SkeletonCircle(size = Sizing.avatar)
        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.weight(1f),
        ) {
            SkeletonBlock(widthFraction = 0.7f)
            SkeletonBlock(widthFraction = 0.4f, height = 12.dp)
        }
    }
}

/** Card skeleton used by dashboard-style surfaces. */
@Composable
fun SkeletonCard(modifier: Modifier = Modifier) {
    EduCard(modifier = modifier) {
        SkeletonBlock(widthFraction = 0.5f, height = 20.dp)
        Box(modifier = Modifier.height(Spacing.sm))
        SkeletonBlock(widthFraction = 1f)
        Box(modifier = Modifier.height(Spacing.xs))
        SkeletonBlock(widthFraction = 0.8f)
    }
}

/**
 * Detail-page skeleton — a header block plus a few paragraph-width lines, for screens whose
 * loading state is a single record (a certificate, a lesson, a profile) rather than a list.
 * A-14 · Global States Kit calls for list, card and detail skeletons; this is the third.
 */
@Composable
fun SkeletonDetail(modifier: Modifier = Modifier) {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier.fillMaxWidth(),
    ) {
        SkeletonBlock(widthFraction = 0.6f, height = 24.dp)
        SkeletonBlock(widthFraction = 0.4f, height = 16.dp)
        Box(modifier = Modifier.height(Spacing.xs))
        SkeletonBlock(widthFraction = 1f)
        SkeletonBlock(widthFraction = 1f)
        SkeletonBlock(widthFraction = 0.75f)
    }
}
