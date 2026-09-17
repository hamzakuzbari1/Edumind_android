"""Writing node selection — curriculum engine only; no static QA defaults."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.selector import CurriculumSelectionResult, select_writing_curriculum_node
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode
from app.services.language_writing_progression.storage import (
    completed_node_ids_from_state,
    load_completed_nodes_from_lessons,
    merge_completed_nodes,
    writing_state_from_payload,
)
from app.services.language_writing_topic_universe.registry import get_universe_catalog


async def select_node_for_student(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    goal: WritingGoal,
    official_cefr: OfficialWritingCEFR,
    progression_payload: dict | None = None,
    chain_id: str | None = None,
    node_id: str | None = None,
) -> CurriculumSelectionResult:
    """Select chain/node using curriculum engine or explicit override."""
    if chain_id and node_id:
        catalog = get_universe_catalog()
        chain = catalog.chain_by_id(chain_id)
        node = chain.node_by_id(node_id) if chain else None
        if chain and node:
            from app.services.language_writing_curriculum.types import CurriculumSelectionScore, WritingCurriculumRecommendation
            from app.services.language_writing_topic_universe.types import TopicSelectionContext

            if node.official_cefr != official_cefr:
                raise ValueError(
                    f"Node CEFR {node.official_cefr.value} does not match official level {official_cefr.value}. "
                    "Use curriculum selection for remediation lessons."
                )
            rec = WritingCurriculumRecommendation(
                chain_node=node,
                topic_context=TopicSelectionContext(
                    topic_id=node.topic_id,
                    context_complexity=node.context_complexity,
                    chain_id=chain_id,
                    chain_node_id=node_id,
                ),
                arc_stage=node.arc_stage,
                goal=goal,
                context_complexity=node.context_complexity,
                score=CurriculumSelectionScore(total=1.0, cefr_fit=1.0),
                selection_reason="Explicit node override",
            )
            return CurriculumSelectionResult(
                chain_id=chain_id,
                node_id=node_id,
                node=node,
                recommendation=rec,
                remediation=False,
            )

    state = writing_state_from_payload(progression_payload)
    from_lessons = await load_completed_nodes_from_lessons(
        db, student_id=student_id, language_id=language_id
    )
    state = merge_completed_nodes(state, from_lessons)
    completed = completed_node_ids_from_state(state)
    recent = frozenset(str(n) for n in (state.get("recent_node_ids") or []) if n)
    weak = tuple(str(w) for w in (state.get("weak_skills") or []) if w)

    return select_writing_curriculum_node(
        goal=goal,
        official_cefr=official_cefr,
        completed_node_ids=completed,
        recent_node_ids=recent,
        weak_skills=weak,
    )


def resolve_chain_node(
    *,
    chain_id: str,
    node_id: str,
) -> WritingKnowledgeChainNode | None:
    catalog = get_universe_catalog()
    chain = catalog.chain_by_id(chain_id)
    if not chain:
        return None
    return chain.node_by_id(node_id)
