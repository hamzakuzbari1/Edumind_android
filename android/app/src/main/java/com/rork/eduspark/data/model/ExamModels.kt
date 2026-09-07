package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-14 · Exam Schedule Capture.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No OCR engine is integrated this slice — [ExamRepository]'s mock produces a deterministic
 * extraction so the capture → correct → confirm journey is real, even though the recognition
 * step behind it is not. [OcrConfidence] is a plain three-level enum on purpose: Design
 * System §9 copy rules apply to numbers too, and a fabricated "97.328%" would claim a
 * precision this mock (or the real OCR pipeline) was never asked to model.
 */

enum class OcrConfidence { High, Medium, Low }

/**
 * One extracted (or manually added) exam row. [subjectId] is set only when the extracted
 * text matched a known course subject — a low-confidence or unmatched row leaves it null so
 * correction UI can tell "recognised but wrong" apart from "not recognised at all".
 */
data class ExamEntry(
    val id: String,
    val subjectId: String?,
    val subjectTitle: String,
    val date: SimpleDate?,
    val time: String? = null,
    val confidence: OcrConfidence,
)

data class ExamSchedule(
    val entries: List<ExamEntry>,
    val isConfirmed: Boolean = false,
)
