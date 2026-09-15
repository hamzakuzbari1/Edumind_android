package com.rork.eduspark.data.repository

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ParentLinkedStudent

suspend fun ParentRepository.parentMessagingTeacherIdsByStudent(
    linkedStudents: List<ParentLinkedStudent>,
): Map<String, Set<String>> = linkedStudents.associate { student ->
    val teacherIds = when (val result = getSubjectsTeachers(student.id)) {
        is AppResult.Success -> result.data.items.map { it.teacher.id }.toSet()
        is AppResult.Failure -> emptySet()
    }
    student.id to teacherIds
}
