package com.rork.eduspark.ui.navigation

import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.StudentOnboardingStep
import com.rork.eduspark.data.model.UserRole
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AuthenticationRoutingTest {
    @Test
    fun completedUsersRouteToTheirRoleGraphs() {
        assertEquals(Routes.STUDENT_GRAPH, destinationAfterAuthentication(user(UserRole.Student, true)))
        assertEquals(Routes.TEACHER_GRAPH, destinationAfterAuthentication(user(UserRole.Teacher, true)))
        assertEquals(Routes.PARENT_GRAPH, destinationAfterAuthentication(user(UserRole.Parent, true)))
    }

    @Test
    fun incompleteStudentAndTeacherRouteToExistingSetupFlows() {
        assertEquals(Routes.ONBOARDING_GRAPH, destinationAfterAuthentication(user(UserRole.Student, false)))
        assertEquals(Routes.TEACHER_SETUP, destinationAfterAuthentication(user(UserRole.Teacher, false)))
    }

    @Test
    fun incompleteStudentResumesServerReportedStep() {
        assertEquals(
            Routes.SO_SUBJECTS,
            destinationAfterAuthentication(user(UserRole.Student, false, StudentOnboardingStep.Subjects)),
        )
        assertEquals(
            Routes.SO_TEACHERS,
            destinationAfterAuthentication(user(UserRole.Student, false, StudentOnboardingStep.Teachers)),
        )
        assertEquals(
            Routes.STUDENT_GRAPH,
            destinationAfterAuthentication(user(UserRole.Student, false, StudentOnboardingStep.Complete)),
        )
    }

    @Test
    fun roleFirstAuthRoutesCarryTheSelectedRole() {
        assertEquals("auth/role-auth/student", Routes.roleAuthRoute(UserRole.Student))
        assertEquals("auth/login/teacher", Routes.loginRoute(UserRole.Teacher))
        assertEquals("auth/login/parent", Routes.loginRoute(UserRole.Parent))
        assertEquals(Routes.REGISTER_STUDENT, Routes.registerRoute(UserRole.Student))
        assertEquals(Routes.REGISTER_TEACHER, Routes.registerRoute(UserRole.Teacher))
        assertEquals(Routes.REGISTER_PARENT, Routes.registerRoute(UserRole.Parent))
        assertTrue(Routes.TWO_FACTOR.contains("{${Routes.ROLE_ARG}}"))
    }

    private fun user(
        role: UserRole,
        complete: Boolean,
        step: StudentOnboardingStep? = null,
    ) = SessionUser(
        id = "1",
        displayName = "User",
        email = "user@example.com",
        role = role,
        isEmailVerified = true,
        requiresTwoFactor = false,
        hasCompletedOnboarding = complete,
        onboardingStep = step,
    )
}
