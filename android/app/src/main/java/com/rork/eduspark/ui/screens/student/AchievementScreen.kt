package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.AchievementKind
import com.rork.eduspark.data.model.AchievementStatus
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.progress.EduLinearProgress
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

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-15 · Achievements.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The level/XP header reuses [GamificationSnapshot] — the exact same model and repository
 * call ST-01 already uses, via [AchievementViewModel]'s own doc comment — so this screen
 * never invents a second gamification concept. No leaderboard, coins, gems or social ranking
 * exists here; none of those are part of the product definition.
 */
@Composable
fun AchievementScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: AchievementViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var detailAchievement by remember { mutableStateOf<Achievement?>(null) }

    EduScaffold(title = stringResource(R.string.st15_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { AchievementSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            AchievementContent(
                gamification = data.gamification,
                achievements = data.achievements,
                longestStreakDays = data.longestStreakDays,
                recentXp = data.recentXp,
                xpRules = data.xpRules,
                onAchievementTap = { detailAchievement = it },
            )
        }
    }

    val current = detailAchievement
    if (current != null) {
        AchievementDetailDialog(achievement = current, onDismiss = { detailAchievement = null })
    }
}

@Composable
private fun AchievementContent(
    gamification: GamificationSnapshot,
    achievements: List<Achievement>,
    longestStreakDays: Int,
    recentXp: List<RecentXpActivity>,
    xpRules: List<XpRule>,
    onAchievementTap: (Achievement) -> Unit,
) {
    val earnedCount = achievements.count { it.status == AchievementStatus.Earned }

    val nextBadge = achievements
        .filter { it.status == AchievementStatus.Locked }
        .maxByOrNull { it.progress?.let { p -> p.current / p.target.toFloat() } ?: 0f }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            val colors = EduTheme.colors
            EduCard {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                    HubProgressRing(progress = gamification.progressToNextLevel, size = 100.dp, tint = colors.highlight) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(numeral(gamification.level), style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold), color = colors.textPrimary)
                            Text(stringResource(R.string.st15_level_label), style = EduTheme.typography.caption, color = colors.textTertiary)
                        }
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = stringResource(R.string.progress_level, gamification.level),
                            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.textPrimary,
                        )
                        Text(
                            text = stringResource(R.string.st15_xp_total, numeral(gamification.xp)),
                            style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                            color = colors.textSecondary,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                        EduLinearProgress(progress = gamification.progressToNextLevel, modifier = Modifier.padding(top = Spacing.sm))
                    }
                }
            }
        }
        if (nextBadge != null) {
            item {
                val colors = EduTheme.colors
                val progress = nextBadge.progress
                EduCard(borderColor = colors.highlight.copy(alpha = 0.45f)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.st15_next_badge), style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold), color = colors.highlight)
                        Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(vertical = Spacing.sm)) {
                            BadgeArt(kind = achievementBadgeKind(nextBadge.kind.name), modifier = Modifier.size(72.dp))
                        }
                        Text(
                            nextBadge.title,
                            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.textPrimary,
                            textAlign = TextAlign.Center,
                        )
                        if (progress != null) {
                            Text(
                                text = stringResource(R.string.st15_progress_of, numeral(progress.current), numeral(progress.target)),
                                style = EduTheme.typography.caption,
                                color = colors.textSecondary,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.sm),
                            )
                            EduLinearProgress(progress = progress.current / progress.target.toFloat())
                        }
                    }
                }
            }
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(R.string.st15_collection),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = stringResource(R.string.st15_progress_of, numeral(earnedCount), numeral(achievements.size)),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textTertiary,
                )
            }
            BadgeGrid(achievements = achievements, onTap = onAchievementTap)
        }
    }
}

/**
 * Approved design's hero (Achievements.dc.html): a solid highlight-tinted level circle (not
 * a [com.rork.eduspark.ui.components.progress.ProgressRing] donut), the XP total as a full
 * sentence, and a plain progress bar toward the next level. Streak moved out into
 * [StatsRow] below, matching the approved design's placement — the streak heatmap stays here
 * unchanged (Android-only richer functionality, explicitly preserved).
 */
@Composable
private fun GamificationHeader(gamification: GamificationSnapshot) {
    val colors = EduTheme.colors
    val xpRemaining = (gamification.xpForNextLevel - gamification.xp).coerceAtLeast(0)

    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.highlightContainer, CircleShape),
            ) {
                Text(text = numeral(gamification.level), style = EduTheme.typography.titleLg, color = colors.highlight)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st15_xp_total, numeral(gamification.xp)),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                if (gamification.xpForNextLevel > 0) {
                    Text(
                        text = stringResource(R.string.st15_xp_to_level, numeral(xpRemaining), numeral(gamification.level + 1)),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                    EduLinearProgress(progress = gamification.progressToNextLevel, modifier = Modifier.padding(top = Spacing.xs))
                }
            }
        }

        if (gamification.streakHistory.isNotEmpty()) {
            Text(
                text = stringResource(R.string.st15_streak_history_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
            )
            StreakHeatmap(history = gamification.streakHistory)
        }
    }
}

