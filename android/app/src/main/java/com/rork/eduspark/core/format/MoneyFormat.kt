package com.rork.eduspark.core.format

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.data.model.Money

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Currency-aware money formatting.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every price/amount in the app must render through this function, never a hardcoded "$"/"ل.س"
 * literal in a composable — [Money.currencyCode] decides the template, so the same UI renders
 * correctly whichever currency a fixture (or, eventually, a real backend) supplies. Batch 1c:
 * confirmed against both the approved mobile design and Test-2SY that SYP is the product's
 * real currency — USD support is kept only because existing fixtures elsewhere in the app
 * (outside this batch's scope) still use it.
 */
@Composable
fun formatMoney(money: Money): String {
    val amountText = numeral(money.amount)
    return when (money.currencyCode) {
        "USD" -> stringResource(R.string.payment_amount_usd, amountText)
        "SYP" -> stringResource(R.string.payment_amount_syp, amountText)
        else -> stringResource(R.string.payment_amount_generic, amountText, money.currencyCode)
    }
}
