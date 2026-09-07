package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-22 · Student Profile / ST-23 · Settings — Account.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [displayName]/[grade] are edited from ST-22's own sheet (grade + school) and ST-23's
 * smaller name/avatar sheet — both write through the same [com.rork.eduspark.data.repository.ProfileRepository],
 * so there is exactly one place this student's name and grade live, never two copies to
 * drift apart. Level/XP/streak/course-progress quick stats are NOT modelled here — ST-22
 * reads [GamificationSnapshot] and [SubjectProgress] directly, the same way ST-15 does, so
 * gamification state is never duplicated.
 */
data class StudentProfile(
    val displayName: String,
    val grade: Grade,
    val school: String,
    /** First letter of [displayName] at the moment of load/edit — this app's established avatar convention (see e.g. onboarding's TeacherCard), never a stored image. */
    val avatarInitial: String,
    /** Student-side parent linking code, matching the live `StudentProfile.parent_link_code` field. */
    val parentLinkCode: String,
)

/** ST-22. A parent account linked to this student, shown so the student knows who can see their progress. */
data class LinkedParent(
    val id: String,
    val name: String,
    val relationship: String,
    val email: String,
)

/**
 * Learning Preferences — a new, persistent, always-editable extension of ST-22 (approved
 * design: `LearningPreferences.dc.html`), reflecting Test-2SY's AI-tutor-personalization
 * concept. Deliberately NOT modelled on [com.rork.eduspark.ui.screens.onboarding.OnboardingViewModel]'s
 * one-time SO-04 study-habits wizard — that answers a different question ("when/what do you
 * study") and is answered once at signup; this answers "how should your AI tutor teach you"
 * and must stay editable for the life of the account, so it lives on [ProfileRepository]
 * (the same hot-flow-backed home every other re-editable ST-22 fact already has), not
 * onboarding state.
 */
enum class LearningGoal { ImproveGrades, PrepareForBaccalaureate, DeeperUnderstanding }

enum class ExplanationLength { Brief, Balanced, Detailed }

enum class LearningInterest { Football, Gaming, Music, Drawing }

data class LearningPreferences(
    val goal: LearningGoal = LearningGoal.ImproveGrades,
    val explanationLength: ExplanationLength = ExplanationLength.Balanced,
    val interests: Set<LearningInterest> = emptySet(),
)
