package com.rork.eduspark.ui.screens.parent

import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.ParentRepository
import kotlinx.coroutines.flow.first

/**
 * Every parent screen scopes itself to one child, and the choice is shared app-wide through
 * [ParentRepository.selectedStudentId] so switching on one tab carries over to the rest.
 */
internal suspend fun ParentRepository.initialSelectedStudentId(
    students: List<ParentLinkedStudent>,
): String? = selectedStudentId.first()?.takeIf { id -> students.any { it.id == id } }
    ?: students.firstOrNull()?.id
