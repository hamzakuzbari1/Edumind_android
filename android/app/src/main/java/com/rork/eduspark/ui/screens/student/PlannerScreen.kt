package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.PlannerSession
import com.rork.eduspark.data.model.SessionStatus
import com.rork.eduspark.data.model.WeekPlan
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.nav.SheetHandle
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.LocalReducedMotion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlannerScreen(
    onBack: () -> Unit,
    onAskAssistant: () -> Unit,
    onOpenRoutine: () -> Unit,
    onOpenExamCapture: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PlannerViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val plan = (state.result as? UiState.Content)?.data
    var selectedDay by rememberSaveable { mutableStateOf<Weekday?>(null) }
    var detailSession by remember { mutableStateOf<PlannerSession?>(null) }
    val effectiveSelectedDay = selectedDay ?: plan?.today ?: Weekday.Sunday

    EduScaffold(
        title = stringResource(R.string.st10_title),
        onBack = onBack,
        modifier = modifier,
        actions = {
            EduIconButton(
                icon = Icons.Filled.CameraAlt,
                contentDescription = stringResource(R.string.st10_open_exam_capture),
                onClick = onOpenExamCapture,
            )
            EduIconButton(
                icon = Icons.Filled.Refresh,
                contentDescription = stringResource(R.string.st10_regenerate),
                onClick = viewModel::regenerateWeek,
            )
        },
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { PlannerSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { loadedPlan ->
            PlannerContent(
                plan = loadedPlan,
                selectedDay = effectiveSelectedDay,
                recommendations = state.recommendations,
                onSelectDay = { selectedDay = it },
                onTapSession = { detailSession = it },
                onApplyRecommendation = viewModel::applyRecommendation,
                onIgnoreRecommendation = viewModel::ignoreRecommendation,
            )
        }
    }

    val openSession = detailSession
    if (openSession != null) {
        SessionDetailSheet(
            session = openSession,
            onDismiss = { detailSession = null },
            onAskAssistant = {
                detailSession = null
                onAskAssistant()
            },
        )
    }
}

@Composable
private fun PlannerContent(
    plan: WeekPlan,
    selectedDay: Weekday,
    recommendations: List<PlannerRecommendation>,
    onSelectDay: (Weekday) -> Unit,
    onTapSession: (PlannerSession) -> Unit,
    onApplyRecommendation: (String) -> Unit,
    onIgnoreRecommendation: (String) -> Unit,
) {
    val colors = EduTheme.colors
    val reducedMotion = LocalReducedMotion.current
    val daySessions = plan.sessions.filter { it.day == selectedDay }.sortedBy { it.startTime }
    val currentId = daySessions.firstOrNull { it.status == SessionStatus.Upcoming }?.id
    val recommendation = recommendations.firstOrNull()

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            HubWeekMini(
                labels = Weekday.entries.map { it.compactLabel() },
                fills = Weekday.entries.map { day ->
                    val sessions = plan.sessions.filter { it.day == day }
                    if (sessions.isEmpty()) 0.12f
                    else sessions.count { it.status == SessionStatus.Completed }.toFloat() / sessions.size.toFloat()
                },
                selectedIndex = selectedDay.ordinal,
                todayIndex = plan.today.ordinal,
                onSelect = { onSelectDay(Weekday.entries[it]) },
            )
        }
        item {
            AnimatedVisibility(
                visible = true,
                enter = if (reducedMotion) fadeIn() else fadeIn() + slideInVertically { it / 8 },
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.st01_today_title),
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                    )
                    if (daySessions.isEmpty()) {
                        MessageState(
                            icon = Icons.Filled.CalendarToday,
                            title = stringResource(R.string.st10_empty_day_title),
                            body = stringResource(R.string.st10_empty_day_body),
                            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
                        )
                    } else {
                        HubTimeline(modifier = Modifier.padding(top = Spacing.sm)) {
                            daySessions.forEach { session ->
                                val state = when (session.status) {
                                    SessionStatus.Completed -> HubTimelineState.Done
                                    SessionStatus.Missed -> HubTimelineState.Missed
                                    SessionStatus.Upcoming -> if (session.id == currentId) HubTimelineState.Current else HubTimelineState.Upcoming
                                }
                                HubTimelineRow(
                                    state = state,
                                    emphasized = session.id == currentId,
                                    modifier = Modifier,
                                ) {
                                    Column(
                                        modifier = Modifier.eduClickable(onClickLabel = session.title, onClick = { onTapSession(session) }),
                                    ) {
                                        Text(session.startTime, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold), color = colors.textTertiary)
                                        Text(session.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        if (recommendation != null) {
            item {
                EduCard(borderColor = colors.aiAccent.copy(alpha = 0.35f)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.icon))
                        Text(
                            text = stringResource(R.string.st10_suggests),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.aiAccent,
                        )
                    }
                    Text(
                        text = if (recommendation.reason.isBlank()) {
                            recommendation.text
                        } else {
                            "${recommendation.text} ${recommendation.reason}"
                        },
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                        PrimaryButton(
                            text = stringResource(R.string.st10_apply),
                            onClick = { onApplyRecommendation(recommendation.id) },
                            modifier = Modifier.weight(1f),
                        )
                        GhostButton(
                            text = stringResource(R.string.st10_ignore),
                            onClick = { onIgnoreRecommendation(recommendation.id) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Weekday.compactLabel(): String = stringResource(
    when (this) {
        Weekday.Sunday -> R.string.so04_weekday_sun
        Weekday.Monday -> R.string.so04_weekday_mon
        Weekday.Tuesday -> R.string.so04_weekday_tue
        Weekday.Wednesday -> R.string.so04_weekday_wed
        Weekday.Thursday -> R.string.so04_weekday_thu
        Weekday.Friday -> R.string.so04_weekday_fri
        Weekday.Saturday -> R.string.so04_weekday_sat
    }
)

@Composable
fun Weekday.fullLabel(): String = stringResource(
    when (this) {
        Weekday.Sunday -> R.string.st10_day_sunday
        Weekday.Monday -> R.string.st10_day_monday
        Weekday.Tuesday -> R.string.st10_day_tuesday
        Weekday.Wednesday -> R.string.st10_day_wednesday
        Weekday.Thursday -> R.string.st10_day_thursday
        Weekday.Friday -> R.string.st10_day_friday
        Weekday.Saturday -> R.string.st10_day_saturday
    }
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SessionDetailSheet(session: PlannerSession, onDismiss: () -> Unit, onAskAssistant: () -> Unit) {
    val colors = EduTheme.colors
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                Text(text = session.subjectTitle, style = EduTheme.typography.caption, color = colors.textSecondary, modifier = Modifier.weight(1f))
                StatusPill(
                    label = stringResource(session.status.labelRes()),
                    contentColor = statusContentColor(session.status),
                    containerColor = statusContainerColor(session.status),
                )
            }
            Text(
                text = session.title,
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
            )
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
                Icon(Icons.Filled.CalendarToday, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
                Text(text = session.day.fullLabel(), style = EduTheme.typography.body, color = colors.textPrimary)
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.padding(top = Spacing.xxs),
            ) {
                Icon(Icons.Filled.Schedule, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
                Text(text = session.startTime, style = EduTheme.typography.body, color = colors.textPrimary)
                Text("·", style = EduTheme.typography.body, color = colors.textSecondary)
                Text(
                    text = pluralStringResource(R.plurals.st01_plan_duration, session.durationMinutes, session.durationMinutes),
                    style = EduTheme.typography.body,
                    color = colors.textPrimary,
                )
            }
            if (session.priorityReason != null) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier
                        .padding(top = Spacing.sm)
                        .fillMaxWidth()
                        .background(colors.aiAccentContainer, RoundedCornerShape(Radius.md))
                        .border(Sizing.hairline, colors.aiAccent, RoundedCornerShape(Radius.md))
                        .padding(Spacing.sm),
                ) {
                    Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.icon))
                    Column {
                        Text(stringResource(R.string.st10_priority_reason_label), style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold), color = colors.aiAccent)
                        Text(session.priorityReason, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
                    }
                }
            }
            PrimaryButton(
                text = stringResource(R.string.st10_ask_assistant),
                onClick = onAskAssistant,
                leadingIcon = Icons.Filled.Chat,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
            )
            GhostButton(text = stringResource(R.string.st10_close), onClick = onDismiss, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun statusContentColor(status: SessionStatus) = when (status) {
    SessionStatus.Completed -> EduTheme.colors.success
    SessionStatus.Missed -> EduTheme.colors.danger
    SessionStatus.Upcoming -> EduTheme.colors.textSecondary
}

@Composable
private fun statusContainerColor(status: SessionStatus) = when (status) {
    SessionStatus.Completed -> EduTheme.colors.success.copy(alpha = 0.12f)
    SessionStatus.Missed -> EduTheme.colors.danger.copy(alpha = 0.12f)
    SessionStatus.Upcoming -> EduTheme.colors.neutralAlpha100
}

private fun SessionStatus.labelRes(): Int = when (this) {
    SessionStatus.Upcoming -> R.string.st10_status_upcoming
    SessionStatus.Completed -> R.string.st10_status_completed
    SessionStatus.Missed -> R.string.st10_status_missed
}

@Composable
private fun PlannerSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(3) { SkeletonListItem() }
    }
}
