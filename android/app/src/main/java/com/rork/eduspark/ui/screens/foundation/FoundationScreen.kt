package com.rork.eduspark.ui.screens.foundation

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.ThemeMode
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.ui.EmptyReason
import com.rork.eduspark.ui.components.ai.AiDisclosureFooter
import com.rork.eduspark.ui.components.ai.AiMessageBubble
import com.rork.eduspark.ui.components.ai.AiTypingIndicator
import com.rork.eduspark.ui.components.ai.UserMessageBubble
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.OtpInput
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.nav.SegmentedControl
import com.rork.eduspark.ui.components.progress.CefrBadge
import com.rork.eduspark.ui.components.progress.LevelBar
import com.rork.eduspark.ui.components.progress.ProgressRing
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.progress.StreakFlame
import com.rork.eduspark.ui.components.progress.XpChip
import com.rork.eduspark.ui.components.scaffold.EduRootScaffold
import com.rork.eduspark.ui.components.state.DefaultEmptyState
import com.rork.eduspark.ui.components.state.ErrorState
import com.rork.eduspark.ui.components.state.OfflineBanner
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Foundation gallery — a development surface, not a product screen.
 *
 * It renders every token and every shared component in one place so the design system can
 * be verified on a real device before any Phase 0 screen exists: Arabic RTL vs English LTR,
 * light vs dark, dynamic type, and the Progress Spine at its three bead states.
 *
 * It is deleted (or moved behind a debug entry point) the moment A-01 becomes the start
 * destination.
 */
