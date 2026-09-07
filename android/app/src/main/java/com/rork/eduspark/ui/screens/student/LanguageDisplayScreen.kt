package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.TextSizePreference
import com.rork.eduspark.core.preferences.ThemeMode
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-25 · Settings — Language & Display.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Purely presentational — every value and setter here already exists in [com.rork.eduspark.ui.AppShellViewModel]/
 * [com.rork.eduspark.core.preferences.AppPreferences] (see this screen's own params), so
 * there is no ViewModel and no second store. [onSelectLanguage] is always the branded
 * [com.rork.eduspark.ui.screens.auth.LocaleSwitchScreen] transition, never a direct
 * [com.rork.eduspark.core.locale.LocaleController] call — the exact rule the auth graph's own
 * `startLocaleTransition` already follows.
 *
 * Numeral system only ever affects `numeral()`-formatted UI counters (XP, streak, question
 * numbers, prices…) through [com.rork.eduspark.ui.theme.LocalNumeralSystem] — this screen
 * changes nothing else, so machine-readable content (OTP codes, reference numbers, version
 * strings) that never routes through `numeral()` is untouched by construction, not by a
 * special case here.
 */
@Composable
fun LanguageDisplayScreen(
    onBack: () -> Unit,
    locale: AppLocale,
    onSelectLanguage: (AppLocale) -> Unit,
    themeMode: ThemeMode,
    onThemeModeChange: (ThemeMode) -> Unit,
    numeralSystem: NumeralSystem,
    onNumeralSystemChange: (NumeralSystem) -> Unit,
    useHijriDates: Boolean,
    onUseHijriDatesChange: (Boolean) -> Unit,
    textSizePreference: TextSizePreference,
    onTextSizePreferenceChange: (TextSizePreference) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    EduScaffold(title = stringResource(R.string.st25_title), onBack = onBack, modifier = modifier) { _ ->
        LazyColumn(
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
            modifier = Modifier.fillMaxSize(),
        ) {
            item {
                SectionHeader(title = stringResource(R.string.st25_language_section))
                EduCard {
                    ChoiceRow(
                        label = stringResource(R.string.st25_language_ar),
                        selected = locale == AppLocale.Arabic,
                        onClick = { onSelectLanguage(AppLocale.Arabic) },
                    )
                    ChoiceRow(
                        label = stringResource(R.string.st25_language_en),
                        selected = locale == AppLocale.English,
                        onClick = { onSelectLanguage(AppLocale.English) },
                    )
                }
            }

            item {
                SectionHeader(title = stringResource(R.string.st25_theme_section))
                EduCard {
                    ChoiceRow(
                        label = stringResource(R.string.st25_theme_system),
                        selected = themeMode == ThemeMode.System,
                        onClick = { onThemeModeChange(ThemeMode.System) },
                    )
                    ChoiceRow(
                        label = stringResource(R.string.st25_theme_light),
                        selected = themeMode == ThemeMode.Light,
                        onClick = { onThemeModeChange(ThemeMode.Light) },
                    )
                    ChoiceRow(
                        label = stringResource(R.string.st25_theme_dark),
                        selected = themeMode == ThemeMode.Dark,
                        onClick = { onThemeModeChange(ThemeMode.Dark) },
                    )
                }
            }

            item {
                SectionHeader(title = stringResource(R.string.st25_numerals_section))
                EduCard {
                    ChoiceRow(
                        label = stringResource(R.string.st25_numerals_western),
                        selected = numeralSystem == NumeralSystem.Western,
                        onClick = { onNumeralSystemChange(NumeralSystem.Western) },
                    )
                    ChoiceRow(
                        label = stringResource(R.string.st25_numerals_arabic_indic),
                        selected = numeralSystem == NumeralSystem.ArabicIndic,
                        onClick = { onNumeralSystemChange(NumeralSystem.ArabicIndic) },
                    )
                    Text(
                        text = stringResource(R.string.st25_numerals_note),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                }
            }

            item {
                SectionHeader(title = stringResource(R.string.st25_text_size_section))
                EduCard {
                    ChoiceRow(
                        label = stringResource(R.string.st25_text_size_default),
                        selected = textSizePreference == TextSizePreference.Default,
                        onClick = { onTextSizePreferenceChange(TextSizePreference.Default) },
                    )
                    ChoiceRow(
                        label = stringResource(R.string.st25_text_size_large),
                        selected = textSizePreference == TextSizePreference.Large,
                        onClick = { onTextSizePreferenceChange(TextSizePreference.Large) },
                    )
                    Text(
                        text = stringResource(R.string.st25_text_size_note),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                }
            }

            item {
                SectionHeader(title = stringResource(R.string.st25_calendar_section))
                EduCard {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                stringResource(R.string.st25_hijri_toggle_title),
                                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                                color = colors.textPrimary,
                            )
                            Text(
                                stringResource(R.string.st25_hijri_toggle_body),
                                style = EduTheme.typography.caption,
                                color = colors.textSecondary,
                                modifier = Modifier.padding(top = Spacing.xxs),
                            )
                        }
                        Switch(
                            checked = useHijriDates,
                            onCheckedChange = onUseHijriDatesChange,
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = colors.onPrimary,
                                checkedTrackColor = colors.primary,
                            ),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ChoiceRow(label: String, selected: Boolean, onClick: () -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(vertical = Spacing.xs),
    ) {
        RadioDot(selected = selected)
        Text(
            text = label,
            style = EduTheme.typography.body,
            color = if (selected) colors.textPrimary else colors.textSecondary,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun RadioDot(selected: Boolean) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(Sizing.iconSm)
            .border(width = Sizing.hairline * 2, color = if (selected) colors.primary else colors.border, shape = CircleShape),
    ) {
        if (selected) {
            Box(
                modifier = Modifier
                    .size(Sizing.iconSm * 0.5f)
                    .background(colors.primary, CircleShape),
            )
        }
    }
}
