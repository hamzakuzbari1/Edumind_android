package com.rork.eduspark.data.remote.routine

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class RoutineOnboardingRequestDto(
    @SerialName("grade_level") val gradeLevel: String,
    @SerialName("school_start") val schoolStart: String,
    @SerialName("school_end") val schoolEnd: String,
    @SerialName("wake_time") val wakeTime: String,
    @SerialName("sleep_time") val sleepTime: String,
    @SerialName("school_days") val schoolDays: List<Int>,
    val activities: RoutineActivitiesDto = RoutineActivitiesDto(),
    @SerialName("weak_subjects") val weakSubjects: List<String> = emptyList(),
)

@Serializable
internal data class RoutineActivitiesDto(
    val selected: List<String> = emptyList(),
    val details: Map<String, RoutineActivityDetailDto> = emptyMap(),
)

@Serializable
internal data class RoutineActivityDetailDto(
    val days: List<Int> = emptyList(),
    val start: String? = null,
    val end: String? = null,
)

@Serializable
internal data class RoutineOnboardingResponseDto(
    val ok: Boolean = false,
    val next: String? = null,
    @SerialName("initial_message") val initialMessage: String? = null,
)

@Serializable
internal data class RoutineProfileDto(
    @SerialName("grade_level") val gradeLevel: String = "",
    @SerialName("school_start") val schoolStart: String = "07:30",
    @SerialName("school_end") val schoolEnd: String = "13:00",
    @SerialName("wake_time") val wakeTime: String = "06:30",
    @SerialName("sleep_time") val sleepTime: String = "22:00",
    @SerialName("school_days") val schoolDays: List<Int> = listOf(0, 1, 2, 3, 4),
    val activities: RoutineActivitiesDto = RoutineActivitiesDto(),
    @SerialName("onboarding_complete") val onboardingComplete: Boolean = false,
    @SerialName("has_schedule") val hasSchedule: Boolean = false,
    @SerialName("chat_stage") val chatStage: String? = null,
)

@Serializable
internal data class RoutineChatRequestDto(
    val message: String,
)

@Serializable
internal data class RoutineChatResponseDto(
    val reply: String = "",
    val schedule: Map<String, List<RoutineSlotDto>>? = null,
    val stage: String? = null,
    val suggestions: List<RoutineSuggestionDto> = emptyList(),
    @SerialName("summary_data") val summaryData: Map<String, String>? = null,
    @SerialName("ready_to_confirm") val readyToConfirm: Boolean = false,
)

@Serializable
internal data class RoutineReviewResponseDto(
    val ok: Boolean = false,
    val text: String = "",
    val suggestions: List<RoutineSuggestionDto> = emptyList(),
)

@Serializable
internal data class RoutineConfirmRequestDto(
    val days: Map<String, List<RoutineSlotDto>>,
)

@Serializable
internal data class RoutineConfirmResponseDto(
    val ok: Boolean = false,
    @SerialName("slots_saved") val slotsSaved: Int = 0,
)

@Serializable
internal data class RoutineWeekResponseDto(
    val days: Map<String, List<RoutineSlotDto>> = emptyMap(),
    @SerialName("onboarding_complete") val onboardingComplete: Boolean = false,
    @SerialName("grade_level") val gradeLevel: String = "",
)

@Serializable
internal data class RoutineRegenerateResponseDto(
    val ok: Boolean = false,
    val regenerated: Boolean = false,
    val renewed: Boolean = false,
    @SerialName("slots_saved") val slotsSaved: Int = 0,
    val days: Map<String, List<RoutineSlotDto>> = emptyMap(),
    val reply: String? = null,
)

@Serializable
internal data class RoutineSlotStatusResponseDto(
    val ok: Boolean = false,
    val status: String = "",
)

@Serializable
internal data class RoutineOkResponseDto(
    val ok: Boolean = false,
)

@Serializable
internal data class RoutineSlotDto(
    val id: Int? = null,
    val start: String,
    val end: String? = null,
    val type: String = "other",
    val title: String,
    val subject: String? = null,
    val fixed: Boolean = false,
    val status: String = "planned",
)

@Serializable
internal data class RoutineSuggestionDto(
    val id: String? = null,
    val title: String? = null,
    val text: String? = null,
    val description: String? = null,
    val priority: String? = null,
    @SerialName("priority_tier") val priorityTier: String? = null,
)
