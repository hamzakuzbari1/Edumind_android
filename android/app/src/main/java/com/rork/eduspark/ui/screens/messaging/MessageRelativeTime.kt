package com.rork.eduspark.ui.screens.messaging

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.MessagingChatMessage
import kotlinx.coroutines.delay

@Composable
internal fun rememberMessageRelativeNowMillis(enabled: Boolean = true): Long {
    var nowMillis by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(enabled) {
        if (!enabled) return@LaunchedEffect
        nowMillis = System.currentTimeMillis()
        while (true) {
            delay(MessageRelativeTimeTickMs)
            nowMillis = System.currentTimeMillis()
        }
    }
    return nowMillis
}

@Composable
internal fun parentRelativeMessageTimeLabel(message: MessagingChatMessage, nowMillis: Long): String {
    val elapsedMinutes = ((nowMillis - message.sentAtMillis).coerceAtLeast(0L) / 60_000L).toInt()
    return when {
        elapsedMinutes < 1 -> stringResource(R.string.pr12_time_now)
        elapsedMinutes < 60 -> stringResource(R.string.pr12_time_minutes_ago, numeral(elapsedMinutes))
        elapsedMinutes < 24 * 60 -> stringResource(R.string.pr12_time_hours_ago, numeral(elapsedMinutes / 60))
        else -> message.sentAtLabel
    }
}

private const val MessageRelativeTimeTickMs = 30_000L
