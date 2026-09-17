package com.rork.eduspark.ui.screens.auth

import com.rork.eduspark.R
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AuthRoleGuardTest {

    @Test
    fun matchingRolesAreAccepted() {
        UserRole.entries.forEach { role ->
            assertTrue(sessionMatchesSelectedRole(user(role), role))
        }
    }

    @Test
    fun mismatchedRolesAreRejectedAndMappedToTheAccountRole() {
        val selected = UserRole.Teacher
        val actual = UserRole.Parent
        val session = user(actual)

        assertFalse(sessionMatchesSelectedRole(session, selected))
        assertEquals(R.string.a04_error_role_mismatch_parent, roleMismatchMessageRes(actual))
        assertEquals(R.string.a04_error_role_mismatch_teacher, roleMismatchMessageRes(UserRole.Teacher))
        assertEquals(R.string.a04_error_role_mismatch_student, roleMismatchMessageRes(UserRole.Student))
    }

    @Test
    fun parseUserRoleArgReadsRouteTokens() {
        assertEquals(UserRole.Student, parseUserRoleArg("student"))
        assertEquals(UserRole.Teacher, parseUserRoleArg("TEACHER"))
        assertEquals(UserRole.Parent, parseUserRoleArg("Parent"))
        assertNull(parseUserRoleArg(null))
        assertNull(parseUserRoleArg(""))
        assertNull(parseUserRoleArg("admin"))
    }

    private fun user(role: UserRole) = SessionUser(
        id = "1",
        displayName = "User",
        email = "user@example.com",
        role = role,
        isEmailVerified = true,
        requiresTwoFactor = false,
        hasCompletedOnboarding = true,
    )
}
