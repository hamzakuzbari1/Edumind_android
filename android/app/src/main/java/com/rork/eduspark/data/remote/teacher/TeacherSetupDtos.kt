package com.rork.eduspark.data.remote.teacher

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class TeacherSetupStatusDto(
    @SerialName("setup_complete") val setupComplete: Boolean,
    @SerialName("full_name") val fullName: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("image_url") val imageUrl: String? = null,
    @SerialName("avatar_url") val avatarUrl: String? = null,
    val bio: String? = null,
    @SerialName("subject_ids") val subjectIds: List<Int> = emptyList(),
    val grades: List<Int> = emptyList(),
)

@Serializable
internal data class TeacherProfileUpdateDto(
    @SerialName("full_name") val fullName: String,
    val bio: String? = null,
)

@Serializable
internal data class TeacherTeachingUpdateDto(
    @SerialName("subject_ids") val subjectIds: List<Int>,
    val grades: List<Int>,
)

@Serializable
internal data class TeacherSubjectDto(
    val id: Int,
    @SerialName("name_ar") val nameAr: String,
    val grade: Int,
    val slug: String,
)

@Serializable
internal data class TeacherQualificationDto(
    val id: Int,
    val title: String,
    val institution: String? = null,
    val year: Int? = null,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherQualificationWriteDto(
    val title: String,
    val institution: String? = null,
    val year: Int? = null,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherTeachingExperienceDto(
    val id: Int,
    val title: String,
    val organization: String? = null,
    @SerialName("year_from") val yearFrom: Int? = null,
    @SerialName("year_to") val yearTo: Int? = null,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherTeachingExperienceWriteDto(
    val title: String,
    val organization: String? = null,
    @SerialName("year_from") val yearFrom: Int? = null,
    @SerialName("year_to") val yearTo: Int? = null,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherProfileCvDto(
    val qualifications: List<TeacherQualificationDto> = emptyList(),
    @SerialName("teaching_experiences")
    val teachingExperiences: List<TeacherTeachingExperienceDto> = emptyList(),
)

@Serializable
internal data class TeachingImpactDto(
    @SerialName("total_students_taught") val totalStudentsTaught: Int? = null,
    @SerialName("grade12_students_taught") val grade12StudentsTaught: Int? = null,
    @SerialName("students_completed_subject") val studentsCompletedSubject: Int? = null,
    @SerialName("students_excellent_grades") val studentsExcellentGrades: Int? = null,
    @SerialName("years_teaching_subject") val yearsTeachingSubject: Int? = null,
    val highlights: List<String> = emptyList(),
)

@Serializable
internal data class TeachingImpactUpdateDto(
    @SerialName("total_students_taught") val totalStudentsTaught: Int? = null,
    @SerialName("grade12_students_taught") val grade12StudentsTaught: Int? = null,
    @SerialName("students_completed_subject") val studentsCompletedSubject: Int? = null,
    @SerialName("students_excellent_grades") val studentsExcellentGrades: Int? = null,
    @SerialName("years_teaching_subject") val yearsTeachingSubject: Int? = null,
)

@Serializable
internal data class TeachingPhilosophyDto(
    @SerialName("teaching_style") val teachingStyle: String? = null,
    @SerialName("lesson_approach") val lessonApproach: String? = null,
    @SerialName("exam_preparation_strategy") val examPreparationStrategy: String? = null,
)

@Serializable
internal data class TeacherWhyStudyPointDto(
    val id: Int,
    val title: String,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherWhyStudyPointWriteDto(
    val title: String,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherPortfolioDto(
    @SerialName("teaching_impact") val teachingImpact: TeachingImpactDto,
    @SerialName("teaching_philosophy") val teachingPhilosophy: TeachingPhilosophyDto,
    @SerialName("why_study_points") val whyStudyPoints: List<TeacherWhyStudyPointDto> = emptyList(),
    @SerialName("professional_documents") val professionalDocuments: List<TeacherProfessionalDocumentDto> = emptyList(),
)

@Serializable
internal data class TeacherProfessionalDocumentDto(
    val id: Int,
    val title: String,
    @SerialName("document_type") val documentType: String = "certificate",
    @SerialName("file_url") val fileUrl: String,
    @SerialName("original_filename") val originalFilename: String? = null,
    @SerialName("mime_type") val mimeType: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class TeacherSetupCompleteDto(
    val ok: Boolean = true,
    @SerialName("next_route") val nextRoute: String = "/teacher/dashboard",
)
