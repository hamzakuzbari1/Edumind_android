package com.rork.eduspark.ui.screens.auth

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.nav.SegmentedControl
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * THE AUTHENTICATION SHELL — shared by A-01 … A-11.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Everything in this file is *composition*, not new design-system primitives: it arranges
 * existing components (SegmentedControl, GhostButton, EduIconButton) into the three parts
 * every auth screen repeats, so the eight screens of the flow cannot drift apart.
 *
 *  1. [BrandWordmark]     — the monogram + wordmark block at the top.
 *  2. [AuthLanguageToggle] — the language switch pinned to the bottom, reachable *before*
 *     login, because locale is chosen before authentication (Design System §6.8).
 *  3. [AuthFooterPrompt]  — the "already have an account? / no account yet?" cross-link.
 *  4. [AuthPageHeader]    — the [BrandMark] + title + one line of context that the longer
 *     form screens (A-05…A-07) use instead of the full wordmark, which would push the
 *     first field below the fold.
 *  5. [AuthErrorRegion] + [AuthProgressRow] + [AuthMessageSurface] — the single error
 *     region. Every auth screen reserves one slot of fixed height in which validation,
 *     progress and every failure speak, so no form reflows under the user's thumb.
 *
 * Layout direction is never hard-coded here. The blocks use Column/Row with start/end
 * semantics only, so the identical code renders right-anchored in Arabic and
 * left-anchored in English.
 */

/** How prominent the wordmark is: A-01 gives it the screen, A-04 gives it the header. */
enum class WordmarkSize { Hero, Compact }

/**
 * The brand block: monogram tile, wordmark in the display face, the same name in the
 * other script, then the tagline.
 *
 * Design System §4 — this is one of the few genuinely branded moments in the app, so it
 * is the only place on these screens that uses IBM Plex; everything else is the system face.
 */
@Composable
fun BrandWordmark(
    modifier: Modifier = Modifier,
    size: WordmarkSize = WordmarkSize.Compact,
) {
    val colors = EduTheme.colors

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.fillMaxWidth(),
    ) {
        BrandMark(size = if (size == WordmarkSize.Hero) 72.dp else 56.dp)

        Text(
            text = stringResource(R.string.app_name),
            style = if (size == WordmarkSize.Hero) {
                EduTheme.typography.display
            } else {
                EduTheme.typography.brandTitle
            },
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.sm),
        )

        // The wordmark in the other script — the bilingual promise, stated visually,
        // on the very first screen the user sees.
        Text(
            text = stringResource(R.string.brand_name_alternate),
            style = EduTheme.typography.caption.copy(letterSpacing = 3.sp, fontWeight = FontWeight.Medium),
            color = colors.textMuted,
            textAlign = TextAlign.Center,
        )

        Text(
            text = stringResource(R.string.brand_tagline),
            style = EduTheme.typography.body,
            color = colors.textMuted,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

/**
 * The monogram tile on its own.
 *
 * Extracted so the wordmark block and the form headers draw the identical mark rather than
 * two lookalike tiles that could drift apart.
 */
@Composable
fun BrandMark(
    modifier: Modifier = Modifier,
    size: Dp = 56.dp,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(size)
            .background(
                color = if (colors.isDark) colors.zaytounSoft else colors.zaytoun,
                shape = shape,
            ),
    ) {
        Image(
            painter = painterResource(R.drawable.ic_launcher_foreground),
            contentDescription = stringResource(R.string.app_name),
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .size(size)
                .clip(shape),
        )
    }
}

/**
 * A centred circular icon tile — the "moment" screens' equivalent of [BrandMark]: A-08's
 * envelope, A-10/A-11's key. One shared shape so these screens read as a family rather than
 * three near-identical circles drifting apart over time.
 */
@Composable
fun AuthIconMark(
    icon: ImageVector,
    modifier: Modifier = Modifier,
    size: Dp = 56.dp,
) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(size)
            .background(colors.zaytounSoft, CircleShape),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = colors.zaytoun,
            modifier = Modifier.size(Sizing.iconLg),
        )
    }
}

/**
 * Header for the form screens: mark, what this screen is, and one line of context.
 *
 * Start-aligned rather than centred like the wordmark, because the eye should land on the
 * first field next, and a centred block above a start-aligned form reads as two designs.
 */
