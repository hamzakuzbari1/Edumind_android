"""Select next Curriculum Graph node + Educational Case variant.

Curriculum owns progression. Claude never chooses the path.
"""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_curriculum_engine.progression_catalog import (
    PROGRESSION_NODES,
    PROGRESSION_SPINE_IDS,
    path_index,
    spine_nodes_for_cefr,
)
from app.services.language_speaking_curriculum_engine.progression_memory import (
    ProgressionMasteryLedger,
    progression_ledger_from_payload,
)
from app.services.language_speaking_curriculum_engine.progression_types import (
    CaseVariant,
    MicroSkillNode,
    ProgressionDecision,
)


def _normalize_cefr(cefr: str) -> str:
    level = (cefr or "A2").upper()
    if level.startswith("C"):
        return "C1"
    if level.startswith("B2"):
        return "B2"
    if level.startswith("B1"):
        return "B1"
    if level == "A1":
        return "A1"
    return "A2"


def _cefr_ok(node: MicroSkillNode, cefr: str) -> bool:
    order = ("A1", "A2", "B1", "B2", "C1")
    level = _normalize_cefr(cefr)
    try:
        return order.index(node.cefr_min) <= order.index(level)
    except ValueError:
        return True


def _prerequisites_met(node: MicroSkillNode, ledger: ProgressionMasteryLedger) -> bool:
    for pid in node.prerequisite_ids:
        prereq = PROGRESSION_NODES.get(pid)
        if prereq is None:
            continue
        mastery = float(ledger.node_mastery.get(pid) or 0.0)
        if mastery < prereq.estimated_mastery_advance * 0.85:
            # Soft gate: exposure also counts toward unlocked progress
            if int(ledger.node_exposure.get(pid) or 0) < 1:
                return False
    return True


def _node_mastery(
    node: MicroSkillNode,
    ledger: ProgressionMasteryLedger,
    skill_mastery_snapshot: dict[str, float] | None,
) -> float:
    if node.node_id in ledger.node_mastery:
        return float(ledger.node_mastery[node.node_id])
    # Map linked speaking skills → soft mastery hint
    if skill_mastery_snapshot:
        linked = [float(skill_mastery_snapshot.get(sid) or 0.0) for sid in node.linked_skill_ids]
        if linked:
            return max(linked)
        # Blended average of all provided skill mastery as weak prior
        vals = [float(v) for v in skill_mastery_snapshot.values()]
        if vals:
            return sum(vals) / len(vals) * 0.5
    return 0.0


def _pick_case_variant(
    node: MicroSkillNode,
    *,
    used_case_ids: set[str],
    used_titles: set[str],
    used_themes: set[str],
    skill_ids: list[str],
    learning_focus: str,
) -> CaseVariant:
    variants = list(node.case_variants)
    if not variants:
        raise ValueError(f"progression_node_has_no_cases:{node.node_id}")

    blob = " ".join([*(skill_ids or []), learning_focus or ""]).lower()

    def score(v: CaseVariant) -> tuple[int, int, int]:
        # Prefer unused cases; lightly prefer keyword match; never prefer used
        used = 1 if v.case_id in used_case_ids else 0
        title_used = 1 if v.title_hint.lower() in used_titles else 0
        theme_used = 1 if v.theme_key in used_themes else 0
        keyword = 0
        if any(k in blob for k in (v.theme_key, v.case_category, v.scenario_type) if k):
            keyword = -1
        return (used + title_used + theme_used, keyword, len(v.case_id))

    variants.sort(key=score)
    return variants[0]


def _entry_node_for_cefr(cefr: str, ledger: ProgressionMasteryLedger) -> MicroSkillNode:
    """First unfinished spine node allowed for this CEFR."""
    nodes = spine_nodes_for_cefr(cefr)
    if not nodes:
        return PROGRESSION_NODES[PROGRESSION_SPINE_IDS[0]]
    for node in nodes:
        mastery = float(ledger.node_mastery.get(node.node_id) or 0.0)
        if mastery < node.estimated_mastery_advance:
            if _prerequisites_met(node, ledger) and _cefr_ok(node, cefr):
                return node
    # All finished for band → last node in band (repeat new cases)
    for node in reversed(nodes):
        if _cefr_ok(node, cefr):
            return node
    return nodes[-1]


