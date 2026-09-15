package com.rork.eduspark.data.remote.teacher

import com.rork.eduspark.data.model.TeacherParentNote

internal fun ParentNoteListDto.toTeacherParentNotes(studentId: String): List<TeacherParentNote> =
    notes
        .sortedBy { it.createdAt }
        .flatMap { it.toTeacherParentNotes(studentId) }

internal fun ParentNoteDto.toTeacherParentNotes(studentId: String): List<TeacherParentNote> {
    val root = TeacherParentNote(
        id = id.toString(),
        studentId = studentId,
        message = description.ifBlank { title },
        sentLabel = formatParentNoteTimestamp(createdAt),
    )
    val replyNotes = replies
        .sortedBy { it.createdAt }
        .map { reply ->
            TeacherParentNote(
                id = "reply-${reply.id}",
                studentId = studentId,
                message = reply.body,
                sentLabel = formatParentNoteTimestamp(reply.createdAt),
            )
        }
    return listOf(root) + replyNotes
}

internal fun ParentNoteDto.toTeacherParentNote(studentId: String): TeacherParentNote =
    TeacherParentNote(
        id = id.toString(),
        studentId = studentId,
        message = description.ifBlank { title },
        sentLabel = formatParentNoteTimestamp(createdAt),
    )

internal fun formatParentNoteTimestamp(raw: String): String {
    val value = raw.trim()
    if (value.isEmpty()) return ""
    return value.take(16).replace('T', ' ')
}

internal fun parseTeacherStudentNumericId(studentId: String): Int? {
    val digits = studentId.filter { it.isDigit() }
    return digits.toIntOrNull()?.takeIf { it > 0 }
}

internal fun buildParentNoteCreateBody(message: String): ParentNoteCreateDto {
    val trimmed = message.trim()
    val title = trimmed.lineSequence().firstOrNull()?.trim().orEmpty()
        .ifBlank { trimmed }
        .take(80)
        .ifBlank { "ملاحظة" }
    return ParentNoteCreateDto(
        title = title,
        description = trimmed,
        category = "academic",
        priority = "medium",
    )
}
