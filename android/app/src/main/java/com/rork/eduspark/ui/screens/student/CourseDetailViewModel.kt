package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.PaymentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-02 · Course Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [LearningPath.isPublished] false is rendered by the screen as its own dedicated state
 * (the anchor's "NOT PUBLISHED YET" card) — it is still [UiState.Content], not a failure or
 * an empty state, because the fetch genuinely succeeded and the course genuinely exists.
 */
data class CourseDetailUiState(
    val result: UiState<LearningPath> = UiState.Loading,
    /** Fetched only when the loaded course is published but [LearningPath.isEntitled] is
     *  false — the whole-course-locked state's price/benefits card. Null otherwise. */
    val offer: CourseOffer? = null,
    val isOnline: Boolean = true,
)

class CourseDetailViewModel(
    private val courseId: String,
    private val learningRepository: LearningRepository,
    private val paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(CourseDetailUiState())
    val state: StateFlow<CourseDetailUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        // Same hot-flow shape PlannerViewModel already collects exam schedule through — a
        // lesson completed on ST-03 lands here without the student having to leave and reopen
        // this screen. Silent (no Loading flash): [fetch] alone, never [load].
        viewModelScope.launch {
            learningRepository.completedLessonIds.collect { fetch() }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading, offer = null) }
        viewModelScope.launch { fetch() }
    }

    private suspend fun fetch() {
        when (val result = learningRepository.getPath(courseId)) {
            is AppResult.Success -> {
                val course = result.data
                val offer = if (course.isPublished && !course.isEntitled) {
                    (paymentRepository.getCourseOffer(courseId) as? AppResult.Success)?.data
                } else {
                    null
                }
                _state.update { it.copy(result = UiState.Content(course), offer = offer) }
            }
            is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
        }
    }
}
