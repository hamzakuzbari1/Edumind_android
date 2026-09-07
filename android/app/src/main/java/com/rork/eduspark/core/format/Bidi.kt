package com.rork.eduspark.core.format

import androidx.core.text.BidiFormatter

/**
 * Isolates a Latin run (an email address, a code) inside a surrounding Arabic sentence.
 *
 * Design System §6.5 — "Wrap Latin runs in an isolating span; never concatenate translated
 * strings." Without this, an address like `reem@mail.com` embedded in an Arabic sentence via
 * a `%1$s` placeholder can visually scramble the surrounding punctuation, because the two
 * scripts disagree on run direction. [BidiFormatter] is the platform's own fix for exactly
 * this, so nothing here reimplements bidi algorithms — it only applies the existing one at
 * the point where user data (an email address) is interpolated into translated copy.
 */
fun String.isolateBidi(): String = BidiFormatter.getInstance().unicodeWrap(this)
