package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentActionItem
import com.rork.eduspark.data.model.ParentFeatureSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentMetric
import com.rork.eduspark.data.model.ParentNotificationSnapshot
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@Composable
fun ParentHomeScreen(
    onOpenLinkStudent: () -> Unit,
    onOpenProgress: () -> Unit,
    onOpenPlanner: () -> Unit,
    onOpenAlerts: () -> Unit,
    onOpenAiInsights: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentHomeViewModel = koinViewModel(),
) {
    ParentFeatureScreen(
        title = "الرئيسية",
        icon = Icons.Filled.School,
        state = viewModel.state.collectAsStateWithLifecycle().value,
        onRetry = viewModel::retry,
        onSelectStudent = viewModel::selectStudent,
        modifier = modifier,
        emptyAction = onOpenLinkStudent,
        actions = listOf(
            ParentScreenAction("التقدم", Icons.Filled.Insights, onOpenProgress),
            ParentScreenAction("الخطة", Icons.Filled.CalendarMonth, onOpenPlanner),
            ParentScreenAction("التنبيهات", Icons.Filled.Notifications, onOpenAlerts),
            ParentScreenAction("الرؤى", Icons.Filled.AutoAwesome, onOpenAiInsights),
        ),
    )
}

@Composable
fun ParentProgressScreen(
    onOpenAttendance: () -> Unit,
    onOpenLessons: () -> Unit,
    onOpenSubjectsTeachers: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentProgressViewModel = koinViewModel(),
) {
    ParentFeatureScreen(
        title = "التقدم",
        icon = Icons.Filled.Insights,
        state = viewModel.state.collectAsStateWithLifecycle().value,
        onRetry = viewModel::retry,
        onSelectStudent = viewModel::selectStudent,
        modifier = modifier,
        actions = listOf(
            ParentScreenAction("الحضور ووقت الدراسة", Icons.Filled.Schedule, onOpenAttendance),
            ParentScreenAction("تقدم الدروس", Icons.Filled.CheckCircle, onOpenLessons),
            ParentScreenAction("المواد والمعلمين", Icons.Filled.Groups, onOpenSubjectsTeachers),
        ),
    )
}

@Composable
fun ParentReportsScreen(
    modifier: Modifier = Modifier,
    viewModel: ParentReportsViewModel = koinViewModel(),
) {
    ParentFeatureScreen(
        title = "التقارير",
        icon = Icons.Filled.Assessment,
        state = viewModel.state.collectAsStateWithLifecycle().value,
        onRetry = viewModel::retry,
        onSelectStudent = viewModel::selectStudent,
        modifier = modifier,
    )
}

@Composable
fun ParentAttendanceStudyTimeScreen(onBack: () -> Unit, viewModel: ParentAttendanceStudyTimeViewModel = koinViewModel()) {
    ParentNestedFeatureScreen("الحضور ووقت الدراسة", Icons.Filled.Schedule, onBack, viewModel)
}

@Composable
fun ParentPlannerScreen(onBack: () -> Unit, viewModel: ParentPlannerViewModel = koinViewModel()) {
    ParentNestedFeatureScreen("خطة الطالب", Icons.Filled.CalendarMonth, onBack, viewModel)
}

@Composable
fun ParentAiInsightsScreen(onBack: () -> Unit, viewModel: ParentAiInsightsViewModel = koinViewModel()) {
    ParentNestedFeatureScreen("الرؤى الذكية", Icons.Filled.AutoAwesome, onBack, viewModel)
}

@Composable
fun ParentAlertsScreen(onBack: () -> Unit, viewModel: ParentAlertsViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = "التنبيهات", icon = Icons.Filled.Notifications, onBack = onBack) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLoadingContent() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentStudentSelector(data.linkedStudents, data.selectedStudentId, viewModel::selectStudent)
            val payload = data.payload
            if (payload == null) {
                SkeletonCard()
            } else {
                ParentMetricsRow(listOf(ParentMetric("غير مقروء", payload.unreadCount.toString())))
                ParentItemsCard("آخر التنبيهات", payload.notifications)
                ParentItemsCard("تفضيلات التنبيه", payload.preferences)
            }
        }
    }
}