@Composable
fun AuthPageHeader(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        BrandMark(size = 40.dp)
        Text(
            text = title,
            style = EduTheme.typography.titleLg,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Text(
            text = body,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

/**
 * The single error region.
 *
 * A fixed minimum height that every auth form reserves whether or not anything is wrong,
 * so an idle form and a failed one are the same shape and the primary button never moves
 * between the moment the user aims and the moment they press.
 */
@Composable
fun AuthErrorRegion(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .defaultMinSize(minHeight = Sizing.tabBarHeight)
            .padding(vertical = Spacing.sm),
        content = content,
    )
}

/**
 * The honest waiting state inside the error region.
 *
 * No percentage and no fake step list: a sign-in or a registration is a single round trip
 * whose duration we do not know.
 */
@Composable
fun AuthProgressRow(
    text: String,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier
            .fillMaxWidth()
            .semantics { liveRegion = LiveRegionMode.Polite },
    ) {
        CircularProgressIndicator(
            color = EduTheme.colors.zaytoun,
            strokeWidth = Sizing.hairline * 2,
            modifier = Modifier.size(Sizing.icon),
        )
        Text(
            text = text,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
    }
}

/**
 * The container every message in the error region uses: tinted fill plus a hairline in the
 * accent colour — the design system's two-level elevation model, never a shadow.
 *
 * Announced assertively: a user who just pressed the button needs to hear what happened.
 * Colour never carries the meaning alone; each caller pairs its accent with an icon and a
 * sentence saying what happened *and* what to do next.
 */
@Composable
fun AuthMessageSurface(
    icon: ImageVector,
    accent: Color,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    val tintAlpha = if (EduTheme.colors.isDark) 0.16f else 0.08f

    EduCard(
        containerColor = accent.copy(alpha = tintAlpha),
        borderColor = accent.copy(alpha = 0.5f),
        contentPadding = PaddingValues(Spacing.sm),
        modifier = modifier.semantics { liveRegion = LiveRegionMode.Assertive },
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = accent,
                modifier = Modifier.size(Sizing.icon),
            )
            Column(modifier = Modifier.weight(1f), content = content)
        }
    }
}

/**
 * The language switch, pinned to the bottom of every auth screen.
 *
 * Options are [AppLocale] entries in declaration order, laid out in a plain Row, so Arabic
 * sits on the right in Arabic and on the left in English without a single direction check.
 * Labels are autonyms — «العربية» and "English" are identical in both string bundles,
 * because a language always names itself in its own script.
 *
 * @param note the "changing the language restarts the app" caption. Shown where the flip
 * genuinely reloads the app (A-03, A-04); omitted on A-01, where nothing is running yet.
 */
@Composable
fun AuthLanguageToggle(
    current: AppLocale,
    onSelect: (AppLocale) -> Unit,
    modifier: Modifier = Modifier,
    note: String? = null,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.fillMaxWidth(),
    ) {
        SegmentedControl(
            options = AppLocale.entries,
            selected = current,
            onSelect = onSelect,
            labelOf = { locale ->
                stringResource(
                    when (locale) {
                        AppLocale.Arabic -> R.string.settings_language_arabic
                        AppLocale.English -> R.string.settings_language_english
                    }
                )
            },
        )
        if (note != null) {
            Text(
                text = note,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

/** The cross-link between login and register, centred under the primary action. */
@Composable
fun AuthFooterPrompt(
    question: String,
    actionLabel: String,
    onAction: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = question,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
        )
        GhostButton(text = actionLabel, onClick = onAction)
    }
}

/**
 * The shared auth page frame: an optional back affordance and trailing action at the top,
 * a scroll-free content column in the middle, and a bottom block that stays pinned.
 *
 * The back affordance is always *visible* when [onBack] is supplied — the hardware back
 * button is handled by the caller's `BackHandler`, but it is never the only way back,
 * because these same screens ship on iOS later.
 *
 * @param headerBand replaces the default back-button row with a caller-supplied, full-bleed
 * band — used only by A-09 Two-Factor Verify, whose brief calls for a visual identity
 * unmistakably distinct from every other screen in this shell (a full-bleed Basalt security
 * band with its own back affordance, rather than the plain top bar). Every other screen
 * leaves this null and gets the ordinary top bar. Because it renders *before* the padded
 * content column — at the same level as the top bar it replaces — it is genuinely edge to
 * edge, not just tinted within the screen gutter.
 */
@Composable
fun AuthScaffold(
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    topEndAction: @Composable (() -> Unit)? = null,
    headerBand: (@Composable () -> Unit)? = null,
    bottomBlock: @Composable ColumnScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding()
            .imePadding(),
    ) {
        if (headerBand != null) {
            headerBand()
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(Sizing.topBarHeight)
                    .padding(horizontal = Spacing.xs),
            ) {
                if (onBack != null) {
                    EduIconButton(
                        // AutoMirrored: the arrow points right in Arabic and left in English.
                        icon = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.a11y_back),
                        onClick = onBack,
                    )
                }
                Box(modifier = Modifier.weight(1f))
                topEndAction?.invoke()
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter),
            content = content,
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter)
                .padding(top = Spacing.sm, bottom = Spacing.md),
            content = bottomBlock,
        )
    }
}