@Composable
fun FoundationScreen(
    onOpenStudentShell: () -> Unit,
    onOpenTeacherShell: () -> Unit,
    onOpenParentShell: () -> Unit,
    onOpenAuth: () -> Unit,
    modifier: Modifier = Modifier,
    themeMode: ThemeMode = ThemeMode.System,
    onThemeModeChange: (ThemeMode) -> Unit = {},
    numeralSystem: NumeralSystem = NumeralSystem.Western,
    onNumeralSystemChange: (NumeralSystem) -> Unit = {},
    onToggleLocale: () -> Unit = {},
    isOffline: Boolean = false,
) {
    EduRootScaffold(
        title = stringResource(R.string.foundation_title),
        modifier = modifier,
    ) { innerPadding ->
        LazyColumn(
            contentPadding = androidx.compose.foundation.layout.PaddingValues(
                start = Spacing.gutter,
                end = Spacing.gutter,
                top = Spacing.xs,
                bottom = Spacing.xl,
            ),
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(innerPadding),
        ) {
            item { OfflineBanner(visible = isOffline) }

            item {
                Text(
                    text = stringResource(R.string.foundation_subtitle),
                    style = EduTheme.typography.body,
                    color = EduTheme.colors.textMuted,
                )
            }

            // ── Display settings: prove locale + theme + numerals switch live ──
            item { SectionHeader(title = stringResource(R.string.settings_language)) }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    SecondaryButton(
                        text = stringResource(R.string.settings_language_arabic),
                        onClick = onToggleLocale,
                    )
                    SecondaryButton(
                        text = stringResource(R.string.settings_language_english),
                        onClick = onToggleLocale,
                    )
                }
            }

            item { SectionHeader(title = stringResource(R.string.settings_theme)) }
            item {
                SegmentedControl(
                    options = ThemeMode.entries,
                    selected = themeMode,
                    onSelect = onThemeModeChange,
                    labelOf = { mode ->
                        stringResource(
                            when (mode) {
                                ThemeMode.System -> R.string.settings_theme_system
                                ThemeMode.Light -> R.string.settings_theme_light
                                ThemeMode.Dark -> R.string.settings_theme_dark
                            }
                        )
                    },
                )
            }

            item { SectionHeader(title = stringResource(R.string.settings_numerals)) }
            item {
                SegmentedControl(
                    options = NumeralSystem.entries,
                    selected = numeralSystem,
                    onSelect = onNumeralSystemChange,
                    labelOf = { system ->
                        stringResource(
                            when (system) {
                                NumeralSystem.Western -> R.string.settings_numerals_western
                                NumeralSystem.ArabicIndic -> R.string.settings_numerals_arabic
                            }
                        )
                    },
                )
            }

            // ── Colour ────────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_color)) }
            item { ColorSwatches() }

            // ── Typography ────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_type)) }
            item {
                EduCard {
                    Text(
                        text = stringResource(R.string.foundation_sample_brand),
                        style = EduTheme.typography.display,
                        color = EduTheme.colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.foundation_sample_body),
                        style = EduTheme.typography.bodyLg,
                        color = EduTheme.colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                    Text(
                        text = "A1 · 12:45 · 4821",
                        style = EduTheme.typography.mono,
                        color = EduTheme.colors.textMuted,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
            }

            // ── Actions ───────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_actions)) }
            item {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    PrimaryButton(
                        text = stringResource(R.string.common_continue),
                        onClick = {},
                        leadingIcon = Icons.Filled.PlayArrow,
                    )
                    SecondaryButton(text = stringResource(R.string.common_retry), onClick = {})
                    GhostButton(text = stringResource(R.string.common_close), onClick = {})
                }
            }

            // ── Surfaces ──────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_surfaces)) }
            item {
                EduCard {
                    ListRow(
                        title = stringResource(R.string.foundation_sample_question),
                        supporting = stringResource(R.string.common_loading),
                        showChevron = true,
                        onClick = {},
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                        StatusPill(label = "PDF")
                        StatusPill(
                            label = stringResource(R.string.common_done),
                            contentColor = EduTheme.colors.success,
                        )
                    }
                    SkeletonListItem()
                }
            }

            // ── Inputs ────────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_inputs)) }
            item { InputsPreview() }

            // ── Progress + the Spine ──────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_progress)) }
            item {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    ProgressRing(progress = 0.62f)
                    StreakFlame(days = 11)
                    XpChip(xp = 1240)
                    CefrBadge(level = "B1")
                }
            }
            item { LevelBar(level = 7, progressToNextLevel = 0.62f) }
            item { SpinePreview() }

            // ── AI surfaces ───────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_ai)) }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    UserMessageBubble(text = stringResource(R.string.foundation_sample_question))
                    AiMessageBubble(text = stringResource(R.string.foundation_sample_answer)) {
                        AiDisclosureFooter()
                    }
                    AiTypingIndicator()
                }
            }

            // ── States ────────────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_states)) }
            item {
                Box(modifier = Modifier.height(220.dp)) {
                    DefaultEmptyState(reason = EmptyReason.NoContent)
                }
            }
            item {
                Box(modifier = Modifier.height(240.dp)) {
                    ErrorState(error = AppError.Offline, onRetry = {})
                }
            }

            // ── Role shells ───────────────────────────────────────────────
            item { SectionHeader(title = stringResource(R.string.foundation_section_shells)) }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    PrimaryButton(
                        text = stringResource(R.string.foundation_open_student),
                        onClick = onOpenStudentShell,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    SecondaryButton(
                        text = stringResource(R.string.foundation_open_teacher),
                        onClick = onOpenTeacherShell,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    SecondaryButton(
                        text = stringResource(R.string.foundation_open_parent),
                        onClick = onOpenParentShell,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    GhostButton(
                        text = stringResource(R.string.placeholder_title),
                        onClick = onOpenAuth,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun ColorSwatches() {
    val colors = EduTheme.colors
    val swatches = listOf(
        "zaytoun" to colors.zaytoun,
        "barq" to colors.barq,
        "jouri" to colors.jouri,
        "success" to colors.success,
        "warning" to colors.warning,
        "danger" to colors.danger,
    )
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        swatches.forEach { (name, color) -> Swatch(name = name, color = color) }
    }
}

@Composable
private fun Swatch(name: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(Sizing.stateIcon)
                .background(color, RoundedCornerShape(Radius.sm))
                .border(Sizing.hairline, EduTheme.colors.border, RoundedCornerShape(Radius.sm))
        )
        Text(text = name, style = EduTheme.typography.caption, color = EduTheme.colors.textMuted)
    }
}

@Composable
private fun InputsPreview() {
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var query by rememberSaveable { mutableStateOf("") }
    var otp by rememberSaveable { mutableStateOf("12") }
    var chipSelected by rememberSaveable { mutableStateOf(true) }

    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        EduTextField(
            value = email,
            onValueChange = { email = it },
            label = stringResource(R.string.settings_language),
        )
        PasswordField(
            value = password,
            onValueChange = { password = it },
            label = stringResource(R.string.a11y_password_show),
        )
        SearchField(value = query, onValueChange = { query = it })
        OtpInput(
            value = otp,
            onValueChange = { otp = it },
            contentDescription = stringResource(R.string.common_confirm),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            EduChip(
                label = stringResource(R.string.tab_student_courses),
                selected = chipSelected,
                onClick = { chipSelected = !chipSelected },
            )
            EduChip(
                label = stringResource(R.string.tab_student_english),
                selected = !chipSelected,
                onClick = { chipSelected = !chipSelected },
            )
        }
    }
}

/** The Progress Spine at all three bead states, on the leading edge. */
@Composable
private fun SpinePreview() {
    val nodes = listOf(
        SpineNode(id = "1", state = SpineNodeState.Completed),
        SpineNode(id = "2", state = SpineNodeState.Completed),
        SpineNode(id = "3", state = SpineNodeState.Current),
        SpineNode(id = "4", state = SpineNodeState.Locked),
    )
    val titles = listOf(
        "المتتاليات العددية",
        "النهايات والاتصال",
        "الاشتقاق وتطبيقاته",
        "درس Python الأول",
    )

    ProgressSpine(nodes = nodes) { index, node ->
        EduCard(
            borderColor = if (node.state == SpineNodeState.Current) {
                EduTheme.colors.zaytoun
            } else {
                EduTheme.colors.border
            },
        ) {
            Text(
                text = titles[index],
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.progress_percent, (index + 1) * 25),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )
        }
    }
}
