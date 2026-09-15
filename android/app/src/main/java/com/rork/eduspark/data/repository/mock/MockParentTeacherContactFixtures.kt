package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.data.model.ParentSubjectTeacher
import com.rork.eduspark.data.model.ParentSubjectTeacherStatus
import com.rork.eduspark.data.model.ParentTeacherAvailability
import com.rork.eduspark.data.model.ParentTeacherName
import com.rork.eduspark.data.model.ParentTeacherProfile
import com.rork.eduspark.data.model.ParentTeacherResponseTime
import com.rork.eduspark.data.model.ParentTeacherRole

/**
 * Canonical mock Parent teacher set for a linked student. Parent Subjects & Teachers and
 * Parent-visible messaging both read from this fixture so they cannot drift apart.
 */
internal object MockParentTeacherContactFixtures {

    fun subjectsTeachersFor(studentId: String): List<ParentSubjectTeacher> = listOf(
        ParentSubjectTeacher(
            id = "$studentId-math-teacher",
            subject = ParentSubjectKind.Mathematics,
            teacher = ParentTeacherProfile(
                id = "teacher-rami-al-hassan",
                name = ParentTeacherName.RamiAlHassan,
                role = ParentTeacherRole.MathematicsTeacher,
                avatarInitial = "ر",
                availability = ParentTeacherAvailability.SundayTuesday,
                responseTime = ParentTeacherResponseTime.SameDay,
            ),
            progressPercent = 76,
            status = ParentSubjectTeacherStatus.NeedsFollowUp,
            weeklySessions = 3,
        ),
        ParentSubjectTeacher(
            id = "$studentId-science-teacher",
            subject = ParentSubjectKind.Science,
            teacher = ParentTeacherProfile(
                id = "teacher-sara-al-khatib",
                name = ParentTeacherName.SaraAlKhatib,
                role = ParentTeacherRole.ScienceTeacher,
                avatarInitial = "س",
                availability = ParentTeacherAvailability.MondayWednesday,
                responseTime = ParentTeacherResponseTime.OneSchoolDay,
            ),
            progressPercent = 92,
            status = ParentSubjectTeacherStatus.OnTrack,
            weeklySessions = 2,
        ),
        ParentSubjectTeacher(
            id = "$studentId-arabic-teacher",
            subject = ParentSubjectKind.Arabic,
            teacher = ParentTeacherProfile(
                id = "teacher-mona-nassar",
                name = ParentTeacherName.MonaNassar,
                role = ParentTeacherRole.ArabicTeacher,
                avatarInitial = "م",
                availability = ParentTeacherAvailability.SaturdayMonday,
                responseTime = ParentTeacherResponseTime.SameDay,
            ),
            progressPercent = 88,
            status = ParentSubjectTeacherStatus.OnTrack,
            weeklySessions = 3,
        ),
    )

    fun messagingTeacherContactsFor(studentId: String): List<MessageParticipant> =
        subjectsTeachersFor(studentId).map { item ->
            MessageParticipant(
                id = item.teacher.id,
                displayName = teacherDisplayName(item.teacher.name),
                role = MessageParticipantRole.Teacher,
                avatarInitial = item.teacher.avatarInitial,
                contextLabel = "${subjectLabel(item.subject)} · ${teacherRoleLabel(item.teacher.role)}",
            )
        }

    fun messagingTeacherContact(teacherId: String, studentId: String): MessageParticipant? =
        messagingTeacherContactsFor(studentId).firstOrNull { it.id == teacherId }

    fun teacherIdsFor(studentId: String): Set<String> =
        subjectsTeachersFor(studentId).map { it.teacher.id }.toSet()

    private fun teacherDisplayName(name: ParentTeacherName): String = when (name) {
        ParentTeacherName.RamiAlHassan -> "رامي الحسن"
        ParentTeacherName.SaraAlKhatib -> "سارة الخطيب"
        ParentTeacherName.MonaNassar -> "منى نصار"
    }

    private fun subjectLabel(subject: ParentSubjectKind): String = when (subject) {
        ParentSubjectKind.Mathematics -> "الرياضيات"
        ParentSubjectKind.Science -> "العلوم"
        ParentSubjectKind.Arabic -> "اللغة العربية"
    }

    private fun teacherRoleLabel(role: ParentTeacherRole): String = when (role) {
        ParentTeacherRole.MathematicsTeacher -> "مدرس الرياضيات"
        ParentTeacherRole.ScienceTeacher -> "مدرس العلوم"
        ParentTeacherRole.ArabicTeacher -> "مدرس اللغة العربية"
    }
}