def resolve_progression_decision(
    *,
    cefr: str,
    skill_ids: list[str] | None = None,
    learning_focus: str = "",
    ledger: ProgressionMasteryLedger | None = None,
    skill_mastery_snapshot: dict[str, float] | None = None,
    used_case_titles: list[str] | tuple[str, ...] | None = None,
    used_theme_keys: list[str] | tuple[str, ...] | None = None,
    force_node_id: str = "",
) -> ProgressionDecision:
    """Curriculum selects graph node + case variant (repeat vs advance)."""
    level = _normalize_cefr(cefr)
    ledger = ledger or ProgressionMasteryLedger()
    skills = list(skill_ids or [])
    used_cases = set(ledger.used_case_ids)
    used_titles = {t.lower() for t in (used_case_titles or [])}
    used_themes = set(used_theme_keys or [])

    previous = ledger.current_node_id
    current: MicroSkillNode | None = None
    if force_node_id and force_node_id in PROGRESSION_NODES:
        current = PROGRESSION_NODES[force_node_id]
    elif previous and previous in PROGRESSION_NODES:
        current = PROGRESSION_NODES[previous]
    else:
        current = _entry_node_for_cefr(level, ledger)

    assert current is not None
    # If current node is above CEFR, clamp to entry
    if not _cefr_ok(current, level):
        current = _entry_node_for_cefr(level, ledger)

    mastery = _node_mastery(current, ledger, skill_mastery_snapshot)
    prereq_ok = _prerequisites_met(current, ledger)
    action = "enter"
    reason = "starting_or_continuing_node"
    selected = current

    can_advance = (
        prereq_ok
        and mastery >= current.estimated_mastery_advance
        and bool(current.recommended_next_ids)
    )
    if can_advance:
        for nid in current.recommended_next_ids:
            nxt = PROGRESSION_NODES.get(nid)
            if nxt is None:
                continue
            if not _cefr_ok(nxt, level):
                continue
            if not _prerequisites_met(nxt, ledger):
                continue
            selected = nxt
            action = "advance"
            reason = "mastery_met_advance_to_next_node"
            mastery = _node_mastery(selected, ledger, skill_mastery_snapshot)
            break
        else:
            action = "repeat_new_case"
            reason = "mastery_met_but_next_blocked_repeat_case"
    else:
        if int(ledger.node_exposure.get(current.node_id) or 0) >= 1:
            action = "repeat_new_case"
            reason = "weak_or_incomplete_mastery_new_case_same_node"
        else:
            action = "enter"
            reason = "first_case_on_node"

    variant = _pick_case_variant(
        selected,
        used_case_ids=used_cases,
        used_titles=used_titles,
        used_themes=used_themes,
        skill_ids=skills,
        learning_focus=learning_focus,
    )
    idx = path_index(selected.node_id)
    return ProgressionDecision(
        action=action,
        node=selected,
        case_variant=variant,
        previous_node_id=previous or "",
        prerequisites_met=prereq_ok,
        estimated_mastery=mastery,
        path_index=max(0, idx),
        path_length=len(PROGRESSION_SPINE_IDS),
        reason=reason,
    )


def resolve_progression_from_payload(payload: dict[str, Any]) -> ProgressionDecision:
    """Convenience: read mastery ledger + optional snapshots from constraints payload."""
    promo = payload.get("progression_readiness_snapshot") or payload.get(
        "promotion_readiness_json"
    )
    ledger = progression_ledger_from_payload(
        promo if isinstance(promo, dict) else payload.get("speaking_progression_mastery_host")
    )
    # Direct ledger dict on payload
    if isinstance(payload.get("speaking_progression_mastery"), dict):
        ledger = ProgressionMasteryLedger.from_dict(payload["speaking_progression_mastery"])

    skill_mastery = payload.get("skill_mastery_snapshot")
    if not isinstance(skill_mastery, dict):
        skill_mastery = None
    else:
        skill_mastery = {str(k): float(v) for k, v in skill_mastery.items()}

    memory = payload.get("case_memory_snapshot")
    used_titles: list[str] = []
    used_themes: list[str] = []
    if isinstance(memory, dict):
        used_titles = [str(x) for x in (memory.get("used_case_titles") or [])]
        used_themes = [str(x) for x in (memory.get("used_theme_keys") or [])]

    return resolve_progression_decision(
        cefr=str(payload.get("official_cefr") or "A2"),
        skill_ids=[str(s) for s in (payload.get("target_skill_ids") or []) if s],
        learning_focus=str(payload.get("learning_focus") or ""),
        ledger=ledger,
        skill_mastery_snapshot=skill_mastery,
        used_case_titles=used_titles,
        used_theme_keys=used_themes,
        force_node_id=str(payload.get("force_progression_node_id") or ""),
    )


def sample_progression_path(
    *,
    cefr: str,
    steps: int = 4,
    start_mastery_advance: bool = True,
) -> list[ProgressionDecision]:
    """Generate a sample multi-lesson path for verification (simulated mastery)."""
    ledger = ProgressionMasteryLedger()
    out: list[ProgressionDecision] = []
    for i in range(max(1, steps)):
        # Simulate KM readiness: after first case on a node, bump mastery to advance
        if start_mastery_advance and ledger.current_node_id:
            node = PROGRESSION_NODES.get(ledger.current_node_id)
            if node:
                ledger.node_mastery[node.node_id] = max(
                    float(ledger.node_mastery.get(node.node_id) or 0.0),
                    node.estimated_mastery_advance,
                )
                ledger.node_exposure[node.node_id] = max(
                    1, int(ledger.node_exposure.get(node.node_id) or 0)
                )
        decision = resolve_progression_decision(cefr=cefr, ledger=ledger)
        out.append(decision)
        # Record exposure without full advance simulation on first enter
        ledger.current_node_id = decision.node.node_id
        ledger.node_exposure[decision.node.node_id] = (
            int(ledger.node_exposure.get(decision.node.node_id) or 0) + 1
        )
        if decision.case_variant.case_id not in ledger.used_case_ids:
            ledger.used_case_ids.append(decision.case_variant.case_id)
        if decision.action == "advance":
            # Mastery of previous is already high; start next with low mastery
            ledger.node_mastery[decision.node.node_id] = max(
                float(ledger.node_mastery.get(decision.node.node_id) or 0.0),
                0.15,
            )
        else:
            # Weak mastery → stay; nudge slightly
            cur = float(ledger.node_mastery.get(decision.node.node_id) or 0.0)
            ledger.node_mastery[decision.node.node_id] = min(
                decision.node.estimated_mastery_advance - 0.01,
                cur + 0.2,
            )
        # After enough repeats, allow advance next loop
        if (
            int(ledger.node_exposure.get(decision.node.node_id) or 0) >= 2
            and start_mastery_advance
        ):
            ledger.node_mastery[decision.node.node_id] = decision.node.estimated_mastery_advance
    return out
