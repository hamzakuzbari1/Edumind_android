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
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material3.CircularProgressIndicator
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
import com.rork.eduspark.core.format.formatMoney
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.state.OfflineBanner
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-19 · Payment Pending.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately not a success screen. Backend `unlocked=true` navigates to ST-20 instead of
 * staying on this Pending review UI. Genuine pending is the only case that remains here.
 */
@Composable
fun PaymentPendingScreen(
    courseId: String,
    methodId: String,
    onDone: () -> Unit,
    onVerified: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PaymentPendingViewModel = koinViewModel(parameters = { parametersOf(courseId, methodId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.phase) {
        if (state.phase == PaymentPendingPhase.Succeeded) onVerified()
    }

    EduScaffold(title = stringResource(R.string.st19_title), onBack = onDone, modifier = modifier) { _ ->
        Column(modifier = Modifier.fillMaxSize()) {
            OfflineBanner(visible = !state.isOnline)
            when (state.phase) {
                PaymentPendingPhase.Submitting,
                PaymentPendingPhase.Succeeded,
                -> SubmittingContent()
                PaymentPendingPhase.Pending -> state.pending?.let { PendingContent(it, onDone) } ?: SubmittingContent()
                PaymentPendingPhase.Failed -> FailedContent(onRetry = viewModel::retry)
            }
        }
    }
}

@Composable
private fun SubmittingContent() {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        CircularProgressIndicator(color = colors.primary)
        Text(
            text = stringResource(R.string.st19_submitting_title),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st19_submitting_body),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
        )
    }
}

@Composable
private fun PendingContent(pending: PendingPayment, onDone: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.accent.copy(alpha = 0.16f), CircleShape),
            ) {
                Icon(Icons.Filled.HourglassTop, contentDescription = null, tint = colors.accent)
            }
            Column {
                StatusPill(
                    label = stringResource(R.string.st19_status_pending),
                    contentColor = colors.accent,
                    containerColor = colors.accent.copy(alpha = 0.14f),
                )
                Text(
                    text = stringResource(R.string.st19_pending_headline),
                    style = EduTheme.typography.titleLg,
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }

        EduCard(modifier = Modifier.padding(top = Spacing.md)) {
            SummaryRow(stringResource(R.string.st19_course_label), pending.courseTitle)
            SummaryRow(
                stringResource(R.string.st19_amount_label),
                formatMoney(pending.amount),
            )
            SummaryRow(stringResource(R.string.st19_method_label), pending.methodName)
            SummaryRow(stringResource(R.string.st19_reference_label), pending.referenceId)
            SummaryRow(stringResource(R.string.st19_submitted_label), pending.submittedAtLabel)
        }

        Text(
            text = stringResource(R.string.st19_explanation),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.md),
        )
        Text(
            text = stringResource(R.string.st19_next_steps),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        Spacer(modifier = Modifier.height(Spacing.section))

        PrimaryButton(
            text = stringResource(R.string.st19_done),
            onClick = onDone,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun SummaryRow(label: String, value: String) {
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

@Composable
private fun FailedContent(onRetry: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        Icon(
            imageVector = Icons.Filled.ErrorOutline,
            contentDescription = null,
            tint = colors.danger,
            modifier = Modifier.size(Sizing.stateIcon),
        )
        Text(
            text = stringResource(R.string.st19_failed_title),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st19_failed_body),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
        )
        SecondaryButton(
            text = stringResource(R.string.common_retry),
            onClick = onRetry,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}
