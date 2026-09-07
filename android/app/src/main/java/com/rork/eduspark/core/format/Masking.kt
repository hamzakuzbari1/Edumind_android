package com.rork.eduspark.core.format

/**
 * Masks the local part of an email address for display on A-09 Two-Factor Verify.
 *
 * Source Audit §3 / §4: the platform's second factor is **email OTP**, not SMS — there is no
 * phone number on file to mask. The PDF security brief specifies a masked destination in the
 * same visual language as a masked phone number; this is the email equivalent of that
 * treatment, not a stand-in for a phone flow that does not exist on the backend.
 *
 * The domain is left legible — masking it too would make the destination unrecognisable,
 * which defeats the point of showing it at all.
 */
fun maskEmail(email: String): String {
    val at = email.indexOf('@')
    if (at <= 0) return email

    val local = email.substring(0, at)
    val domain = email.substring(at)
    val visible = local.take(2)
    return "$visible***$domain"
}
