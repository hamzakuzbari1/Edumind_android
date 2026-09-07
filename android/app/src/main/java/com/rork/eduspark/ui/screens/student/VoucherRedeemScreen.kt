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
import androidx.compose.material.icons.filled.ConfirmationNumber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.RedeemedVoucher
import com.rork.eduspark.data.model.VoucherStatus
import com.rork.eduspark.data.model.VoucherValidationResult
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.OfflineBanner
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-21 · Voucher Redeem.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A dedicated screen, not a third payment method inside ST-18 — vouchers are their own
 * entitlement rail (see [com.rork.eduspark.data.repository.VoucherRepository]'s own doc
 * comment). Simple and transactional on purpose: one field, one clear action at a time.
 */
@Composable
fun VoucherRedeemScreen(
    onBack: () -> Unit,
    onOpenCourse: (courseId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: VoucherRedeemViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.st21_title), onBack = onBack, modifier = modifier) { _ ->
        Column(modifier = Modifier.fillMaxSize()) {
            OfflineBanner(visible = !state.isOnline)
            when (val phase = state.phase) {
                is VoucherPhase.Redeemed -> RedeemedContent(
                    redeemed = phase.redeemed,
                    onOpenCourse = { onOpenCourse(phase.redeemed.courseId) },
                    onDone = onBack,
                )
                else -> InputContent(
                    code = state.code,
                    phase = phase,
                    isValidating = state.isValidating,
                    isRedeeming = state.isRedeeming,
                    onCodeChange = viewModel::updateCode,
                    onValidate = viewModel::validate,
                    onRedeem = viewModel::redeem,
                )
            }
        }
    }
}

@Composable
private fun InputContent(
    code: String,
    phase: VoucherPhase,
    isValidating: Boolean,
    isRedeeming: Boolean,
    onCodeChange: (String) -> Unit,
    onValidate: () -> Unit,
    onRedeem: () -> Unit,
) {
    val colors = EduTheme.colors
    val validated = phase as? VoucherPhase.Validated
    val rejectionMessage = validated?.result?.takeIf { it.status != VoucherStatus.Valid }?.let { rejectionCopyFor(it.status) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Text(
            text = stringResource(R.string.st21_intro),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
        )

        EduTextField(
            value = code,
            onValueChange = onCodeChange,
            label = stringResource(R.string.st21_code_label),
            placeholder = stringResource(R.string.st21_code_placeholder),
            errorText = rejectionMessage,
            leadingIcon = Icons.Filled.ConfirmationNumber,
            keyboardType = KeyboardType.Text,
            imeAction = ImeAction.Done,
            modifier = Modifier.padding(top = Spacing.md),
        )

        val grant = validated?.result?.takeIf { it.status == VoucherStatus.Valid }
        if (grant != null) {
            VoucherGrantPreview(grant)
        }

        Spacer(modifier = Modifier.height(Spacing.section))

        if (grant != null) {
            PrimaryButton(
                text = stringResource(R.string.st21_confirm_redeem),
                onClick = onRedeem,
                isLoading = isRedeeming,
                modifier = Modifier.fillMaxWidth(),
            )
        } else {
            PrimaryButton(
                text = stringResource(R.string.st21_validate),
                onClick = onValidate,
                enabled = code.isNotBlank(),
                isLoading = isValidating,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun VoucherGrantPreview(grant: VoucherValidationResult) {
    val colors = EduTheme.colors
    EduCard(borderColor = colors.primary, modifier = Modifier.padding(top = Spacing.md)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconSm))
            Text(stringResource(R.string.st21_grant_title), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        }
        SummaryLine(stringResource(R.string.st21_grant_course_label), grant.courseTitle.orEmpty())
        SummaryLine(stringResource(R.string.st21_grant_period_label), grant.accessPeriodLabel.orEmpty())
    }
}

@Composable
private fun RedeemedContent(redeemed: RedeemedVoucher, onOpenCourse: () -> Unit, onDone: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.success.copy(alpha = 0.14f), CircleShape),
            ) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.iconLg))
            }
            StatusPill(
                label = stringResource(R.string.st21_status_redeemed),
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.14f),
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.st21_redeemed_headline),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        EduCard(modifier = Modifier.padding(top = Spacing.md)) {
            SummaryLine(stringResource(R.string.st21_grant_course_label), redeemed.courseTitle)
            SummaryLine(stringResource(R.string.st21_grant_period_label), redeemed.accessPeriodLabel)
        }

        Spacer(modifier = Modifier.height(Spacing.section))

        PrimaryButton(
            text = stringResource(R.string.st21_open_course),
            onClick = onOpenCourse,
            modifier = Modifier.fillMaxWidth(),
        )
        SecondaryButton(
            text = stringResource(R.string.common_close),
            onClick = onDone,
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

@Composable
private fun rejectionCopyFor(status: VoucherStatus): String = when (status) {
    VoucherStatus.Invalid -> stringResource(R.string.st21_error_invalid)
    VoucherStatus.Expired -> stringResource(R.string.st21_error_expired)
    VoucherStatus.AlreadyUsed -> stringResource(R.string.st21_error_used)
    VoucherStatus.Valid -> ""
}
