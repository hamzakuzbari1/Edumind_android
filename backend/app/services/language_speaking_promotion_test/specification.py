"""Build deterministic SPA specification + curriculum coverage selection (S18)."""

from __future__ import annotations

import hashlib
import json

from app.services.language_speaking_curriculum.types import SpeakingSkillNode
from app.services.language_speaking_promotion_test.policy import (
    CURRICULUM_VERSION_PIN,
    MAX_SHARE_PER_SKILL,
    MAX_SHARE_PER_SKILL_TYPE,
    MIN_DISTINCT_SKILL_IDS,
    SPA_COMPOSITION_VERSION,
    SPA_POLICY_VERSION,
    SPA_REQUIRES_INTERACTION_EVIDENCE,
    SPA_SCHEMA_VERSION,
    SPA_TASK_COUNT,
    SPA_TASK_SLOTS,
    SpaCapabilityKind,
    SpaSkillEvaluatorCompatibility,
    classify_skill_evaluator_compatibility,
    core_curriculum_skills,
    curriculum_skills_for_official_cefr,
    skill_requires_interactive_evaluation,
)
from app.services.language_speaking_promotion_test.types import (
    SpaAssessmentCoverageGap,
    SpaSkillCoverageItem,
    SpaSlotSpecification,
    SpeakingPromotionAssessmentSpecification,
)


