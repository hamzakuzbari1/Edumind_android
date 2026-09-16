package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.OnboardingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * STUDENT_COURSES tab ("موادي") — teacher discovery via `GET /api/catalog/teachers`,
 * plus separately listed real published courses from the student dashboard.
 */
data class DiscoverableTeacher(
    val id: String,
    val name: String,
    val subjectId: String,
    val subjectName: String,
    val rating: Float,
    val studentCount: Int,
)

data class StudentCoursesCatalog(
    val teachers: List<DiscoverableTeacher> = emptyList(),
    val courses: List<StudentCourseSummary> = emptyList(),
)

data class StudentCoursesUiState(
    val result: UiState<StudentCoursesCatalog> = UiState.Loading,
    val isOnline: Boolean = true,
)

class StudentCoursesViewModel(
    private val learningRepository: LearningRepository,
    private val onboardingRepository: OnboardingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(StudentCoursesUiState())
    val state: StateFlow<StudentCoursesUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        if (_state.value.result !is UiState.Content) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            val coursesResult = learningRepository.getStudentCourses()
            val courses = (coursesResult as? AppResult.Success)?.data.orEmpty()
            val teachers = loadMatchingTeachers()
            when {
                coursesResult is AppResult.Failure && teachers.isEmpty() -> {
                    _state.update { it.copy(result = UiState.Failure(coursesResult.error)) }
                }
                else -> _state.update {
                    it.copy(result = UiState.Content(StudentCoursesCatalog(teachers = teachers, courses = courses)))
                }
            }
        }
    }

    private suspend fun loadMatchingTeachers(): List<DiscoverableTeacher> {
        val grade = when (val home = learningRepository.getStudentHome()) {
            is AppResult.Success -> home.data.grade
            is AppResult.Failure -> return emptyList()
        }
        val subjects = when (val listed = onboardingRepository.getSubjects(grade)) {
            is AppResult.Success -> listed.data
            is AppResult.Failure -> return emptyList()
        }
        val teachers = mutableListOf<DiscoverableTeacher>()
        val seen = mutableSetOf<String>()
        for (subject in subjects) {
            val rows = when (val listed = onboardingRepository.getTeachers(subject.id, grade)) {
                is AppResult.Success -> listed.data
                is AppResult.Failure -> continue
            }
            for (teacher in rows) {
                val key = "${teacher.id}:${subject.id}"
                if (!seen.add(key)) continue
                teachers += teacher.toDiscoverable(subject.name)
            }
        }
        return teachers
    }
}

private fun OnboardingTeacher.toDiscoverable(subjectName: String) = DiscoverableTeacher(
    id = id,
    name = name,
    subjectId = subjectId,
    subjectName = subjectName,
    rating = rating,
    studentCount = studentCount,
)
