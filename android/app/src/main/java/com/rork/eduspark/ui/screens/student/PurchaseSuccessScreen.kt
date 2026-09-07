package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.formatMoney
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-20 · Purchase Success.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately plain: a single [Icons.Filled.CheckCircle] badge and [StatusPill], no
 * confetti/coins/urgency copy — "confirmed and clear," not a celebration. See
 * [PurchaseSuccessViewModel]'s own doc comment for why this can never show for a still-Pending
 * payment.
 */
@Composable
fun PurchaseSuccessScreen(
    courseId: String,
    onOpenCourse: (courseId: String) -> Unit,
    onBackToSubscriptions: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PurchaseSuccessViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.st20_title), onBack = onBackToSubscriptions, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            modifier = Modifier.fillMaxSize(),
        ) { payment ->
            ConfirmedContent(
                payment = payment,
                justActivated = state.justActivated,
                onOpenCourse = { onOpenCourse(payment.courseId) },
                onBackToSubscriptions = onBackToSubscriptions,
            )
        }
    }
}

@Composable
private fun ConfirmedContent(
    payment: PendingPayment,
    justActivated: Boolean,
    onOpenCourse: () -> Unit,
    onBackToSubscriptions: () -> Unit,
) {
    val colors = EduTheme.colors

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            // Approved design's subtle success halo (PurchaseSuccess.dc.html) — a soft radial
            // glow behind the badge, not a flat circle.
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg + Spacing.section)
                    .background(
                        Brush.radialGradient(
                            colors = listOf(colors.success.copy(alpha = 0.14f), colors.success.copy(alpha = 0f)),
                        ),
                        CircleShape,
                    ),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(Sizing.avatarLg)
                        .background(colors.success, CircleShape),
                ) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.onPrimary, modifier = Modifier.size(Sizing.iconLg))
                }
            }
            StatusPill(
                label = stringResource(R.string.st20_status_confirmed),
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.14f),
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = if (justActivated) stringResource(R.string.st20_headline) else stringResource(R.string.st20_headline_already),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        EduCard(modifier = Modifier.padding(top = Spacing.md)) {
            // Approved design's teacher/course identity + "مفتوحة الآن" open-now confirmation
            // (PurchaseSuccess.dc.html) — shown only when a teacher name is known.
            if (payment.teacherName != null) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatarSm)
                            .background(colors.primaryContainer, CircleShape),
                    ) {
                        Text(payment.teacherName.take(1), style = EduTheme.typography.caption, color = colors.primary)
                    }
                    Text(
                        text = stringResource(R.string.st20_course_teacher_format, payment.courseTitle, payment.teacherName),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                    )
                }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                    modifier = Modifier.padding(top = Spacing.xxs),
                ) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.iconSm))
                    Text(text = stringResource(R.string.st20_open_now), style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold), color = colors.success)
                }
                androidx.compose.material3.HorizontalDivider(modifier = Modifier.padding(vertical = Spacing.sm), color = colors.border)
            }
            SummaryLine(stringResource(R.string.st20_course_label), payment.courseTitle)
            SummaryLine(stringResource(R.string.st20_amount_label), formatMoney(payment.amount))
            SummaryLine(stringResource(R.string.st20_reference_label), payment.referenceId)
        }

        Text(
            text = stringResource(R.string.st20_access_confirmation),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.md),
        )

        Spacer(modifier = Modifier.height(Spacing.section))

        PrimaryButton(
            text = stringResource(R.string.st20_open_course),
            onClick = onOpenCourse,
            modifier = Modifier.fillMaxWidth(),
        )
        SecondaryButton(
            text = stringResource(R.string.st20_back_to_subscriptions),
            onClick = onBackToSubscriptions,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun SummaryLine(label: String, value: String) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xxs),
    ) {
        Text(label, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        Text(value, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = EduTheme.colors.textPrimary)
    }
}
