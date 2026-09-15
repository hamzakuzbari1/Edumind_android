package com.rork.eduspark.data.remote.profile

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class StudentProfileDto(
    val interests: List<String> = emptyList(),
    val hobbies: List<String> = emptyList(),
    val difficulty: String = "medium",
    val age: Int? = null,
    @SerialName("learning_style") val learningStyle: String = "theoretical",
    @SerialName("future_goal") val futureGoal: String = "undecided",
    @SerialName("preferred_explanation_style") val preferredExplanationStyle: String = "normal",
    @SerialName("personality_mode") val personalityMode: String = "friendly_teacher",
)

@Serializable
internal data class StudentProfileUpdateDto(
    val interests: List<String> = emptyList(),
    val hobbies: List<String> = emptyList(),
    val difficulty: String = "medium",
    val age: Int? = null,
    @SerialName("learning_style") val learningStyle: String = "theoretical",
    @SerialName("future_goal") val futureGoal: String = "undecided",
    @SerialName("preferred_explanation_style") val preferredExplanationStyle: String = "normal",
    @SerialName("personality_mode") val personalityMode: String = "friendly_teacher",
)

@Serializable
internal data class ParentLinkCodeDto(
    @SerialName("link_code") val linkCode: String,
)

@Serializable
internal data class LinkedParentsDto(
    val parents: List<LinkedParentDto> = emptyList(),
)

@Serializable
internal data class LinkedParentDto(
    @SerialName("parent_id") val parentId: Int,
    @SerialName("display_name") val displayName: String,
    @SerialName("relationship_label") val relationshipLabel: String,
    @SerialName("is_active") val isActive: Boolean = true,
)
