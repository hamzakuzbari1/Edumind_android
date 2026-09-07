package com.rork.eduspark.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import com.rork.eduspark.R

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Typography — NEW identity, migrated from the old 3-face system per the
 * approved Part 1/Part 2 Batch 1 plan.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Two faces, replacing the old system-font/Plex-brand-only split — the reference bundles
 * one Arabic-first face across essentially all UI text, not just brand moments:
 *
 *  • UI face — **Cairo**, bundled as a single variable font (`wght` axis) rather than four
 *    static files, instanced per weight via [FontVariation]. This is a deliberate reversal
 *    of the old "OS system font for 95% of text" rule — the new visual authority bundles
 *    Cairo for all of it — and a real bundle-size cost against the app's documented
 *    low-end-Android device floor that should get verified once real screens use it at
 *    scale, not just assumed away.
 *
 *  • Utility face — **Tajawal**, for numerals: scores, timers, codes, day/level chips —
 *    matching the reference's deliberate prose/numeral font split. It replaces IBM Plex
 *    Mono; note it is not a monospaced font (Tajawal digits are not guaranteed tabular),
 *    which is a real risk for ticking timers and worth a dedicated check before it's used
 *    behind a live countdown.
 *
 * RTL line-height ramp is UNCHANGED in mechanism from the old system: Arabic needs ~1.6–1.8×
 * where Latin needs ~1.35–1.45×, which is why [eduTypographyFor] still builds a different
 * ramp per script — this is exactly the ratio range the new reference's own CSS uses too, so
 * the old ramp logic carries over unmodified, only the concrete sizes/weights change below.
 */
// The Font(resId, weight, style, loadingStrategy, variationSettings) overload used below to
// instance the Cairo variable font per weight is @ExperimentalTextApi in androidx.compose.ui.text
// (see androidx.compose.ui.text.font.Font.kt) — opting in here only, not file-wide, since this
// is the only declaration in this file that touches it.
@OptIn(ExperimentalTextApi::class)
private val Cairo = FontFamily(
    Font(
        resId = R.font.cairo,
        weight = FontWeight.Normal,
        variationSettings = FontVariation.Settings(FontVariation.weight(400)),
    ),
    Font(
        resId = R.font.cairo,
        weight = FontWeight.SemiBold,
        variationSettings = FontVariation.Settings(FontVariation.weight(600)),
    ),
    Font(
        resId = R.font.cairo,
        weight = FontWeight.Bold,
        variationSettings = FontVariation.Settings(FontVariation.weight(700)),
    ),
    Font(
        resId = R.font.cairo,
        weight = FontWeight.ExtraBold,
        variationSettings = FontVariation.Settings(FontVariation.weight(800)),
    ),
)

private val Tajawal = FontFamily(
    Font(R.font.tajawal_regular, FontWeight.Normal),
    Font(R.font.tajawal_medium, FontWeight.Medium),
    Font(R.font.tajawal_bold, FontWeight.Bold),
    Font(R.font.tajawal_extrabold, FontWeight.ExtraBold),
)

@Immutable
data class EduTypography(
    /** Brand display — 28pt ExtraBold. Splash, certificates, celebration. */
    val display: TextStyle,
    /** Brand title — 22pt ExtraBold. Onboarding + empty-state headlines. */
    val brandTitle: TextStyle,
    /** UI title-lg — 22pt ExtraBold. Screen titles. */
    val titleLg: TextStyle,
    /** UI title — 20pt Bold. Card/lesson titles. */
    val title: TextStyle,
    /** UI body-lg — 17pt Regular. Reading-heavy surfaces: lessons, tutor replies. */
    val bodyLg: TextStyle,
    /** UI body — 15pt Regular. The default. */
    val body: TextStyle,
    /** UI caption — 12pt Bold. Matches the reference's dominant caption size/weight. */
    val caption: TextStyle,
    /** Utility numeral face (Tajawal) — 15pt Medium. Scores, timers, codes, IDs. */
    val mono: TextStyle,
    /** Button label — 14pt ExtraBold, bold-forward per the new reference's CTA treatment. */
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
 * @param isRtl true for Arabic — selects the taller Arabic leading.
 * @param textScale ST-25's text-size preference, applied as a multiplier on top of the base
 * `.sp` sizes below — 1f for [com.rork.eduspark.core.preferences.TextSizePreference.Default].
 */
fun eduTypographyFor(isRtl: Boolean, textScale: Float = 1f): EduTypography {
    fun style(
        size: Int,
        arabicLineHeight: Int,
        latinLineHeight: Int,
        weight: FontWeight,
        family: FontFamily = Cairo,
    ) = TextStyle(
        fontFamily = family,
        fontSize = (size * textScale).sp,
        lineHeight = ((if (isRtl) arabicLineHeight else latinLineHeight) * textScale).sp,
        fontWeight = weight,
        lineHeightStyle = EduLineHeightStyle,
        textAlign = TextAlign.Start,
    )

    return EduTypography(
        display = style(28, 48, 40, FontWeight.ExtraBold),
        brandTitle = style(22, 38, 32, FontWeight.ExtraBold),
        titleLg = style(22, 38, 32, FontWeight.ExtraBold),
        title = style(20, 34, 28, FontWeight.Bold),
        bodyLg = style(17, 29, 24, FontWeight.Normal),
        body = style(15, 26, 21, FontWeight.Normal),
        caption = style(12, 20, 17, FontWeight.Bold),
        mono = style(15, 20, 20, FontWeight.Medium, Tajawal),
        label = style(14, 24, 20, FontWeight.ExtraBold),
    )
}

internal val LocalEduTypography = staticCompositionLocalOf { eduTypographyFor(isRtl = true) }