/** Approved design's `.tworow` compact stat pair — current streak and earned/total badges. */
@Composable
private fun StatsRow(streakDays: Int, longestStreakDays: Int, earnedCount: Int, totalCount: Int) {
    val colors = EduTheme.colors
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
        EduCard(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(R.string.st15_stat_streak_label),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textSecondary,
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.padding(top = Spacing.xxs),
            ) {
                Icon(Icons.Filled.LocalFireDepartment, contentDescription = null, tint = colors.highlight, modifier = Modifier.size(Sizing.iconSm))
                Text(text = numeral(streakDays), style = EduTheme.typography.titleLg, color = colors.highlight)
            }
        }
        EduCard(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(R.string.st15_stat_longest_streak_label),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textSecondary,
            )
            Text(
                text = numeral(longestStreakDays),
                style = EduTheme.typography.titleLg,
                color = colors.highlight,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm)) {
        EduCard(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(R.string.st15_stat_badges_label),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textSecondary,
            )
            Text(
                text = stringResource(R.string.st15_badges_fraction, numeral(earnedCount), numeral(totalCount)),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
private fun RecentXpCard(activities: List<RecentXpActivity>) {
    val colors = EduTheme.colors
    EduCard {
        activities.forEachIndexed { index, activity ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.padding(vertical = Spacing.xs),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(Sizing.avatar)
                        .background(colors.highlightContainer, CircleShape),
                ) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.highlight, modifier = Modifier.size(Sizing.icon))
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(activity.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                    Text(activity.detail, style = EduTheme.typography.caption, color = colors.textSecondary)
                }
                Text(
                    text = stringResource(R.string.st15_xp_gain_format, numeral(activity.xp)),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.highlight,
                )
            }
            if (index != activities.lastIndex) Spacer(modifier = Modifier.height(Spacing.xs))
        }
    }
}

@Composable
private fun XpRulesCard(rules: List<XpRule>) {
    val colors = EduTheme.colors
    EduCard {
        rules.forEachIndexed { index, rule ->
            Row(
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.padding(vertical = Spacing.xs),
            ) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
                Column(modifier = Modifier.weight(1f)) {
                    Text(rule.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                    Text(rule.detail, style = EduTheme.typography.caption, color = colors.textSecondary)
                }
            }
            if (index != rules.lastIndex) Spacer(modifier = Modifier.height(Spacing.xs))
        }
    }
}

/**
 * Approved design's 4-column badge grid (Achievements.dc.html), replacing the previous
 * full-width row list. Earned vs. locked is never colour-alone: a locked tile swaps in a
 * plain lock glyph in place of the achievement's own icon, exactly like the approved design's
 * own locked tiles do.
 */
@Composable
private fun BadgeGrid(achievements: List<Achievement>, onTap: (Achievement) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        achievements.chunked(3).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                row.forEach { achievement ->
                    BadgeGridItem(achievement = achievement, onClick = { onTap(achievement) }, modifier = Modifier.weight(1f))
                }
                repeat(3 - row.size) { Spacer(modifier = Modifier.weight(1f)) }
            }
        }
    }
}

@Composable
private fun BadgeGridItem(achievement: Achievement, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val isEarned = achievement.status == AchievementStatus.Earned

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.eduClickable(onClickLabel = achievement.title, onClick = onClick),
    ) {
        BadgeArt(
            kind = achievementBadgeKind(achievement.kind.name),
            locked = !isEarned,
            modifier = Modifier.size(56.dp),
        )
        Text(
            text = achievement.title,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            textAlign = TextAlign.Center,
            maxLines = 2,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun StreakHeatmap(history: List<Boolean>) {
    val colors = EduTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
        history.chunked(7).forEach { week ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
                week.forEach { studied ->
                    Box(
                        modifier = Modifier
                            .size(Sizing.iconSm)
                            .background(if (studied) colors.primary else colors.neutralAlpha100, RoundedCornerShape(Radius.sm)),
                    )
                }
            }
        }
    }
}

@Composable
private fun NoAchievementsYetBanner() {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.primaryContainer, RoundedCornerShape(Radius.md))
            .padding(Spacing.card),
    ) {
        Text(
            text = stringResource(R.string.st15_no_earned_title),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.primary,
        )
        Text(
            text = stringResource(R.string.st15_no_earned_body),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

/** Reused by [StudentHomeScreen]'s achievements preview row so the icon-per-kind mapping has one home. */
@Composable
internal fun AchievementKind.icon(): ImageVector = when (this) {
    AchievementKind.Streak -> Icons.Filled.TrendingUp
    AchievementKind.LessonCompletion -> Icons.Filled.MenuBook
    AchievementKind.QuizPerformance -> Icons.Filled.Quiz
    AchievementKind.StudyConsistency -> Icons.Filled.EmojiEvents
    AchievementKind.CourseProgress -> Icons.Filled.TrendingUp
}

@Composable
private fun AchievementDetailDialog(achievement: Achievement, onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    val isEarned = achievement.status == AchievementStatus.Earned

    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, RoundedCornerShape(Radius.lg))
                .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
                .padding(Spacing.card),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(if (isEarned) colors.primary else colors.neutralAlpha100, CircleShape),
            ) {
                androidx.compose.material3.Icon(
                    imageVector = achievement.kind.icon(),
                    contentDescription = null,
                    tint = if (isEarned) colors.onPrimary else colors.textSecondary,
                    modifier = Modifier.size(Sizing.iconLg),
                )
            }
            Text(
                text = achievement.title,
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.md),
            )
            Text(
                text = achievement.description,
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )

            if (isEarned) {
                Text(
                    text = stringResource(R.string.st15_detail_earned_label),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                if (achievement.earnedDateLabel != null) {
                    Text(text = achievement.earnedDateLabel, style = EduTheme.typography.body, color = colors.success)
                }
            } else {
                val progress = achievement.progress
                if (progress != null) {
                    Text(
                        text = stringResource(R.string.st15_detail_requirement_label),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                    Text(
                        text = stringResource(R.string.st06_question_of, numeral(progress.current), numeral(progress.target)),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.xs),
                    )
                    EduLinearProgress(progress = progress.current / progress.target.toFloat())
                }
            }

            GhostButton(
                text = stringResource(R.string.st10_close),
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
        }
    }
}

@Composable
private fun AchievementSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(4) { SkeletonListItem() }
    }
}
