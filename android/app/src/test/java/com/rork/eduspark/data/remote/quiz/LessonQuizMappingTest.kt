package com.rork.eduspark.data.remote.quiz

import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.QuestionType
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class LessonQuizMappingTest {

    @Test
    fun optionIdsAreZeroBasedIndices() {
        val q = LessonQuizQuestionDto(
            id = 7,
            question = "2+2?",
            options = listOf("3", "4", "5"),
            hint = "جمع",
        ).toDomainQuestion()
        assertEquals("7", q.id)
        assertEquals(listOf("0", "1", "2"), q.options.map { it.id })
        assertEquals("4", q.options[1].text)
        assertEquals("", q.correctAnswer)
    }

    @Test
    fun answerPackUsesOptionIndex() {
        val questions = listOf(
            QuizQuestion(
                id = "7",
                type = QuestionType.MultipleChoice,
                prompt = "?",
                options = listOf(
                    QuizOption("0", "A"),
                    QuizOption("1", "B"),
                ),
                correctAnswer = "",
                explanation = "",
            ),
        )
        val packed = mapOf(
            "7" to QuizAnswer("7", "1"),
        ).toLessonQuizAnswerIndices(questions)
        assertEquals(mapOf("7" to 1), packed)
    }

    @Test
    fun submitResultUsesServerScoreAndAnnotatesWrong() {
        val quiz = listOf(
            LessonQuizQuestionDto(1, "Q1", listOf("a", "b")),
            LessonQuizQuestionDto(2, "Q2", listOf("c", "d")),
        ).toDomainQuiz(clientQuizId = "lesson-9", lessonId = 9)
        val answers = mapOf(
            "1" to QuizAnswer("1", "0"),
            "2" to QuizAnswer("2", "0"),
        )
        val result = LessonQuizSubmitResponseDto(
            correctCount = 1,
            total = 2,
            scorePercent = 50,
            feedback = listOf(
                LessonQuizFeedbackItemDto(questionId = 1, correct = true, message = "ok"),
                LessonQuizFeedbackItemDto(questionId = 2, correct = false, hint = "راجع", message = "خطأ"),
            ),
        ).toQuizResult(quiz, answers)

        assertEquals(50, result.scorePercent)
        assertEquals(1, result.correctCount)
        assertEquals(2, result.totalCount)
        assertEquals("0", result.quiz.questions[0].correctAnswer)
        assertEquals("__other__", result.quiz.questions[1].correctAnswer)
        assertFalse(result.quiz.questions[1].correctAnswer == answers["2"]!!.response)
        assertTrue(result.quiz.questions[1].explanation.contains("خطأ") || result.quiz.questions[1].hint == "راجع")
    }

    @Test
    fun lessonQuizIdHelpers() {
        assertEquals("lesson-42", LessonQuizIds.lessonQuizId(42))
        assertEquals(42, LessonQuizIds.parseLessonId("lesson-42"))
        assertEquals(42, LessonQuizIds.parseLessonId("remedial-lesson-42"))
        assertTrue(LessonQuizIds.isAiLessonClientId("lesson-1"))
        assertTrue(LessonQuizIds.isRemedialClientId("remedial-lesson-1"))
        assertFalse(LessonQuizIds.isAiLessonClientId("manual-5"))
    }
}
