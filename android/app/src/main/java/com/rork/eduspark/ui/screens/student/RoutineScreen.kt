package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
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
import androidx.compose.material.icons.filled.Bedtime
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.CalendarViewWeek
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.EventAvailable
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.RoutineSlotType
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-13 · Routine Week View.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately not styled like ST-10's Planner: a tab-style day strip instead of circular day
 * chips, slot rows carry a type icon (wake/school/commitment/study/sleep) instead of a
 * subject badge, and every slot exposes three explicit actions (Complete / Miss / Undo)
 * instead of one checkbox — the interaction model itself, not just the colour, is different,
 * because Routine (recurring structure) and Planner (dated study content) are different
 * concepts, not two skins on the same screen.
 */
@Composable
fun RoutineTabRootScreen(
    onBuildRoutine: () -> Unit,
    onRebuild: () -> Unit,
    onOpenPlanner: () -> Unit = {},
    modifier: Modifier = Modifier,
    viewModel: RoutineViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var didRequestBuilder by rememberSaveable { mutableStateOf(false) }
    var showDeleteConfirm by rememberSaveable { mutableStateOf(false) }

    if (showDeleteConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.st13_delete_routine),
            body = stringResource(R.string.st13_delete_routine_body),
            confirmLabel = stringResource(R.string.st13_delete_routine),
            onConfirm = {
                showDeleteConfirm = false
                viewModel.deleteRoutine()
            },
            onDismiss = { showDeleteConfirm = false },
            isDestructive = true,
        )
    }

    LaunchedEffect(state.result) {
        if (state.result is UiState.Empty && !didRequestBuilder) {
            didRequestBuilder = true
            onBuildRoutine()
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { RoutineSkeleton() },
        empty = {
            MessageState(
                icon = Icons.Filled.CalendarViewWeek,
                title = stringResource(R.string.st13_first_time_title),
                body = stringResource(R.string.st13_first_time_body),
                primaryActionLabel = stringResource(R.string.st13_first_time_action),
                onPrimaryAction = onBuildRoutine,
                modifier = Modifier.fillMaxSize(),
            )
        },
        modifier = modifier.fillMaxSize(),
    ) { loadedProfile ->
        RoutineContent(
            profile = loadedProfile,
            onComplete = viewModel::completeSlot,
            onMiss = viewModel::missSlot,
            onUndo = viewModel::undoSlot,
            onAcknowledgeRenewal = viewModel::acknowledgeRenewal,
            onRebuild = onRebuild,
            onRenew = viewModel::renewWeek,
            onDelete = { showDeleteConfirm = true },
            onOpenPlanner = onOpenPlanner,
        )
    }
}

@Composable
fun RoutineScreen(
    onBack: () -> Unit,
    onRebuild: () -> Unit,
    onOpenPlanner: () -> Unit = {},
    modifier: Modifier = Modifier,
    viewModel: RoutineViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showDeleteConfirm by rememberSaveable { mutableStateOf(false) }

    if (showDeleteConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.st13_delete_routine),
            body = stringResource(R.string.st13_delete_routine_body),
            confirmLabel = stringResource(R.string.st13_delete_routine),
            onConfirm = {
                showDeleteConfirm = false
                viewModel.deleteRoutine()
            },
            onDismiss = { showDeleteConfirm = false },
            isDestructive = true,
        )
    }

    EduScaffold(
        title = stringResource(R.string.st13_title),
        onBack = onBack,
        modifier = modifier,
        actions = {
            EduIconButton(
                icon = Icons.Filled.Edit,
                contentDescription = stringResource(R.string.st13_rebuild),
                onClick = onRebuild,
            )
        },
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { RoutineSkeleton() },
            empty = {
                MessageState(
                    icon = Icons.Filled.CalendarViewWeek,
                    title = stringResource(R.string.st13_first_time_title),
                    body = stringResource(R.string.st13_first_time_body),
                    primaryActionLabel = stringResource(R.string.st13_first_time_action),
                    onPrimaryAction = onRebuild,
                    modifier = Modifier.fillMaxSize(),
                )
            },
            modifier = Modifier.fillMaxSize(),
        ) { loadedProfile ->
            RoutineContent(
                profile = loadedProfile,
                onComplete = viewModel::completeSlot,
                onMiss = viewModel::missSlot,
                onUndo = viewModel::undoSlot,
                onAcknowledgeRenewal = viewModel::acknowledgeRenewal,
                onRebuild = onRebuild,
                onRenew = viewModel::renewWeek,
                onDelete = { showDeleteConfirm = true },
                onOpenPlanner = onOpenPlanner,
            )
        }
    }
}

