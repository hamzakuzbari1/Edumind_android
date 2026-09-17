"""Pure Journey graph projection — compose catalog + progression + mastery only."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarMasteryState
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot
from app.services.language_grammar_mastery.types import GrammarMasterySnapshot
from app.services.language_grammar_progression.types import GrammarProgressionSnapshot
from app.services.language_learning_journey.enums import JourneyLevelStatus, JourneyStageStatus
from app.services.language_learning_journey.types import (
    JourneyGraph,
    JourneyLevel,
    JourneyProgress,
    JourneyStage,
)

CEFR_ORDER: tuple[GrammarCEFRBand, ...] = (
    GrammarCEFRBand.A1,
    GrammarCEFRBand.A2,
    GrammarCEFRBand.B1,
    GrammarCEFRBand.B2,
    GrammarCEFRBand.C1,
    GrammarCEFRBand.C2,
)


def _empty_graph(*, curriculum_version: str = "") -> JourneyGraph:
    return JourneyGraph(
        enabled=False,
        anchor_cefr="",
        current_grammar_id=None,
        next_grammar_id=None,
        curriculum_version=curriculum_version,
        progress=JourneyProgress(
            cefr_label="",
            stage_index=0,
            stage_total_in_level=0,
            level_percent=0.0,
            overall_completed=0,
            overall_total=0,
        ),
        levels=(),
    )


def project_journey_graph(
    *,
    catalog: GrammarCatalogSnapshot,
    progression: GrammarProgressionSnapshot | None,
    mastery: GrammarMasterySnapshot | None,
) -> JourneyGraph:
    """Compose UI journey graph. Never unlocks or writes educational state."""
    if not catalog.topics:
        return _empty_graph(curriculum_version=str(catalog.version))

    unlocked = set(progression.unlocked_ids) if progression and progression.enabled else set()
    locked = set(progression.locked_ids) if progression and progression.enabled else set()
    future = set(progression.future_ids) if progression and progression.enabled else set()
    current_id = progression.current_grammar_id if progression and progression.enabled else None
    next_id = progression.next_grammar_id if progression and progression.enabled else None
    anchor = (
        progression.anchor_cefr.value
        if progression and progression.enabled and hasattr(progression.anchor_cefr, "value")
        else (progression.anchor_cefr if progression else "")
    )
    if not anchor and current_id:
        topic = catalog.topic_by_id(current_id) if hasattr(catalog, "topic_by_id") else None
        if topic is None:
            for t in catalog.topics:
                if t.grammar_id == current_id:
                    topic = t
                    break
        if topic is not None:
            anchor = topic.cefr_band.value

    mastery_by_id: dict[str, object] = {}
    if mastery and mastery.enabled:
        for rec in mastery.records:
            mastery_by_id[rec.grammar_id] = rec

    # Group topics by CEFR in introduction_order
    by_band: dict[GrammarCEFRBand, list] = {b: [] for b in CEFR_ORDER}
    for topic in sorted(catalog.topics, key=lambda t: (t.cefr_band.value, t.introduction_order, t.grammar_id)):
        band = topic.cefr_band
        if band in by_band:
            by_band[band].append(topic)

    levels: list[JourneyLevel] = []
    overall_completed = 0
    current_level_cefr = anchor or ""
    current_stage_index = 0
    current_level_total = 0
    current_level_completed = 0

    for band in CEFR_ORDER:
        topics = by_band[band]
        if not topics:
            continue
        stages: list[JourneyStage] = []
        completed_count = 0
        for idx, topic in enumerate(topics, start=1):
            rec = mastery_by_id.get(topic.grammar_id)
            mastery_state = (
                rec.state.value if rec is not None and hasattr(rec.state, "value") else GrammarMasteryState.unknown.value
            )
            overall = float(rec.dimensions.overall_mastery) if rec is not None else 0.0
            is_mastered = rec is not None and rec.state is GrammarMasteryState.mastered
            gid = topic.grammar_id

            if gid == current_id:
                status = JourneyStageStatus.current
            elif is_mastered:
                status = JourneyStageStatus.completed
                completed_count += 1
                overall_completed += 1
            elif gid in unlocked:
                status = JourneyStageStatus.unlocked
            elif gid in locked or gid in future or (unlocked and gid not in unlocked):
                status = JourneyStageStatus.locked
            elif not unlocked and not current_id:
                # Engine empty — first topics stay locked until progression exists
                status = JourneyStageStatus.locked
            else:
                status = JourneyStageStatus.locked

            skills = tuple(s.value for s in topic.best_reinforcement_skills)
            # UI always offers quiz label alongside reinforcement skills
            skill_list = list(skills)
            if "quiz" not in skill_list:
                skill_list.append("quiz")

            stages.append(
                JourneyStage(
                    grammar_id=gid,
                    display_code=topic.display_code or "",
                    display_name=topic.display_name,
                    stage_index=idx,
                    status=status,
                    mastery_state=str(mastery_state),
                    overall_mastery=round(overall, 2),
                    estimated_minutes=int(topic.estimated_duration_minutes or 18),
                    skills=tuple(skill_list),
                )
            )

        band_value = band.value
        has_current = any(s.status is JourneyStageStatus.current for s in stages)
        all_done = completed_count == len(stages) and len(stages) > 0
        any_unlocked = any(
            s.status in {JourneyStageStatus.unlocked, JourneyStageStatus.current, JourneyStageStatus.completed}
            for s in stages
        )

        if all_done:
            level_status = JourneyLevelStatus.done
        elif has_current or (any_unlocked and not all_done):
            level_status = JourneyLevelStatus.current
        else:
            level_status = JourneyLevelStatus.locked

        expanded = has_current or (
            level_status is JourneyLevelStatus.current and band_value == current_level_cefr
        )
        # Exactly one expanded: prefer level containing current grammar
        if has_current:
            expanded = True

        if has_current or band_value == current_level_cefr:
            current_level_total = len(stages)
            current_level_completed = completed_count
            if has_current:
                for s in stages:
                    if s.status is JourneyStageStatus.current:
                        current_stage_index = s.stage_index
                        break
            elif current_stage_index == 0 and completed_count:
                current_stage_index = min(completed_count + 1, len(stages))

        levels.append(
            JourneyLevel(
                cefr=band_value,
                status=level_status,
                expanded=expanded,
                completed_count=completed_count,
                total_count=len(stages),
                stages=tuple(stages),
            )
        )

    # Ensure only one level expanded
    if any(lv.expanded for lv in levels):
        seen_expanded = False
        fixed: list[JourneyLevel] = []
        for lv in levels:
            if lv.expanded and not seen_expanded:
                fixed.append(lv)
                seen_expanded = True
            elif lv.expanded and seen_expanded:
                fixed.append(
                    JourneyLevel(
                        cefr=lv.cefr,
                        status=lv.status,
                        expanded=False,
                        completed_count=lv.completed_count,
                        total_count=lv.total_count,
                        stages=lv.stages,
                    )
                )
            else:
                fixed.append(lv)
        levels = fixed
    elif levels:
        # Expand first current level, else first done-with-next, else first level
        idx = next((i for i, lv in enumerate(levels) if lv.status is JourneyLevelStatus.current), 0)
        levels = [
            JourneyLevel(
                cefr=lv.cefr,
                status=lv.status,
                expanded=(i == idx),
                completed_count=lv.completed_count,
                total_count=lv.total_count,
                stages=lv.stages,
            )
            for i, lv in enumerate(levels)
        ]
        current_level_total = levels[idx].total_count
        current_level_completed = levels[idx].completed_count
        current_level_cefr = levels[idx].cefr
        if current_stage_index == 0:
            cur = next((s for s in levels[idx].stages if s.status is JourneyStageStatus.current), None)
            current_stage_index = cur.stage_index if cur else min(current_level_completed + 1, current_level_total or 1)

    total = len(catalog.topics)
    level_percent = (
        round(100.0 * current_level_completed / current_level_total, 1) if current_level_total else 0.0
    )

    enabled = bool(progression and progression.enabled and catalog.topics)
    return JourneyGraph(
        enabled=enabled,
        anchor_cefr=str(anchor or current_level_cefr),
        current_grammar_id=current_id,
        next_grammar_id=next_id,
        curriculum_version=str(catalog.version),
        progress=JourneyProgress(
            cefr_label=str(anchor or current_level_cefr),
            stage_index=int(current_stage_index),
            stage_total_in_level=int(current_level_total),
            level_percent=level_percent,
            overall_completed=overall_completed,
            overall_total=total,
        ),
        levels=tuple(levels),
    )
