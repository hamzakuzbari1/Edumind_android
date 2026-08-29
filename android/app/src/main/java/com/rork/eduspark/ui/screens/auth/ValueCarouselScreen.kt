package com.rork.eduspark.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-02 · Value Carousel
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Three slides, swipeable, skippable — and type-led, with no illustration anywhere, exactly
 * as the Design System demands ("the Arabic script itself is the texture").
 *
 * **The hero is the Progress Spine.** Rather than drawing three decorative graphics and a
 * row of dots, this screen puts the app's signature element on the leading edge — right in
 * Arabic, left in English — and lets it double as the page indicator. Slide 1 makes bead 1
 * current; swiping to slide 2 completes bead 1 and lights bead 2. So the first time a user
 * ever swipes, they are taught the vocabulary that every course, language path and project
 * board in the app will reuse.
 *
 * The spine is composed **outside** the pager, not inside it: one spine per screen is a
 * hard rule, and hoisting it also means the rail is not rebuilt on every page change.
 */
private data class CarouselSlide(
    val titleRes: Int,
    val bodyRes: Int,
)

private val CarouselSlides = listOf(
    CarouselSlide(R.string.a02_slide_1_title, R.string.a02_slide_1_body),
    CarouselSlide(R.string.a02_slide_2_title, R.string.a02_slide_2_body),
    CarouselSlide(R.string.a02_slide_3_title, R.string.a02_slide_3_body),
)

@Composable
fun ValueCarouselScreen(
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onFinished: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val pagerState = rememberPagerState(pageCount = { CarouselSlides.size })
    val scope = rememberCoroutineScope()
    val currentPage = pagerState.currentPage
    val isLastPage = currentPage == CarouselSlides.lastIndex

    val pagerLabel = stringResource(R.string.a11y_a02_pager)

    val nodes = remember(currentPage) {
        CarouselSlides.indices.map { index ->
            SpineNode(
                id = index.toString(),
                state = when {
                    index < currentPage -> SpineNodeState.Completed
                    index == currentPage -> SpineNodeState.Current
                    else -> SpineNodeState.Locked
                },
            )
        }
    }

    AuthScaffold(
        modifier = modifier,
        topEndAction = {
            GhostButton(text = stringResource(R.string.a02_skip), onClick = onFinished)
        },
        bottomBlock = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    // Mono, because it is a counter — Design System §4 utility face.
                    text = stringResource(
                        R.string.a02_step,
                        numeral(currentPage + 1),
                        numeral(CarouselSlides.size),
                    ),
                    style = EduTheme.typography.mono,
                    color = EduTheme.colors.textMuted,
                )
                Spacer(modifier = Modifier.weight(1f))
                PrimaryButton(
                    text = stringResource(
                        if (isLastPage) R.string.a02_start else R.string.common_next
                    ),
                    onClick = {
                        if (isLastPage) {
                            onFinished()
                        } else {
                            scope.launch { pagerState.animateScrollToPage(currentPage + 1) }
                        }
                    },
                )
            }

            AuthLanguageToggle(
                current = locale,
                onSelect = onSelectLocale,
                modifier = Modifier.padding(top = Spacing.md),
            )
        },
    ) {
        Row(modifier = Modifier.fillMaxWidth().weight(1f)) {
            // The spine: leading edge, full height, one bead per slide.
            ProgressSpine(
                nodes = nodes,
                modifier = Modifier
                    .width(Sizing.spineGutter)
                    .fillMaxHeight()
                    .padding(top = Spacing.lg),
            ) { _, _ ->
                Spacer(modifier = Modifier.height(BEAD_SPACING))
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .semantics { contentDescription = pagerLabel },
            ) { page ->
                val slide = CarouselSlides[page]
                Column(
                    verticalArrangement = Arrangement.Center,
                    modifier = Modifier
                        .fillMaxHeight()
                        .padding(start = Spacing.xs, bottom = Spacing.section),
                ) {
                    Text(
                        text = stringResource(slide.titleRes),
                        // Onboarding headlines are a brand moment: Plex, per §4.
                        style = EduTheme.typography.display,
                        color = EduTheme.colors.textPrimary,
                    )
                    Text(
                        text = stringResource(slide.bodyRes),
                        style = EduTheme.typography.bodyLg,
                        color = EduTheme.colors.textMuted,
                        modifier = Modifier.padding(top = Spacing.md),
                    )
                }
            }
        }

        Box(modifier = Modifier.height(Spacing.md))
    }
}

/** Vertical gap between hero beads — tuned so three beads span the slide area. */
private val BEAD_SPACING = 120.dp
