package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-12 · Students List — PDF page 12.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Lives inside Batch 1 [com.rork.eduspark.ui.navigation.RoleShell] — no second scaffold.
 * Search still filters the one loaded roster locally. Course/grade/status chip filters stay
 * on the ViewModel but are not part of the approved primary composition.
 */
@Composable
fun TeacherStudentsScreen(
    onOpenStudentDetail: (studentId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherStudentsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherStudentsEvent.OpenStudentDetail -> onOpenStudentDetail(event.studentId)
            }
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherStudentsSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { students ->
        TeacherStudentsContent(
            students = students,
            searchQuery = state.searchQuery,
            onSearchChange = viewModel::updateSearchQuery,
            onClearSearch = viewModel::clearFilters,
            onStudentTap = viewModel::onStudentTapped,
        )
    }
}

@Composable
private fun TeacherStudentsContent(
    students: List<TeacherStudentSummary>,
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    onClearSearch: () -> Unit,
    onStudentTap: (studentId: String) -> Unit,
) {
    val filtered = students.filter { student ->
        searchQuery.isBlank() || student.displayName.contains(searchQuery, ignoreCase = true)
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SearchField(
                value = searchQuery,
                onValueChange = onSearchChange,
                placeholder = stringResource(R.string.tc12_search_hint),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.xs),
            )
        }

        if (filtered.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Groups,
                    title = stringResource(R.string.tc12_empty_title),
                    body = stringResource(R.string.tc12_empty_body),
                    primaryActionLabel = stringResource(R.string.pj01_clear_filters),
                    onPrimaryAction = onClearSearch,
                )
            }
        } else {
            items(filtered, key = { it.studentId }) { student ->
                StudentRow(student = student, onClick = { onStudentTap(student.studentId) })
            }
        }
    }
}

@Composable
private fun StudentRow(student: TeacherStudentSummary, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val statusColor = when (student.status) {
        StudentMonitoringStatus.Active -> colors.success
        StudentMonitoringStatus.NeedsAttention, StudentMonitoringStatus.Inactive -> colors.warning
    }
    val progress = student.progressPercent.coerceIn(0f, 1f)

    EduCard(
        onClick = onClick,
        contentPadding = PaddingValues(Spacing.sm),
        modifier = Modifier.padding(bottom = Spacing.xs),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarSm)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = student.displayName.trim().firstOrNull()?.toString().orEmpty(),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = student.displayName,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(
                        R.string.tc12_row_meta,
                        teacherGradeShortLabel(student.grade),
                        student.lastActiveLabel,
                    ),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
            StatusPill(
                label = studentMonitoringStatusLabel(student.status),
                contentColor = statusColor,
                containerColor = statusColor.copy(alpha = 0.14f),
            )
        }
        EduLinearProgress(
            progress = progress,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
        Text(
            text = stringResource(R.string.progress_percent, (progress * 100).toInt()),
            style = EduTheme.typography.caption,
            color = colors.textMuted,
            modifier = Modifier.padding(top = 2.dp),
        )
    }
}

@Composable
private fun TeacherStudentsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
