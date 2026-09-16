package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.model.SubscriptionStatus
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ConfirmationNumber
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Star
import org.koin.androidx.compose.koinViewModel
import com.rork.eduspark.core.format.formatMoney

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-16 · Subscriptions.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * This screen only reports subscription/access status — it never processes a payment itself.
 * Renew/Subscribe now navigate into ST-17's Course Paywall Sheet (see
 * [com.rork.eduspark.ui.screens.student.CoursePaywallScreen]); [onRenew]/[onSubscribe] are
 * plain `(courseId) -> Unit` callbacks the caller wires to that route, same shape as every
 * other cross-screen navigation in this app.
 */
@Composable
fun SubscriptionScreen(
    onBack: () -> Unit,
    onOpenCourse: (courseId: String) -> Unit,
    onRenew: (courseId: String) -> Unit,
    onSubscribe: (courseId: String) -> Unit,
    onRedeemVoucher: () -> Unit,
    onOpenVerifiedPurchase: (courseId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SubscriptionViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.refresh()
    }

    EduScaffold(title = stringResource(R.string.st16_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SubscriptionSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { subscriptions ->
            SubscriptionContent(
                subscriptions = subscriptions,
                availableCourses = state.availableCourses,
                verifiedPurchase = state.verifiedPurchase,
                voucherEntryEnabled = state.voucherEntryEnabled,
                onRenew = onRenew,
                onOpenCourse = onOpenCourse,
                onSubscribe = onSubscribe,
                onRedeemVoucher = onRedeemVoucher,
                onOpenVerifiedPurchase = onOpenVerifiedPurchase,
            )
        }
    }
}

@Composable
private fun SubscriptionContent(
    subscriptions: List<CourseSubscription>,
    availableCourses: List<AvailableCourse>,
    verifiedPurchase: PendingPayment?,
    voucherEntryEnabled: Boolean,
    onRenew: (String) -> Unit,
    onOpenCourse: (String) -> Unit,
    onSubscribe: (String) -> Unit,
    onRedeemVoucher: () -> Unit,
    onOpenVerifiedPurchase: (String) -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (verifiedPurchase != null) {
            item {
                VerifiedPurchaseBanner(
                    payment = verifiedPurchase,
                    onClick = { onOpenVerifiedPurchase(verifiedPurchase.courseId) },
                )
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        }

        item {
            SubscriptionOverviewCard(
                activeCount = subscriptions.count { it.status == SubscriptionStatus.Active },
                availableCount = availableCourses.size,
            )
            Spacer(modifier = Modifier.height(Spacing.md))
        }

        if (subscriptions.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.st16_active_section)) }
            items(subscriptions, key = { it.courseId }) { sub ->
                SubscriptionCard(
                    subscription = sub,
                    onOpenCourse = { onOpenCourse(sub.courseId) },
                    onRenew = { onRenew(sub.courseId) },
                )
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        } else {
            item {
                MessageState(
                    icon = Icons.Filled.School,
                    title = stringResource(R.string.st16_no_subscriptions_title),
                    body = stringResource(R.string.st16_no_subscriptions_body),
                )
            }
        }

        if (availableCourses.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.st16_available_section)) }
            items(availableCourses, key = { it.courseId }) { course ->
                AvailableCourseCard(course = course, onSubscribe = { onSubscribe(course.courseId) })
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        }

        if (voucherEntryEnabled) {
            item {
                SectionHeader(title = stringResource(R.string.st16_voucher_section))
                ListRow(
                    title = stringResource(R.string.st16_voucher_row_title),
                    supporting = stringResource(R.string.st16_voucher_row_supporting),
                    leading = Icons.Filled.ConfirmationNumber,
                    showChevron = true,
                    onClick = onRedeemVoucher,
                )
            }
        }
    }
}

@Composable
private fun VerifiedPurchaseBanner(payment: PendingPayment, onClick: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(onClick = onClick, borderColor = colors.success) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.success.copy(alpha = 0.14f), CircleShape),
            ) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st16_verified_purchase_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.st16_verified_purchase_body, payment.courseTitle),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        }
    }
}

