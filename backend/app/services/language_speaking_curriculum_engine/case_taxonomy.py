"""Curriculum-owned Educational Case taxonomy — Claude never invents categories."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class EducationalCaseCategory(StrEnum):
    daily_life = "daily_life"
    family = "family"
    school = "school"
    university = "university"
    travel = "travel"
    career = "career"
    business = "business"
    healthcare = "healthcare"
    technology = "technology"
    immigration = "immigration"
    culture = "culture"
    ethics = "ethics"
    law = "law"
    society = "society"
    finance = "finance"
    relationships = "relationships"
    leadership = "leadership"
    decision_making = "decision_making"
    conflict_resolution = "conflict_resolution"
    negotiation = "negotiation"
    customer_service = "customer_service"
    public_communication = "public_communication"


# CEFR → allowed / preferred categories (Curriculum locks the menu Claude may use)
_CEFR_CATEGORY_POOL: dict[str, tuple[EducationalCaseCategory, ...]] = {
    "A1": (
        EducationalCaseCategory.daily_life,
        EducationalCaseCategory.travel,
        EducationalCaseCategory.customer_service,
        EducationalCaseCategory.school,
    ),
    "A2": (
        EducationalCaseCategory.daily_life,
        EducationalCaseCategory.travel,
        EducationalCaseCategory.school,
        EducationalCaseCategory.relationships,
        EducationalCaseCategory.customer_service,
        EducationalCaseCategory.conflict_resolution,
    ),
    "B1": (
        EducationalCaseCategory.career,
        EducationalCaseCategory.university,
        EducationalCaseCategory.decision_making,
        EducationalCaseCategory.relationships,
        EducationalCaseCategory.travel,
        EducationalCaseCategory.healthcare,
        EducationalCaseCategory.business,
    ),
    "B2": (
        EducationalCaseCategory.ethics,
        EducationalCaseCategory.family,
        EducationalCaseCategory.career,
        EducationalCaseCategory.immigration,
        EducationalCaseCategory.business,
        EducationalCaseCategory.healthcare,
        EducationalCaseCategory.society,
        EducationalCaseCategory.negotiation,
    ),
    "C1": (
        EducationalCaseCategory.law,
        EducationalCaseCategory.society,
        EducationalCaseCategory.leadership,
        EducationalCaseCategory.finance,
        EducationalCaseCategory.ethics,
        EducationalCaseCategory.public_communication,
        EducationalCaseCategory.immigration,
        EducationalCaseCategory.business,
    ),
}

_CEFR_ARCHETYPE: dict[str, str] = {
    "A1": "simple_daily_one_problem_one_solution",
    "A2": "simple_dilemma_two_viewpoints",
    "B1": "personal_responsibility_several_solutions",
    "B2": "ethical_hidden_motivations_valid_opinions",
    "C1": "legal_policy_long_term_no_single_answer",
}


def _normalize_cefr(cefr: str) -> str:
    level = (cefr or "A2").upper()
    if level.startswith("C"):
        return "C1"
    if level.startswith("B2") or level == "B2":
        return "B2"
    if level.startswith("B1") or level == "B1":
        return "B1"
    if level == "A1":
        return "A1"
    return "A2"


def select_case_category(
    *,
    cefr: str,
    skill_ids: list[str] | None = None,
    learning_focus: str = "",
    scenario_type: str = "",
) -> EducationalCaseCategory:
    """Curriculum selects Educational Case category — never Claude."""
    level = _normalize_cefr(cefr)
    pool = _CEFR_CATEGORY_POOL.get(level) or _CEFR_CATEGORY_POOL["A2"]
    blob = " ".join(
        [*(skill_ids or []), learning_focus or "", scenario_type or ""]
    ).lower()

    keyword_map: list[tuple[tuple[str, ...], EducationalCaseCategory]] = [
        (("airport", "travel", "flight", "greeting"), EducationalCaseCategory.travel),
        (("family", "divorce", "parent", "home"), EducationalCaseCategory.family),
        (("interview", "job", "career", "hiring"), EducationalCaseCategory.career),
        (("workplace", "office", "client", "colleague"), EducationalCaseCategory.business),
        (("medical", "doctor", "clinic", "health"), EducationalCaseCategory.healthcare),
        (("visa", "immigration", "residency", "document"), EducationalCaseCategory.immigration),
        (("university", "campus", "professor", "essay"), EducationalCaseCategory.university),
        (("school", "classroom", "homework"), EducationalCaseCategory.school),
        (("ethic", "integrity", "honest"), EducationalCaseCategory.ethics),
        (("law", "legal", "court", "contract"), EducationalCaseCategory.law),
        (("finance", "budget", "loan", "money"), EducationalCaseCategory.finance),
        (("leader", "manage", "team"), EducationalCaseCategory.leadership),
        (("negotiat", "deal", "bargain"), EducationalCaseCategory.negotiation),
        (("politic", "policy", "public"), EducationalCaseCategory.public_communication),
        (("society", "community", "social"), EducationalCaseCategory.society),
        (("tech", "digital", "online"), EducationalCaseCategory.technology),
        (("culture", "custom", "tradition"), EducationalCaseCategory.culture),
        (("friend", "relationship", "partner"), EducationalCaseCategory.relationships),
        (("conflict", "disagree", "argument"), EducationalCaseCategory.conflict_resolution),
        (("decision", "choose", "plan"), EducationalCaseCategory.decision_making),
        (("service", "customer", "help desk"), EducationalCaseCategory.customer_service),
    ]
    for keys, cat in keyword_map:
        if any(k in blob for k in keys) and cat in pool:
            return cat
    return pool[0]


def case_archetype_for_cefr(cefr: str) -> str:
    return _CEFR_ARCHETYPE[_normalize_cefr(cefr)]


def select_educational_case_seed(
    *,
    cefr: str,
    skill_ids: list[str] | None = None,
    learning_focus: str = "",
    scenario_type: str = "",
) -> dict[str, Any]:
    """Backend-owned Educational Case seed for PackageConstraints / complexity policy."""
    level = _normalize_cefr(cefr)
    category = select_case_category(
        cefr=level,
        skill_ids=skill_ids,
        learning_focus=learning_focus,
        scenario_type=scenario_type,
    )
    archetype = case_archetype_for_cefr(level)
    return {
        "case_category": category.value,
        "case_archetype": archetype,
        "cefr_band": level,
    }
