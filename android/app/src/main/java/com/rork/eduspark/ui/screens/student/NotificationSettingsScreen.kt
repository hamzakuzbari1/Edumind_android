package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.preferences.NotificationCategory
import com.rork.eduspark.core.preferences.NotificationPreferences
import com.rork.eduspark.core.preferences.QuietHours
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Remove
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-26 · Settings — Notifications.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Preferences only — see [NotificationSettingsViewModel]'s own doc comment for why there is no
 * offline state here. No Firebase/FCM, no push permission request, no scheduled Android
 * notification anywhere in this file: every toggle only ever writes a local preference.
 */
@Composable
fun NotificationSettingsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: NotificationSettingsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.st26_title), onBack = onBack, modifier = modifier) { _ ->
        val prefs = state.preferences
        if (prefs == null) {
            NotificationSkeleton()
        } else {
            NotificationContent(
                prefs = prefs,
                onCategoryToggle = viewModel::setCategoryEnabled,
                onQuietHoursEnabledChange = viewModel::setQuietHoursEnabled,
                onQuietHoursStartChange = viewModel::setQuietHoursStart,
                onQuietHoursEndChange = viewModel::setQuietHoursEnd,
            )
        }
    }
}

@Composable
private fun NotificationContent(
    prefs: NotificationPreferences,
    onCategoryToggle: (NotificationCategory, Boolean) -> Unit,
    onQuietHoursEnabledChange: (Boolean) -> Unit,
    onQuietHoursStartChange: (Int, Int) -> Unit,
    onQuietHoursEndChange: (Int, Int) -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SectionHeader(title = stringResource(R.string.st26_categories_section))
            EduCard {
                NotificationCategory.entries.forEachIndexed { index, category ->
                    CategoryRow(
                        category = category,
                        enabled = prefs.isEnabled(category),
                        onToggle = { onCategoryToggle(category, it) },
                    )
                    if (index != NotificationCategory.entries.lastIndex) {
                        Spacer(modifier = Modifier.height(Spacing.xs))
                    }
                }
            }
            if (prefs.allDisabled) {
                Text(
                    text = stringResource(R.string.st26_all_disabled_note),
                    style = EduTheme.typography.caption,
                    color = colors.warning,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.st26_quiet_hours_section))
            EduCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.st26_quiet_hours_toggle_title),
                            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                            color = colors.textPrimary,
                        )
                        Text(
                            stringResource(R.string.st26_quiet_hours_toggle_body),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                    Switch(
                        checked = prefs.quietHours.enabled,
                        onCheckedChange = onQuietHoursEnabledChange,
                        colors = SwitchDefaults.colors(checkedThumbColor = colors.onPrimary, checkedTrackColor = colors.primary),
                    )
                }

                if (prefs.quietHours.enabled) {
                    TimeStepperRow(
                        label = stringResource(R.string.st26_quiet_hours_start),
                        hour = prefs.quietHours.startHour,
                        minute = prefs.quietHours.startMinute,
                        onChange = onQuietHoursStartChange,
                        modifier = Modifier.padding(top = Spacing.md),
                    )
                    TimeStepperRow(
                        label = stringResource(R.string.st26_quiet_hours_end),
                        hour = prefs.quietHours.endHour,
                        minute = prefs.quietHours.endMinute,
                        onChange = onQuietHoursEndChange,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                }
            }
        }
    }
}

@Composable
private fun CategoryRow(category: NotificationCategory, enabled: Boolean, onToggle: (Boolean) -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(categoryTitleRes(category)),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(categoryBodyRes(category)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        Switch(
            checked = enabled,
            onCheckedChange = onToggle,
            colors = SwitchDefaults.colors(checkedThumbColor = colors.onPrimary, checkedTrackColor = colors.primary),
        )
    }
}

private fun categoryTitleRes(category: NotificationCategory): Int = when (category) {
    NotificationCategory.StudyReminders -> R.string.st26_category_study_title
    NotificationCategory.LessonUpdates -> R.string.st26_category_lessons_title
    NotificationCategory.QuizReminders -> R.string.st26_category_quiz_title
    NotificationCategory.PaymentStatus -> R.string.st26_category_payment_title
    NotificationCategory.Achievements -> R.string.st26_category_achievements_title
}

private fun categoryBodyRes(category: NotificationCategory): Int = when (category) {
    NotificationCategory.StudyReminders -> R.string.st26_category_study_body
    NotificationCategory.LessonUpdates -> R.string.st26_category_lessons_body
    NotificationCategory.QuizReminders -> R.string.st26_category_quiz_body
    NotificationCategory.PaymentStatus -> R.string.st26_category_payment_body
    NotificationCategory.Achievements -> R.string.st26_category_achievements_body
}

@Composable
private fun TimeStepperRow(
    label: String,
    hour: Int,
    minute: Int,
    onChange: (Int, Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(label, style = EduTheme.typography.body, color = colors.textPrimary)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            EduIconButton(
                icon = Icons.Filled.Remove,
                contentDescription = stringResource(R.string.st26_time_decrease),
                onClick = { val (h, m) = shiftTime(hour, minute, -STEP_MINUTES); onChange(h, m) },
            )
            Text(
                text = numeral(formatTime(hour, minute)),
                style = EduTheme.typography.mono,
                color = colors.textPrimary,
            )
            EduIconButton(
                icon = Icons.Filled.Add,
                contentDescription = stringResource(R.string.st26_time_increase),
                onClick = { val (h, m) = shiftTime(hour, minute, STEP_MINUTES); onChange(h, m) },
            )
        }
    }
}

private const val STEP_MINUTES = 30
private const val MINUTES_IN_DAY = 24 * 60

private fun shiftTime(hour: Int, minute: Int, deltaMinutes: Int): Pair<Int, Int> {
    val total = ((hour * 60 + minute + deltaMinutes) % MINUTES_IN_DAY + MINUTES_IN_DAY) % MINUTES_IN_DAY
    return total / 60 to total % 60
}

private fun formatTime(hour: Int, minute: Int): String = "%02d:%02d".format(hour, minute)

@Composable
private fun NotificationSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
