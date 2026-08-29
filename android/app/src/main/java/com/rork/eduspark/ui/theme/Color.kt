package com.rork.eduspark.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * ══════════════════════════════════════════════════════════════════════════
 * EduSpark colour tokens — Design System §3, transcribed exactly.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Components read colours from [EduTheme.colors] only. A raw hex literal anywhere
 * outside this file is a defect.
 *
 * Three rules the tokens encode, restated because they are product rules, not styling:
 *  • `barq` is rationed — XP, streaks, achievements, certificates. Never a button colour.
 *    If it covers more than ~10% of a screen, remove some.
 *  • `jouri` marks the machine — anything the AI generated carries a jouri hairline or dot.
 *    Human-authored content (a teacher's lesson, a parent's note) never does. This is a
 *    trust contract with parents, not decoration.
 *  • Dark is designed, not derived. Every token below has a hand-picked dark value.
 */
@Immutable
data class EduColors(
    val basalt: Color,
    val zaytoun: Color,
    val zaytounSoft: Color,
    val barq: Color,
    val jouri: Color,
    val hajar50: Color,
    val hajar100: Color,
    val hajar300: Color,
    val surface: Color,
    val textMuted: Color,
    val success: Color,
    val warning: Color,
    val danger: Color,
    val info: Color,

    // ── Derived roles ────────────────────────────────────────────────────
    // Not new hues: these name *where* the tokens above are used, so that light
    // and dark can swap the same pair without any component branching on theme.
    /** App background — hajar-50 in light, basalt in dark. */
    val background: Color,
    /** Primary text — basalt in light, the light neutral in dark. */
    val textPrimary: Color,
    /** Text/icon sitting on a zaytoun fill. */
    val onZaytoun: Color,
    /** Text/icon sitting on a barq fill. */
    val onBarq: Color,
    /** Hairline borders and dividers — hajar-300. */
    val border: Color,
    /** 6% scrim behind level-2 surfaces (sheets, dialogs). */
    val scrim: Color,
    val isDark: Boolean,
)

/** Light theme — Design System §3 "Light" column. */
val EduLightColors = EduColors(
    basalt = Color(0xFF101416),
    zaytoun = Color(0xFF146B58),
    zaytounSoft = Color(0xFFE4F0EB),
    barq = Color(0xFFE0A42B),
    jouri = Color(0xFFB23A5B),
    hajar50 = Color(0xFFF5F7F4),
    hajar100 = Color(0xFFE8ECE7),
    hajar300 = Color(0xFFCBD2C9),
    surface = Color(0xFFFFFFFF),
    textMuted = Color(0xFF5C6763),
    success = Color(0xFF1F8A4C),
    warning = Color(0xFFC97A0E),
    danger = Color(0xFFC33A3A),
    info = Color(0xFF2C6E8F),
    background = Color(0xFFF5F7F4),
    textPrimary = Color(0xFF101416),
    onZaytoun = Color(0xFFFFFFFF),
    onBarq = Color(0xFF101416),
    border = Color(0xFFCBD2C9),
    scrim = Color(0x0F101416),
    isDark = false,
)

/** Dark theme — Design System §3 "Dark" column. Students study at night, on battery. */
val EduDarkColors = EduColors(
    basalt = Color(0xFF101416),
    zaytoun = Color(0xFF3FA98F),
    zaytounSoft = Color(0xFF16302A),
    barq = Color(0xFFF0B740),
    jouri = Color(0xFFD9607F),
    hajar50 = Color(0xFF171C1E),
    hajar100 = Color(0xFF1F2528),
    hajar300 = Color(0xFF2C3438),
    surface = Color(0xFF171C1E),
    textMuted = Color(0xFF94A19C),
    success = Color(0xFF3FBF74),
    warning = Color(0xFFEDA23A),
    danger = Color(0xFFEB6A6A),
    info = Color(0xFF5AA6C7),
    background = Color(0xFF101416),
    textPrimary = Color(0xFFECF1EE),
    onZaytoun = Color(0xFF06120F),
    onBarq = Color(0xFF101416),
    border = Color(0xFF2C3438),
    scrim = Color(0x0FFFFFFF),
    isDark = true,
)

internal val LocalEduColors = staticCompositionLocalOf { EduLightColors }
