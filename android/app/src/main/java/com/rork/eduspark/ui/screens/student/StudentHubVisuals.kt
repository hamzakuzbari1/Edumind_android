package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.standardSpec

enum class HubTimelineState { Done, Current, Upcoming, Missed }

@Composable
internal fun HubProgressRing(
    progress: Float,
    modifier: Modifier = Modifier,
    size: Dp = 96.dp,
    stroke: Dp = 10.dp,
    tint: Color = EduTheme.colors.success,
    content: @Composable BoxScope.() -> Unit,
) {
    val colors = EduTheme.colors
    val clamped = progress.coerceIn(0f, 1f)
    val animated by animateFloatAsState(clamped, standardSpec(), label = "hubRing")
    Box(contentAlignment = Alignment.Center, modifier = modifier.size(size)) {
        Canvas(modifier = Modifier.size(size)) {
            val width = stroke.toPx()
            val diameter = this.size.minDimension - width
            drawCircle(colors.border, radius = diameter / 2f, style = Stroke(width))
            drawArc(
                color = tint,
                startAngle = -90f,
                sweepAngle = 360f * animated,
                useCenter = false,
                style = Stroke(width = width, cap = StrokeCap.Round),
                topLeft = Offset(width / 2f, width / 2f),
                size = Size(this.size.width - width, this.size.height - width),
            )
        }
        content()
    }
}

@Composable
internal fun HubWeekMini(
    labels: List<String>,
    fills: List<Float>,
    selectedIndex: Int,
    todayIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier.fillMaxWidth(),
    ) {
        labels.forEachIndexed { index, label ->
            val selected = index == selectedIndex
            val isToday = index == todayIndex
            val fill = fills.getOrElse(index) { 0f }.coerceIn(0f, 1f)
            val barColor = when {
                fill >= 0.99f -> colors.success
                isToday -> colors.primary
                fill > 0f -> colors.primary.copy(alpha = 0.45f)
                else -> colors.neutralAlpha100
            }
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier
                    .weight(1f)
                    .eduClickable(onClickLabel = label, role = Role.Tab, onClick = { onSelect(index) })
                    .semantics { this.selected = selected }
                    .padding(vertical = Spacing.xxs),
            ) {
                Box(
                    contentAlignment = Alignment.BottomCenter,
                    modifier = Modifier
                        .height(36.dp)
                        .fillMaxWidth()
                        .background(colors.neutralAlpha100, RoundedCornerShape(6.dp)),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .fillMaxHeight(fill.coerceAtLeast(0.12f))
                            .background(barColor, RoundedCornerShape(6.dp)),
                    )
                }
                Text(
                    text = label,
                    style = EduTheme.typography.caption.copy(fontWeight = if (selected || isToday) FontWeight.ExtraBold else FontWeight.SemiBold),
                    color = if (selected || isToday) colors.primary else colors.textTertiary,
                )
            }
        }
    }
}

@Composable
internal fun HubTimeline(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val colors = EduTheme.colors
    Box(modifier = modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .matchParentSize()
                .padding(start = 7.dp, top = 10.dp, bottom = 10.dp),
        ) {
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .fillMaxHeight()
                    .background(colors.border, RoundedCornerShape(2.dp)),
            )
        }
        Column {
            content()
        }
    }
}

@Composable
internal fun HubTimelineDot(state: HubTimelineState, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val border = when (state) {
        HubTimelineState.Done -> colors.success
        HubTimelineState.Current -> colors.primary
        HubTimelineState.Missed -> colors.danger
        HubTimelineState.Upcoming -> colors.border
    }
    val fill = when (state) {
        HubTimelineState.Done -> colors.success
        HubTimelineState.Current -> colors.primary
        HubTimelineState.Missed -> colors.danger.copy(alpha = 0.12f)
        HubTimelineState.Upcoming -> colors.surface
    }
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(16.dp)
            .background(fill, CircleShape)
            .border(
                width = if (state == HubTimelineState.Current) 3.dp else 2.5.dp,
                color = if (state == HubTimelineState.Current) colors.primary else border,
                shape = CircleShape,
            ),
    ) {
        when (state) {
            HubTimelineState.Done -> Icon(Icons.Filled.Check, contentDescription = null, tint = colors.onPrimary, modifier = Modifier.size(9.dp))
            HubTimelineState.Missed -> Icon(Icons.Filled.Close, contentDescription = null, tint = colors.danger, modifier = Modifier.size(8.dp))
            HubTimelineState.Current -> Box(modifier = Modifier.size(5.dp).background(colors.onPrimary, CircleShape))
            HubTimelineState.Upcoming -> Unit
        }
    }
}

