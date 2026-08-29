package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.input.PASSWORD_MIN_LENGTH

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Shared client-side validation for the auth flow.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One set of rules for A-04 login, A-05…A-07 register and A-11 reset, so the same address
 * cannot be accepted on one screen and rejected on the next.
 *
 * The guiding principle: **client validation catches typos, the server decides truth.** We
 * check what a user can obviously fix before spending a round trip on a phone with patchy
 * data — an empty field, a mistyped address, two passwords that disagree. We never
 * re-implement the platform's password policy or its idea of a valid domain, because
 * guessing at rules the server owns means rejecting people the server would have accepted.
 *
 * Each function returns a string resource for the message, or null when the value is fine.
 */

/**
 * Deliberately permissive: something, an @, a dotted domain. That is the whole check.
 *
 * Stricter regexes reject real addresses far more often than they catch bad ones.
 */
private val EmailPattern = Regex("^[^@\\s]+@[^@\\s.]+\\.[^@\\s]+$")

@StringRes
fun emailErrorOf(email: String): Int? {
    val trimmed = email.trim()
    return when {
        trimmed.isEmpty() -> R.string.a04_error_email_required
        !EmailPattern.matches(trimmed) -> R.string.a04_error_email_invalid
        else -> null
    }
}

/**
 * A name is required and must be more than a single character.
 *
 * No character-set restriction: the name field must accept Arabic, Latin, a mix of both,
 * and the spaces and apostrophes real Syrian names contain.
 */
@StringRes
fun fullNameErrorOf(name: String): Int? {
    val trimmed = name.trim()
    return when {
        trimmed.isEmpty() -> R.string.reg_error_name_required
        trimmed.length < 2 -> R.string.reg_error_name_short
        else -> null
    }
}

/** Length only — strength is shown as guidance by the meter, never enforced as a gate. */
@StringRes
fun newPasswordErrorOf(password: String): Int? = when {
    password.isEmpty() -> R.string.a04_error_password_required
    password.length < PASSWORD_MIN_LENGTH -> R.string.reg_error_password_short
    else -> null
}

@StringRes
fun passwordConfirmationErrorOf(password: String, confirmation: String): Int? = when {
    confirmation.isEmpty() -> R.string.reg_error_confirm_required
    confirmation != password -> R.string.reg_error_confirm_mismatch
    else -> null
}
