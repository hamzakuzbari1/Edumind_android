package com.rork.eduspark.ui.screens.auth

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.standardSpec
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-01 · Splash & Language Gate
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Two states in one screen:
 *
 *  • **First run** — the wordmark plus two large, equal language cards. Neither is
 *    pre-selected: choosing is the point, and a pre-ticked option would quietly make one
 *    language the default in an app whose whole premise is that Arabic is not a translation.
 *    Each card is written in its own language, so a reader who cannot read the current
 *    interface language can still find their way out.
 *
 *  • **Returning** — the wordmark and a restrained progress hairline while the stored
 *    session is read. No token refresh happens, because no refresh endpoint exists.
 *
 * The screen is type-led and illustration-free, and it is the only screen where the
 * wordmark is rendered at [WordmarkSize.Hero].
 */
@Composable
fun SplashScreen(
    isLanguageGate: Boolean,
    onChooseLanguage: (AppLocale) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding()
            .padding(horizontal = Spacing.gutter),
    ) {
        Box(modifier = Modifier.weight(if (isLanguageGate) 0.8f else 1f))

        AnimatedBrandEntrance()

        if (isLanguageGate) {
            Text(
                text = stringResource(R.string.a01_gate_title),
                style = EduTheme.typography.title,
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.lg),
            )
            Text(
                text = stringResource(R.string.a01_gate_body),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xs),
            )

            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.section),
            ) {
                LanguageChoiceCard(
                    title = stringResource(R.string.settings_language_arabic),
                    hint = stringResource(R.string.a01_hint_arabic),
                    clickLabel = stringResource(R.string.a11y_a01_choose_arabic),
                    onClick = { onChooseLanguage(AppLocale.Arabic) },
                )
                LanguageChoiceCard(
                    title = stringResource(R.string.settings_language_english),
                    hint = stringResource(R.string.a01_hint_english),
                    clickLabel = stringResource(R.string.a11y_a01_choose_english),
                    onClick = { onChooseLanguage(AppLocale.English) },
                )
            }

            Box(modifier = Modifier.weight(1f))
        } else {
            LaunchPulse(modifier = Modifier.padding(top = Spacing.lg))
            Text(
                text = stringResource(R.string.a01_preparing),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Box(modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun AnimatedBrandEntrance(modifier: Modifier = Modifier) {
    val alpha = remember { Animatable(0f) }
    val scale = remember { Animatable(0.86f) }
    val offsetY = remember { Animatable(22f) }

    LaunchedEffect(Unit) {
        launch { alpha.animateTo(1f, animationSpec = tween(420, easing = LinearOutSlowInEasing)) }
        launch { scale.animateTo(1f, animationSpec = tween(720, easing = FastOutSlowInEasing)) }
        launch { offsetY.animateTo(0f, animationSpec = tween(720, easing = FastOutSlowInEasing)) }
    }

    BrandWordmark(
        size = WordmarkSize.Hero,
        modifier = modifier.graphicsLayer {
            this.alpha = alpha.value
            scaleX = scale.value
            scaleY = scale.value
            translationY = offsetY.value
        },
    )
}

/**
 * One language choice. Large, equal, and unselected.
 *
 * The two cards are deliberately identical in weight — no primary/secondary treatment,
 * no accent on either — because the app has no opinion about which language you read.
 */
@Composable
private fun LanguageChoiceCard(
    title: String,
    hint: String,
    clickLabel: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(Radius.md)

    Column(
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier
            .fillMaxWidth()
            .height(96.dp)
            .background(EduTheme.colors.surface, shape)
            .border(Sizing.hairline, EduTheme.colors.border, shape)
            .eduClickable(onClickLabel = clickLabel, onClick = onClick),
    ) {
        Text(
            // Brand face: a language name is a brand moment, not interface chrome.
            text = title,
            style = EduTheme.typography.brandTitle,
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = hint,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

/**
 * The returning-launch indicator: a short segment of the Progress Spine's rail, filling once.
 *
 * Not a spinner and not a looping animation — §8 bans ambient loops, and this is a single
 * 200ms fill that respects reduced motion through [standardSpec].
 */
@Composable
private fun LaunchPulse(modifier: Modifier = Modifier) {
    val progress by animateFloatAsState(
        targetValue = 1f,
        animationSpec = standardSpec(),
        label = "launchPulse",
    )

    Box(
        contentAlignment = Alignment.CenterStart,
        modifier = modifier
            .width(80.dp)
            .height(Sizing.spineRail)
            .background(EduTheme.colors.hajar300, RoundedCornerShape(Radius.pill)),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth(progress)
                .height(Sizing.spineRail)
                .alpha(progress)
                .background(EduTheme.colors.zaytoun, RoundedCornerShape(Radius.pill)),
        ) {
            Box(modifier = Modifier.size(0.dp))
        }
    }
}