/**
 * Approved design's vertical day-accordion (RoutineWeek.dc.html) — replaces the previous
 * horizontal day-tab-strip + single flat list. Every existing per-slot action (Complete /
 * Miss / Undo, via the unchanged [RoutineSlotRow]) is preserved verbatim inside each expanded
 * panel; only the day-to-day navigation shell changed shape. [RoutineRepository] state and
 * [RoutineProfile.slots] are read exactly as before — no repository change was needed for this.
 */
@Composable
private fun RoutineContent(
    profile: RoutineProfile,
    onComplete: (String) -> Unit,
    onMiss: (String) -> Unit,
    onUndo: (String) -> Unit,
    onAcknowledgeRenewal: () -> Unit,
    onRebuild: () -> Unit,
    onRenew: () -> Unit,
    onDelete: () -> Unit,
    onOpenPlanner: () -> Unit,
) {
    var selectedDay by rememberSaveable { mutableStateOf(profile.today.name) }
    val day = Weekday.entries.firstOrNull { it.name == selectedDay } ?: profile.today
    val daySlots = profile.slots.filter { it.day == day }.sortedBy { it.startTime.toMinutesOfDay() }
    val completedToday = daySlots.count { it.status == RoutineSlotStatus.Completed }
    val remainingToday = daySlots.count { it.status != RoutineSlotStatus.Completed }
    val currentSlot = daySlots.firstOrNull { it.status == RoutineSlotStatus.Upcoming }
    val weekCompleted = profile.slots.count { it.status == RoutineSlotStatus.Completed }
    val weekTotal = profile.slots.size.coerceAtLeast(1)
    val completedDays = Weekday.entries.count { weekday ->
        val slots = profile.slots.filter { it.day == weekday }
        slots.isNotEmpty() && slots.all { it.status == RoutineSlotStatus.Completed }
    }
    val currentStreak = completedDayStreak(profile)
    val longestStreak = longestCompletedStreak(profile)

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.sm),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            RoutineTodayHeader(
                completed = completedToday,
                total = daySlots.size,
                remaining = remainingToday,
            )
            RoutineWeekStrip(
                selectedDay = day,
                today = profile.today,
                slots = profile.slots,
                onSelectDay = { selectedDay = it.name },
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = if (day == profile.today) {
                        stringResource(R.string.st13_today_line)
                    } else {
                        day.fullLabel()
                    },
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = stringResource(R.string.st10_title),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.primary,
                    modifier = Modifier
                        .eduClickable(onClickLabel = stringResource(R.string.st10_title), onClick = onOpenPlanner)
                        .padding(horizontal = Spacing.xs, vertical = Spacing.sm),
                )
            }
            if (daySlots.isEmpty()) {
                MessageState(
                    icon = Icons.Filled.CalendarViewWeek,
                    title = stringResource(R.string.st13_empty_day_title),
                    body = stringResource(R.string.st13_empty_day_body),
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            } else {
                HubTimeline(modifier = Modifier.padding(top = Spacing.xs)) {
                    daySlots.forEach { slot ->
                        val state = when {
                            slot.status == RoutineSlotStatus.Completed -> HubTimelineState.Done
                            slot.status == RoutineSlotStatus.Missed -> HubTimelineState.Missed
                            slot.id == currentSlot?.id -> HubTimelineState.Current
                            else -> HubTimelineState.Upcoming
                        }
                        HubTimelineRow(state = state, emphasized = slot.id == currentSlot?.id) {
                            RoutineTimelineItem(
                                slot = slot,
                                isCurrent = slot.id == currentSlot?.id,
                                onComplete = { onComplete(slot.id) },
                                onMiss = { onMiss(slot.id) },
                                onUndo = { onUndo(slot.id) },
                            )
                        }
                    }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                EduCard(modifier = Modifier.weight(1f), contentPadding = PaddingValues(Spacing.sm)) {
                    Icon(Icons.Filled.LocalFireDepartment, contentDescription = null, tint = EduTheme.colors.highlight, modifier = Modifier.size(Sizing.icon))
                    Text(numeral(currentStreak), style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
                    Text(stringResource(R.string.st13_current_streak), style = EduTheme.typography.caption, color = EduTheme.colors.textTertiary)
                    Text(
                        text = stringResource(R.string.st13_longest_streak, numeral(longestStreak.coerceAtLeast(completedDays))),
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.textTertiary,
                    )
                }
                EduCard(modifier = Modifier.weight(1f), contentPadding = PaddingValues(Spacing.sm)) {
                    Icon(Icons.Filled.TrendingUp, contentDescription = null, tint = EduTheme.colors.success, modifier = Modifier.size(Sizing.icon))
                    Text(
                        text = stringResource(R.string.progress_percent, ((weekCompleted * 100f) / weekTotal).toInt()),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                        color = EduTheme.colors.textPrimary,
                    )
                    Text(stringResource(R.string.st13_week_adherence), style = EduTheme.typography.caption, color = EduTheme.colors.textTertiary)
                }
            }
        }
        if (profile.needsRenewal) {
            item {
                RenewalBanner(onAcknowledge = onAcknowledgeRenewal, onRebuild = onRebuild)
            }
        }
        item {
            RoutineManageRow(onRebuild = onRebuild, onRenew = onRenew, onDelete = onDelete)
        }
    }
}

