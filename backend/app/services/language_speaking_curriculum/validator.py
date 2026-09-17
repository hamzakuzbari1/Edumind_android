"""Speaking Skill Dependency Graph validator (S1).

Prerequisite edges form a DAG. Related-skill links are non-directional and do not
create prerequisite edges or cycle constraints.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from app.services.language_speaking.enums import OfficialSpeakingCEFR, SpeakingSkillType
from app.services.language_speaking_curriculum.evidence_ids import ALL_EVIDENCE_CODES
from app.services.language_speaking_curriculum.types import SpeakingSkillGraph, SpeakingSkillNode

_CEFR_RANK: dict[OfficialSpeakingCEFR, int] = {
    OfficialSpeakingCEFR.A1: 1,
    OfficialSpeakingCEFR.A2: 2,
    OfficialSpeakingCEFR.B1: 3,
    OfficialSpeakingCEFR.B2: 4,
    OfficialSpeakingCEFR.C1: 5,
    OfficialSpeakingCEFR.C2: 6,
}

_SUPPORTED_SKILL_TYPES = frozenset(SpeakingSkillType)


@dataclass
class GraphValidationIssue:
    code: str
    message: str
    skill_id: str = ""


@dataclass
class GraphValidationResult:
    valid: bool
    issues: list[GraphValidationIssue] = field(default_factory=list)

    def add(self, code: str, message: str, *, skill_id: str = "") -> None:
        self.issues.append(GraphValidationIssue(code=code, message=message, skill_id=skill_id))
        self.valid = False


def _cefr_range_valid(cefr_min: OfficialSpeakingCEFR, cefr_max: OfficialSpeakingCEFR) -> bool:
    return _CEFR_RANK[cefr_min] <= _CEFR_RANK[cefr_max]


def _prereq_cefr_feasible(node: SpeakingSkillNode, prereq: SpeakingSkillNode) -> bool:
    """Prerequisite should not require a higher CEFR floor than the dependent skill."""
    return _CEFR_RANK[prereq.cefr_min] <= _CEFR_RANK[node.cefr_min] + 1


def _detect_prereq_cycles(graph: SpeakingSkillGraph) -> list[str]:
    """Return skill IDs involved in prerequisite cycles, if any."""
    ids = graph.node_ids()
    state: dict[str, int] = dict.fromkeys(ids, 0)  # 0=unvisited, 1=visiting, 2=done
    cycle_nodes: list[str] = []

    def dfs(skill_id: str, path: list[str]) -> bool:
        state[skill_id] = 1
        path.append(skill_id)
        node = graph.node_by_id(skill_id)
        if node:
            for prereq in node.prerequisite_skill_ids:
                if prereq not in ids:
                    continue
                if state[prereq] == 1:
                    cycle_nodes.extend(path[path.index(prereq) :] + [prereq])
                    return True
                if state[prereq] == 0 and dfs(prereq, path):
                    return True
        path.pop()
        state[skill_id] = 2
        return False

    for sid in ids:
        if state[sid] == 0:
            dfs(sid, [])
    return cycle_nodes


def _unreachable_from_roots(graph: SpeakingSkillGraph) -> set[str]:
    """Skills not reachable by following next_skill_ids from roots."""
    roots = {n.skill_id for n in graph.roots}
    if not roots:
        return graph.node_ids()

    reachable: set[str] = set()
    queue: deque[str] = deque(roots)
    while queue:
        sid = queue.popleft()
        if sid in reachable:
            continue
        reachable.add(sid)
        node = graph.node_by_id(sid)
        if node:
            for nxt in node.next_skill_ids:
                queue.append(nxt)
    return graph.node_ids() - reachable


def validate_skill_graph(graph: SpeakingSkillGraph) -> GraphValidationResult:
    result = GraphValidationResult(valid=True)
    if not graph.nodes:
        result.add("EMPTY_GRAPH", "Skill graph has no nodes")
        return result

    ids = graph.node_ids()
    if len(ids) != len(graph.nodes):
        result.add("DUPLICATE_SKILL_ID", "Duplicate skill_id values in catalog")

    by_id = {n.skill_id: n for n in graph.nodes}

    for node in graph.nodes:
        if node.skill_id in node.prerequisite_skill_ids:
            result.add("SELF_PREREQ", "Node lists itself as prerequisite", skill_id=node.skill_id)
        if node.skill_id in node.next_skill_ids:
            result.add("SELF_NEXT", "Node lists itself as next skill", skill_id=node.skill_id)
        if node.skill_id in node.related_skill_ids:
            result.add("SELF_RELATED", "Node lists itself as related", skill_id=node.skill_id)

        if node.skill_type not in _SUPPORTED_SKILL_TYPES:
            result.add("UNSUPPORTED_SKILL_TYPE", f"Unknown skill_type {node.skill_type}", skill_id=node.skill_id)

        if not _cefr_range_valid(node.cefr_min, node.cefr_max):
            result.add("INVALID_CEFR_RANGE", "cefr_min > cefr_max", skill_id=node.skill_id)

        if not node.mastery_requirements or node.mastery_requirements.minimum_evidence_count < 1:
            result.add("EMPTY_MASTERY", "mastery_requirements.minimum_evidence_count required", skill_id=node.skill_id)

        if not node.evidence_requirements.evidence_codes:
            result.add("EMPTY_EVIDENCE", "evidence_requirements.evidence_codes required", skill_id=node.skill_id)
        else:
            for code in node.evidence_requirements.evidence_codes:
                if code not in ALL_EVIDENCE_CODES:
                    result.add("UNKNOWN_EVIDENCE", f"Unknown evidence code {code}", skill_id=node.skill_id)

        if ":" not in node.skill_id or node.skill_id.startswith(":") or node.skill_id.endswith(":"):
            result.add("INVALID_SKILL_ID", "skill_id must use category:slug format", skill_id=node.skill_id)

        for prereq in node.prerequisite_skill_ids:
            if prereq not in ids:
                result.add("MISSING_PREREQ", f"prerequisite {prereq} not in graph", skill_id=node.skill_id)
            else:
                pnode = by_id[prereq]
                if node.skill_id not in pnode.next_skill_ids:
                    result.add(
                        "ASYMMETRIC_NEXT",
                        f"{prereq} is prereq of {node.skill_id} but next link missing",
                        skill_id=node.skill_id,
                    )
                if not _prereq_cefr_feasible(node, pnode):
                    result.add(
                        "CEFR_PREREQ_MISMATCH",
                        f"prerequisite {prereq} cefr_min too high for {node.skill_id}",
                        skill_id=node.skill_id,
                    )

        for nxt in node.next_skill_ids:
            if nxt not in ids:
                result.add("MISSING_NEXT", f"next_skill {nxt} not in graph", skill_id=node.skill_id)
            else:
                nnode = by_id[nxt]
                if node.skill_id not in nnode.prerequisite_skill_ids:
                    result.add(
                        "ASYMMETRIC_PREREQ",
                        f"{node.skill_id} -> {nxt} but reverse prereq missing",
                        skill_id=node.skill_id,
                    )

        for rel in node.related_skill_ids:
            if rel not in ids:
                result.add("MISSING_RELATED", f"related_skill {rel} not in graph", skill_id=node.skill_id)

        if not node.is_root and not node.prerequisite_skill_ids:
            result.add("ORPHAN_NODE", "Non-root node without prerequisites", skill_id=node.skill_id)

        if not node.goal_relevance:
            result.add("EMPTY_GOAL_RELEVANCE", "goal_relevance required", skill_id=node.skill_id)

    cycle = _detect_prereq_cycles(graph)
    if cycle:
        result.add("PREREQ_CYCLE", f"Prerequisite cycle detected: {' -> '.join(cycle)}")

    unreachable = _unreachable_from_roots(graph)
    for sid in sorted(unreachable):
        node = by_id[sid]
        if not node.is_root and node.prerequisite_skill_ids:
            result.add("UNREACHABLE_NODE", "Node not reachable from roots via next links", skill_id=sid)

    return result
