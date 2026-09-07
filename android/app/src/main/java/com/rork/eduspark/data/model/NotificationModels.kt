package com.rork.eduspark.data.model

enum class StudentNotificationType {
    InternalMessage,
    PaymentStatus,
    LessonUpdate,
    Achievement,
}

data class StudentNotification(
    val id: String,
    val type: StudentNotificationType,
    val title: String,
    val body: String,
    val timestampLabel: String,
    val createdAtMillis: Long,
    val isRead: Boolean = false,
    val threadId: String? = null,
    val courseId: String? = null,
)
