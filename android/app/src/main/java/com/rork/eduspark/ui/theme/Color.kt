package com.rork.eduspark.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * ══════════════════════════════════════════════════════════════════════════
 * EduSpark colour tokens — NEW global identity, migrated from the old
 * zaytoun/barq/jouri/hajar palette per docs/design/EDUMIND_NEW_VISUAL_REFERENCE
 * (see the approved Part 1 audit + Part 2 Batch 1 plan).
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Components read colours from [EduTheme.colors] only. A raw hex literal anywhere
 * outside this file is a defect.
 *
 * Three rules the tokens encode, restated because they are product rules, not styling:
 *  • `highlight` (was `barq`) is rationed — XP, streaks, achievements, certificates. Never
 *    a button colour. If it covers more than ~10% of a screen, remove some.
 *  • `aiAccent` (was `jouri`) marks the machine — anything the AI generated carries an
 *    aiAccent hairline or dot. Human-authored content (a teacher's lesson, a parent's note)
 *    never does. This is a trust contract with parents, not decoration. The colour changed
 *    (rose → cyan, per the approved AI-accent decision); the rule did not.
 *  • Dark is designed, not derived from a literal source — the new reference has no dark
 *    palette, so every dark value below is deliberately derived from its light counterpart
 *    (brighten accents ~1 step, invert the neutral/text scale), not a naive colour-invert.
 *
 * Old → new field renames (docs/design/... Part 1 §3, approved): zaytoun→primary,
 * zaytounSoft→primaryContainer, onZaytoun→onPrimary, barq→highlight, onBarq→onHighlight,
 * jouri→aiAccent, info→accent (merged), basalt→(retired, see textPrimary/background),
 * hajar50→background, hajar100→neutralAlpha100, hajar300→border, textMuted→textSecondary.
 * Deprecated aliases below keep every screen that hasn't been visually migrated yet
 * compiling — and rendering the NEW colours under the OLD names — until its own batch
 * replaces the call sites.
 */
@Immutable
data class EduColors(
    // ── Brand / primary (indigo) ────────────────────────────────────────────
    val primary: Color,
    val primaryContainer: Color,
    val onPrimary: Color,

    // ── Accent — informational + AI/insight (cyan) ──────────────────────────
    // aiAccent is numerically identical to accent today (approved decision: cyan is the
    // single AI/insight hue) but stays a distinct field so AI-marked components read their
    // own semantic token rather than the general accent — the trust-contract rule lives in
    // the field name, not just the value.
    val accent: Color,
    val accentContainer: Color,
    val onAccent: Color,
    val aiAccent: Color,
    val aiAccentContainer: Color,

    // ── Highlight — XP / streaks / achievements (amber), rationed ───────────
    val highlight: Color,
    val highlightContainer: Color,
    val onHighlight: Color,

    // ── Neutral / alpha-derived scale (new mechanism — an ink colour at
    // varying alpha, replacing the old three discrete hajar greys) ──────────
    val neutralAlpha100: Color,
    val border: Color,

    val surface: Color,
    val background: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textTertiary: Color,

    // ── Semantic status ──────────────────────────────────────────────────────
    val success: Color,
    val warning: Color,
    val danger: Color,
    val onDanger: Color,

    val scrim: Color,
    val isDark: Boolean,
) {
    // ── Deprecated aliases — remove once every screen's own migration batch
    // has replaced these call sites with the renamed field above. ───────────
    @Deprecated("Renamed to primary", ReplaceWith("primary"))
    val zaytoun: Color get() = primary

    @Deprecated("Renamed to primaryContainer", ReplaceWith("primaryContainer"))
    val zaytounSoft: Color get() = primaryContainer

    @Deprecated("Renamed to onPrimary", ReplaceWith("onPrimary"))
    val onZaytoun: Color get() = onPrimary

    @Deprecated("Renamed to highlight", ReplaceWith("highlight"))
    val barq: Color get() = highlight

    @Deprecated("Renamed to onHighlight", ReplaceWith("onHighlight"))
    val onBarq: Color get() = onHighlight

    @Deprecated("Replaced by aiAccent (cyan) — jouri's rose has no successor", ReplaceWith("aiAccent"))
    val jouri: Color get() = aiAccent

    @Deprecated("Merged into accent", ReplaceWith("accent"))
    val info: Color get() = accent

    @Deprecated("Retired — use textPrimary or background", ReplaceWith("textPrimary"))
    val basalt: Color get() = textPrimary

    @Deprecated("Renamed to neutralAlpha100", ReplaceWith("neutralAlpha100"))
    val hajar100: Color get() = neutralAlpha100

    @Deprecated("Renamed to border", ReplaceWith("border"))
    val hajar300: Color get() = border

    @Deprecated("Renamed to background", ReplaceWith("background"))
    val hajar50: Color get() = background

    @Deprecated("Renamed to textSecondary", ReplaceWith("textSecondary"))
    val textMuted: Color get() = textSecondary
}

