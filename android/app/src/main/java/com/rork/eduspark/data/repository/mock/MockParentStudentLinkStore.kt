package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.StudentProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Canonical mock source for the one Parent ↔ Student relationship used by PR-01/PR-13 and
 * the existing Student parent-linking surface. Repository classes expose role-specific
 * contracts, but this store owns the actual fixture relationship so both sides stay in sync.
 */
class MockParentStudentLinkStore {

    private val _studentProfile = MutableStateFlow(
        StudentProfile(
            displayName = "ريم الحلبي",
            grade = Grade.Baccalaureate,
            school = "مدرسة الفارابي الثانوية",
            avatarInitial = "ر",
            parentLinkCode = StudentLinkCode,
        )
    )
    val studentProfile: StateFlow<StudentProfile> = _studentProfile.asStateFlow()

    private val linkedParentFixture = LinkedParent(
        id = ParentId,
        name = "محمد الحلبي",
        relationship = "الأب",
        email = "m.halabi@example.com",
    )

    private val _linkedParents = MutableStateFlow(listOf(linkedParentFixture))
    val linkedParents: StateFlow<List<LinkedParent>> = _linkedParents.asStateFlow()

    private val _linkedStudents = MutableStateFlow(listOf(linkedStudentFrom(_studentProfile.value)))
    val linkedStudents: StateFlow<List<ParentLinkedStudent>> = _linkedStudents.asStateFlow()

    fun updateStudentProfile(displayName: String, grade: Grade, school: String): StudentProfile {
        val updated = _studentProfile.value.copy(
            displayName = displayName,
            grade = grade,
            school = school,
            avatarInitial = displayName.take(1),
        )
        _studentProfile.value = updated
        if (_linkedStudents.value.any { it.id == StudentId }) {
            _linkedStudents.value = listOf(linkedStudentFrom(updated))
        }
        return updated
    }

    fun revokeParent(parentId: String) {
        _linkedParents.value = _linkedParents.value.filterNot { it.id == parentId }
        if (parentId == ParentId) {
            _linkedStudents.value = emptyList()
        }
    }

    fun linkStudent(code: String): AppResult<ParentLinkedStudent> {
        if (code.trim().uppercase() != _studentProfile.value.parentLinkCode) {
            return AppResult.Failure(AppError.Domain("invalid_parent_link_code"))
        }

        if (_linkedParents.value.none { it.id == ParentId }) {
            _linkedParents.value = listOf(linkedParentFixture)
        }

        val linkedStudent = linkedStudentFrom(_studentProfile.value)
        if (_linkedStudents.value.none { it.id == linkedStudent.id }) {
            _linkedStudents.value = listOf(linkedStudent)
        }
        return AppResult.Success(linkedStudent)
    }

    private fun linkedStudentFrom(profile: StudentProfile) = ParentLinkedStudent(
        id = StudentId,
        displayName = profile.displayName,
        gradeLabel = gradeLabel(profile.grade),
        sectionLabel = "الشعبة أ",
        schoolName = profile.school,
        avatarInitial = profile.avatarInitial,
        statusLabel = "نشط",
        linkCode = profile.parentLinkCode,
    )

    private fun gradeLabel(grade: Grade) = when (grade) {
        Grade.Grade10 -> "الصف العاشر"
        Grade.Grade11 -> "الصف الحادي عشر"
        Grade.Baccalaureate -> "البكالوريا"
    }

    private companion object {
        const val StudentId = "s1"
        const val ParentId = "parent-1"
        const val StudentLinkCode = "REEM-7429"
    }
}

