package com.rork.eduspark.ui.theme

import android.provider.Settings
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.TextSizePreference
import com.rork.eduspark.core.preferences.ThemeMode

/**
 * The EduSpark theme.
 *
 * Provides the design-system tokens ([EduColors], [EduTypography]) plus the two
 * cross-cutting display preferences (numerals, reduced motion) to the whole tree.
 *
 * Note what is deliberately absent: **Material You dynamic colour**. EduSpark has a
 * fixed brand palette in which `barq` and `jouri` carry meaning (celebration and
 * "a machine wrote this"). Letting the OS wallpaper recolour them would break a
 * trust contract, so dynamic colour is off by design.
 *
 * Layout direction is *not* forced here — it is resolved by the framework from the
 * per-app locale (see [com.rork.eduspark.core.locale.LocaleController]), which is why
 * switching language requires the branded reload of screen A-13.
 */
@Composable
fun EduSparkTheme(
    themeMode: ThemeMode = ThemeMode.System,
    numeralSystem: NumeralSystem = NumeralSystem.Western,
    reduceMotionOverride: Boolean = false,
    textSizePreference: TextSizePreference = TextSizePreference.Default,
    content: @Composable () -> Unit,
) {
    val darkTheme = when (themeMode) {
        ThemeMode.System -> isSystemInDarkTheme()
        ThemeMode.Light -> false
        ThemeMode.Dark -> true
    }

    val colors = if (darkTheme) EduDarkColors else EduLightColors

    // The script in play, taken from the resolved layout direction so no component
    // ever needs to know which language is active.
    val isRtl = LocalLayoutDirection.current == LayoutDirection.Rtl
    val textScale = if (textSizePreference == TextSizePreference.Large) LARGE_TEXT_SCALE else 1f
    val typography = remember(isRtl, textScale) { eduTypographyFor(isRtl, textScale) }

    val context = LocalContext.current
    @Suppress("DEPRECATION") // LocalConfiguration is the supported read path for font scale.
    val configuration = LocalConfiguration.current
    val systemAnimationsDisabled = remember(configuration) {
        Settings.Global.getFloat(
            context.contentResolver,
            Settings.Global.ANIMATOR_DURATION_SCALE,
            1f,
        ) == 0f
    }

    CompositionLocalProvider(
        LocalEduColors provides colors,
        LocalEduTypography provides typography,
        LocalNumeralSystem provides numeralSystem,
        LocalReducedMotion provides (reduceMotionOverride || systemAnimationsDisabled),
    ) {
        MaterialTheme(
            colorScheme = colors.toMaterialColorScheme(),
            shapes = EduShapes,
            content = content,
        )
    }
}

/** Token accessors. Components read `EduTheme.colors.primary`, never a hex value. */
object EduTheme {
    val colors: EduColors
        @Composable @ReadOnlyComposable get() = LocalEduColors.current

    val typography: EduTypography
        @Composable @ReadOnlyComposable get() = LocalEduTypography.current

    val isRtl: Boolean
        @Composable @ReadOnlyComposable get() = LocalLayoutDirection.current == LayoutDirection.Rtl
}

val LocalNumeralSystem = staticCompositionLocalOf { NumeralSystem.Western }

/**
 * Maps EduSpark tokens onto Material 3 roles so built-in M3 components (text fields,
 * sheets, dialogs, navigation bar) inherit the brand instead of Material defaults.
 * Application code should still prefer [EduTheme.colors] directly.
 */
private fun EduColors.toMaterialColorScheme() = if (isDark) {
    darkColorScheme(
        primary = primary,
        onPrimary = onPrimary,
        primaryContainer = primaryContainer,
        onPrimaryContainer = textPrimary,
        secondary = highlight,
        onSecondary = onHighlight,
        tertiary = aiAccent,
        onTertiary = textPrimary,
        background = background,
        onBackground = textPrimary,
        surface = surface,
        onSurface = textPrimary,
        surfaceVariant = neutralAlpha100,
        onSurfaceVariant = textSecondary,
        outline = border,
        outlineVariant = border,
        error = danger,
        onError = onDanger,
        // Always the dark ink, regardless of theme — this darkens the backdrop behind a
        // modal barrier and must not flip to near-white in dark mode the way textPrimary does.
        scrim = ScrimInk,
    )
} else {
    lightColorScheme(
        primary = primary,
        onPrimary = onPrimary,
        primaryContainer = primaryContainer,
        onPrimaryContainer = textPrimary,
        secondary = highlight,
        onSecondary = onHighlight,
        tertiary = aiAccent,
        onTertiary = surface,
        background = background,
        onBackground = textPrimary,
        surface = surface,
        onSurface = textPrimary,
        surfaceVariant = neutralAlpha100,
        onSurfaceVariant = textSecondary,
        outline = border,
        outlineVariant = border,
        error = danger,
        onError = onDanger,
        scrim = ScrimInk,
    )
}

/** Dark ink used for the Material scrim role only — never flips with the theme. */
private val ScrimInk = Color(0xFF0C1929)

/** ST-25 · Large text size — a modest step, not a second accessibility system. */
private const val LARGE_TEXT_SCALE = 1.15f