@Composable
private fun RoutineTodayHeader(
    completed: Int,
    total: Int,
    remaining: Int,
) {
    val colors = EduTheme.colors
    val progress = if (total == 0) 0f else completed / total.toFloat()
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.md), verticalAlignment = Alignment.CenterVertically) {
            HubProgressRing(progress = progress, tint = colors.success) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("${numeral(completed)}/${numeral(total)}", style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = colors.textPrimary)
                    Text(stringResource(R.string.st13_today_chip), style = EduTheme.typography.caption, color = colors.textTertiary)
                }
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = when {
                        remaining == 0 && total > 0 -> stringResource(R.string.st13_all_done)
                        remaining == 1 -> stringResource(R.string.st13_one_left)
                        remaining > 1 -> stringResource(R.string.st13_keep_going)
                        else -> stringResource(R.string.st13_strong_today)
                    },
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                if (remaining > 1) {
                    Text(
                        text = stringResource(R.string.st13_tasks_left, numeral(remaining)),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }
    }
}

@Composable
private fun RoutineWeekStrip(
    selectedDay: Weekday,
    today: Weekday,
    slots: List<RoutineSlot>,
    onSelectDay: (Weekday) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier.fillMaxWidth(),
    ) {
        SYRIAN_WEEK_ORDER.forEach { weekday ->
            val daySlots = slots.filter { it.day == weekday }
            val selected = weekday == selectedDay
            val isToday = weekday == today
            val completed = daySlots.isNotEmpty() && daySlots.all { it.status == RoutineSlotStatus.Completed }
            val label = weekday.fullLabel()
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier
                    .weight(1f)
                    .defaultMinSize(minHeight = Sizing.touchTarget)
                    .background(
                        when {
                            selected -> colors.primary
                            isToday -> colors.primaryContainer
                            else -> colors.surface
                        },
                        RoundedCornerShape(Radius.sm),
                    )
                    .border(
                        Sizing.hairline,
                        when {
                            selected -> colors.primary
                            isToday -> colors.primary
                            completed -> colors.success
                            else -> colors.border
                        },
                        RoundedCornerShape(Radius.sm),
                    )
                    .eduClickable(onClickLabel = label, role = Role.Tab, onClick = { onSelectDay(weekday) })
                    .semantics { this.selected = selected }
                    .padding(horizontal = 2.dp, vertical = Spacing.xxs),
            ) {
                Text(
                    text = label,
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                    color = if (selected) colors.onPrimary else colors.textPrimary,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                when {
                    isToday && !selected -> Text(
                        text = stringResource(R.string.st13_today_chip),
                        style = EduTheme.typography.caption,
                        color = colors.primary,
                        maxLines = 1,
                    )
                    completed -> Icon(
                        imageVector = Icons.Filled.CheckCircle,
                        contentDescription = stringResource(R.string.st13_done),
                        tint = if (selected) colors.onPrimary else colors.success,
                        modifier = Modifier.size(Sizing.iconSm),
                    )
                    daySlots.isNotEmpty() -> Text(
                        text = stringResource(R.string.st13_day_tasks, numeral(daySlots.size)),
                        style = EduTheme.typography.caption,
                        color = if (selected) colors.onPrimary.copy(alpha = 0.88f) else colors.textSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun RoutineTimelineItem(
    slot: RoutineSlot,
    isCurrent: Boolean,
    onComplete: () -> Unit,
    onMiss: () -> Unit,
    onUndo: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = slot.title,
                    style = if (isCurrent) {
                        EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold)
                    } else {
                        EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold)
                    },
                    color = when {
                        slot.status == RoutineSlotStatus.Missed -> colors.textTertiary
                        isCurrent -> colors.textPrimary
                        else -> colors.textSecondary
                    },
                )
                Text(
                    text = if (slot.endTime != null) "${slot.startTime} – ${slot.endTime}" else slot.startTime,
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.textTertiary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = when {
                        slot.status == RoutineSlotStatus.Completed -> stringResource(R.string.st13_done)
                        slot.status == RoutineSlotStatus.Missed -> stringResource(R.string.st13_status_missed)
                        isCurrent -> stringResource(R.string.st13_now)
                        else -> stringResource(R.string.st10_status_upcoming)
                    },
                    style = EduTheme.typography.caption.copy(fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.SemiBold),
                    color = when (slot.status) {
                        RoutineSlotStatus.Completed -> colors.success
                        RoutineSlotStatus.Missed -> colors.danger
                        RoutineSlotStatus.Upcoming -> if (isCurrent) colors.primary else colors.textTertiary
                    },
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            when {
                isCurrent -> PrimaryButton(text = stringResource(R.string.st13_continue), onClick = onComplete)
                slot.status == RoutineSlotStatus.Completed -> StatusPill(
                    label = stringResource(R.string.st13_done),
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.12f),
                )
                slot.status == RoutineSlotStatus.Upcoming -> RoutineQuietAction(stringResource(R.string.st13_start), onComplete)
            }
        }
        if (slot.status != RoutineSlotStatus.Upcoming) {
            RoutineQuietAction(stringResource(R.string.st13_undo), onUndo)
        } else if (isCurrent) {
            RoutineQuietAction(stringResource(R.string.st13_miss), onMiss)
        }
    }
}

