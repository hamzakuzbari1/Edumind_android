package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ParentFeatureSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNotificationSnapshot
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentScopedData<T>(
    val linkedStudents: List<ParentLinkedStudent>,
    val selectedStudentId: String?,
    val payload: T?,
)

data class ParentRemoteUiState<T>(
    val result: UiState<ParentScopedData<T>> = UiState.Loading,
    val isOnline: Boolean = true,
)

abstract class ParentScopedViewModel<T>(
    protected val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {
    private val _state = MutableStateFlow(ParentRemoteUiState<T>())
    val state: StateFlow<ParentRemoteUiState<T>> = _state.asStateFlow()

    private var payloadJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students -> applyStudents(students) }
        }
        load()
    }

    fun retry() = load()

    fun selectStudent(studentId: String) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        if (data.selectedStudentId == studentId || data.linkedStudents.none { it.id == studentId }) return
        viewModelScope.launch { parentRepository.selectStudent(studentId) }
        _state.update { it.copy(result = UiState.Content(data.copy(selectedStudentId = studentId, payload = null))) }
        loadPayload(studentId)
    }

    protected abstract suspend fun requestPayload(studentId: String): AppResult<T>

    private fun load() {
        payloadJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val students = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> {
                    val selected = parentRepository.selectedStudentId.first()
                        ?.takeIf { id -> students.data.any { it.id == id } }
                        ?: students.data.firstOrNull()?.id
                    _state.update {
                        it.copy(result = UiState.Content(ParentScopedData(students.data, selected, null)))
                    }
                    selected?.let(::loadPayload)
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(students.error)) }
            }
        }
    }

    private fun applyStudents(students: List<ParentLinkedStudent>) {
        val content = state.value.result as? UiState.Content ?: return
        val data = content.data
        val selected = data.selectedStudentId
            ?.takeIf { id -> students.any { it.id == id } }
            ?: students.firstOrNull()?.id
        val keepPayload = selected != null && selected == data.selectedStudentId
        _state.update {
            it.copy(
                result = UiState.Content(
                    data.copy(
                        linkedStudents = students,
                        selectedStudentId = selected,
                        payload = if (keepPayload) data.payload else null,
                    ),
                ),
            )
        }
        if (selected != null && !keepPayload) loadPayload(selected)
    }

    private fun loadPayload(studentId: String) {
        payloadJob?.cancel()
        payloadJob = viewModelScope.launch {
            when (val result = requestPayload(studentId)) {
                is AppResult.Success -> _state.update { current ->
                    val content = current.result as? UiState.Content ?: return@update current
                    if (content.data.selectedStudentId == studentId) {
                        current.copy(result = UiState.Content(content.data.copy(payload = result.data)))
                    } else {
                        current
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }
}

class ParentHomeViewModel(
    parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getChildOverview(studentId).let {
        when (it) {
            is AppResult.Success -> AppResult.Success(
                ParentFeatureSnapshot(
                    title = it.data.child.name,
                    subtitle = it.data.child.gradeLabel.ifBlank { it.data.child.academicStatusLabel },
                    metrics = listOf(
                        com.rork.eduspark.data.model.ParentMetric("الجلسات", it.data.weeklySessions.toString(), "هذا الأسبوع"),
                        com.rork.eduspark.data.model.ParentMetric("الاختبارات", it.data.weeklyQuizzes.toString(), "هذا الأسبوع"),
                        com.rork.eduspark.data.model.ParentMetric("المعدل", "${it.data.averageScore}%", "متوسط الأداء"),
                        com.rork.eduspark.data.model.ParentMetric("الحضور", "${it.data.attendancePercentage}%", "آخر فترة"),
                    ),
                    items = it.data.recentActivity.take(5).map { activity ->
                        com.rork.eduspark.data.model.ParentActionItem(
                            id = activity.id,
                            title = activity.title,
                            subtitle = activity.description.orEmpty(),
                            status = activity.relativeTime,
                        )
                    },
                ),
            )
            is AppResult.Failure -> AppResult.Failure(it.error)
        }
    }
}

class ParentProgressViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getPerformanceSummary(studentId)
}

class ParentAttendanceStudyTimeViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getAttendanceStudyTime(studentId)
}

class ParentPlannerViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getPlannerSnapshot(studentId)
}

class ParentAiInsightsViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getInsightsSnapshot(studentId)
}

class ParentReportsViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentFeatureSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getReportsSnapshot(studentId)
}

class ParentLessonProgressViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentLessonProgressSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getLessonProgress(studentId)
}

class ParentLessonDetailsViewModel(
    private val lessonId: String,
    parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ParentScopedViewModel<ParentLessonDetails>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getLessonDetails(studentId, lessonId)
}

class ParentSubjectsTeachersViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentSubjectsTeachersSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getSubjectsTeachers(studentId)
}

class ParentAlertsViewModel(parentRepository: ParentRepository, connectivity: ConnectivityObserver) :
    ParentScopedViewModel<ParentNotificationSnapshot>(parentRepository, connectivity) {
    override suspend fun requestPayload(studentId: String) = parentRepository.getNotificationsSnapshot(studentId)
}

data class ParentLinkStudentUiState(
    val result: UiState<List<ParentLinkedStudent>> = UiState.Loading,
    val code: String = "",
    val isSubmitting: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false,
    val isOnline: Boolean = true,
)

class ParentLinkStudentViewModel(
    private val parentRepository: ParentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {
    private val _state = MutableStateFlow(ParentLinkStudentUiState())
    val state: StateFlow<ParentLinkStudentUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun updateCode(code: String) = _state.update { it.copy(code = code.uppercase(), message = null, isError = false) }
    fun retry() = load()

    fun submit() {
        val code = state.value.code.trim()
        if (code.isEmpty()) {
            _state.update { it.copy(message = "أدخل رمز الربط أولاً", isError = true) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isSubmitting = true, message = null, isError = false) }
            when (val result = parentRepository.linkStudent(code)) {
                is AppResult.Success -> {
                    _state.update { it.copy(code = "", message = "تم ربط الطالب بنجاح", isError = false) }
                    load()
                }
                is AppResult.Failure -> _state.update {
                    it.copy(isSubmitting = false, message = linkErrorMessage(result.error), isError = true)
                }
            }
        }
    }

    private fun load() {
        viewModelScope.launch {
            _state.update { it.copy(result = UiState.Loading, isSubmitting = false) }
            when (val result = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun linkErrorMessage(error: AppError): String = when (error) {
        is AppError.Domain -> error.code
        AppError.NotFound -> "رمز الربط غير صالح"
        is AppError.Validation -> "تحقق من الرمز (6 إلى 16 حرفاً) وحاول مجدداً"
        AppError.Network, AppError.Offline -> "تعذر الاتصال. حاول مجدداً"
        AppError.Server -> "تعذر الربط بسبب خطأ في الخادم. حاول مجدداً"
        AppError.SessionExpired -> "انتهت الجلسة. سجّل الدخول مجدداً"
        AppError.Forbidden -> "لا يمكن ربط هذا الرمز بهذا الحساب"
        else -> "تعذر الربط. تحقق من الرمز وحاول مجدداً"
    }
}

data class ParentMeUiState(
    val user: SessionUser? = null,
    val students: List<ParentLinkedStudent> = emptyList(),
    val error: AppError? = null,
)

class ParentMeViewModel(
    private val authRepository: AuthRepository,
    private val parentRepository: ParentRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ParentMeUiState())
    val state: StateFlow<ParentMeUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.session.collect { session -> _state.update { it.copy(user = session) } }
        }
        viewModelScope.launch {
            parentRepository.linkedStudents.collect { students ->
                _state.update { it.copy(students = students) }
            }
        }
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            when (val result = parentRepository.getLinkedStudents()) {
                is AppResult.Success -> _state.update { it.copy(students = result.data, error = null) }
                is AppResult.Failure -> _state.update { it.copy(error = result.error) }
            }
        }
    }
}
