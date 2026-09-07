package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Science
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing

@Composable
internal fun SubjectVisual(
    courseId: String,
    modifier: Modifier = Modifier,
    compact: Boolean = false,
    fillWidth: Boolean = true,
) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .then(
                if (fillWidth) {
                    Modifier
                        .fillMaxWidth()
                        .aspectRatio(if (compact) 2.6f else 1.95f)
                } else {
                    Modifier
                },
            )
            .background(colors.accentContainer.copy(alpha = 0.72f), RoundedCornerShape(Radius.lg)),
    ) {
        when {
            courseId.contains("math", ignoreCase = true) -> MathVisual()
            courseId.contains("biology", ignoreCase = true) || courseId.contains("chemistry", ignoreCase = true) -> {
                Icon(Icons.Filled.Science, contentDescription = null, tint = colors.accent, modifier = Modifier.size(if (compact) Sizing.stateIcon else Sizing.heroRing))
            }
            courseId.contains("english", ignoreCase = true) -> {
                Icon(Icons.Filled.ChatBubbleOutline, contentDescription = null, tint = colors.primary, modifier = Modifier.size(if (compact) Sizing.stateIcon else Sizing.heroRing))
            }
            else -> PhysicsVisual(compact = compact)
        }
    }
}

@Composable
private fun PhysicsVisual(compact: Boolean) {
    val colors = EduTheme.colors
    Canvas(modifier = Modifier.size(if (compact) 92.dp else 132.dp)) {
        val stroke = Stroke(width = 5.dp.toPx(), cap = StrokeCap.Round)
        val center = Offset(size.width * 0.5f, size.height * 0.52f)
        val radius = size.minDimension * 0.34f
        drawCircle(colors.accent.copy(alpha = 0.28f), radius, center, style = Stroke(width = 4.dp.toPx()))
        drawArc(
            color = colors.accent,
            startAngle = 205f,
            sweepAngle = 235f,
            useCenter = false,
            topLeft = Offset(center.x - radius, center.y - radius),
            size = Size(radius * 2, radius * 2),
            style = stroke,
        )
        drawLine(colors.accent, center, Offset(center.x + radius * 0.82f, center.y), strokeWidth = 5.dp.toPx(), cap = StrokeCap.Round)
        drawCircle(colors.accent, radius = 7.dp.toPx(), center = center)
        drawCircle(colors.primary, radius = 14.dp.toPx(), center = Offset(center.x + radius * 0.96f, center.y))
        drawCircle(colors.accent.copy(alpha = 0.22f), radius * 0.52f, center, style = Stroke(width = 3.dp.toPx(), pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(14f, 12f))))
    }
}

@Composable
private fun MathVisual() {
    val colors = EduTheme.colors
    Canvas(modifier = Modifier.size(132.dp)) {
        val stroke = Stroke(width = 4.dp.toPx(), cap = StrokeCap.Round)
        val baseY = size.height * 0.66f
        drawLine(colors.primary.copy(alpha = 0.2f), Offset(size.width * 0.18f, baseY), Offset(size.width * 0.82f, baseY), 2.dp.toPx())
        drawLine(colors.primary.copy(alpha = 0.2f), Offset(size.width * 0.5f, size.height * 0.2f), Offset(size.width * 0.5f, size.height * 0.82f), 2.dp.toPx())
        var previous: Offset? = null
        for (i in 0..40) {
            val x = -1.2f + (2.4f * i / 40f)
            val y = x * x
            val point = Offset(size.width * (0.22f + (x + 1.2f) / 2.4f * 0.56f), baseY - y * size.height * 0.22f)
            previous?.let { drawLine(colors.primary, it, point, strokeWidth = stroke.width, cap = StrokeCap.Round) }
            previous = point
        }
        drawCircle(colors.primary, 7.dp.toPx(), Offset(size.width * 0.38f, baseY - size.height * 0.04f))
        drawCircle(colors.primary, 7.dp.toPx(), Offset(size.width * 0.62f, baseY - size.height * 0.04f))
        drawLine(colors.primary.copy(alpha = 0.3f), Offset(size.width * 0.38f, baseY - size.height * 0.04f), Offset(size.width * 0.62f, baseY - size.height * 0.04f), 3.dp.toPx(), cap = StrokeCap.Round)
    }
}