private fun completedDayStreak(profile: RoutineProfile): Int {
    var streak = 0
    val todayIndex = profile.today.ordinal
    for (offset in 0..todayIndex) {
        val day = Weekday.entries[todayIndex - offset]
        val slots = profile.slots.filter { it.day == day }
        if (slots.isNotEmpty() && slots.all { it.status == RoutineSlotStatus.Completed }) streak += 1 else break
    }
    return streak
}

private fun longestCompletedStreak(profile: RoutineProfile): Int {
    var best = 0
    var current = 0
    Weekday.entries.forEach { day ->
        val slots = profile.slots.filter { it.day == day }
        if (slots.isNotEmpty() && slots.all { it.status == RoutineSlotStatus.Completed }) {
            current += 1
            best = maxOf(best, current)
        } else {
            current = 0
        }
    }
    return best
}

@Composable
private fun RenewalBanner(onAcknowledge: () -> Unit, onRebuild: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(contentPadding = PaddingValues(Spacing.sm)) {
        Text(text = stringResource(R.string.st13_renewal_title), style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = colors.textSecondary)
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.md), modifier = Modifier.padding(top = Spacing.xxs)) {
            RoutineQuietAction(stringResource(R.string.st13_renewal_rebuild), onRebuild)
            RoutineQuietAction(stringResource(R.string.st13_renewal_keep), onAcknowledge)
        }
    }
}

