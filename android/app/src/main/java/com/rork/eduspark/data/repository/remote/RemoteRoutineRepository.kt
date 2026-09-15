package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.CommitmentSchedule
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.PlannerPriority
import com.rork.eduspark.data.model.RoutineBuildMessage
import com.rork.eduspark.data.model.RoutineBuilderAnswers
import com.rork.eduspark.data.model.RoutineDayDraft
import com.rork.eduspark.data.model.RoutineDraft
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.RoutineSlotType
import com.rork.eduspark.data.model.RoutineSuggestion
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.routine.RoutineActivitiesDto
import com.rork.eduspark.data.remote.routine.RoutineActivityDetailDto
import com.rork.eduspark.data.remote.routine.RoutineChatRequestDto
import com.rork.eduspark.data.remote.routine.RoutineConfirmRequestDto
import com.rork.eduspark.data.remote.routine.RoutineOnboardingRequestDto
import com.rork.eduspark.data.remote.routine.RoutineReviewResponseDto
import com.rork.eduspark.data.remote.routine.RoutineSlotDto
import com.rork.eduspark.data.remote.routine.RoutineSuggestionDto
import com.rork.eduspark.data.remote.routine.RoutineWeekResponseDto
import com.rork.eduspark.data.remote.routine.StudentRoutineApi
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.RoutineRepository
import java.util.Calendar
import kotlin.math.absoluteValue
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal class RemoteRoutineRepository(
    private val api: StudentRoutineApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : RoutineRepository {

    private val _routineProfile = MutableStateFlow<RoutineProfile?>(null)
    override val routineProfile: Flow<RoutineProfile?> = _routineProfile.asStateFlow()

    private val _routineDraft = MutableStateFlow<RoutineDraft?>(null)
    override val routineDraft: Flow<RoutineDraft?> = _routineDraft.asStateFlow()

    override suspend fun loadRoutine(): AppResult<RoutineProfile> {
        val weekResponse = authorizedRequest(api::week)
        return when (weekResponse) {
            is ApiCallResult.Success -> {
                val profile = weekResponse.value.toProfile()
                if (profile.slots.isEmpty() || !weekResponse.value.onboardingComplete) {
                    AppResult.Failure(AppError.NotFound)
                } else {
                    _routineProfile.value = profile
                    AppResult.Success(profile)
                }
            }
            else -> AppResult.Failure(handleFailure(weekResponse))
        }
    }

    override suspend fun confirmRoutine(answers: RoutineBuilderAnswers): AppResult<RoutineProfile> {
        val onboarding = saveOnboarding(answers)
        if (onboarding is AppResult.Failure) return onboarding
        val days = answers.toRoutineSlots().toBackendDays()
        val confirmResponse = authorizedRequest { token ->
            api.confirm(token, RoutineConfirmRequestDto(days))
        }
        if (confirmResponse !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(confirmResponse))
        }
        return loadRoutine()
    }

    override suspend fun startRoutineAiBuild(answers: RoutineBuilderAnswers): AppResult<RoutineDraft> {
        val onboarding = saveOnboarding(answers)
        if (onboarding is AppResult.Failure) return AppResult.Failure(onboarding.error)
        val slots = answers.toRoutineSlots()
        val initialText = (onboarding as AppResult.Success).data
        val draft = RoutineDraft(
            answers = answers,
            messages = listOf(
                RoutineBuildMessage(
                    id = "routine-ai-initial",
                    sender = PlannerChatSender.Assistant,
                    text = initialText,
                ),
            ),
            dayDrafts = Weekday.entries.map { day ->
                RoutineDayDraft(
                    day = day,
                    slots = slots.filter { it.day == day }.sortedBy { it.startTime },
                    confirmed = false,
                    reasoning = "تم ترتيب اليوم حسب معلوماتك المحفوظة وسيتم تثبيته عند إنهاء الروتين.",
                )
            },
            currentDay = Weekday.Sunday,
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun confirmRoutineDraftDay(day: Weekday): AppResult<RoutineDraft> {
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val updatedDays = current.dayDrafts.map { if (it.day == day) it.copy(confirmed = true) else it }
        val nextDay = updatedDays.firstOrNull { !it.confirmed }?.day ?: day
        val draft = current.copy(
            dayDrafts = updatedDays,
            currentDay = nextDay,
            messages = current.messages + RoutineBuildMessage(
                id = "routine-ai-confirm-${day.name}",
                sender = PlannerChatSender.Assistant,
                text = if (updatedDays.all { it.confirmed }) {
                    "كل الأيام جاهزة للمراجعة النهائية."
                } else {
                    "تم تثبيت ${day.name} مؤقتاً. نراجع الآن ${nextDay.name}."
                },
            ),
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun adjustRoutineDraft(message: String): AppResult<RoutineDraft> {
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val response = authorizedRequest { token ->
            api.chat(token, RoutineChatRequestDto(message))
        }
        return when (response) {
            is ApiCallResult.Success -> {
                val scheduleSlots = response.value.schedule?.toDomainSlots()
                val draft = if (scheduleSlots.isNullOrEmpty()) {
                    current
                } else {
                    current.copy(dayDrafts = current.dayDrafts.map { dayDraft ->
                        dayDraft.copy(slots = scheduleSlots.filter { it.day == dayDraft.day })
                    })
                }.copy(
                    messages = current.messages +
                        RoutineBuildMessage("routine-user-${current.messages.size + 1}", PlannerChatSender.Student, message) +
                        RoutineBuildMessage(
                            "routine-ai-${current.messages.size + 2}",
                            PlannerChatSender.Assistant,
                            response.value.reply.ifBlank { "تم تحديث الروتين بناءً على رسالتك." },
                        ),
                )
                _routineDraft.value = draft
                AppResult.Success(draft)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun reviewRoutineDraft(): AppResult<RoutineDraft> {
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val response = authorizedRequest(api::review)
        return when (response) {
            is ApiCallResult.Success -> {
                val draft = current.copy(
                    reviewText = response.value.text.ifBlank { "راجعت الأسبوع. يمكنك تثبيته الآن." },
                    suggestions = response.value.toSuggestions(),
                )
                _routineDraft.value = draft
                AppResult.Success(draft)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun setRoutineSuggestion(
        suggestionId: String,
        accepted: Boolean?,
    ): AppResult<RoutineDraft> {
        val current = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val draft = current.copy(
            suggestions = current.suggestions.map {
                if (it.id == suggestionId) it.copy(accepted = accepted) else it
            },
        )
        _routineDraft.value = draft
        return AppResult.Success(draft)
    }

    override suspend fun finalizeRoutineDraft(): AppResult<RoutineProfile> {
        val draft = _routineDraft.value ?: return AppResult.Failure(AppError.NotFound)
        val response = authorizedRequest { token ->
            api.confirm(token, RoutineConfirmRequestDto(draft.dayDrafts.flatMap { it.slots }.toBackendDays()))
        }
        if (response !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(response))
        }
        return loadRoutine()
    }

    override suspend fun updateSlotStatus(
        slotId: String,
        status: RoutineSlotStatus,
    ): AppResult<RoutineProfile> {
        val id = slotId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Validation(mapOf("slotId" to "invalid_slot_id")))
        val response = authorizedRequest { token ->
            when (status) {
                RoutineSlotStatus.Completed -> api.completeSlot(token, id)
                RoutineSlotStatus.Missed -> api.missSlot(token, id)
                RoutineSlotStatus.Upcoming -> api.undoSlot(token, id)
            }
        }
        if (response !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(response))
        }
        return loadRoutine()
    }

    override suspend fun acknowledgeRenewal(): AppResult<RoutineProfile> {
        val current = _routineProfile.value ?: return AppResult.Failure(AppError.NotFound)
        val updated = current.copy(needsRenewal = false)
        _routineProfile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun renewRoutineWeek(): AppResult<RoutineProfile> {
        val response = authorizedRequest(api::renewWeek)
        if (response !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(response))
        }
        return loadRoutine()
    }

    override suspend fun deleteRoutine(): AppResult<Unit> =
        when (val response = authorizedRequest(api::resetProfile)) {
            is ApiCallResult.Success -> {
                _routineProfile.value = null
                _routineDraft.value = null
                AppResult.Success(Unit)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    private suspend fun saveOnboarding(answers: RoutineBuilderAnswers): AppResult<String> {
        val response = authorizedRequest { token ->
            api.saveOnboarding(token, answers.toOnboardingRequest())
        }
        return when (response) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.initialMessage ?: "تم حفظ معلومات الروتين. لنبدأ بناء الأسبوع.",
            )
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private suspend fun <T> authorizedRequest(
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = tokenStore.read() ?: return ApiCallResult.HttpFailure(401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> call(refreshed.data.accessToken)
            is AppResult.Failure -> ApiCallResult.HttpFailure(401)
        }
    }

    private suspend fun handleFailure(response: ApiCallResult<*>): AppError {
        val error = when (response) {
            ApiCallResult.NetworkFailure -> AppError.Network
            ApiCallResult.InvalidResponse -> AppError.Unknown
            is ApiCallResult.Success -> AppError.Unknown
            is ApiCallResult.HttpFailure -> when (response.statusCode) {
                401 -> AppError.SessionExpired
                403 -> AppError.Forbidden
                404, 410 -> AppError.NotFound
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "routine_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private fun RoutineBuilderAnswers.toOnboardingRequest(): RoutineOnboardingRequestDto {
    val schoolHours = schoolHoursId.toSchoolHours()
    return RoutineOnboardingRequestDto(
        gradeLevel = "baccalaureate",
        schoolStart = schoolHours.first,
        schoolEnd = schoolHours.second,
        wakeTime = wakeTime ?: "06:30",
        sleepTime = sleepTime ?: "22:00",
        schoolDays = listOf(6, 0, 1, 2, 3),
        activities = RoutineActivitiesDto(
            selected = commitmentIds.toList(),
            details = commitmentSchedules.mapValues { (_, schedule) -> schedule.toActivityDetail() },
        ),
        weakSubjects = emptyList(),
    )
}

private fun CommitmentSchedule.toActivityDetail() = RoutineActivityDetailDto(
    days = days.map(Weekday::toBackendDay),
    start = startTime,
    end = endTime,
)

private fun String?.toSchoolHours(): Pair<String, String> = when (this) {
    "early" -> "08:00" to "14:00"
    "late" -> "09:00" to "15:30"
    else -> "08:00" to "15:00"
}

private fun RoutineBuilderAnswers.toRoutineSlots(): List<RoutineSlot> {
    val schoolDays = listOf(Weekday.Sunday, Weekday.Monday, Weekday.Tuesday, Weekday.Wednesday, Weekday.Thursday)
    val schoolHours = schoolHoursId.toSchoolHours()
    val slots = mutableListOf<RoutineSlot>()
    (schoolDays + Weekday.Friday).forEach { day ->
        slots += RoutineSlot(
            id = "local-wake-${day.name}",
            day = day,
            type = RoutineSlotType.Wake,
            title = "الاستيقاظ",
            startTime = wakeTime ?: "06:30",
            status = RoutineSlotStatus.Upcoming,
        )
        if (day in schoolDays) {
            slots += RoutineSlot(
                id = "local-school-${day.name}",
                day = day,
                type = RoutineSlotType.School,
                title = "الدوام المدرسي",
                startTime = schoolHours.first,
                endTime = schoolHours.second,
                status = RoutineSlotStatus.Upcoming,
            )
        }
        slots += RoutineSlot(
            id = "local-sleep-${day.name}",
            day = day,
            type = RoutineSlotType.Sleep,
            title = "النوم",
            startTime = sleepTime ?: "22:00",
            status = RoutineSlotStatus.Upcoming,
        )
    }
    commitmentIds.forEach { id ->
        val schedule = commitmentSchedules[id] ?: CommitmentSchedule()
        val defaults = commitmentDefaults(id)
        val days = schedule.days.takeIf { it.isNotEmpty() } ?: defaults.days
        days.forEach { day ->
            slots += RoutineSlot(
                id = "local-commitment-$id-${day.name}",
                day = day,
                type = RoutineSlotType.Commitment,
                title = defaults.title,
                startTime = schedule.startTime ?: defaults.start,
                endTime = schedule.endTime ?: defaults.end,
                status = RoutineSlotStatus.Upcoming,
            )
        }
    }
    studyWindowIds.forEach { id ->
        val window = studyWindowDefaults(id, energyPattern)
        schoolDays.forEach { day ->
            slots += RoutineSlot(
                id = "local-study-$id-${day.name}",
                day = day,
                type = RoutineSlotType.StudyWindow,
                title = window.title,
                startTime = window.start,
                endTime = window.end,
                status = RoutineSlotStatus.Upcoming,
            )
        }
    }
    return slots.sortedWith(compareBy<RoutineSlot> { it.day.ordinal }.thenBy { it.startTime })
}

private data class CommitmentDefault(
    val title: String,
    val days: Set<Weekday>,
    val start: String,
    val end: String,
)

private fun commitmentDefaults(id: String): CommitmentDefault = when (id) {
    "sports" -> CommitmentDefault("تدريب رياضي", setOf(Weekday.Tuesday, Weekday.Thursday), "16:00", "17:30")
    "tutoring" -> CommitmentDefault("دروس خصوصية", setOf(Weekday.Monday), "17:00", "18:00")
    "family" -> CommitmentDefault("وقت العائلة", setOf(Weekday.Friday), "18:00", "19:30")
    else -> CommitmentDefault("التزام", setOf(Weekday.Tuesday), "16:00", "17:00")
}

private data class StudyWindowDefault(val title: String, val start: String, val end: String)

private fun studyWindowDefaults(id: String, energyPattern: StudyTimeOfDay?): StudyWindowDefault = when (id) {
    "morning" -> StudyWindowDefault("مراجعة صباحية", "06:00", "06:30")
    "evening" -> StudyWindowDefault("جلسة دراسة مسائية", "18:00", "19:00")
    "night" -> StudyWindowDefault("مراجعة هادئة", "20:00", "20:45")
    else -> when (energyPattern) {
        StudyTimeOfDay.EarlyMorning -> StudyWindowDefault("جلسة دراسة", "06:00", "06:45")
        StudyTimeOfDay.LateNight -> StudyWindowDefault("جلسة دراسة", "20:00", "20:45")
        else -> StudyWindowDefault("جلسة دراسة", "18:00", "19:00")
    }
}

private fun List<RoutineSlot>.toBackendDays(): Map<String, List<RoutineSlotDto>> =
    groupBy { it.day.toBackendDay().toString() }
        .mapValues { (_, slots) ->
            slots.sortedBy { it.startTime }.map { it.toDto() }
        }

private fun RoutineSlot.toDto() = RoutineSlotDto(
    start = startTime,
    end = endTime ?: startTime,
    type = type.toBackendType(),
    title = title,
    fixed = type == RoutineSlotType.School || type == RoutineSlotType.Wake || type == RoutineSlotType.Sleep,
    status = status.toBackendStatus(),
)

private fun RoutineSlotType.toBackendType(): String = when (this) {
    RoutineSlotType.Wake -> "wake"
    RoutineSlotType.School -> "school"
    RoutineSlotType.Commitment -> "other"
    RoutineSlotType.StudyWindow -> "study"
    RoutineSlotType.Sleep -> "sleep"
}

private fun RoutineSlotStatus.toBackendStatus(): String = when (this) {
    RoutineSlotStatus.Completed -> "completed"
    RoutineSlotStatus.Missed -> "missed"
    RoutineSlotStatus.Upcoming -> "planned"
}

private fun RoutineWeekResponseDto.toProfile(): RoutineProfile = RoutineProfile(
    weekLabel = "هذا الأسبوع",
    today = currentWeekday(),
    slots = days.toDomainSlots(),
    lastConfirmedLabel = if (onboardingComplete) "محمّل من الخادم" else "لم يتم تثبيت الروتين بعد",
    needsRenewal = false,
)

private fun Map<String, List<RoutineSlotDto>>.toDomainSlots(): List<RoutineSlot> =
    flatMap { (dayKey, slots) ->
        val day = dayKey.toIntOrNull()?.toWeekday() ?: Weekday.Sunday
        slots.map { it.toDomain(day) }
    }.sortedWith(compareBy<RoutineSlot> { it.day.ordinal }.thenBy { it.startTime })

private fun RoutineSlotDto.toDomain(day: Weekday) = RoutineSlot(
    id = id?.toString() ?: "remote-${day.name}-${title.hashCode().absoluteValue}-${start.hashCode().absoluteValue}",
    day = day,
    type = type.toSlotType(title),
    title = title,
    startTime = start.take(5),
    endTime = end?.take(5)?.takeIf { it != start.take(5) },
    status = status.toSlotStatus(),
)

private fun String.toSlotType(title: String): RoutineSlotType = when (lowercase()) {
    "wake" -> RoutineSlotType.Wake
    "school" -> RoutineSlotType.School
    "study" -> RoutineSlotType.StudyWindow
    "sleep" -> RoutineSlotType.Sleep
    else -> when {
        title.contains("استيقاظ") -> RoutineSlotType.Wake
        title.contains("نوم") -> RoutineSlotType.Sleep
        title.contains("مدرس") || title.contains("دوام") -> RoutineSlotType.School
        title.contains("دراس") || title.contains("مراجعة") -> RoutineSlotType.StudyWindow
        else -> RoutineSlotType.Commitment
    }
}

private fun String.toSlotStatus(): RoutineSlotStatus = when (lowercase()) {
    "completed", "done" -> RoutineSlotStatus.Completed
    "missed" -> RoutineSlotStatus.Missed
    else -> RoutineSlotStatus.Upcoming
}

private fun RoutineReviewResponseDto.toSuggestions(): List<RoutineSuggestion> =
    suggestions.mapIndexed { index, suggestion ->
        suggestion.toDomain(index)
    }.ifEmpty {
        listOf(
            RoutineSuggestion(
                id = "remote-review-default",
                title = "ثبّت الروتين",
                description = "الجدول جاهز ويمكن اعتماده لهذا الأسبوع.",
                priority = PlannerPriority.Medium,
            ),
        )
    }

private fun RoutineSuggestionDto.toDomain(index: Int) = RoutineSuggestion(
    id = id ?: "remote-suggestion-$index-${(title ?: text ?: description.orEmpty()).hashCode().absoluteValue}",
    title = title ?: text ?: "اقتراح",
    description = description ?: text ?: "",
    priority = (priorityTier ?: priority).toPlannerPriority(),
)

private fun String?.toPlannerPriority(): PlannerPriority = when (this?.lowercase()) {
    "high", "urgent" -> PlannerPriority.High
    "low" -> PlannerPriority.Low
    else -> PlannerPriority.Medium
}

private fun Weekday.toBackendDay(): Int = when (this) {
    Weekday.Monday -> 0
    Weekday.Tuesday -> 1
    Weekday.Wednesday -> 2
    Weekday.Thursday -> 3
    Weekday.Friday -> 4
    Weekday.Saturday -> 5
    Weekday.Sunday -> 6
}

private fun Int.toWeekday(): Weekday = when (this) {
    0 -> Weekday.Monday
    1 -> Weekday.Tuesday
    2 -> Weekday.Wednesday
    3 -> Weekday.Thursday
    4 -> Weekday.Friday
    5 -> Weekday.Saturday
    else -> Weekday.Sunday
}

private fun currentWeekday(): Weekday = when (Calendar.getInstance().get(Calendar.DAY_OF_WEEK)) {
    Calendar.SUNDAY -> Weekday.Sunday
    Calendar.MONDAY -> Weekday.Monday
    Calendar.TUESDAY -> Weekday.Tuesday
    Calendar.WEDNESDAY -> Weekday.Wednesday
    Calendar.THURSDAY -> Weekday.Thursday
    Calendar.FRIDAY -> Weekday.Friday
    else -> Weekday.Saturday
}