/** Light theme — sourced directly from EDUMIND_NEW_VISUAL_REFERENCE (Part 1 §1/§3). */
val EduLightColors = EduColors(
    primary = Color(0xFF6366F1),
    primaryContainer = Color(0xFFECEDFD),
    onPrimary = Color(0xFFFFFFFF),

    accent = Color(0xFF0E7490),
    accentContainer = Color(0xFFE1F6FA),
    onAccent = Color(0xFFFFFFFF),
    aiAccent = Color(0xFF0E7490),
    aiAccentContainer = Color(0xFFE1F6FA),

    highlight = Color(0xFFB45309),
    highlightContainer = Color(0xFFFAEFE1),
    onHighlight = Color(0xFFFFFFFF),

    neutralAlpha100 = Color(0x0F0C1929),
    border = Color(0x170C1929),

    surface = Color(0xFFFFFFFF),
    background = Color(0xFFF4F7FB),
    textPrimary = Color(0xFF0C1929),
    textSecondary = Color(0xFF475569),
    textTertiary = Color(0xFF64748B),

    success = Color(0xFF047857),
    warning = Color(0xFFB45309),
    danger = Color(0xFFEF4444),
    onDanger = Color(0xFFFFFFFF),

    scrim = Color(0x0F0C1929),
    isDark = false,
)

/**
 * Dark theme — DERIVED, not sourced: the reference file has no dark/night system (confirmed
 * absent — no `prefers-color-scheme`, `.dark`, or `:root` block in the source). Method,
 * applied consistently field by field:
 *  1. Neutral/surface/text roles invert (near-white ↔ near-dark ink), same as the old system.
 *  2. Brand/accent/status hues brighten ~one step (roughly a 500→400 shift) so they still
 *     read against a dark background, keeping the same hue — never a naive RGB invert.
 *  3. Each "on*" colour sits close to the dark background's own ink rather than plain white,
 *     because the brightened accents are light enough that white text on them would wash
 *     out — the same reasoning the old dark onZaytoun (`#06120F`, not white) already used.
 */
val EduDarkColors = EduColors(
    primary = Color(0xFF818CF8),
    primaryContainer = Color(0xFF262B46),
    onPrimary = Color(0xFF161A2E),

    accent = Color(0xFF22D3EE),
    accentContainer = Color(0xFF153844),
    onAccent = Color(0xFF0C2024),
    aiAccent = Color(0xFF22D3EE),
    aiAccentContainer = Color(0xFF153844),

    highlight = Color(0xFFFBBF24),
    highlightContainer = Color(0xFF3C3420),
    onHighlight = Color(0xFF2B1D08),

    neutralAlpha100 = Color(0x0FECEFF4),
    border = Color(0x17ECEFF4),

    surface = Color(0xFF12161F),
    background = Color(0xFF0B0E14),
    textPrimary = Color(0xFFECEFF4),
    textSecondary = Color(0xFFA8B3C7),
    textTertiary = Color(0xFF8A94A8),

    success = Color(0xFF34D399),
    warning = Color(0xFFFBBF24),
    danger = Color(0xFFF87171),
    onDanger = Color(0xFFFFFFFF),

    scrim = Color(0x0FECEFF4),
    isDark = true,
)

internal val LocalEduColors = staticCompositionLocalOf { EduLightColors }
