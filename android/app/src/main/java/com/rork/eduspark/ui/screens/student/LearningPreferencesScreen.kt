package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ExplanationLength
import com.rork.eduspark.data.model.LearningGoal
import com.rork.eduspark.data.model.LearningInterest
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Learning Preferences — extends ST-22 · Student Profile.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * New screen, approved design `LearningPreferences.dc.html` — reflects Test-2SY's AI-tutor
 * personalization concept. Every piece here is assembled from components that already exist
 * ([EduChip], [PrimaryButton], the `aiAccent`-tinted card pattern already used in ST-04's
 * lesson-context pill) rather than inventing new ones. See [LearningPreferencesViewModel]'s
 * own doc comment for why this is deliberately NOT the onboarding SO-04 wizard.
 */
@Composable
fun LearningPreferencesScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LearningPreferencesViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.saved) {
        if (state.saved) onBack()
    }

    EduScaffold(
        title = stringResource(R.string.st_lp_title),
        onBack = onBack,
        modifier = modifier,
        bottomBar = {
            if (state.result is UiState.Content) {
                PrimaryButton(
                    text = stringResource(R.string.common_save),
                    onClick = viewModel::save,
                    isLoading = state.isSaving,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
                )
            }
        },
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { PreferencesSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { preferences ->
            PreferencesContent(
                preferences = preferences,
                onSelectGoal = viewModel::selectGoal,
                onSelectLength = viewModel::selectExplanationLength,
                onToggleInterest = viewModel::toggleInterest,
            )
        }
    }
}

@Composable
private fun PreferencesContent(
    preferences: LearningPreferences,
    onSelectGoal: (LearningGoal) -> Unit,
    onSelectLength: (ExplanationLength) -> Unit,
    onToggleInterest: (LearningInterest) -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item { AiTintedCard { Text(text = stringResource(R.string.st_lp_intro), style = EduTheme.typography.caption, color = colors.textPrimary) } }

        item {
            Column {
                Text(text = stringResource(R.string.st_lp_goal_section), style = EduTheme.typography.title, color = colors.textPrimary)
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(top = Spacing.xs),
                ) {
                    LearningGoal.entries.forEach { goal ->
                        EduChip(label = goal.label(), selected = goal == preferences.goal, onClick = { onSelectGoal(goal) })
                    }
                }
            }
        }

        item {
            Column {
                Text(text = stringResource(R.string.st_lp_length_section), style = EduTheme.typography.title, color = colors.textPrimary)
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(top = Spacing.xs),
                ) {
                    ExplanationLength.entries.forEach { length ->
                        EduChip(label = length.label(), selected = length == preferences.explanationLength, onClick = { onSelectLength(length) })
                    }
                }
            }
        }

        item {
            Column {
                Text(text = stringResource(R.string.st_lp_interests_section), style = EduTheme.typography.title, color = colors.textPrimary)
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(top = Spacing.xs),
                ) {
                    LearningInterest.entries.forEach { interest ->
                        EduChip(
                            label = interest.label(),
                            selected = interest in preferences.interests,
                            onClick = { onToggleInterest(interest) },
                        )
                    }
                }
            }
        }

        item {
            AiTintedCard {
                Text(
                    text = stringResource(R.string.st_lp_preview_label),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.aiAccent,
                )
                Text(
                    text = previewText(preferences),
                    style = EduTheme.typography.caption,
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

/** The intro/preview cyan `aiAccent`-tinted card pattern already used elsewhere (e.g. ST-04's lesson-context pill). */
@Composable
private fun AiTintedCard(content: @Composable () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.aiAccentContainer, RoundedCornerShape(Radius.md))
            .border(Sizing.hairline, colors.aiAccent, RoundedCornerShape(Radius.md))
            .padding(Spacing.card),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.iconSm))
            Column { content() }
        }
    }
}

@Composable
private fun previewText(preferences: LearningPreferences): String {
    val interestLabels = preferences.interests.map { it.label() }
    val interestsText = when (interestLabels.size) {
        0 -> stringResource(R.string.st_lp_preview_generic_interest)
        1 -> interestLabels.first()
        else -> {
            // Locale-aware join — never hardcode "و"/"and": the last two items join via a
            // template string, everything before that via a plain (also localized) separator.
            val allButLast = interestLabels.dropLast(1).joinToString(stringResource(R.string.st_lp_list_separator))
            stringResource(R.string.st_lp_list_last_join, allButLast, interestLabels.last())
        }
    }
    return stringResource(R.string.st_lp_preview_body, preferences.explanationLength.label(), interestsText)
}

@Composable
private fun LearningGoal.label(): String = when (this) {
    LearningGoal.ImproveGrades -> stringResource(R.string.st_lp_goal_improve_grades)
    LearningGoal.PrepareForBaccalaureate -> stringResource(R.string.st_lp_goal_prepare_bac)
    LearningGoal.DeeperUnderstanding -> stringResource(R.string.st_lp_goal_deeper_understanding)
}

@Composable
private fun ExplanationLength.label(): String = when (this) {
    ExplanationLength.Brief -> stringResource(R.string.st_lp_length_brief)
    ExplanationLength.Balanced -> stringResource(R.string.st_lp_length_balanced)
    ExplanationLength.Detailed -> stringResource(R.string.st_lp_length_detailed)
}

@Composable
private fun LearningInterest.label(): String = when (this) {
    LearningInterest.Football -> stringResource(R.string.st_lp_interest_football)
    LearningInterest.Gaming -> stringResource(R.string.st_lp_interest_gaming)
    LearningInterest.Music -> stringResource(R.string.st_lp_interest_music)
    LearningInterest.Drawing -> stringResource(R.string.st_lp_interest_drawing)
}

@Composable
private fun PreferencesSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