@Composable
internal fun HubTimelineRow(
    state: HubTimelineState,
    modifier: Modifier = Modifier,
    emphasized: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.sm)
            .then(
                if (emphasized) {
                    Modifier
                        .background(colors.primaryContainer.copy(alpha = 0.55f), RoundedCornerShape(Radius.sm))
                        .padding(Spacing.xs)
                } else {
                    Modifier
                },
            ),
    ) {
        Box(modifier = Modifier.padding(top = 2.dp)) {
            HubTimelineDot(state)
        }
        Box(modifier = Modifier.weight(1f)) { content() }
    }
}

@Composable
internal fun CafeConversationVisual(modifier: Modifier = Modifier, ink: Color = Color.White, dim: Color = Color.White.copy(alpha = 0.4f)) {
    Canvas(modifier = modifier.size(132.dp)) {
        val cup = Path().apply {
            moveTo(size.width * 0.32f, size.height * 0.42f)
            lineTo(size.width * 0.38f, size.height * 0.78f)
            lineTo(size.width * 0.62f, size.height * 0.78f)
            lineTo(size.width * 0.68f, size.height * 0.42f)
            close()
        }
        drawPath(cup, ink)
        drawArc(
            color = dim,
            startAngle = -70f,
            sweepAngle = 140f,
            useCenter = false,
            topLeft = Offset(size.width * 0.64f, size.height * 0.46f),
            size = Size(size.width * 0.16f, size.height * 0.22f),
            style = Stroke(width = 5.dp.toPx(), cap = StrokeCap.Round),
        )
        drawCircle(dim, radius = 16.dp.toPx(), center = Offset(size.width * 0.72f, size.height * 0.28f))
        drawCircle(ink.copy(alpha = 0.22f), radius = 22.dp.toPx(), center = Offset(size.width * 0.28f, size.height * 0.24f))
        drawLine(dim, Offset(size.width * 0.44f, size.height * 0.28f), Offset(size.width * 0.46f, size.height * 0.16f), 3.dp.toPx(), StrokeCap.Round)
        drawLine(dim, Offset(size.width * 0.50f, size.height * 0.26f), Offset(size.width * 0.52f, size.height * 0.14f), 3.dp.toPx(), StrokeCap.Round)
        drawLine(dim, Offset(size.width * 0.56f, size.height * 0.28f), Offset(size.width * 0.58f, size.height * 0.16f), 3.dp.toPx(), StrokeCap.Round)
    }
}

@Composable
internal fun WaveformVisual(modifier: Modifier = Modifier, color: Color = EduTheme.colors.primary) {
    Canvas(modifier = modifier.size(width = 72.dp, height = 22.dp)) {
        val bars = intArrayOf(6, 12, 18, 10, 20, 8, 16, 11)
        val gap = 4.dp.toPx()
        val barW = 4.dp.toPx()
        bars.forEachIndexed { i, h ->
            val x = i * (barW + gap)
            val height = h.dp.toPx()
            drawRoundRect(
                color = color,
                topLeft = Offset(x, (size.height - height) / 2f),
                size = Size(barW, height),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
            )
        }
    }
}

@Composable
internal fun SolarProjectVisual(modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .height(148.dp)
            .background(colors.accentContainer, RoundedCornerShape(topStart = Radius.md, topEnd = Radius.md)),
    ) {
        Canvas(modifier = Modifier.size(148.dp)) {
            drawCircle(colors.highlight.copy(alpha = 0.35f), radius = 28.dp.toPx(), center = Offset(size.width * 0.72f, size.height * 0.28f))
            drawCircle(colors.highlight, radius = 18.dp.toPx(), center = Offset(size.width * 0.72f, size.height * 0.28f))
            val panel = Path().apply {
                moveTo(size.width * 0.18f, size.height * 0.48f)
                lineTo(size.width * 0.72f, size.height * 0.40f)
                lineTo(size.width * 0.78f, size.height * 0.72f)
                lineTo(size.width * 0.24f, size.height * 0.80f)
                close()
            }
            drawPath(panel, colors.accent)
            drawLine(colors.surface.copy(alpha = 0.45f), Offset(size.width * 0.32f, size.height * 0.46f), Offset(size.width * 0.38f, size.height * 0.76f), 2.dp.toPx())
            drawLine(colors.surface.copy(alpha = 0.45f), Offset(size.width * 0.50f, size.height * 0.43f), Offset(size.width * 0.56f, size.height * 0.74f), 2.dp.toPx())
            drawLine(colors.surface.copy(alpha = 0.45f), Offset(size.width * 0.22f, size.height * 0.58f), Offset(size.width * 0.75f, size.height * 0.50f), 2.dp.toPx())
        }
    }
}