@Composable
private fun SubscriptionOverviewCard(activeCount: Int, availableCount: Int) {
    val colors = EduTheme.colors
    EduCard(borderColor = colors.primary.copy(alpha = 0.2f)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Icon(Icons.Filled.Payments, contentDescription = null, tint = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st16_overview_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.st16_overview_body),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        ) {
            OverviewStat(
                label = stringResource(R.string.st16_active_count_label),
                value = numeral(activeCount),
                modifier = Modifier.weight(1f),
            )
            OverviewStat(
                label = stringResource(R.string.st16_available_count_label),
                value = numeral(availableCount),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun OverviewStat(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .background(EduTheme.colors.neutralAlpha100, RoundedCornerShape(Radius.md))
            .padding(vertical = Spacing.sm, horizontal = Spacing.xs),
    ) {
        Text(value, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.primary)
        Text(label, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
    }
}

@Composable
private fun SubscriptionCard(
    subscription: CourseSubscription,
    onOpenCourse: () -> Unit,
    onRenew: () -> Unit,
) {
    val colors = EduTheme.colors
    val borderColor = when (subscription.status) {
        SubscriptionStatus.Active -> colors.border
        SubscriptionStatus.ExpiringSoon -> colors.warning
        SubscriptionStatus.Expired -> colors.danger
    }
    val pillLabel = when (subscription.status) {
        SubscriptionStatus.Active -> stringResource(R.string.st16_status_active)
        SubscriptionStatus.ExpiringSoon -> stringResource(R.string.st16_status_expiring)
        SubscriptionStatus.Expired -> stringResource(R.string.st16_status_expired)
    }
    val pillColor = when (subscription.status) {
        SubscriptionStatus.Active -> colors.success
        SubscriptionStatus.ExpiringSoon -> colors.warning
        SubscriptionStatus.Expired -> colors.danger
    }

    EduCard(borderColor = borderColor) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.neutralAlpha100, CircleShape),
            ) {
                Icon(Icons.Filled.School, contentDescription = null, tint = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(subscription.courseTitle, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(subscription.teacherName, style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            StatusPill(label = pillLabel, contentColor = pillColor, containerColor = pillColor.copy(alpha = 0.14f))
        }

        if (subscription.expiryDateLabel != null) {
            Text(
                text = stringResource(R.string.st16_expires_on, subscription.expiryDateLabel),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }

        val daysLeft = subscription.daysUntilExpiry
        if (subscription.status == SubscriptionStatus.ExpiringSoon && daysLeft != null) {
            Text(
                text = pluralStringResource(R.plurals.st16_expires_in_days, daysLeft, numeral(daysLeft)),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.warning,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }

        if (subscription.includedFeatures.isNotEmpty()) {
            FeatureLine(features = subscription.includedFeatures, modifier = Modifier.padding(top = Spacing.sm))
        }

        if (subscription.status == SubscriptionStatus.Active) {
            PrimaryButton(
                text = stringResource(R.string.st16_continue_course),
                onClick = onOpenCourse,
                leadingIcon = Icons.Filled.PlayArrow,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
        } else {
            PrimaryButton(
                text = stringResource(R.string.st16_renew),
                onClick = onRenew,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
        }
    }
}

@Composable
private fun AvailableCourseCard(course: AvailableCourse, onSubscribe: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(borderColor = colors.primary.copy(alpha = 0.22f)) {
        Text(
            text = stringResource(R.string.st16_available_eyebrow),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = colors.primary,
        )
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.neutralAlpha100, CircleShape),
            ) {
                Icon(Icons.Filled.School, contentDescription = null, tint = colors.textSecondary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(course.courseTitle, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(course.teacherName, style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            Text(
                course.price?.let { formatMoney(it) } ?: course.priceLabel,
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                color = colors.primary,
            )
        }
        if (course.benefits.isNotEmpty()) {
            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(top = Spacing.sm),
            ) {
                course.benefits.forEach { benefit ->
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    ) {
                        Icon(Icons.Filled.Star, contentDescription = null, tint = colors.highlight, modifier = Modifier.size(Sizing.iconSm))
                        Text(benefit, style = EduTheme.typography.caption, color = colors.textSecondary)
                    }
                }
            }
        }
        if (course.includedFeatures.isNotEmpty()) {
            FeatureLine(features = course.includedFeatures, modifier = Modifier.padding(top = Spacing.sm))
        }
        SecondaryButton(
            text = stringResource(R.string.st16_subscribe),
            onClick = onSubscribe,
            leadingIcon = Icons.Filled.LockOpen,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun FeatureLine(features: List<String>, modifier: Modifier = Modifier) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier.fillMaxWidth(),
    ) {
        features.take(4).forEach { feature ->
            StatusPill(
                label = feature,
                contentColor = EduTheme.colors.primary,
                containerColor = EduTheme.colors.primary.copy(alpha = 0.1f),
            )
        }
    }
}

@Composable
private fun SubscriptionSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        repeat(3) { SkeletonCard() }
    }
}
