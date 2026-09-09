package com.rork.eduspark.data.model

/**
 * Parent-only linked student summary. It mirrors the existing mock student persona without
 * changing the student-side [StudentProfile] ownership boundary.
 */
data class ParentLinkedStudent(
    val id: String,
    val displayName: String,
    val gradeLabel: String,
    val sectionLabel: String,
    val schoolName: String,
    val avatarInitial: String,
    val statusLabel: String,
    val linkCode: String,
)

