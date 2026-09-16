package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-06 · Quiz Runner / ST-07 · Quiz Results / ST-08 · Remedial Quiz / ST-09 · Manual Quiz Runner.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit's domain sketch models two genuinely separate backend concepts —
 * `QuizQuestion` hanging off a `Lesson` (the AI-generated comprehension check) and
 * `CourseQuiz` (teacher-authored, course-level, "separate from lesson quiz"). [QuizOrigin]
 * mirrors that split on the client rather than inventing one shared shape: it is what
 * [com.rork.eduspark.ui.components.ai.AiMessageBubble]-style jouri marking and ST-09's
 * teacher-attribution header both key off.
 *
 * One shell (`QuizRunnerScreen`) serves ST-06, ST-08 and ST-09 — [Quiz.origin] and
 * [Quiz.isRemedial] are the only two switches it branches on; there is no second engine.
 */

/** The four interaction types the runner supports — no others are modelled this slice. */
enum class QuestionType { MultipleChoice, TrueFalse, GapFill, ShortAnswer }

/** Whether a quiz reveals correctness per-question or only at the end. Fixture-driven — never hardcoded per screen. */
enum class FeedbackMode { Immediate, Deferred }

/** Which backend concept a quiz's questions came from — drives Jouri marking and attribution copy. */
enum class QuizOrigin { AiLesson, TeacherManual }

/** One selectable choice — multiple-choice and true/false only. */
data class QuizOption(
    val id: String,
    val text: String,
)

data class QuizQuestion(
    val id: String,
    val type: QuestionType,
    val prompt: String,
    /** Multiple-choice / true-false only; empty for the two free-text types. */
    val options: List<QuizOption> = emptyList(),
    /** The correct option id (MC/T-F) or the accepted text (gap-fill/short-answer — trimmed, case-insensitive). */
    val correctAnswer: String,
    /** Shown once the question is scored. AI-authored for [QuizOrigin.AiLesson], teacher-authored otherwise. */
    val explanation: String,
    /** ST-08 only — a single progressively-revealed hint; null when a question has none. */
    val hint: String? = null,
)

data class Quiz(
    val id: String,
    val origin: QuizOrigin,
    /** The lesson this quiz is grounded in — also where ST-08's "back to lesson" returns. */
    val lessonId: String,
    val lessonTitle: String,
    val title: String,
    val teacherName: String,
    val feedbackMode: FeedbackMode,
    val timerSeconds: Int? = null,
    val questions: List<QuizQuestion>,
    /** True only for a quiz [com.rork.eduspark.data.repository.QuizRepository.buildRemedialQuiz] produced — ST-08's calmer, no-timer, hint-bearing framing. */
    val isRemedial: Boolean = false,
)

/** One student response to one question in the current attempt. */
data class QuizAnswer(
    val questionId: String,
    val response: String,
)

/**
 * The in-progress or completed attempt. Held in-memory by the repository (not this model)
 * so "bail out and resume" survives navigating away without a persistence layer to invent.
 */
data class QuizAttempt(
    val quizId: String,
    val currentQuestionIndex: Int = 0,
    val answers: Map<String, QuizAnswer> = emptyMap(),
    val isCompleted: Boolean = false,
    /** Backend manual-quiz attempt id when remote; null for local/mock attempts. */
    val attemptId: String? = null,
)

/** ST-07 — scored client-side from [Quiz] + [QuizAttempt] for AI/mock; manual remote uses server percent/score. */
data class QuizResult(
    val quiz: Quiz,
    val attempt: QuizAttempt,
    val correctCount: Int,
    val totalCount: Int,
    val xpEarned: Int,
    /** Approved design's third result stat (QuizResults.dc.html) — mock-estimated, not a real stopwatch. */
    val timeTakenSeconds: Int = 0,
    /** Server-authoritative percent for manual quizzes; null when client-scored. */
    val scorePercent: Int? = null,
    val passed: Boolean? = null,
    val hasPendingEssay: Boolean = false,
    val earnedScore: Float? = null,
    val maxScore: Float? = null,
)

/** Teacher TC-11 analytics for one manual quiz (remote). */
data class TeacherQuizAnalytics(
    val quizId: String,
    val quizTitle: String = "",
    val enrolledStudents: Int = 0,
    val attemptedCount: Int = 0,
    val completionRate: Float = 0f,
    val averageScore: Float? = null,
    val highestScore: Float? = null,
    val lowestScore: Float? = null,
)

/** Course-level rollup of manual quiz analytics (remote). */
data class TeacherCourseQuizAnalytics(
    val courseId: String,
    val courseTitle: String = "",
    val quizCount: Int = 0,
    val enrolledStudents: Int = 0,
    val totalAttempts: Int = 0,
    val averageScore: Float? = null,
    val completionRate: Float = 0f,
    val quizzes: List<TeacherQuizAnalytics> = emptyList(),
)

/** One published student-facing manual quiz row on ST-02 (list/detail contracts). */
data class StudentCourseQuizSummary(
    val id: String,
    val courseId: String,
    val title: String,
    val questionCount: Int = 0,
    val durationMinutes: Int? = null,
    val attemptStatus: String? = null,
    val scorePercent: Int? = null,
    val isCompleted: Boolean = false,
)

/** True when [response] matches [correctAnswer] — trimmed, case-insensitive for the free-text types. */
fun String?.matchesQuizAnswer(correctAnswer: String): Boolean =
    this != null && this.trim().equals(correctAnswer.trim(), ignoreCase = true)