@Composable
fun ParentLessonProgressScreen(
    onBack: () -> Unit,
    onOpenLesson: (String) -> Unit,
    viewModel: ParentLessonProgressViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = "تقدم الدروس", icon = Icons.Filled.CheckCircle, onBack = onBack) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLoadingContent() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentStudentSelector(data.linkedStudents, data.selectedStudentId, viewModel::selectStudent)
            val payload = data.payload
            if (payload == null) {
                SkeletonCard()
            } else {
                ParentMetricsRow(
                    listOf(
                        ParentMetric("مكتمل", payload.completedLessons.toString()),
                        ParentMetric("إجمالي", payload.totalLessons.toString()),
                    ),
                )
                ParentItemsCard(
                    title = "الدروس",
                    items = payload.lessons,
                    onClick = { lesson -> onOpenLesson(lesson.id) },
                )
            }
        }
    }
}

@Composable
fun ParentLessonDetailsScreen(
    lessonId: String,
    onBack: () -> Unit,
    viewModel: ParentLessonDetailsViewModel = koinViewModel(parameters = { parametersOf(lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = "تفاصيل الدرس", icon = Icons.Filled.CheckCircle, onBack = onBack) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLoadingContent() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            val details: ParentLessonDetails? = data.payload
            if (details == null) {
                SkeletonCard()
            } else {
                ParentHeroCard(title = details.title, subtitle = details.subtitle, icon = Icons.Filled.CheckCircle)
                ParentMetricsRow(details.metrics)
                ParentItemsCard("خط النشاط", details.timeline)
            }
        }
    }
}

@Composable
fun ParentSubjectsTeachersScreen(onBack: () -> Unit, onOpenMessages: () -> Unit, viewModel: ParentSubjectsTeachersViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = "المواد والمعلمين", icon = Icons.Filled.Groups, onBack = onBack) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLoadingContent() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentStudentSelector(data.linkedStudents, data.selectedStudentId, viewModel::selectStudent)
            val payload: ParentSubjectsTeachersSnapshot? = data.payload
            ParentItemsCard(
                title = "المواد والمعلمين",
                items = payload?.items.orEmpty(),
                onClick = { onOpenMessages() },
            )
        }
    }
}

@Composable
fun ParentLinkStudentScreen(onBack: () -> Unit, viewModel: ParentLinkStudentViewModel = koinViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = "ربط طالب", icon = Icons.Filled.Link, onBack = onBack) {
        EduCard {
            Text("أدخل رمز الربط الذي يظهر في حساب الطالب.", style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
            OutlinedTextField(
                value = state.code,
                onValueChange = viewModel::updateCode,
                label = { Text("رمز الربط") },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
            Button(
                onClick = viewModel::submit,
                enabled = !state.isSubmitting,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(Sizing.icon), strokeWidth = Sizing.hairline)
                } else {
                    Text("ربط الطالب")
                }
            }
            state.message?.let {
                Text(
                    it,
                    style = EduTheme.typography.caption,
                    color = if (state.isError) EduTheme.colors.danger else EduTheme.colors.primary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLoadingContent() },
        ) { students ->
            ParentItemsCard(
                title = "الطلاب المرتبطون",
                items = students.map { ParentActionItem(it.id, it.name, it.gradeLabel, status = it.academicStatusLabel) },
            )
        }
    }
}

