package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-15 · Teacher Analytics — PDF page 22.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Compact attention landing: one indigo sparkline from the existing engagement snapshot,
 * one insight card for the weakest class, then a short attention list. Not a BI wall.
 */
@Composable
fun TeacherAnalyticsScreen(
    onBack: () -> Unit,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    onOpenStudentDetail: (studentId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherAnalyticsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherAnalyticsEvent.OpenCourse -> onOpenCourse(event.courseId)
                is TeacherAnalyticsEvent.OpenQuizResults -> onOpenQuizResults(event.quizId)
                is TeacherAnalyticsEvent.OpenStudentDetail -> onOpenStudentDetail(event.studentId)
            }
        }
    }

    EduScaffold(title = stringResource(R.string.tc15_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherAnalyticsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherAnalyticsContent(
                data = data,
                onOpenCourse = viewModel::onOpenCourse,
                onOpenQuizResults = viewModel::onOpenQuizResults,
                onOpenStudentDetail = viewModel::onOpenStudentDetail,
            )
        }
    }
}

@Composable
private fun TeacherAnalyticsContent(
    data: TeacherAnalyticsScreenData,
    onOpenCourse: (String) -> Unit,
    onOpenQuizResults: (String) -> Unit,
    onOpenStudentDetail: (String) -> Unit,
) {
    val colors = EduTheme.colors
    val hasAttention = data.quizAttention != null || data.inactiveAttention != null

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            AnalyticsSparkline(
                counts = data.engagementCounts,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            )
        }

        data.insight?.let { insight ->
            item {
                InsightCard(
                    insight = insight,
                    onOpenCourse = { onOpenCourse(insight.courseId) },
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
            }
        }

        item {
            Text(
                text = stringResource(R.string.tc15_attention_section),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }

        if (!hasAttention) {
            item {
                Text(
                    text = stringResource(R.string.tc15_attention_empty),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        } else {
            data.quizAttention?.let { row ->
                item {
                    AttentionRow(
                        title = stringResource(
                            R.string.tc15_attention_quiz,
                            row.quizTitle,
                            stringResource(R.string.tc10_pending_pill, numeral(row.pendingCount)),
                        ),
                        onClick = { onOpenQuizResults(row.quizId) },
                    )
                }
            }
            data.inactiveAttention?.let { row ->
                item {
                    val inactiveLabel = if (row.inactiveCount == 1) {
                        stringResource(R.string.tc02_inactive_one)
                    } else {
                        stringResource(R.string.tc02_inactive_many, numeral(row.inactiveCount))
                    }
                    AttentionRow(
                        title = stringResource(R.string.tc15_attention_inactive, row.subjectTitle, inactiveLabel),
                        onClick = {
                            val studentId = row.firstStudentId
                            if (row.inactiveCount == 1 && studentId != null) {
                                onOpenStudentDetail(studentId)
                            } else {
                                onOpenCourse(row.courseId)
                            }
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun AnalyticsSparkline(
    counts: List<Int>,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .height(100.dp)
            .background(colors.primaryContainer, RoundedCornerShape(Radius.md)),
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp)
                .padding(horizontal = Spacing.section),
        ) {
            if (counts.isEmpty()) return@Canvas
            val max = (counts.maxOrNull() ?: 1).coerceAtLeast(1).toFloat()
            val min = (counts.minOrNull() ?: 0).toFloat()
            val span = (max - min).coerceAtLeast(1f)
            val lastIndex = (counts.size - 1).coerceAtLeast(1)
            val points = counts.mapIndexed { index, count ->
                val t = index / lastIndex.toFloat()
                val x = size.width * t
                val y = size.height * (1f - ((count - min) / span).coerceIn(0.08f, 1f) * 0.84f - 0.08f)
                Offset(x, y)
            }
            val path = Path().apply {
                moveTo(points.first().x, points.first().y)
                for (i in 1 until points.size) {
                    lineTo(points[i].x, points[i].y)
                }
            }
            drawPath(
                path = path,
                color = colors.primary,
                style = Stroke(width = 6f, cap = StrokeCap.Round),
            )
            drawCircle(color = colors.primary, radius = 8f, center = points.last())
        }
    }
}

@Composable
private fun InsightCard(
    insight: TeacherAnalyticsInsight,
    onOpenCourse: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(listOf(Color(0xFF6366F1), Color(0xFF4F46E5))),
                RoundedCornerShape(Radius.lg),
            )
            .padding(Spacing.sm),
    ) {
        Text(
            text = stringResource(R.string.tc15_insight_needs_reinforcement, insight.subjectTitle),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
            color = Color.White,
        )
        Text(
            text = stringResource(
                R.string.tc15_lesson_completion,
                stringResource(R.string.progress_percent, insight.completionPercent),
            ),
            style = EduTheme.typography.caption,
            color = Color.White.copy(alpha = 0.9f),
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
        )
        Button(
            onClick = onOpenCourse,
            shape = RoundedCornerShape(Radius.sm),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color.White,
                contentColor = colors.primary,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.touchTarget),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stringResource(R.string.tc02_open_class),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                )
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                    contentDescription = null,
                )
            }
        }
    }
}

@Composable
private fun AttentionRow(
    title: String,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        onClick = onClick,
        contentPadding = PaddingValues(Spacing.sm),
        modifier = Modifier.padding(bottom = Spacing.xs),
    ) {
        Text(
            text = title,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
    }
}

@Composable
private fun TeacherAnalyticsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
