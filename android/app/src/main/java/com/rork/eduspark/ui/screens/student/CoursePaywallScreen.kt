package com.rork.eduspark.ui.screens.student

import androidx.activity.compose.BackHandler
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.formatMoney
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonBlock
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-17 · Course Paywall Sheet.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Styled as a bottom-sheet/modal surface (rounded top corners, a drag handle, a close action)
 * rather than reusing [com.rork.eduspark.ui.components.scaffold.EduScaffold]'s title-bar
 * chrome — this app's nav graph has no bottom-sheet-as-destination mechanism to reuse instead
 * (see [com.rork.eduspark.ui.navigation.Routes.STUDENT_PAYWALL]'s own doc comment), so it is
 * still a pushed destination, just one that *looks* and reads like a sheet. This also makes
 * "ST-18 back → ST-17" a plain backstack pop rather than something a screen needs to fake.
 */
@Composable
fun CoursePaywallScreen(
    courseId: String,
    onDismiss: () -> Unit,
    onContinueToPayment: (courseId: String) -> Unit,
    onRedeemVoucher: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PaywallViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    BackHandler(onBack = onDismiss)

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background),
    ) {
        PaywallSheetHeader(onDismiss = onDismiss)
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { PaywallSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { content ->
            when (content) {
                is PaywallContent.AlreadySubscribed -> AlreadySubscribedContent(
                    courseTitle = content.courseTitle,
                    onDismiss = onDismiss,
                )
                is PaywallContent.Offer -> OfferContent(
                    offer = content.offer,
                    onContinue = { onContinueToPayment(courseId) },
                    onDismiss = onDismiss,
                    onRedeemVoucher = onRedeemVoucher,
                )
            }
        }
    }
}

@Composable
private fun PaywallSheetHeader(onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface, RoundedCornerShape(topStart = Radius.lg, topEnd = Radius.lg)),
    ) {
        Box(
            modifier = Modifier
                .padding(top = Spacing.sm)
                .size(width = Sizing.icon * 1.5f, height = Sizing.hairline * 2)
                .background(colors.border, RoundedCornerShape(Radius.pill))
                .align(Alignment.CenterHorizontally),
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = Spacing.gutter, end = Spacing.xs, top = Spacing.xs),
        ) {
            Text(
                text = stringResource(R.string.st17_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
            )
            EduIconButton(
                icon = Icons.Filled.Close,
                contentDescription = stringResource(R.string.common_close),
                onClick = onDismiss,
            )
        }
    }
}

@Composable
private fun OfferContent(offer: CourseOffer, onContinue: () -> Unit, onDismiss: () -> Unit, onRedeemVoucher: () -> Unit) {
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
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Icon(Icons.Filled.School, contentDescription = null, tint = colors.primary)
            }
            Column {
                Text(offer.courseTitle, style = EduTheme.typography.titleLg, color = colors.textPrimary)
                Text(offer.teacherName, style = EduTheme.typography.body, color = colors.textSecondary)
            }
        }

        Text(
            text = offer.accessSummary,
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.md),
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md)
                .background(colors.surface, RoundedCornerShape(Radius.md))
                .padding(Spacing.card),
        ) {
            BenefitRow(stringResource(R.string.st17_benefit_lessons))
            BenefitRow(stringResource(R.string.st17_benefit_quizzes))
            BenefitRow(stringResource(R.string.st17_benefit_tutor))
            BenefitRow(stringResource(R.string.st17_benefit_progress))
        }

        Spacer(modifier = Modifier.height(Spacing.md))

        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.st17_access_period_label), style = EduTheme.typography.body, color = colors.textSecondary)
            Text(offer.accessPeriodLabel, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        }
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        ) {
            Text(stringResource(R.string.st17_price_label), style = EduTheme.typography.body, color = colors.textSecondary)
            Text(
                text = formatMoney(offer.price),
                style = EduTheme.typography.titleLg,
                color = colors.primary,
            )
        }

        Spacer(modifier = Modifier.height(Spacing.section))

        PrimaryButton(
            text = if (offer.isRenewal) stringResource(R.string.st17_cta_renew) else stringResource(R.string.st17_cta_subscribe),
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
        )
        SecondaryButton(
            text = stringResource(R.string.common_cancel),
            onClick = onDismiss,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
        GhostButton(
            text = stringResource(R.string.st17_have_voucher),
            onClick = onRedeemVoucher,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xxs),
        )
    }
}

// Not private: CourseDetailScreen's whole-course-locked state (ST-02) reuses this exact
// benefit-row treatment rather than duplicating it — same package, same visual vocabulary.
@Composable
fun BenefitRow(label: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.padding(vertical = Spacing.xxs),
    ) {
        Icon(
            imageVector = Icons.Filled.CheckCircle,
            contentDescription = null,
            tint = EduTheme.colors.primary,
            modifier = Modifier.size(Sizing.iconSm),
        )
        Text(text = label, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
    }
}

@Composable
private fun AlreadySubscribedContent(courseTitle: String, onDismiss: () -> Unit) {
    MessageState(
        icon = Icons.Filled.CheckCircle,
        title = stringResource(R.string.st17_already_subscribed_title),
        body = stringResource(R.string.st17_already_subscribed_body, courseTitle),
        iconTint = EduTheme.colors.success,
        primaryActionLabel = stringResource(R.string.st17_close_action),
        onPrimaryAction = onDismiss,
    )
}

@Composable
private fun PaywallSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonBlock(widthFraction = 0.6f, height = 24.dp)
        SkeletonCard()
        SkeletonCard()
    }
}
