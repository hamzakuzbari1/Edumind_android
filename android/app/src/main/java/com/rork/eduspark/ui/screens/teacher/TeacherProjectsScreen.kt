package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.RateReview
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.TeacherProject
import com.rork.eduspark.data.model.TeacherProjectStatus
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-17 · Project Authoring — Teacher Projects tab root.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Same "group by course, Add lives per course section" shape TC-10's [TeacherQuizListScreen]
 * already established for quizzes — reused verbatim, not reinvented, right down to only
 * showing a course section once it has at least one project (the exact same scope TC-10 itself
 * accepts).
 */
@Composable
fun TeacherProjectsScreen(
    onOpenEditor: (projectId: String) -> Unit,
    onOpenReviewQueue: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherProjectsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherProjectsEvent.OpenEditor -> onOpenEditor(event.projectId)
                TeacherProjectsEvent.OpenReviewQueue -> onOpenReviewQueue()
            }
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherProjectsSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { projects ->
        TeacherProjectsContent(
            projects = projects,
            onCreateProject = viewModel::createProject,
            onOpenProject = viewModel::onProjectTapped,
            onOpenReviewQueue = viewModel::onReviewQueueTapped,
        )
    }
}

@Composable
private fun TeacherProjectsContent(
    projects: List<TeacherProject>,
    onCreateProject: (String) -> Unit,
    onOpenProject: (String) -> Unit,
    onOpenReviewQueue: () -> Unit,
) {
    val colors = EduTheme.colors
    val grouped = projects.groupBy { it.courseId to it.courseTitle }.toSortedMap(compareBy { it.first })

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(onClick = onOpenReviewQueue, modifier = Modifier.padding(bottom = Spacing.sm)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    Icon(Icons.Filled.RateReview, contentDescription = null, tint = colors.zaytoun)
                    Text(
                        text = stringResource(R.string.tc17_review_queue_entry),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }

        if (projects.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Add,
                    title = stringResource(R.string.tc17_empty_title),
                    body = stringResource(R.string.tc17_empty_body),
                    modifier = Modifier.fillMaxSize(),
                )
            }
        } else {
            grouped.forEach { (course, courseProjects) ->
                val (courseId, courseTitle) = course
                item {
                    SectionHeader(title = courseTitle)
                }
                items(courseProjects, key = { it.id }) { project ->
                    ProjectRow(project = project, onClick = { onOpenProject(project.id) })
                }
                item {
                    GhostButton(
                        text = stringResource(R.string.tc17_add_project),
                        onClick = { onCreateProject(courseId) },
                        leadingIcon = Icons.Filled.Add,
                        modifier = Modifier.padding(bottom = Spacing.section),
                    )
                }
            }
        }
    }
}

@Composable
private fun ProjectRow(project: TeacherProject, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val statusColor = if (project.status == TeacherProjectStatus.Published) colors.success else colors.textMuted

    EduCard(onClick = onClick, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(
                text = project.title.ifBlank { stringResource(R.string.tc17_untitled_project) },
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            StatusPill(label = teacherProjectStatusLabel(project.status), contentColor = statusColor, containerColor = statusColor.copy(alpha = 0.14f))
        }
        Text(
            text = stringResource(R.string.tc17_team_size, numeral(project.teamSize)),
            style = EduTheme.typography.caption, color = colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun TeacherProjectsSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
