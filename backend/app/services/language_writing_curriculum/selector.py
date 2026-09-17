"""Curriculum selection runtime — CEFR + goal + chain progress + weak skills + anti-repetition."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal
from app.services.language_writing_curriculum.types import CurriculumSelectionScore, WritingCurriculumRecommendation
from app.services.language_writing_knowledge_chain.progression_rules import can_access_node, recommend_next_node
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChain, WritingKnowledgeChainNode
from app.services.language_writing_topic_universe.registry import get_universe_catalog, list_chains
from app.services.language_writing_topic_universe.types import TopicSelectionContext

SELECTOR_VERSION = "7.2.0"
_CEFR_ORDER = tuple(OfficialWritingCEFR)


def _cefr_rank(level: OfficialWritingCEFR) -> int:
    return _CEFR_ORDER.index(level)


def _candidate_chains(goal: WritingGoal) -> tuple[WritingKnowledgeChain, ...]:
    profile = profile_for_goal(goal)
    catalog = get_universe_catalog()
    chains: list[WritingKnowledgeChain] = []
    seen: set[str] = set()
    for chain_id in profile.knowledge_chain_preferences:
        chain = catalog.chain_by_id(chain_id)
        if chain and chain.chain_id not in seen:
            chains.append(chain)
            seen.add(chain.chain_id)
    for topic_key in profile.preferred_topic_ids:
        for chain in list_chains():
            if chain.topic_id.value == topic_key and chain.chain_id not in seen:
                chains.append(chain)
                seen.add(chain.chain_id)
    if not chains:
        chains = list(list_chains())[:6]
    return tuple(chains)


def _score_node(
    *,
    node: WritingKnowledgeChainNode,
    chain: WritingKnowledgeChain,
    goal: WritingGoal,
    official_cefr: OfficialWritingCEFR,
    completed_node_ids: frozenset[str],
    recent_node_ids: frozenset[str],
    weak_skills: frozenset[str],
    recommended_next_id: str | None,
    remediation: bool,
) -> CurriculumSelectionScore:
    profile = profile_for_goal(goal)
    contributions: dict[str, float] = {}

    cefr_fit = 1.0 if node.official_cefr == official_cefr else (0.35 if remediation else 0.0)
    contributions["cefr_fit"] = cefr_fit

    chain_prog = 0.0
    if recommended_next_id and node.node_id == recommended_next_id:
        chain_prog = 1.0
    elif node.node_id not in completed_node_ids and not node.previous_node_ids:
        chain_prog = 0.4
    contributions["chain_progression"] = chain_prog

    goal_align = 0.0
    if node.task_type in profile.preferred_task_types:
        goal_align += 0.5
    if node.genre in profile.preferred_genres:
        goal_align += 0.5
    contributions["goal_alignment"] = min(goal_align, 1.0)

    anti_rep = 1.0
    if node.node_id in recent_node_ids:
        anti_rep = 0.0
    elif node.node_id in completed_node_ids:
        anti_rep = 0.15
    contributions["anti_repetition"] = anti_rep

    grammar_needs = 0.0
    grammar_key = node.grammar_focus_primary or ""
    for weak in weak_skills:
        if grammar_key and grammar_key in weak:
            grammar_needs = 1.0
            break
    contributions["grammar_needs"] = grammar_needs

    complexity_fit = 0.5 + min(node.context_complexity, 5) * 0.08
    contributions["complexity_fit"] = min(complexity_fit, 1.0)

    weights = {
        "cefr_fit": 0.30,
        "chain_progression": 0.25,
        "goal_alignment": 0.15,
        "anti_repetition": 0.15,
        "grammar_needs": 0.10,
        "complexity_fit": 0.05,
    }
    total = sum(contributions[k] * weights[k] for k in weights)
    return CurriculumSelectionScore(
        total=total,
        cefr_fit=cefr_fit,
        chain_progression=chain_prog,
        goal_alignment=contributions["goal_alignment"],
        complexity_fit=contributions["complexity_fit"],
        grammar_needs=grammar_needs,
        anti_repetition=anti_rep,
        contributions=contributions,
    )


@dataclass(frozen=True, slots=True)
class CurriculumSelectionResult:
    chain_id: str
    node_id: str
    node: WritingKnowledgeChainNode
    recommendation: WritingCurriculumRecommendation
    remediation: bool = False


def select_writing_curriculum_node(
    *,
    goal: WritingGoal,
    official_cefr: OfficialWritingCEFR,
    completed_node_ids: frozenset[str],
    recent_node_ids: frozenset[str] | None = None,
    weak_skills: tuple[str, ...] = (),
) -> CurriculumSelectionResult:
    """Select next lesson node — never repeats unless pool exhausted."""
    recent = recent_node_ids or frozenset()
    weak = frozenset(weak_skills)
    chains = _candidate_chains(goal)

    def _level_entry_node(chain: WritingKnowledgeChain) -> WritingKnowledgeChainNode | None:
        has_current_level_progress = any(
            node.node_id in completed_node_ids and node.official_cefr == official_cefr
            for node in chain.nodes
        )
        if has_current_level_progress:
            return None
        for node in chain.nodes:
            if node.official_cefr == official_cefr and node.node_id not in completed_node_ids:
                return node
        return None

    def _collect(remediation: bool) -> list[tuple[WritingKnowledgeChain, WritingKnowledgeChainNode, CurriculumSelectionScore, str]]:
        picks: list[tuple[WritingKnowledgeChain, WritingKnowledgeChainNode, CurriculumSelectionScore, str]] = []
        cefr_for_rules = official_cefr
        for chain in chains:
            level_entry = None if remediation else _level_entry_node(chain)
            if level_entry is not None:
                score = _score_node(
                    node=level_entry,
                    chain=chain,
                    goal=goal,
                    official_cefr=official_cefr,
                    completed_node_ids=completed_node_ids,
                    recent_node_ids=recent,
                    weak_skills=weak,
                    recommended_next_id=level_entry.node_id,
                    remediation=False,
                )
                picks.append((chain, level_entry, score, f"Level-entry selection for {goal.value}"))
                if picks and picks[-1][0].chain_id == chain.chain_id:
                    continue

            rec = recommend_next_node(
                chain=chain,
                completed_node_ids=completed_node_ids,
                official_cefr=cefr_for_rules if not remediation else OfficialWritingCEFR(
                    _CEFR_ORDER[max(0, _cefr_rank(official_cefr) - 1)].value
                ),
            )
            if not rec.allowed or not rec.next_node_id:
                continue
            node = chain.node_by_id(rec.next_node_id)
            if node is None:
                continue
            if remediation:
                if _cefr_rank(node.official_cefr) >= _cefr_rank(official_cefr):
                    continue
            elif node.official_cefr != official_cefr:
                continue
            access = can_access_node(
                chain=chain,
                node_id=node.node_id,
                completed_node_ids=completed_node_ids,
                official_cefr=official_cefr if not remediation else node.official_cefr,
            )
            if not access.allowed:
                continue
            score = _score_node(
                node=node,
                chain=chain,
                goal=goal,
                official_cefr=official_cefr,
                completed_node_ids=completed_node_ids,
                recent_node_ids=recent,
                weak_skills=weak,
                recommended_next_id=rec.next_node_id,
                remediation=remediation,
            )
            reason = f"{'Remediation' if remediation else 'Standard'} selection for {goal.value}"
            picks.append((chain, node, score, reason))
        return picks

    candidates = _collect(remediation=False)
    remediation = False
    if not candidates:
        candidates = _collect(remediation=True)
        remediation = True

    if not candidates:
        chain = chains[0]
        entry = chain.entry_node
        if entry is None:
            raise ValueError("No selectable writing curriculum node")
        node = entry
        score = CurriculumSelectionScore(total=0.1, cefr_fit=0.1)
        reason = "Fallback chain entry"
        remediation = True
        candidates = [(chain, node, score, reason)]
    else:
        candidates.sort(key=lambda item: item[2].total, reverse=True)
        chain, node, score, reason = candidates[0]

    exhausted_repeat = all(
        n.node_id in completed_node_ids or n.node_id in recent for n in chain.nodes
    )
    if exhausted_repeat and node.node_id in completed_node_ids:
        for chain2, node2, score2, reason2 in sorted(candidates, key=lambda i: i[2].total, reverse=True):
            if node2.node_id not in recent:
                chain, node, score, reason = chain2, node2, score2, reason2
                break

    topic_ctx = TopicSelectionContext(
        topic_id=node.topic_id,
        context_complexity=node.context_complexity,
        chain_id=chain.chain_id,
        chain_node_id=node.node_id,
    )
    recommendation = WritingCurriculumRecommendation(
        chain_node=node,
        topic_context=topic_ctx,
        arc_stage=node.arc_stage,
        goal=goal,
        context_complexity=node.context_complexity,
        score=score,
        selection_reason=reason,
    )
    return CurriculumSelectionResult(
        chain_id=chain.chain_id,
        node_id=node.node_id,
        node=node,
        recommendation=recommendation,
        remediation=remediation,
    )
