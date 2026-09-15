package com.rork.eduspark.ui.screens.teacher

import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.UserRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse

class TeacherIdentityCompositionTest {
    private val teacher = SessionUser(
        id = "42",
        displayName = "Real Teacher",
        email = "teacher@example.com",
        role = UserRole.Teacher,
        isEmailVerified = true,
        requiresTwoFactor = false,
        hasCompletedOnboarding = false,
    )

    @Test
    fun sessionIdentityOverridesMockTeacherName() {
        val state = TeacherSetupState(
            teacherId = "42",
            identity = TeacherIdentityInfo(displayName = "Mock Teacher", headline = "Bio"),
        ).withCanonicalTeacherIdentity(teacher)

        assertEquals("Real Teacher", state.identity.displayName)
        assertEquals("Bio", state.identity.headline)
        assertFalse(state.identity.displayName.contains("Mock"))
        assertEquals("Real Teacher", canonicalTeacherDisplayName(teacher))
    }

    @Test
    fun missingOrNonTeacherSessionNeverFallsBackToMockIdentity() {
        val student = teacher.copy(role = UserRole.Student, displayName = "Student")

        assertEquals("", canonicalTeacherDisplayName(null))
        assertEquals("", canonicalTeacherDisplayName(student))
        assertEquals(
            "",
            TeacherSetupState(
                teacherId = "42",
                identity = TeacherIdentityInfo(displayName = "Mock Teacher"),
            ).withCanonicalTeacherIdentity(null).identity.displayName,
        )
    }
}