@Composable
fun ParentMeScreen(
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentMeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            ParentHeroCard(
                title = state.user?.displayName ?: "حساب ولي الأمر",
                subtitle = state.user?.email.orEmpty(),
                icon = Icons.Filled.AccountCircle,
            )
        }
        item {
            ParentItemsCard(
                title = "الأطفال المرتبطون",
                items = state.students.map { ParentActionItem(it.id, it.name, it.gradeLabel, status = it.academicStatusLabel) },
            )
        }
        item {
            ParentNavigationCard(
                title = "ربط طالب جديد",
                subtitle = "استخدم رمز الطالب لإضافته إلى حسابك",
                icon = Icons.Filled.Link,
                onClick = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentNestedFeatureScreen(
    title: String,
    icon: ImageVector,
    onBack: () -> Unit,
    viewModel: ParentScopedViewModel<ParentFeatureSnapshot>,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ParentScaffold(title = title, icon = icon, onBack = onBack) {
        ParentFeatureScreenBody(
            state = state,
            onRetry = viewModel::retry,
            onSelectStudent = viewModel::selectStudent,
            icon = icon,
        )
    }
}

@Composable
private fun ParentFeatureScreen(
    title: String,
    icon: ImageVector,
    state: ParentRemoteUiState<ParentFeatureSnapshot>,
    onRetry: () -> Unit,
    onSelectStudent: (String) -> Unit,
    modifier: Modifier = Modifier,
    emptyAction: (() -> Unit)? = null,
    actions: List<ParentScreenAction> = emptyList(),
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            ParentFeatureScreenBody(
                state = state,
                onRetry = onRetry,
                onSelectStudent = onSelectStudent,
                icon = icon,
                titleOverride = title,
                emptyAction = emptyAction,
                actions = actions,
            )
        }
    }
}

@Composable
private fun ParentFeatureScreenBody(
    state: ParentRemoteUiState<ParentFeatureSnapshot>,
    onRetry: () -> Unit,
    onSelectStudent: (String) -> Unit,
    icon: ImageVector,
    titleOverride: String? = null,
    emptyAction: (() -> Unit)? = null,
    actions: List<ParentScreenAction> = emptyList(),
) {
    ScreenStateHost(
        state = state.result,
        onRetry = onRetry,
        isOffline = !state.isOnline,
        loading = { ParentLoadingContent() },
        modifier = Modifier.fillMaxWidth(),
    ) { data ->
        if (data.linkedStudents.isEmpty()) {
            ParentEmptyLinkedStudentCard(emptyAction)
            return@ScreenStateHost
        }
        ParentStudentSelector(data.linkedStudents, data.selectedStudentId, onSelectStudent)
        val payload = data.payload
        if (payload == null) {
            ParentLoadingContent()
        } else {
            ParentHeroCard(title = titleOverride ?: payload.title, subtitle = payload.subtitle, icon = icon)
            ParentMetricsRow(payload.metrics)
            if (actions.isNotEmpty()) ParentActionGrid(actions)
            ParentItemsCard(title = "آخر التفاصيل", items = payload.items)
        }
    }
}

@Composable
private fun ParentScaffold(
    title: String,
    icon: ImageVector,
    onBack: () -> Unit,
    content: @Composable () -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                }
                ParentIconBadge(icon = icon)
                Text(title, style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                content()
            }
        }
    }
}

