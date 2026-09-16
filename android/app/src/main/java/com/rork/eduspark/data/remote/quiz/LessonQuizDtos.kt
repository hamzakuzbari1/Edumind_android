package com.rork.eduspark.data.remote.quiz

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** GET `/api/student/quiz/{lesson_id}` — no answer key. */
@Serializable
internal data class LessonQuizQuestionDto(
    val id: Int,
    val question: String,
    val options: List<String> = emptyList(),
    val hint: String? = null,
)

/** Regenerated / remedial question payloads include `correctIndex`. */
@Serializable
internal data class LessonQuizGeneratedQuestionDto(
    val id: String,
    val question: String,
    val options: List<String> = emptyList(),
    @SerialName("correctIndex") val correctIndex: Int = 0,
    val hint: String? = null,
)

@Serializable
internal data class LessonQuizRegenerateResponseDto(
    val quizQuestions: List<LessonQuizGeneratedQuestionDto> = emptyList(),
)

@Serializable
internal data class LessonQuizRemedialRequestDto(
    val answers: Map<String, Int>,
)

@Serializable
internal data class LessonQuizRemedialResponseDto(
    val questions: List<LessonQuizGeneratedQuestionDto> = emptyList(),
)

@Serializable
internal data class LessonQuizSubmitRequestDto(
    @SerialName("lesson_id") val lessonId: Int,
    val answers: Map<String, Int>,
)

@Serializable
internal data class LessonQuizFeedbackItemDto(
    val questionId: Int? = null,
    val correct: Boolean = false,
    val hint: String? = null,
    val message: String? = null,
)

@Serializable
internal data class LessonQuizSubmitResponseDto(
    @SerialName("correct_count") val correctCount: Int = 0,
    val total: Int = 0,
    val feedback: List<LessonQuizFeedbackItemDto> = emptyList(),
    @SerialName("score_percent") val scorePercent: Int = 0,
)

internal object LessonQuizIds {
    const val LESSON_PREFIX = "lesson-"
    const val REMEDIAL_PREFIX = "remedial-"

    fun lessonQuizId(lessonId: Int): String = "$LESSON_PREFIX$lessonId"

    fun remedialQuizId(lessonId: Int): String = "$REMEDIAL_PREFIX$LESSON_PREFIX$lessonId"

    fun isAiLessonClientId(quizId: String): Boolean =
        quizId.startsWith(LESSON_PREFIX) || quizId.startsWith(REMEDIAL_PREFIX)

    fun isRemedialClientId(quizId: String): Boolean = quizId.startsWith(REMEDIAL_PREFIX)

    fun parseLessonId(quizId: String): Int? {
        when {
            quizId.startsWith(REMEDIAL_PREFIX) -> {
                val rest = quizId.removePrefix(REMEDIAL_PREFIX)
                return if (rest.startsWith(LESSON_PREFIX)) {
                    rest.removePrefix(LESSON_PREFIX).substringBefore('-').toIntOrNull()
                } else {
                    rest.substringBefore('-').toIntOrNull()
                }
            }
            quizId.startsWith(LESSON_PREFIX) ->
                return quizId.removePrefix(LESSON_PREFIX).substringBefore('-').toIntOrNull()
            else -> return null
        }
    }
}
