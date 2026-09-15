package com.rork.eduspark.data.remote.onboarding

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class OnboardingStatusDto(
    val step: String,
    val grade: Int? = null,
    @SerialName("onboarding_complete") val onboardingComplete: Boolean = false,
    @SerialName("needs_payment") val needsPayment: Boolean = false,
    @SerialName("payment_complete") val paymentComplete: Boolean = false,
    @SerialName("selected_subject_ids") val selectedSubjectIds: List<Int> = emptyList(),
    @SerialName("teacher_choices") val teacherChoices: List<TeacherChoiceDto> = emptyList(),
)

@Serializable
internal data class GradeUpdateDto(val grade: Int)

@Serializable
internal data class SubjectsUpdateDto(
    @SerialName("subject_ids") val subjectIds: List<Int>,
)

@Serializable
internal data class TeacherChoiceDto(
    @SerialName("subject_id") val subjectId: Int,
    @SerialName("teacher_profile_id") val teacherProfileId: Int,
)

@Serializable
internal data class TeachersUpdateDto(val choices: List<TeacherChoiceDto>)

@Serializable
internal data class SubjectDto(
    val id: Int,
    @SerialName("name_ar") val nameAr: String,
    val slug: String,
    val grade: Int,
)

@Serializable
internal data class TeacherDto(
    val id: Int,
    @SerialName("full_name") val fullName: String,
    @SerialName("image_url") val imageUrl: String? = null,
    val bio: String? = null,
    val rating: Float,
    @SerialName("student_count") val studentCount: Int,
    @SerialName("subject_id") val subjectId: Int,
    @SerialName("subject_name") val subjectName: String,
)

@Serializable
internal data class CoursePreviewDto(
    val id: Int,
    val title: String,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("teacher_name") val teacherName: String,
    @SerialName("teacher_image_url") val teacherImageUrl: String? = null,
    val summary: String = "",
    val grade: Int,
    val price: Float,
    val currency: String,
)

@Serializable
internal data class OnboardingCompleteDto(
    val ok: Boolean = true,
    @SerialName("next_route") val nextRoute: String = "/student/payment",
    @SerialName("checkout_preview") val checkoutPreview: List<CoursePreviewDto> = emptyList(),
)
