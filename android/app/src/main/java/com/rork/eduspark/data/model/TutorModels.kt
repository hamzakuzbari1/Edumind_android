package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-04 · AI Tutor Chat / ST-05 · AI Tutor Voice Mode.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One transcript model serves both screens on purpose — a voice exchange in ST-05 has to
 * still be there when the student backs out to ST-04, and that only works if both read the
 * same list of [ChatMessage] rather than keeping separate histories.
 */

/** Who authored one line of the tutor conversation. */
enum class ChatSender { Student, Tutor }

/**
 * One line of the transcript. [isVoice] marks a line that came from ST-05's press-and-hold
 * mic rather than typed input — the bubble itself renders identically either way, but the
 * flag lets a screen show a small mic glyph if it ever needs to distinguish the two.
 */
data class ChatMessage(
    val id: String,
    val sender: ChatSender,
    val text: String,
    val isVoice: Boolean = false,
)

/** The tutor's one-shot reply. Non-streaming by design — see [com.rork.eduspark.data.repository.TutorRepository]. */
data class TutorReply(val text: String)
