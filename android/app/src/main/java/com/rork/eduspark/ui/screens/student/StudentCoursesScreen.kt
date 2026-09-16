package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun StudentCoursesScreen(
    onOpenCourse: (courseId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: StudentCoursesViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { CoursesSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { catalog ->
        CoursesContent(
            teachers = catalog.teachers,
            courses = catalog.courses,
            onOpenCourse = onOpenCourse,
            onOpenSubscriptions = onOpenSubscriptions,
        )
    }
}

@Composable
private fun CoursesContent(
    teachers: List<DiscoverableTeacher>,
    courses: List<StudentCourseSummary>,
    onOpenCourse: (String) -> Unit,
    onOpenSubscriptions: () -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (teachers.isNotEmpty()) {
            item {
                TeacherDiscoverySection(teachers = teachers)
            }
        }
        if (courses.isNotEmpty() || teachers.isEmpty()) {
            item {
                StudentCourseCatalogSection(
                    courses = courses,
                    gradeLabel = null,
                    onOpenCourse = onOpenCourse,
                    onOpenSubscriptions = onOpenSubscriptions,
                )
            }
        }
    }
}

@Composable
private fun CoursesSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        repeat(4) { SkeletonListItem() }
    }
}