class SpaSpecificationError(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


def _fingerprint_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _select_production_skills(
    target_nodes: tuple[SpeakingSkillNode, ...],
) -> tuple[list[SpeakingSkillNode], list[SpaAssessmentCoverageGap], list[SpaSkillCoverageItem]]:
    production: list[SpeakingSkillNode] = []
    gaps: list[SpaAssessmentCoverageGap] = []
    items: list[SpaSkillCoverageItem] = []

    core = core_curriculum_skills(target_nodes)
    core_ids = {n.skill_id for n in core}
    # Prefer core production skills; still classify all target nodes for gap transparency.
    ordered = list(core) + [n for n in target_nodes if n.skill_id not in core_ids]

    for node in ordered:
        compat = classify_skill_evaluator_compatibility(node)
        interactive = skill_requires_interactive_evaluation(node)
        if interactive:
            gaps.append(
                SpaAssessmentCoverageGap(
                    skill_id=node.skill_id,
                    skill_type=node.skill_type.value,
                    label=node.label,
                    gap_kind="interaction_required",
                    reason=(
                        "Skill requires interactive turn-taking, clarification, repair, "
                        "or conversational adaptation; recorded SPA tasks prove spontaneous "
                        "production only and must not claim spontaneous interaction."
                    ),
                    required_capability=SpaCapabilityKind.spontaneous_interaction,
                )
            )
        elif compat is SpaSkillEvaluatorCompatibility.production_compatible:
            if node.skill_id not in {p.skill_id for p in production}:
                production.append(node)
        items.append(
            SpaSkillCoverageItem(
                skill_id=node.skill_id,
                skill_type=node.skill_type.value,
                label=node.label,
                evaluator_compatibility=compat,
                selected_for_tasks=False,  # filled after slot assignment
            )
        )

    # Ensure production list prefers core then diversity by skill_type.
    core_prod = [n for n in production if n.skill_id in core_ids]
    other_prod = [n for n in production if n.skill_id not in core_ids]
    # Deduplicate preserving order
    seen: set[str] = set()
    ordered_prod: list[SpeakingSkillNode] = []
    for n in core_prod + other_prod:
        if n.skill_id in seen:
            continue
        seen.add(n.skill_id)
        ordered_prod.append(n)

    return ordered_prod, gaps, items


def _assign_skills_to_slots(
    production_skills: list[SpeakingSkillNode],
) -> list[tuple[str, ...]]:
    if len(production_skills) < MIN_DISTINCT_SKILL_IDS:
        raise SpaSpecificationError(
            "insufficient_production_skills",
            f"Need ≥{MIN_DISTINCT_SKILL_IDS} production-compatible target skills; "
            f"got {len(production_skills)}",
        )

    assignments: list[list[str]] = [[] for _ in SPA_TASK_SLOTS]
    skill_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    used_ids: set[str] = set()

    def can_use(node: SpeakingSkillNode) -> bool:
        if skill_counts.get(node.skill_id, 0) >= MAX_SHARE_PER_SKILL:
            return False
        if type_counts.get(node.skill_type.value, 0) >= MAX_SHARE_PER_SKILL_TYPE:
            return False
        return True

    def take(node: SpeakingSkillNode, slot_idx: int) -> None:
        assignments[slot_idx].append(node.skill_id)
        skill_counts[node.skill_id] = skill_counts.get(node.skill_id, 0) + 1
        type_counts[node.skill_type.value] = type_counts.get(node.skill_type.value, 0) + 1
        used_ids.add(node.skill_id)

    # Pass 1: preferred types per slot
    for idx, slot in enumerate(SPA_TASK_SLOTS):
        candidates = [
            n
            for n in production_skills
            if n.skill_type in slot.preferred_skill_types and can_use(n)
        ]
        if not candidates:
            candidates = [n for n in production_skills if can_use(n)]
        if not candidates:
            raise SpaSpecificationError(
                "insufficient_production_skills",
                f"Cannot assign production skill for SPA slot {slot.task_order}",
            )
        # Prefer unused skills for diversity
        unused = [n for n in candidates if n.skill_id not in used_ids]
        pick = unused[0] if unused else candidates[0]
        take(pick, idx)

    # Pass 2: ensure minimum distinct skill ids by adding second skills where needed
    if len(used_ids) < MIN_DISTINCT_SKILL_IDS:
        for n in production_skills:
            if len(used_ids) >= MIN_DISTINCT_SKILL_IDS:
                break
            if n.skill_id in used_ids or not can_use(n):
                continue
            # Attach as secondary skill on a slot that still has room
            for idx, slot_skills in enumerate(assignments):
                if len(slot_skills) < 2:
                    take(n, idx)
                    break

    if len(used_ids) < MIN_DISTINCT_SKILL_IDS:
        raise SpaSpecificationError(
            "insufficient_production_skills",
            f"Could not diversify to {MIN_DISTINCT_SKILL_IDS} distinct skills",
        )

    return [tuple(a) for a in assignments]


def build_speaking_promotion_assessment_specification(
    *,
    source_cefr: str,
    target_cefr: str,
) -> SpeakingPromotionAssessmentSpecification:
    """Deterministic target-band coverage selection — no LLM skill picking."""
    src = (source_cefr or "").upper()
    tgt = (target_cefr or "").upper()
    if not src or not tgt:
        raise SpaSpecificationError("cefr_mismatch", "source_cefr and target_cefr required")

    target_nodes = curriculum_skills_for_official_cefr(tgt)
    if not target_nodes:
        raise SpaSpecificationError(
            "unsupported_target",
            f"No curriculum skills for target CEFR {tgt}",
        )

    production_skills, gaps, coverage_items = _select_production_skills(target_nodes)

    # Fail closed if policy required interaction evidence we cannot provide.
    interaction_coverage_required = SPA_REQUIRES_INTERACTION_EVIDENCE
    fail_closed = interaction_coverage_required and any(
        g.gap_kind == "interaction_required" for g in gaps
    )
    if fail_closed:
        raise SpaSpecificationError(
            "coverage_gap_required",
            "SPA policy requires interaction evidence that recorded task families cannot evaluate",
        )

    slot_skill_ids = _assign_skills_to_slots(production_skills)
    selected_ids = {sid for ids in slot_skill_ids for sid in ids}

    # Refresh selected flags on coverage items
    refreshed_items = tuple(
        SpaSkillCoverageItem(
            skill_id=c.skill_id,
            skill_type=c.skill_type,
            label=c.label,
            evaluator_compatibility=c.evaluator_compatibility,
            selected_for_tasks=c.skill_id in selected_ids,
        )
        for c in coverage_items
    )

    slots: list[SpaSlotSpecification] = []
    for slot, skill_ids in zip(SPA_TASK_SLOTS, slot_skill_ids, strict=True):
        forbidden = (
            "spontaneous_interaction",
            "live_dialogue_proof",
            "evi_interaction",
        )
        slots.append(
            SpaSlotSpecification(
                task_order=slot.task_order,
                task_family=slot.task_family,
                execution_mode=slot.execution_mode,
                authorized_skill_ids=skill_ids,
                preparation_seconds=slot.preparation_seconds,
                max_duration_seconds=slot.max_duration_seconds,
                min_follow_ups=slot.min_follow_ups,
                max_follow_ups=slot.max_follow_ups,
                spontaneous_production_required=slot.spontaneous_production_required,
                spontaneous_interaction_required=slot.spontaneous_interaction_required,
                proves_capabilities=tuple(sorted(slot.proves_capabilities, key=lambda c: c.value)),
                forbidden_claims=forbidden,
            )
        )

    if len(slots) != SPA_TASK_COUNT:
        raise SpaSpecificationError("composition_invalid", "SPA must have exactly 5 slots")

    authorized = tuple(sorted(selected_ids))
    fp_payload = {
        "schema_version": SPA_SCHEMA_VERSION,
        "policy_version": SPA_POLICY_VERSION,
        "composition_version": SPA_COMPOSITION_VERSION,
        "curriculum_version": CURRICULUM_VERSION_PIN,
        "source_cefr": src,
        "target_cefr": tgt,
        "slots": [s.to_dict() for s in slots],
        "authorized_skill_ids": list(authorized),
        "coverage_gap_skill_ids": sorted(g.skill_id for g in gaps),
        "requires_interaction_evidence": SPA_REQUIRES_INTERACTION_EVIDENCE,
    }
    spec_fp = _fingerprint_payload(fp_payload)

    return SpeakingPromotionAssessmentSpecification(
        schema_version=SPA_SCHEMA_VERSION,
        policy_version=SPA_POLICY_VERSION,
        composition_version=SPA_COMPOSITION_VERSION,
        curriculum_version=CURRICULUM_VERSION_PIN,
        source_cefr=src,
        target_cefr=tgt,
        specification_fingerprint=spec_fp,
        slots=tuple(slots),
        authorized_skill_ids=authorized,
        coverage_items=refreshed_items,
        coverage_gaps=tuple(gaps),
        requires_interaction_evidence=SPA_REQUIRES_INTERACTION_EVIDENCE,
        interaction_coverage_required=interaction_coverage_required,
        fail_closed_on_interaction_gap=fail_closed,
    )
