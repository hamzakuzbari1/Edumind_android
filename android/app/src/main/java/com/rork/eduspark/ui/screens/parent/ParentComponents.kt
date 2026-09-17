package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentLoginSession
import com.rork.eduspark.data.model.ParentStudyTimeAverages
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import java.util.Locale

@Composable
internal fun ParentAvatar(
    initial: String,
    modifier: Modifier = Modifier,
    containerColor: Color = EduTheme.colors.primaryContainer,
    contentColor: Color = EduTheme.colors.primary,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(Sizing.avatar)
            .background(containerColor, CircleShape),
    ) {
        Text(
            text = initial,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = contentColor,
        )
    }
}

@Composable
internal fun ParentLinkedStudentCard(
    student: ParentLinkedStudent,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    action: @Composable (() -> Unit)? = null,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier, onClick = onClick) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = student.avatarInitial,
                containerColor = colors.primaryContainer,
                contentColor = colors.primary,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = student.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                if (student.gradeLabel.isNotBlank()) {
                    Text(
                        text = student.gradeLabel,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
                if (student.email.isNotBlank()) {
                    Text(
                        text = student.email,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
            if (action != null) {
                action()
            } else if (student.statusLabel.isNotBlank()) {
                StatusPill(
                    label = student.statusLabel,
                    icon = Icons.Filled.School,
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.14f),
                )
            }
        }
    }
}

@Composable
internal fun ParentEmptyCaption(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = EduTheme.typography.body,
        color = EduTheme.colors.textSecondary,
        modifier = modifier,
    )
}

@Composable
internal fun ParentTrendDelta(percent: Float?, modifier: Modifier = Modifier) {
    if (percent == null) return
    val colors = EduTheme.colors
    val color = when {
        percent > 0f -> colors.success
        percent < 0f -> colors.warning
        else -> colors.textSecondary
    }
    StatusPill(
        label = stringResource(
            R.string.pr_vs_previous_percent,
            numeral(String.format(Locale.US, "%+.1f", percent)),
        ),
        contentColor = color,
        containerColor = color.copy(alpha = 0.14f),
        modifier = modifier,
    )
}

@Composable
internal fun ParentStudyTimeAveragesCard(
    averages: ParentStudyTimeAverages,
    weeklyComparisonPercent: Float? = null,
    monthlyComparisonPercent: Float? = null,
) {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = stringResource(R.string.pr04_averages_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        if (!averages.hasValues) {
            ParentEmptyCaption(
                text = stringResource(R.string.pr04_averages_empty),
                modifier = Modifier.padding(top = Spacing.sm),
            )
            return@EduCard
        }
        ParentAverageRow(
            label = stringResource(R.string.pr04_average_daily),
            hours = averages.dailyHours,
            trendPercent = averages.dailyTrendPercent,
        )
        EduDivider()
        ParentAverageRow(
            label = stringResource(R.string.pr04_average_weekly),
            hours = averages.weeklyHours,
            trendPercent = averages.weeklyTrendPercent ?: weeklyComparisonPercent,
        )
        EduDivider()
        ParentAverageRow(
            label = stringResource(R.string.pr04_average_monthly),
            hours = averages.monthlyHours,
            trendPercent = averages.monthlyTrendPercent ?: monthlyComparisonPercent,
        )
    }
}

@Composable
private fun ParentAverageRow(
    label: String,
    hours: Float,
    trendPercent: Float?,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
    ) {
        Text(
            text = label,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = stringResource(
                R.string.pr04_hours_value,
                numeral(String.format(Locale.US, "%.1f", hours)),
            ),
            style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textSecondary,
        )
        ParentTrendDelta(percent = trendPercent)
    }
}

@Composable
internal fun ParentLoginSessionsCard(
    sessions: List<ParentLoginSession>,
    emptyText: String,
) {
    EduCard {
        if (sessions.isEmpty()) {
            ParentEmptyCaption(text = emptyText)
            return@EduCard
        }
        sessions.forEachIndexed { index, session ->
            ParentLoginSessionRow(session = session)
            if (index != sessions.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentLoginSessionRow(session: ParentLoginSession) {
    val logoutText = when {
        session.isOpen -> stringResource(R.string.pr04_session_open)
        !session.logoutLabel.isNullOrBlank() -> session.logoutLabel
        else -> stringResource(R.string.pr_no_data_short)
    }
    val durationText = if (session.durationMinutes > 0) {
        stringResource(R.string.pr04_minutes_value, numeral(session.durationMinutes))
    } else {
        stringResource(R.string.pr_no_data_short)
    }
    val supporting = stringResource(
        R.string.pr04_session_supporting,
        session.loginLabel.ifBlank { stringResource(R.string.pr_no_data_short) },
        logoutText,
        durationText,
    )
    ListRow(
        title = session.dateLabel.ifBlank { stringResource(R.string.pr04_session_untitled) },
        supporting = supporting,
        trailingContent = {
            if (session.isOpen) {
                StatusPill(
                    label = stringResource(R.string.pr04_session_open),
                    contentColor = EduTheme.colors.primary,
                    containerColor = EduTheme.colors.primaryContainer,
                )
            } else {
                Text(
                    text = durationText,
                    style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textSecondary,
                )
            }
        },
    )
}

@Composable
internal fun ParentLabeledBarChart(
    values: List<Pair<String, Float>>,
    contentDescription: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val maxValue = values.maxOfOrNull { it.second }?.coerceAtLeast(1f) ?: 1f
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        verticalAlignment = Alignment.Bottom,
        modifier = modifier
            .fillMaxWidth()
            .height(Sizing.heroBadge + Spacing.lg)
            .semantics { this.contentDescription = contentDescription },
    ) {
        values.forEach { (label, value) ->
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Bottom,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
            ) {
                Box(
                    contentAlignment = Alignment.BottomCenter,
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .fillMaxHeight((value / maxValue).coerceIn(0.08f, 1f))
                            .background(
                                colors.primary.copy(alpha = 0.82f),
                                RoundedCornerShape(topStart = Radius.sm, topEnd = Radius.sm),
                            ),
                    )
                }
                Text(
                    text = label,
                    style = EduTheme.typography.caption,
                    color = colors.textTertiary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}