@Composable
private fun ParentStudentSelector(
    students: List<ParentLinkedStudent>,
    selectedStudentId: String?,
    onSelectStudent: (String) -> Unit,
) {
    EduCard {
        val selected = students.firstOrNull { it.id == selectedStudentId } ?: students.firstOrNull()
        if (selected != null) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                ParentAvatar(name = selected.name)
                Column(modifier = Modifier.weight(1f)) {
                    Text(selected.name, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
                    Text(selected.gradeLabel.ifBlank { selected.email }, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                }
                StatusPill(label = selected.academicStatusLabel.ifBlank { "مرتبط" })
            }
        }
        if (students.size > 1) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                items(students, key = { it.id }) { student ->
                    EduChip(
                        label = student.name,
                        selected = student.id == selectedStudentId,
                        onClick = { onSelectStudent(student.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ParentHeroCard(title: String, subtitle: String, icon: ImageVector) {
    EduCard(containerColor = EduTheme.colors.primary, borderColor = EduTheme.colors.primary) {
        ParentIconBadge(icon = icon, containerColor = EduTheme.colors.onPrimary.copy(alpha = 0.14f), contentColor = EduTheme.colors.onPrimary)
        Text(
            text = title,
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.onPrimary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        if (subtitle.isNotBlank()) {
            Text(
                text = subtitle,
                style = EduTheme.typography.body,
                color = EduTheme.colors.onPrimary.copy(alpha = 0.84f),
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun ParentMetricsRow(metrics: List<ParentMetric>) {
    if (metrics.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        metrics.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                row.forEach { metric ->
                    EduCard(modifier = Modifier.weight(1f)) {
                        Text(metric.value, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.primary)
                        Text(metric.label, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = EduTheme.colors.textPrimary)
                        if (metric.supporting.isNotBlank()) {
                            Text(metric.supporting, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                        }
                    }
                }
                if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ParentActionGrid(actions: List<ParentScreenAction>) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        actions.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                row.forEach { action ->
                    ParentNavigationCard(
                        title = action.title,
                        subtitle = "فتح",
                        icon = action.icon,
                        onClick = action.onClick,
                        modifier = Modifier.weight(1f),
                    )
                }
                if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ParentNavigationCard(
    title: String,
    subtitle: String,
    icon: ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    EduCard(modifier = modifier, onClick = onClick) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            ParentIconBadge(icon = icon)
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
                Text(subtitle, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = EduTheme.colors.textSecondary)
        }
    }
}

@Composable
private fun ParentItemsCard(
    title: String,
    items: List<ParentActionItem>,
    onClick: ((ParentActionItem) -> Unit)? = null,
) {
    EduCard {
        Text(title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
        if (items.isEmpty()) {
            Text("لا توجد بيانات حالياً.", style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
        } else {
            items.forEachIndexed { index, item ->
                ListRow(
                    title = item.title,
                    supporting = listOf(item.subtitle, item.status).filter { it.isNotBlank() }.joinToString(" · "),
                    leading = Icons.Filled.School,
                    leadingTint = EduTheme.colors.primary,
                    showChevron = onClick != null,
                    trailingContent = {
                        if (item.value.isNotBlank()) {
                            StatusPill(label = item.value)
                        }
                    },
                    onClick = onClick?.let { click -> { click(item) } },
                )
                if (index != items.lastIndex) EduDivider()
            }
        }
    }
}

@Composable
private fun ParentEmptyLinkedStudentCard(onOpenLinkStudent: (() -> Unit)?) {
    EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.24f)) {
        ParentIconBadge(icon = Icons.Filled.Link)
        Text("لا يوجد طالب مرتبط", style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
        Text("اربط حساب الطالب أولاً حتى تظهر المتابعة الحقيقية.", style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        if (onOpenLinkStudent != null) {
            Button(onClick = onOpenLinkStudent, modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm)) {
                Text("ربط طالب")
            }
        }
    }
}

@Composable
private fun ParentLoadingContent() {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
        SkeletonCard()
        SkeletonCard()
    }
}

@Composable
private fun ParentAvatar(name: String) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(Sizing.avatar)
            .background(EduTheme.colors.primaryContainer, CircleShape),
    ) {
        Text(
            text = name.take(1).ifBlank { "و" },
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.primary,
        )
    }
}

@Composable
private fun ParentIconBadge(
    icon: ImageVector,
    containerColor: Color = EduTheme.colors.primaryContainer,
    contentColor: Color = EduTheme.colors.primary,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(Sizing.touchTarget)
            .background(containerColor, androidx.compose.foundation.shape.RoundedCornerShape(Radius.pill)),
    ) {
        Icon(icon, contentDescription = null, tint = contentColor, modifier = Modifier.size(Sizing.icon))
    }
}

private data class ParentScreenAction(
    val title: String,
    val icon: ImageVector,
    val onClick: () -> Unit,
)
