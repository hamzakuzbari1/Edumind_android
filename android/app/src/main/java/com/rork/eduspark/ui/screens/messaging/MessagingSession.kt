package com.rork.eduspark.ui.screens.messaging

import com.rork.eduspark.data.model.CURRENT_STUDENT_MESSAGING_ID
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole

/**
 * Resolves a signed-in [SessionUser] onto the messaging identity space — the ONE place this
 * mapping happens, referenced by every X-01/X-02/X-03 ViewModel, so the decision is made once.
 *
 * Teacher sessions use their own session id directly — it already matches
 * [com.rork.eduspark.data.repository.mock.MockMessagingRepository]'s "mock-teacher" persona.
 * The single Student persona resolves onto [CURRENT_STUDENT_MESSAGING_ID] instead of its own
 * raw session id — see that constant's own doc comment for why. Parent has no messaging
 * surface yet (Phase 6 batch 1 is Student + Teacher only), so both resolve to null for it.
 */
fun SessionUser.messagingParticipantIdOrNull(): String? = when (role) {
    UserRole.Teacher -> id
    UserRole.Student -> CURRENT_STUDENT_MESSAGING_ID
    UserRole.Parent -> null
}

fun SessionUser.messagingRoleOrNull(): MessageParticipantRole? = when (role) {
    UserRole.Teacher -> MessageParticipantRole.Teacher
    UserRole.Student -> MessageParticipantRole.Student
    UserRole.Parent -> null
}
