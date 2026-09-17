package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Wallet
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.formatMoney
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-18 · Payment Method Select.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * `PAYMENT_MODE = "direct"` — [PaymentMethodViewModel]'s fixtures are the only two mock
 * direct-payment options in this build; there is no card form, no gateway SDK, nothing to
 * configure per method beyond a name and an instruction line.
 */
@Composable
fun PaymentMethodScreen(
    courseId: String,
    onBack: () -> Unit,
    onSubmit: (methodId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PaymentMethodViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.st18_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { PaymentMethodSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            PaymentMethodContent(
                offer = data.offer,
                methods = data.methods,
                selectedMethodId = state.selectedMethodId,
                onSelectMethod = viewModel::selectMethod,
                onSubmit = { state.selectedMethodId?.let(onSubmit) },
            )
        }
    }
}

@Composable
private fun PaymentMethodContent(
    offer: CourseOffer,
    methods: List<PaymentMethod>,
    selectedMethodId: String?,
    onSelectMethod: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val colors = EduTheme.colors

    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
            modifier = Modifier.weight(1f),
        ) {
            item {
                EduCard {
                    Text(stringResource(R.string.st18_order_summary_label), style = EduTheme.typography.body, color = colors.textSecondary)
                    // Approved design's teacher avatar + name row (PaymentMethod.dc.html).
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                        modifier = Modifier.padding(top = Spacing.xs),
                    ) {
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .size(Sizing.avatarSm)
                                .background(colors.primaryContainer, CircleShape),
                        ) {
                            Text(offer.teacherName.take(1), style = EduTheme.typography.caption, color = colors.primary)
                        }
                        Column {
                            Text(offer.courseTitle, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                            Text(offer.teacherName, style = EduTheme.typography.caption, color = colors.textSecondary)
                        }
                    }
                    Row(
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.sm),
                    ) {
                        Text(stringResource(R.string.st18_amount_label), style = EduTheme.typography.body, color = colors.textSecondary)
                        Text(
                            text = formatMoney(offer.price),
                            style = EduTheme.typography.titleLg,
                            color = colors.primary,
                        )
                    }
                }
                SectionHeader(title = stringResource(R.string.st18_methods_section))
                Text(
                    text = stringResource(R.string.st18_methods_dev_note),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
            }

            // Approved design's 2×2 payment-method icon grid (PaymentMethod.dc.html),
            // replacing the previous vertical full-width list — built as fixed rows (the
            // method count is small and known), not a lazy grid nested in this LazyColumn.
            items(methods.chunked(2)) { rowMethods ->
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                    rowMethods.forEach { method ->
                        PaymentMethodGridCell(
                            method = method,
                            selected = method.id == selectedMethodId,
                            onClick = { onSelectMethod(method.id) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    if (rowMethods.size < 2) Spacer(modifier = Modifier.weight(1f))
                }
                Spacer(modifier = Modifier.height(Spacing.sm))
            }

            val selectedMethod = methods.firstOrNull { it.id == selectedMethodId }
            if (selectedMethod != null) {
                item {
                    Text(
                        text = selectedMethod.instruction,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            PrimaryButton(
                text = stringResource(R.string.st18_continue),
                onClick = onSubmit,
                enabled = selectedMethodId != null,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

private fun PaymentMethod.icon(): ImageVector = when (id) {
    "card" -> Icons.Filled.CreditCard
    "transfer" -> Icons.Filled.AccountBalance
    "wallet" -> Icons.Filled.Wallet
    else -> Icons.Filled.Payments
}

/** Approved design's 2×2 payment-method grid cell (PaymentMethod.dc.html's `.method`). */
@Composable
private fun PaymentMethodGridCell(method: PaymentMethod, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    val container = if (selected) colors.primaryContainer else colors.surface
    val border = if (selected) colors.primary else colors.border
    val content = if (selected) colors.primary else colors.textPrimary

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier
            .background(container, shape)
            .border(width = if (selected) Sizing.hairline * 2 else Sizing.hairline, color = border, shape = shape)
            .eduClickable(onClickLabel = method.name, onClick = onClick)
            .padding(vertical = Spacing.card, horizontal = Spacing.xs),
    ) {
        Icon(imageVector = method.icon(), contentDescription = null, tint = content, modifier = Modifier.size(Sizing.iconLg))
        Text(text = method.name, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold), color = content)
    }
}

@Composable
private fun PaymentMethodSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
