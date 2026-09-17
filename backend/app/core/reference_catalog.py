"""Reference data: grade-specific subjects (no users/courses). Run via ensure_reference_subjects."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.academic_grades import ACADEMIC_GRADES
from app.models.catalog import Subject

logger = logging.getLogger(__name__)

SUBJECT_CATALOG: dict[str, tuple[str, str]] = {
    "math": ("رياضيات", "math"),
    "science": ("علوم", "science"),
    "arabic": ("عربي", "arabic"),
    "english": ("إنكليزي", "english"),
    "physics": ("فيزياء", "physics"),
    "chemistry": ("كيمياء", "chemistry"),
    "biology": ("أحياء", "biology"),
}

# Elementary (e.g. grade 4): math, science, arabic, english
ELEMENTARY_SLUGS = frozenset({"math", "science", "arabic", "english"})
# Middle (grades 7–9): core + intro sciences
MIDDLE_SLUGS = frozenset({"math", "science", "arabic", "english", "physics", "chemistry"})
# Secondary (e.g. grade 10): math, arabic, english, physics, chemistry, biology
SECONDARY_SLUGS = frozenset({"math", "arabic", "english", "physics", "chemistry", "biology"})

# Backward-compatible alias used by seed scripts
SUBJECT_NAMES = list(SUBJECT_CATALOG.values())


def subject_slugs_for_grade(grade: int) -> frozenset[str]:
    if grade <= 6:
        return ELEMENTARY_SLUGS
    if grade <= 9:
        return MIDDLE_SLUGS
    return SECONDARY_SLUGS


def subjects_for_grade(grade: int) -> list[tuple[str, str]]:
    slugs = subject_slugs_for_grade(grade)
    return [SUBJECT_CATALOG[slug] for slug in slugs if slug in SUBJECT_CATALOG]


def is_subject_allowed_for_grade(slug: str, grade: int) -> bool:
    return slug in subject_slugs_for_grade(grade)


async def ensure_reference_subjects(db: AsyncSession, *, grades: range | None = None) -> int:
    """Insert canonical subjects per grade tier; sync is_active flags. Returns rows created."""
    grade_range = grades or range(ACADEMIC_GRADES[0], ACADEMIC_GRADES[-1] + 1)
    created = 0
    for grade in grade_range:
        allowed = subject_slugs_for_grade(grade)
        for slug in SUBJECT_CATALOG:
            name_ar, _slug = SUBJECT_CATALOG[slug]
            result = await db.execute(
                select(Subject).where(Subject.grade == grade, Subject.slug == slug).limit(1)
            )
            row = result.scalar_one_or_none()
            should_be_active = slug in allowed
            if row:
                if row.is_active != should_be_active or row.name_ar != name_ar:
                    row.is_active = should_be_active
                    row.name_ar = name_ar
                continue
            db.add(
                Subject(
                    name_ar=name_ar,
                    slug=slug,
                    grade=grade,
                    is_active=should_be_active,
                )
            )
            created += 1
    if created:
        await db.flush()
        logger.info("Created %s reference subjects", created)
    else:
        await db.flush()
    return created
