package com.rork.eduspark.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import com.rork.eduspark.R

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Typography — Design System §4.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Three faces, with a strict division of labour:
 *
 *  • UI face — the **system stack** ([FontFamily.Default] resolves to Noto Sans Arabic /
 *    Roboto on Android). Zero bundle cost on a device floor where every megabyte matters,
 *    native shaping for Arabic, free font-scaling support. ~95% of the app's text.
 *
 *  • Display face — **IBM Plex Sans Arabic**, bundled, for brand moments only: splash,
 *    onboarding headlines, certificates, celebration overlays, empty-state headlines.
 *
 *  • Utility face — **IBM Plex Mono**, for scores, timers, codes and IDs. Never for prose.
 *
 * Practical rule: interface text → system face; brand text → Plex. Never mixed in one block.
 *
 * THE CRITICAL PART — line height switches with the locale. Arabic needs ~1.6–1.8× where
 * Latin needs ~1.35–1.45; a single shared line-height clips Arabic diacritics and descenders.
 * [eduTypographyFor] therefore builds a different ramp per script, and every screen gets the
 * right one automatically from [EduTheme.typography].
 */
private val PlexArabic = FontFamily(
    Font(R.font.plex_arabic_regular, FontWeight.Normal),
    Font(R.font.plex_arabic_semibold, FontWeight.SemiBold),
    Font(R.font.plex_arabic_bold, FontWeight.Bold),
)

private val PlexMono = FontFamily(
    Font(R.font.plex_mono_medium, FontWeight.Medium),
)

/** System stack: Noto Sans Arabic + Roboto on Android, SF Arabic + SF Pro on iOS later. */
private val SystemUi = FontFamily.Default

@Immutable
data class EduTypography(
    /** Brand display, Plex — 32pt. Splash, certificates, celebration. */
    val display: TextStyle,
    /** Brand title, Plex — 24pt. Onboarding + empty-state headlines. */
    val brandTitle: TextStyle,
    /** UI title-lg — 24pt. */
    val titleLg: TextStyle,
    /** UI title — 20pt. */
    val title: TextStyle,
    /** UI body-lg — 17pt. Reading-heavy surfaces: lessons, tutor replies. */
    val bodyLg: TextStyle,
    /** UI body — 15pt. The default. */
    val body: TextStyle,
    /** UI caption — 13pt. */
    val caption: TextStyle,
    /** Utility mono — 15pt. Scores, timers, voucher codes, reference numbers. */
    val mono: TextStyle,
    /** Button label — pill buttons name the outcome, so labels are short and firm. */
    val label: TextStyle,
)

/** Keeps Arabic diacritics from being clipped at the top of the first line. */
private val EduLineHeightStyle = LineHeightStyle(
    alignment = LineHeightStyle.Alignment.Center,
    trim = LineHeightStyle.Trim.None,
)

/**
 * Builds the type ramp for the active script.
 *
 * @param isRtl true for Arabic — selects the taller Arabic leading and the Plex Arabic
 * subset for brand styles.
 */
fun eduTypographyFor(isRtl: Boolean): EduTypography {
    // Design System §4 scale: "size / line-height (AR)" vs "line-height (EN)".
    fun style(
        size: Int,
        arabicLineHeight: Int,
        latinLineHeight: Int,
        weight: FontWeight,
        family: FontFamily = SystemUi,
    ) = TextStyle(
        fontFamily = family,
        fontSize = size.sp,
        lineHeight = (if (isRtl) arabicLineHeight else latinLineHeight).sp,
        fontWeight = weight,
        lineHeightStyle = EduLineHeightStyle,
        textAlign = TextAlign.Start,
    )

    return EduTypography(
        display = style(32, 48, 42, FontWeight.Bold, PlexArabic),
        brandTitle = style(24, 38, 32, FontWeight.SemiBold, PlexArabic),
        titleLg = style(24, 38, 32, FontWeight.SemiBold),
        title = style(20, 32, 28, FontWeight.SemiBold),
        bodyLg = style(17, 30, 26, FontWeight.Normal),
        body = style(15, 27, 23, FontWeight.Normal),
        caption = style(13, 22, 18, FontWeight.Medium),
        mono = style(15, 20, 20, FontWeight.Medium, PlexMono),
        label = style(15, 24, 20, FontWeight.SemiBold),
    )
}

internal val LocalEduTypography = staticCompositionLocalOf { eduTypographyFor(isRtl = true) }
