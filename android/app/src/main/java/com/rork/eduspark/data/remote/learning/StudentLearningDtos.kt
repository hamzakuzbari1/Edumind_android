package com.rork.eduspark.data.remote.learning

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class StudentDashboardDto(
    val grade: Int? = null,
    val courses: List<StudentCourseCardDto> = emptyList(),
    @SerialName("unlocked_count") val unlockedCount: Int = 0,
    @SerialName("locked_count") val lockedCount: Int = 0,
    val gamification: GamificationProfileDto? = null,
)

@Serializable
internal data class StudentCourseCardDto(
    val id: Int,
    val title: String,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("teacher_name") val teacherName: String,
    val grade: Int,
    val price: Float = 0f,
    val currency: String = "SYP",
    val unlocked: Boolean,
    @SerialName("subscription_status") val subscriptionStatus: String = "pending",
    @SerialName("access_status") val accessStatus: String? = null,
    @SerialName("access_source") val accessSource: String? = null,
    @SerialName("enrollment_status") val enrollmentStatus: String? = null,
    @SerialName("lock_reason") val lockReason: String? = null,
    @SerialName("progress_percent") val progressPercent: Int = 0,
    @SerialName("lesson_count") val lessonCount: Int = 0,
    @SerialName("completed_lesson_count") val completedLessonCount: Int = 0,
)

@Serializable
internal data class StudentCourseDetailDto(
    val id: Int,
    val title: String,
    @SerialName("subject_name") val subjectName: String,
    @SerialName("teacher_name") val teacherName: String,
    val grade: Int,
    val price: Float = 0f,
    val currency: String = "SYP",
    val unlocked: Boolean,
    @SerialName("subscription_status") val subscriptionStatus: String = "pending",
    @SerialName("access_status") val accessStatus: String? = null,
    @SerialName("access_source") val accessSource: String? = null,
    @SerialName("enrollment_status") val enrollmentStatus: String? = null,
    @SerialName("lock_reason") val lockReason: String? = null,
    @SerialName("progress_percent") val progressPercent: Int = 0,
    @SerialName("lesson_count") val lessonCount: Int = 0,
    @SerialName("completed_lesson_count") val completedLessonCount: Int = 0,
    val description: String? = null,
    val lessons: List<CourseLessonDto> = emptyList(),
    val units: List<StudentCourseUnitDto> = emptyList(),
    @SerialName("resume_lesson") val resumeLesson: StudentCourseResumeLessonDto? = null,
)

@Serializable
internal data class StudentCourseUnitDto(
    val id: Int? = null,
    val title: String,
    val description: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("lesson_count") val lessonCount: Int = 0,
    @SerialName("completed_lesson_count") val completedLessonCount: Int = 0,
    @SerialName("progress_percent") val progressPercent: Int = 0,
    val lessons: List<CourseLessonDto> = emptyList(),
)

@Serializable
internal data class StudentCourseResumeLessonDto(
    @SerialName("course_id") val courseId: Int,
    @SerialName("lesson_id") val lessonId: Int,
    @SerialName("unit_id") val unitId: Int? = null,
    @SerialName("unit_title") val unitTitle: String? = null,
    val title: String,
    @SerialName("sort_order") val sortOrder: Int = 0,
    val status: String = "pending",
    @SerialName("completion_percent") val completionPercent: Int = 0,
)

@Serializable
internal data class CourseLessonDto(
    val id: Int,
    @SerialName("unit_id") val unitId: Int? = null,
    @SerialName("unit_title") val unitTitle: String? = null,
    val title: String,
    val description: String? = null,
    @SerialName("video_url") val videoUrl: String? = null,
    @SerialName("pdf_url") val pdfUrl: String? = null,
    @SerialName("homework_url") val homeworkUrl: String? = null,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("lesson_type") val lessonType: String = "video",
    @SerialName("lesson_type_label") val lessonTypeLabel: String = "فيديو",
    val status: String? = null,
    val completed: Boolean = false,
    @SerialName("has_video") val hasVideo: Boolean = false,
    @SerialName("has_pdf") val hasPdf: Boolean = false,
    @SerialName("has_ai_chat") val hasAiChat: Boolean = false,
    @SerialName("has_generated_quiz") val hasGeneratedQuiz: Boolean = false,
    @SerialName("quiz_ready") val quizReady: Boolean = false,
    @SerialName("completion_percent") val completionPercent: Int = 0,
    @SerialName("video_progress_percent") val videoProgressPercent: Float = 0f,
    @SerialName("pdf_progress_percent") val pdfProgressPercent: Float = 0f,
)

@Serializable
internal data class GamificationProfileDto(
    val level: Int = 1,
    @SerialName("total_xp") val totalXp: Int = 0,
    @SerialName("xp_to_next_level") val xpToNextLevel: Int = 0,
    @SerialName("xp_for_level") val xpForLevel: Int = 0,
    @SerialName("progress_percent") val progressPercent: Int = 0,
    @SerialName("current_streak") val currentStreak: Int = 0,
)

@Serializable
internal data class LessonProgressUpdateDto(
    @SerialName("video_percent") val videoPercent: Float? = null,
    @SerialName("pdf_percent") val pdfPercent: Float? = null,
    @SerialName("pdf_opened") val pdfOpened: Boolean? = null,
)

@Serializable
internal data class LessonProgressDto(
    @SerialName("lesson_id") val lessonId: Int,
    @SerialName("course_id") val courseId: Int? = null,
    @SerialName("video_progress_percent") val videoProgressPercent: Float = 0f,
    @SerialName("pdf_progress_percent") val pdfProgressPercent: Float = 0f,
    @SerialName("pdf_opened") val pdfOpened: Boolean = false,
    @SerialName("is_completed") val isCompleted: Boolean = false,
    @SerialName("completion_percent") val completionPercent: Int = 0,
    @SerialName("newly_completed") val newlyCompleted: Boolean = false,
)
