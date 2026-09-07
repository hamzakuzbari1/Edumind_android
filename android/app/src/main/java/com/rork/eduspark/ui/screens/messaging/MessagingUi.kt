package com.rork.eduspark.ui.screens.messaging

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole

@Composable
fun messageParticipantRoleLabel(role: MessageParticipantRole): String = when (role) {
    MessageParticipantRole.Teacher -> stringResource(R.string.x02_role_teacher)
    MessageParticipantRole.Student -> stringResource(R.string.x02_role_student)
    MessageParticipantRole.Parent -> stringResource(R.string.x02_role_parent)
}

/** Teacher chat subtitle — parent context as stored, student as "طالب · {context}". */
@Composable
fun teacherConversationSubtitle(participant: MessageParticipant): String = when (participant.role) {
    MessageParticipantRole.Parent ->
        participant.contextLabel.ifBlank { stringResource(R.string.x02_role_parent) }
    MessageParticipantRole.Student ->
        if (participant.contextLabel.isNotBlank()) {
            stringResource(R.string.x02_student_subtitle, participant.contextLabel)
        } else {
            stringResource(R.string.x02_role_student)
        }
    MessageParticipantRole.Teacher -> participant.contextLabel
}
