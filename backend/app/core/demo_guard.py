"""Identify demo/seed accounts — never show in student catalog."""

from __future__ import annotations

DEMO_EMAIL_DOMAIN = "@eduspark.sy"

DEMO_EMAILS: frozenset[str] = frozenset(
    {
        "teacher@eduspark.sy",
        "teacher2@eduspark.sy",
        "teacher3@eduspark.sy",
        "student@eduspark.sy",
        "parent@eduspark.sy",
    }
)

# Legacy seeded display names still present in some databases
DEMO_TEACHER_NAMES: frozenset[str] = frozenset(
    {
        "أحمد الحسين",
        "كريم العلي",
        "أستاذ أحمد",
        "معلم تجريبي",
        "المعلم الأول",
        "المعلم الثاني",
    }
)


def is_demo_email(email: str | None) -> bool:
    if not email:
        return False
    normalized = email.strip().lower()
    return normalized in DEMO_EMAILS


_LEGACY_NAME_FRAGMENTS = ("أحمد الحسين", "كريم العلي", "أستاذ أحمد", "أ. كريم", "أ. سارة")


def is_demo_teacher_name(full_name: str | None) -> bool:
    if not full_name:
        return False
    name = full_name.strip()
    if name in DEMO_TEACHER_NAMES:
        return True
    return any(fragment in name for fragment in _LEGACY_NAME_FRAGMENTS)
