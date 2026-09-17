package com.rork.eduspark.ui.screens.student

import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.model.UserRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse

class StudentIdentityCompositionTest {
    private val remoteUser = SessionUser(
        id = "42",
        displayName = "Abeer Abdullah",
        email = "abeer@example.com",
        role = UserRole.Student,
        isEmailVerified = true,
        requiresTwoFactor = false,
        hasCompletedOnboarding = true,
        grade = 12,
    )

    @Test
    fun sessionIdentityOverridesMockHomeNameAndGrade() {
        val result = mockHome().withSessionIdentity(remoteUser)

        assertEquals("Abeer Abdullah", result.studentName)
        assertEquals(Grade.Baccalaureate, result.grade)
        assertFalse(result.studentName.contains("ريم"))
    }

    @Test
    fun missingSessionNeverFallsBackToMockStudentName() {
        assertEquals("", mockHome().withSessionIdentity(null).studentName)
    }

    @Test
    fun profileUsesCanonicalNameEmailAndGradeWithNeutralSchool() {
        val result = ProfileScreenData(
            profile = StudentProfile("ريم الحلبي", Grade.Grade10, "Mock School", "ر", "MOCK-1"),
            email = "mock@example.com",
            gamification = GamificationSnapshot(1, 0, 0f, 0),
            subjects = emptyList(),
            linkedParents = emptyList(),
            learningPreferences = LearningPreferences(),
        ).withSessionIdentity(remoteUser)

        assertEquals("Abeer Abdullah", result.profile.displayName)
        assertEquals("abeer@example.com", result.email)
        assertEquals(Grade.Baccalaureate, result.profile.grade)
        assertEquals("", result.profile.school)
        assertEquals("A", result.profile.avatarInitial)
    }

    private fun mockHome() = StudentHomeSnapshot(
        studentName = "ريم الحلبي",
        grade = Grade.Grade10,
        streakDays = 0,
        gamification = GamificationSnapshot(1, 0, 0f, 0),
        continueItem = null,
        todayPlan = emptyList(),
        subjects = emptyList(),
        hasActiveProject = false,
        englishAvailable = false,
    )
}
