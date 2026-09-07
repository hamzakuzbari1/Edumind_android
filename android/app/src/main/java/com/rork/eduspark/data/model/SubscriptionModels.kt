package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-16 · Subscriptions.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §2/§6: "Subscriptions — Demo payment only", `/student/subscriptions/…` +
 * `/student/payments/demo-checkout`, and `StudentCourseAccess` — paid access per course.
 * This screen only ever *reads* that access state and shows the correct boundary where a
 * real action would require ST-17 (not built yet); nothing here can mutate a subscription
 * to active, because there is no payment success to fake.
 */

enum class SubscriptionStatus { Active, ExpiringSoon, Expired }

data class CourseSubscription(
    val courseId: String,
    val courseTitle: String,
    val teacherName: String,
    val status: SubscriptionStatus,
    /** Pre-formatted, same convention as [LearningPath.lastUpdatedLabel] — null only if a subscription genuinely has no end date. */
    val expiryDateLabel: String? = null,
    /** Drives the "expires in N days" warning threshold; null once [status] is [SubscriptionStatus.Expired]. */
    val daysUntilExpiry: Int? = null,
    val includedFeatures: List<String> = emptyList(),
)

/** A course the student has not subscribed to yet — shown as something to add, not something to manage. */
data class AvailableCourse(
    val courseId: String,
    val courseTitle: String,
    val teacherName: String,
    val priceLabel: String,
    val price: Money? = null,
    val benefits: List<String> = emptyList(),
    val includedFeatures: List<String> = emptyList(),
)
