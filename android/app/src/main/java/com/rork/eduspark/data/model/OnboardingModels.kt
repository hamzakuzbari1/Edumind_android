package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-01 … SO-05 STUDENT ONBOARDING — client domain models.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §2: "Onboarding (grade → subjects → teachers) ✅ Implemented" — a real,
 * verified backend flow. As with every other model in this package, these describe what
 * the UI needs, not a FastAPI response shape.
 */

/** Syrian secondary grades — Screen Inventory SO-01. */
enum class Grade { Grade10, Grade11, Baccalaureate }

enum class StudentOnboardingStep { Grade, Subjects, Teachers, Complete }

/** Only the Baccalaureate year forks by track (Screen Inventory SO-01). */
enum class Track { Science, Literary }

enum class SubjectGroup { Core, LanguagesAndGeneral }

data class SubjectOption(
    val id: String,
    val name: String,
    val slug: String,
    val group: SubjectGroup,
)

data class StudentOnboardingStatus(
    val step: StudentOnboardingStep,
    val grade: Grade?,
    val onboardingComplete: Boolean,
    val selectedSubjectIds: Set<String>,
    val selectedTeacherIdBySubject: Map<String, String>,
)

/**
 * SO-03. [priceLabel] is pre-formatted display text — Source Audit: pricing is
 * server-driven (PriceSlot), so the client never computes or interprets it, only shows it.
 */
data class OnboardingTeacher(
    val id: String,
    val subjectId: String,
    val name: String,
    val yearsTeaching: Int?,
    val rating: Float,
    val studentCount: Int,
    val priceLabel: String?,
    val introClipSeconds: Int?,
)

/** SO-04 Q1. */
enum class StudyHoursPerDay { ThirtyMinutes, OneHour, TwoHours, ThreePlusHours }

/** SO-04 Q5. */
enum class StudyTimeOfDay { EarlyMorning, Afternoon, Evening, LateNight }

/** A plain Gregorian date with no `java.time` dependency — minSdk 24 has no desugaring configured. */
data class SimpleDate(val year: Int, val month: Int, val day: Int)

/**
 * SO-04. "Not sure yet" is a legitimate answer for every question (Screen Inventory), so
 * each question models it explicitly rather than treating null as ambiguous between
 * "unanswered" and "answered with uncertainty".
 */
data class OnboardingAnswers(
    val studyHours: StudyHoursPerDay? = null,
    val strongestSubjectId: String? = null,
    val strongestNotSure: Boolean = false,
    val weakestSubjectId: String? = null,
    val weakestNotSure: Boolean = false,
    val examDate: SimpleDate? = null,
    val examDateNotSure: Boolean = false,
    val studyTime: StudyTimeOfDay? = null,
)

/** The full set of choices SO-05 reads back to the student before committing to a plan. */
data class OnboardingSelections(
    val grade: Grade? = null,
    val track: Track? = null,
    val subjectIds: Set<String> = emptySet(),
    val teacherIdBySubject: Map<String, String> = emptyMap(),
    val answers: OnboardingAnswers = OnboardingAnswers(),
)
