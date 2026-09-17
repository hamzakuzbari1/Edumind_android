package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import com.rork.eduspark.R
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole

/**
 * Selected Android role is UX context only. After login the backend session identity is
 * the source of truth — a Teacher card must never silently open a Parent account.
 */
internal fun sessionMatchesSelectedRole(user: SessionUser, expectedRole: UserRole): Boolean =
    user.role == expectedRole

@StringRes
internal fun roleMismatchMessageRes(actualRole: UserRole): Int = when (actualRole) {
    UserRole.Student -> R.string.a04_error_role_mismatch_student
    UserRole.Teacher -> R.string.a04_error_role_mismatch_teacher
    UserRole.Parent -> R.string.a04_error_role_mismatch_parent
}

internal fun parseUserRoleArg(raw: String?): UserRole? =
    UserRole.entries.firstOrNull { it.name.equals(raw, ignoreCase = true) }
