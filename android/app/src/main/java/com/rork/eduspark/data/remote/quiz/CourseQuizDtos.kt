package com.rork.eduspark.data.remote.quiz

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
internal data class QuizQuestionCreateDto(
    @SerialName("question_type") val questionType: String,
    @SerialName("question_text") val questionText: String,
    val options: List<String>? = null,
    @SerialName("correct_answer") val correctAnswer: JsonElement? = null,
    val points: Int = 1,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

@Serializable
internal data class QuizQuestionUpdateDto(
    @SerialName("question_type") val questionType: String? = null,
    @SerialName("question_text") val questionText: String? = null,
    val options: List<String>? = null,
    @SerialName("correct_answer") val correctAnswer: JsonElement? = null,
    val points: Int? = null,
    @SerialName("sort_order") val sortOrder: Int? = null,
)

@Serializable
internal data class QuizQuestionOutDto(
    val id: Int,
    @SerialName("question_type") val questionType: String,
    @SerialName("question_text") val questionText: String,
    val options: List<String> = emptyList(),
    val points: Int = 1,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("requires_manual_grading") val requiresManualGrading: Boolean = false,
    @SerialName("correct_answer") val correctAnswer: JsonElement? = null,
)

@Serializable
internal data class QuizQuestionStudentOutDto(
    val id: Int,
    @SerialName("question_type") val questionType: String,
    @SerialName("question_text") val questionText: String,
    val options: List<String> = emptyList(),
    val points: Int = 1,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("requires_manual_grading") val requiresManualGrading: Boolean = false,
)

@Serializable
internal data class CourseQuizCreateDto(
    val title: String,
    val description: String? = null,
    @SerialName("duration_minutes") val durationMinutes: Int? = null,
    @SerialName("passing_score_percent") val passingScorePercent: Int = 60,
    @SerialName("is_published") val isPublished: Boolean = false,
    @SerialName("due_at") val dueAt: String? = null,
)

@Serializable
internal data class CourseQuizUpdateDto(
    val title: String? = null,
    val description: String? = null,
    @SerialName("duration_minutes") val durationMinutes: Int? = null,
    @SerialName("passing_score_percent") val passingScorePercent: Int? = null,
    @SerialName("is_published") val isPublished: Boolean? = null,
    @SerialName("due_at") val dueAt: String? = null,
)

@Serializable
internal data class CourseQuizOutDto(
    val id: Int,
    @SerialName("course_id") val courseId: Int,
    val title: String,
    val description: String? = null,
    @SerialName("duration_minutes") val durationMinutes: Int? = null,
    @SerialName("passing_score_percent") val passingScorePercent: Int = 60,
    @SerialName("is_published") val isPublished: Boolean = false,
    @SerialName("due_at") val dueAt: String? = null,
    @SerialName("question_count") val questionCount: Int = 0,
    @SerialName("total_points") val totalPoints: Int = 0,
    @SerialName("attempt_count") val attemptCount: Int = 0,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
internal data class CourseQuizDetailOutDto(
    val id: Int,
    @SerialName("course_id") val courseId: Int,
    val title: String,
    val description: String? = null,
    @SerialName("duration_minutes") val durationMinutes: Int? = null,
    @SerialName("passing_score_percent") val passingScorePercent: Int = 60,
    @SerialName("is_published") val isPublished: Boolean = false,
    @SerialName("due_at") val dueAt: String? = null,
    @SerialName("question_count") val questionCount: Int = 0,
    @SerialName("total_points") val totalPoints: Int = 0,
    @SerialName("attempt_count") val attemptCount: Int = 0,
    @SerialName("created_at") val createdAt: String? = null,
    val questions: List<QuizQuestionOutDto> = emptyList(),
)

@Serializable
internal data class SaveAnswerItemDto(
    @SerialName("question_id") val questionId: Int,
    val answer: JsonElement? = null,
)

@Serializable
internal data class SaveAnswersRequestDto(
    val answers: List<SaveAnswerItemDto> = emptyList(),
)

@Serializable
internal data class GradeEssayRequestDto(
    @SerialName("points_earned") val pointsEarned: Float,
    @SerialName("teacher_feedback") val teacherFeedback: String? = null,
    val publish: Boolean = true,
)

@Serializable
internal data class QuizAnswerOutDto(
    @SerialName("question_id") val questionId: Int,
    @SerialName("question_type") val questionType: String = "",
    @SerialName("question_text") val questionText: String = "",
    val answer: JsonElement? = null,
    @SerialName("points_earned") val pointsEarned: Float? = null,
    @SerialName("max_points") val maxPoints: Int = 0,
    @SerialName("is_correct") val isCorrect: Boolean? = null,
    @SerialName("teacher_feedback") val teacherFeedback: String? = null,
    @SerialName("requires_manual_grading") val requiresManualGrading: Boolean = false,
    @SerialName("pending_grading") val pendingGrading: Boolean = false,
)

@Serializable
internal data class QuizAttemptOutDto(
    val id: Int,
    @SerialName("quiz_id") val quizId: Int,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String? = null,
    val status: String = "in_progress",
    val score: Float = 0f,
    @SerialName("max_score") val maxScore: Float = 0f,
    val percent: Float? = null,
    val passed: Boolean? = null,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("graded_at") val gradedAt: String? = null,
    val answers: List<QuizAnswerOutDto> = emptyList(),
)

@Serializable
internal data class QuizAttemptSummaryOutDto(
    val id: Int,
    @SerialName("student_id") val studentId: Int,
    @SerialName("student_name") val studentName: String = "",
    val status: String = "in_progress",
    val score: Float = 0f,
    @SerialName("max_score") val maxScore: Float = 0f,
    val percent: Float? = null,
    val passed: Boolean? = null,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("pending_essay_count") val pendingEssayCount: Int = 0,
)

@Serializable
internal data class QuizResultsOutDto(
    val quiz: CourseQuizOutDto,
    val attempts: List<QuizAttemptSummaryOutDto> = emptyList(),
)

@Serializable
internal data class StudentQuizListItemDto(
    val id: Int,
    @SerialName("course_id") val courseId: Int,
    val title: String,
    val description: String? = null,
    @SerialName("duration_minutes") val durationMinutes: Int? = null,
    @SerialName("passing_score_percent") val passingScorePercent: Int = 60,
    @SerialName("due_at") val dueAt: String? = null,
    @SerialName("question_count") val questionCount: Int = 0,
    @SerialName("total_points") val totalPoints: Int = 0,
    @SerialName("attempt_status") val attemptStatus: String? = null,
    val percent: Float? = null,
    val passed: Boolean? = null,
    val score: Float? = null,
    @SerialName("max_score") val maxScore: Float? = null,
)

@Serializable
internal data class StudentQuizTakeOutDto(
    val quiz: StudentQuizListItemDto,
    val questions: List<QuizQuestionStudentOutDto> = emptyList(),
    @SerialName("attempt_id") val attemptId: Int? = null,
    /** JSON object keys are strings even when question ids are numeric. */
    val answers: Map<String, JsonElement?> = emptyMap(),
    @SerialName("time_remaining_seconds") val timeRemainingSeconds: Int? = null,
)

@Serializable
internal data class QuizAnalyticsOutDto(
    @SerialName("quiz_id") val quizId: Int,
    @SerialName("quiz_title") val quizTitle: String = "",
    @SerialName("enrolled_students") val enrolledStudents: Int = 0,
    @SerialName("attempted_count") val attemptedCount: Int = 0,
    @SerialName("completion_rate") val completionRate: Float = 0f,
    @SerialName("average_score") val averageScore: Float? = null,
    @SerialName("highest_score") val highestScore: Float? = null,
    @SerialName("lowest_score") val lowestScore: Float? = null,
    val ranking: List<JsonElement> = emptyList(),
)

@Serializable
internal data class CourseQuizAnalyticsOutDto(
    @SerialName("course_id") val courseId: Int,
    @SerialName("course_title") val courseTitle: String = "",
    @SerialName("quiz_count") val quizCount: Int = 0,
    @SerialName("enrolled_students") val enrolledStudents: Int = 0,
    @SerialName("total_attempts") val totalAttempts: Int = 0,
    @SerialName("average_score") val averageScore: Float? = null,
    @SerialName("completion_rate") val completionRate: Float = 0f,
    val quizzes: List<QuizAnalyticsOutDto> = emptyList(),
)
