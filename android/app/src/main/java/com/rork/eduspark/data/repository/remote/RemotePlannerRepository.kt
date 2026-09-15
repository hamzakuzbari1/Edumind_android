package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ExamEntry
import com.rork.eduspark.data.model.ExamSchedule
import com.rork.eduspark.data.model.OcrConfidence
import com.rork.eduspark.data.model.PlannerChatMessage
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.PlannerPriority
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.PlannerSession
import com.rork.eduspark.data.model.SessionStatus
import com.rork.eduspark.data.model.SimpleDate
import com.rork.eduspark.data.model.WeekPlan
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.planner.PlannerChatRequestDto
import com.rork.eduspark.data.remote.planner.PlannerChatResponseDto
import com.rork.eduspark.data.remote.planner.PlannerCompleteSessionRequestDto
import com.rork.eduspark.data.remote.planner.PlannerLifeEventDto
import com.rork.eduspark.data.remote.planner.PlannerRecommendationDto
import com.rork.eduspark.data.remote.planner.PlannerScheduleSlotDto
import com.rork.eduspark.data.remote.planner.PlannerStateDto
import com.rork.eduspark.data.remote.planner.StudentPlannerApi
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ExamRepository
import com.rork.eduspark.data.repository.PlannerRepository
import java.util.Calendar
import java.util.GregorianCalendar
import kotlin.math.absoluteValue
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal class RemotePlannerRepository(
    private val api: StudentPlannerApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : PlannerRepository, ExamRepository {

    private val _weekPlan = MutableStateFlow<WeekPlan?>(null)
    override val weekPlan: Flow<WeekPlan?> = _weekPlan.asStateFlow()

    private val _recommendations = MutableStateFlow<List<PlannerRecommendation>>(emptyList())
    override val recommendations: Flow<List<PlannerRecommendation>> = _recommendations.asStateFlow()

    private val _examSchedule = MutableStateFlow<ExamSchedule?>(null)
    override val examSchedule: Flow<ExamSchedule?> = _examSchedule.asStateFlow()

    private val dismissedRecommendationIds = mutableSetOf<String>()

    override suspend fun loadWeekPlan(): AppResult<WeekPlan> =
        when (val response = authorizedRequest(api::planner)) {
            is ApiCallResult.Success -> AppResult.Success(acceptState(response.value))
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun regenerateWeek(): AppResult<WeekPlan> =
        when (val response = authorizedRequest(api::generate)) {
            is ApiCallResult.Success -> AppResult.Success(acceptState(response.value))
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun toggleSessionCompletion(sessionId: String): AppResult<WeekPlan> {
        val slotId = sessionId.toIntOrNull()
            ?: return AppResult.Failure(AppError.Validation(mapOf("sessionId" to "invalid_session_id")))
        val currentPlan = _weekPlan.value
        val session = currentPlan?.sessions?.firstOrNull { it.id == sessionId }
        if (session?.status == SessionStatus.Completed) {
            return AppResult.Success(currentPlan)
        }
        val response = authorizedRequest { token ->
            api.completeSession(token, PlannerCompleteSessionRequestDto(slotId))
        }
        return when (response) {
            is ApiCallResult.Success -> AppResult.Success(acceptState(response.value))
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun sendPlannerChatMessage(message: String): AppResult<PlannerChatMessage> {
        val response = authorizedRequest { token ->
            api.chat(token, PlannerChatRequestDto(message))
        }
        return when (response) {
            is ApiCallResult.Success -> {
                acceptState(response.value.toPlannerState())
                AppResult.Success(response.value.toAssistantMessage())
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun acceptProposal(proposalId: String): AppResult<WeekPlan> =
        _weekPlan.value?.let { AppResult.Success(it) } ?: AppResult.Failure(AppError.NotFound)

    override suspend fun rejectProposal(proposalId: String): AppResult<Unit> = AppResult.Success(Unit)

    override suspend fun applyRecommendation(recommendationId: String): AppResult<WeekPlan> {
        val response = authorizedRequest(api::optimize)
        return when (response) {
            is ApiCallResult.Success -> {
                dismissedRecommendationIds += recommendationId
                AppResult.Success(acceptState(response.value))
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun dismissRecommendation(recommendationId: String): AppResult<Unit> {
        dismissedRecommendationIds += recommendationId
        _recommendations.value = _recommendations.value.filterNot { it.id == recommendationId }
        return AppResult.Success(Unit)
    }

    override suspend fun captureSchedule(): AppResult<ExamSchedule> {
        val response = authorizedRequest(api::summary)
        return when (response) {
            is ApiCallResult.Success -> {
                acceptState(response.value)
                AppResult.Success(_examSchedule.value ?: ExamSchedule(emptyList()))
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun confirmSchedule(entries: List<ExamEntry>): AppResult<ExamSchedule> {
        if (entries.isEmpty()) {
            val empty = ExamSchedule(emptyList(), isConfirmed = true)
            _examSchedule.value = empty
            return AppResult.Success(empty)
        }
        val message = buildExamConfirmationMessage(entries)
        val response = authorizedRequest { token ->
            api.chat(token, PlannerChatRequestDto(message))
        }
        return when (response) {
            is ApiCallResult.Success -> {
                acceptState(response.value.toPlannerState())
                val confirmed = ExamSchedule(entries, isConfirmed = true)
                _examSchedule.value = mergeConfirmedExams(confirmed)
                AppResult.Success(_examSchedule.value ?: confirmed)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private fun acceptState(state: PlannerStateDto): WeekPlan {
        val plan = state.toWeekPlan()
        _weekPlan.value = plan
        _examSchedule.value = state.toExamSchedule()
        _recommendations.value = state.recommendations
            .mapIndexed(::toRecommendation)
            .filterNot { it.id in dismissedRecommendationIds }
        return plan
    }

    private fun mergeConfirmedExams(confirmed: ExamSchedule): ExamSchedule {
        val remoteEntries = _examSchedule.value?.entries.orEmpty()
        val merged = (remoteEntries + confirmed.entries)
            .distinctBy { "${it.subjectTitle}-${it.date?.toIsoString()}-${it.time}" }
        return ExamSchedule(merged, isConfirmed = true)
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
                else -> AppError.Domain(response.detail ?: "planner_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private fun PlannerChatResponseDto.toPlannerState() = PlannerStateDto(
    profile = profile,
    lifeEvents = lifeEvents,
    schedule = schedule,
    chatHistory = chatHistory,
    reasoning = reasoning,
    insights = insights,
    weeklyPlan = weeklyPlan,
    subjectAnalytics = subjectAnalytics,
    recommendations = recommendations,
    streak = streak,
    dashboardSnapshot = dashboardSnapshot,
    planStats = planStats,
)

private fun PlannerChatResponseDto.toAssistantMessage() = PlannerChatMessage(
    id = chatHistory.lastOrNull { it.role.equals("assistant", ignoreCase = true) }?.id?.toString()
        ?: "assistant-${reply.hashCode().absoluteValue}",
    sender = PlannerChatSender.Assistant,
    text = reply.ifBlank { "تم تحديث الخطة." },
    proposedChange = null,
)

private fun PlannerStateDto.toWeekPlan(): WeekPlan {
    val sessions = schedule
        .sortedWith(compareBy<PlannerScheduleSlotDto> { it.scheduledAt }.thenBy { it.id })
        .map(PlannerScheduleSlotDto::toSession)
    return WeekPlan(
        weekLabel = "خطة هذا الأسبوع",
        today = currentWeekday(),
        sessions = sessions,
        generatedAtLabel = if (sessions.isEmpty()) "لا توجد جلسات بعد" else "محدّثة من الخادم",
    )
}

private fun PlannerScheduleSlotDto.toSession() = PlannerSession(
    id = id.toString(),
    day = scheduledAt.toWeekday() ?: currentWeekday(),
    subjectId = subject.trim().lowercase().replace(Regex("\\s+"), "-"),
    subjectTitle = subject.ifBlank { "مادة" },
    title = taskLabel?.takeIf { it.isNotBlank() } ?: subject.ifBlank { "جلسة دراسة" },
    startTime = scheduledAt.toClockLabel(),
    durationMinutes = durationMinutes,
    status = status.toSessionStatus(),
    priorityReason = reasoning?.takeIf { it.isNotBlank() } ?: priorityLabel,
)

private fun String.toSessionStatus(): SessionStatus = when (lowercase()) {
    "completed", "done", "finished" -> SessionStatus.Completed
    "missed", "skipped", "overdue" -> SessionStatus.Missed
    else -> SessionStatus.Upcoming
}

private fun toRecommendation(
    index: Int,
    dto: PlannerRecommendationDto,
): PlannerRecommendation {
    val key = "${dto.subject.orEmpty()}-${dto.text}"
    return PlannerRecommendation(
        id = "remote-rec-$index-${key.hashCode().absoluteValue}",
        text = dto.text,
        priority = dto.priorityTier.toPlannerPriority(),
        reason = dto.priorityLabel ?: dto.subject ?: dto.priorityTier ?: "",
    )
}

private fun String?.toPlannerPriority(): PlannerPriority = when (this?.lowercase()) {
    "high", "urgent" -> PlannerPriority.High
    "low" -> PlannerPriority.Low
    else -> PlannerPriority.Medium
}

private fun PlannerStateDto.toExamSchedule(): ExamSchedule? {
    val exams = lifeEvents
        .filter { it.eventType.equals("exam", ignoreCase = true) }
        .mapIndexed(::toExamEntry)
    return if (exams.isEmpty()) null else ExamSchedule(exams, isConfirmed = true)
}

private fun toExamEntry(index: Int, event: PlannerLifeEventDto): ExamEntry {
    val title = event.subject?.takeIf { it.isNotBlank() }
        ?: event.title?.removePrefix("امتحان")?.trim()?.takeIf { it.isNotBlank() }
        ?: "امتحان"
    return ExamEntry(
        id = event.id?.toString() ?: "remote-exam-$index",
        subjectId = event.subject?.trim()?.lowercase()?.replace(Regex("\\s+"), "-"),
        subjectTitle = title,
        date = event.eventDate?.toSimpleDate(),
        time = event.startTime?.take(5),
        confidence = event.confidence.toOcrConfidence(),
    )
}

private fun Double?.toOcrConfidence(): OcrConfidence = when {
    this == null -> OcrConfidence.Medium
    this >= 0.85 -> OcrConfidence.High
    this >= 0.6 -> OcrConfidence.Medium
    else -> OcrConfidence.Low
}

private fun buildExamConfirmationMessage(entries: List<ExamEntry>): String =
    buildString {
        append("Please add these exams to my study planner: ")
        append(
            entries.joinToString("; ") { entry ->
                listOfNotNull(
                    entry.subjectTitle,
                    entry.date?.toIsoString(),
                    entry.time,
                ).joinToString(" ")
            },
        )
    }

private fun String.toClockLabel(): String {
    val timeStart = indexOf('T').takeIf { it >= 0 } ?: indexOf(' ').takeIf { it >= 0 }
    if (timeStart != null && length >= timeStart + 6) return substring(timeStart + 1, timeStart + 6)
    return takeIf { Regex("^\\d{2}:\\d{2}").containsMatchIn(it) }?.take(5) ?: "--:--"
}

private fun String.toWeekday(): Weekday? {
    val date = toSimpleDate() ?: return null
    val calendar = GregorianCalendar(date.year, date.month - 1, date.day)
    return calendar.get(Calendar.DAY_OF_WEEK).toWeekday()
}

private fun String.toSimpleDate(): SimpleDate? {
    val match = Regex("(\\d{4})-(\\d{2})-(\\d{2})").find(this) ?: return null
    val (year, month, day) = match.destructured
    return SimpleDate(
        year = year.toInt(),
        month = month.toInt(),
        day = day.toInt(),
    )
}

private fun SimpleDate.toIsoString(): String =
    "%04d-%02d-%02d".format(year, month, day)

private fun currentWeekday(): Weekday =
    Calendar.getInstance().get(Calendar.DAY_OF_WEEK).toWeekday()

private fun Int.toWeekday(): Weekday = when (this) {
    Calendar.SUNDAY -> Weekday.Sunday
    Calendar.MONDAY -> Weekday.Monday
    Calendar.TUESDAY -> Weekday.Tuesday
    Calendar.WEDNESDAY -> Weekday.Wednesday
    Calendar.THURSDAY -> Weekday.Thursday
    Calendar.FRIDAY -> Weekday.Friday
    else -> Weekday.Saturday
}
