package com.rork.eduspark.core.format

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.ui.theme.LocalNumeralSystem

private const val ARABIC_INDIC_ZERO = '\u0660'

/**
 * Formats a number for display.
 *
 * Western digits are the default in both locales (Design System §6.3). Arabic-Indic digits
 * are opt-in, so the transformation happens at the render edge only — never in stored data,
 * never in anything parsed back.
 */
fun formatNumber(value: Int, system: NumeralSystem): String = formatNumber(value.toString(), system)

fun formatNumber(value: String, system: NumeralSystem): String = when (system) {
    NumeralSystem.Western -> value
    NumeralSystem.ArabicIndic -> buildString(value.length) {
        value.forEach { char ->
            append(if (char in '0'..'9') ARABIC_INDIC_ZERO + (char - '0') else char)
        }
    }
}

/** Composable convenience that reads the user's numeral preference from the theme. */
@Composable
@ReadOnlyComposable
fun numeral(value: Int): String = formatNumber(value, LocalNumeralSystem.current)

@Composable
@ReadOnlyComposable
fun numeral(value: String): String = formatNumber(value, LocalNumeralSystem.current)