@Composable
internal fun BioProjectVisual(modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(40.dp)
            .background(colors.accentContainer, RoundedCornerShape(11.dp)),
    ) {
        Canvas(modifier = Modifier.size(22.dp)) {
            drawCircle(colors.accent.copy(alpha = 0.28f), radius = size.minDimension * 0.42f)
            drawCircle(colors.accent, radius = 4.dp.toPx(), center = Offset(size.width * 0.38f, size.height * 0.42f))
            drawCircle(colors.accent, radius = 3.dp.toPx(), center = Offset(size.width * 0.62f, size.height * 0.58f))
        }
    }
}

@Composable
internal fun BadgeArt(kind: String, modifier: Modifier = Modifier, locked: Boolean = false) {
    val colors = EduTheme.colors
    val ink = if (locked) colors.textTertiary else colors.highlight
    val wash = if (locked) colors.neutralAlpha100 else colors.highlightContainer
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(56.dp)
            .background(wash, RoundedCornerShape(Radius.sm)),
    ) {
        Canvas(modifier = Modifier.size(36.dp)) {
            when (kind) {
                "streak" -> {
                    val flame = Path().apply {
                        moveTo(size.width * 0.5f, size.height * 0.12f)
                        cubicTo(size.width * 0.78f, size.height * 0.38f, size.width * 0.82f, size.height * 0.7f, size.width * 0.5f, size.height * 0.9f)
                        cubicTo(size.width * 0.18f, size.height * 0.7f, size.width * 0.22f, size.height * 0.38f, size.width * 0.5f, size.height * 0.12f)
                    }
                    drawPath(flame, ink)
                }
                "target" -> {
                    drawCircle(ink.copy(alpha = 0.22f), radius = size.minDimension * 0.42f)
                    drawCircle(ink, radius = size.minDimension * 0.28f, style = Stroke(3.dp.toPx()))
                    drawCircle(ink, radius = 4.dp.toPx())
                }
                "crown" -> {
                    val path = Path().apply {
                        moveTo(size.width * 0.12f, size.height * 0.72f)
                        lineTo(size.width * 0.18f, size.height * 0.28f)
                        lineTo(size.width * 0.38f, size.height * 0.5f)
                        lineTo(size.width * 0.5f, size.height * 0.18f)
                        lineTo(size.width * 0.62f, size.height * 0.5f)
                        lineTo(size.width * 0.82f, size.height * 0.28f)
                        lineTo(size.width * 0.88f, size.height * 0.72f)
                        close()
                    }
                    drawPath(path, ink)
                }
                "shield" -> {
                    val path = Path().apply {
                        moveTo(size.width * 0.5f, size.height * 0.1f)
                        lineTo(size.width * 0.84f, size.height * 0.28f)
                        lineTo(size.width * 0.78f, size.height * 0.68f)
                        lineTo(size.width * 0.5f, size.height * 0.9f)
                        lineTo(size.width * 0.22f, size.height * 0.68f)
                        lineTo(size.width * 0.16f, size.height * 0.28f)
                        close()
                    }
                    drawPath(path, ink)
                }
                else -> {
                    drawCircle(ink.copy(alpha = 0.2f), radius = size.minDimension * 0.42f)
                    drawCircle(ink, radius = size.minDimension * 0.22f)
                }
            }
        }
    }
}

internal fun achievementBadgeKind(kindName: String): String = when (kindName) {
    "Streak" -> "streak"
    "QuizPerformance" -> "target"
    "StudyConsistency" -> "shield"
    "CourseProgress" -> "crown"
    else -> "medal"
}