@Composable
private fun RoutineManageRow(onRebuild: () -> Unit, onRenew: () -> Unit, onDelete: () -> Unit) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        RoutineQuietAction(stringResource(R.string.st13_rebuild), onRebuild)
        RoutineQuietAction(stringResource(R.string.st13_renew_week), onRenew)
        RoutineQuietAction(stringResource(R.string.st13_delete_routine), onDelete, color = EduTheme.colors.danger)
    }
}

@Composable
private fun RoutineQuietAction(label: String, onClick: () -> Unit, color: Color = EduTheme.colors.primary) {
    Text(
        text = label,
        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
        color = color,
        modifier = Modifier
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(horizontal = Spacing.xs, vertical = Spacing.sm),
    )
}

// Saturday-first Syrian week. Weekday.fullLabel() is reused from PlannerScreen.kt.
private val SYRIAN_WEEK_ORDER = listOf(
    Weekday.Saturday,
    Weekday.Sunday,
    Weekday.Monday,
    Weekday.Tuesday,
    Weekday.Wednesday,
    Weekday.Thursday,
    Weekday.Friday,
)

@Composable
private fun RoutineSlotRow(slot: RoutineSlot, onComplete: () -> Unit, onMiss: () -> Unit, onUndo: () -> Unit) {
    val colors = EduTheme.colors
    val borderColor = when (slot.status) {
        RoutineSlotStatus.Completed -> colors.success
        RoutineSlotStatus.Missed -> colors.danger
        RoutineSlotStatus.Upcoming -> colors.border
    }

    EduCard(borderColor = borderColor) {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarSm)
                    .background(colors.neutralAlpha100, CircleShape),
            ) {
                Icon(imageVector = slot.type.icon(), contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(text = slot.title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(
                    text = if (slot.endTime != null) "${slot.startTime} – ${slot.endTime}" else slot.startTime,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.xs),
                )

                when (slot.status) {
                    RoutineSlotStatus.Upcoming -> Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                        SecondaryButton(text = stringResource(R.string.st13_complete), onClick = onComplete, modifier = Modifier.weight(1f))
                        GhostButton(text = stringResource(R.string.st13_miss), onClick = onMiss, modifier = Modifier.weight(1f))
                    }

                    RoutineSlotStatus.Completed -> SlotStatusRow(Icons.Filled.CheckCircle, stringResource(R.string.st13_status_completed), colors.success, onUndo)

                    RoutineSlotStatus.Missed -> SlotStatusRow(Icons.Filled.Cancel, stringResource(R.string.st13_status_missed), colors.danger, onUndo)
                }
            }
        }
    }
}

@Composable
private fun SlotStatusRow(icon: ImageVector, label: String, tint: Color, onUndo: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.iconSm))
        Text(text = label, style = EduTheme.typography.caption, color = tint, modifier = Modifier.weight(1f))
        GhostButton(
            text = stringResource(R.string.st13_undo),
            onClick = onUndo,
            leadingIcon = Icons.Filled.Cached,
        )
    }
}

/** "6:30" → 390. Times in this fixture are always "H:MM" or "HH:MM", never padded to two digits. */
private fun String.toMinutesOfDay(): Int {
    val parts = split(":")
    val hours = parts.getOrNull(0)?.toIntOrNull() ?: 0
    val minutes = parts.getOrNull(1)?.toIntOrNull() ?: 0
    return hours * 60 + minutes
}

private fun RoutineSlotType.icon(): ImageVector = when (this) {
    RoutineSlotType.Wake -> Icons.Filled.WbSunny
    RoutineSlotType.School -> Icons.Filled.School
    RoutineSlotType.Commitment -> Icons.Filled.EventAvailable
    RoutineSlotType.StudyWindow -> Icons.Filled.MenuBook
    RoutineSlotType.Sleep -> Icons.Filled.Bedtime
}

@Composable
private fun RoutineSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(3) { SkeletonListItem() }
    }
}
