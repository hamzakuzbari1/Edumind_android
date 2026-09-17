"""Supported academic grades for EduSpark (grades 1–12)."""

from fastapi import HTTPException, status

MIN_ACADEMIC_GRADE = 1
MAX_ACADEMIC_GRADE = 12
ACADEMIC_GRADES = list(range(MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE + 1))

GRADE_LABELS = {
    1: "الصف الأول",
    2: "الصف الثاني",
    3: "الصف الثالث",
    4: "الصف الرابع",
    5: "الصف الخامس",
    6: "الصف السادس",
    7: "الصف السابع",
    8: "الصف الثامن",
    9: "الصف التاسع",
    10: "الصف العاشر",
    11: "الصف الحادي عشر",
    12: "الصف الثاني عشر",
}


def is_valid_academic_grade(grade: int) -> bool:
    return MIN_ACADEMIC_GRADE <= grade <= MAX_ACADEMIC_GRADE


def validate_academic_grade(grade: int) -> None:
    if not is_valid_academic_grade(grade):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"الصف يجب أن يكون بين {MIN_ACADEMIC_GRADE} و {MAX_ACADEMIC_GRADE}",
        )
