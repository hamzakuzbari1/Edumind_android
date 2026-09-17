"""Deterministic graph trace utilities for Speaking skill diagnosis (S1).

Student-specific next-skill selection belongs to S8 (language_speaking_diagnostic).
"""

from __future__ import annotations

from collections import deque

from app.services.language_speaking_curriculum.types import SpeakingSkillGraph, SpeakingSkillNode


class SpeakingSkillGraphTrace:
    """Read-only trace API over a validated SpeakingSkillGraph."""

    def __init__(self, graph: SpeakingSkillGraph) -> None:
        self._graph = graph
        self._by_id = {n.skill_id: n for n in graph.nodes}

    @property
    def graph(self) -> SpeakingSkillGraph:
        return self._graph

    def get_skill(self, skill_id: str) -> SpeakingSkillNode | None:
        return self._by_id.get(skill_id)

    def get_direct_prerequisites(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        node = self.get_skill(skill_id)
        if not node:
            return ()
        return tuple(
            self._by_id[p] for p in node.prerequisite_skill_ids if p in self._by_id
        )

    def get_prerequisites(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        """All transitive prerequisite ancestors (prerequisite DAG only)."""
        seen: set[str] = set()
        order: list[SpeakingSkillNode] = []
        queue: deque[str] = deque()
        node = self.get_skill(skill_id)
        if not node:
            return ()
        for prereq in node.prerequisite_skill_ids:
            queue.append(prereq)
        while queue:
            pid = queue.popleft()
            if pid in seen:
                continue
            seen.add(pid)
            pnode = self._by_id.get(pid)
            if not pnode:
                continue
            order.append(pnode)
            for pp in pnode.prerequisite_skill_ids:
                queue.append(pp)
        return tuple(order)

    def get_ancestors(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        return self.get_prerequisites(skill_id)

    def get_next_skills(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        node = self.get_skill(skill_id)
        if not node:
            return ()
        return tuple(self._by_id[n] for n in node.next_skill_ids if n in self._by_id)

    def get_descendants(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        """All skills reachable via next_skill_ids (forward closure)."""
        seen: set[str] = set()
        order: list[SpeakingSkillNode] = []
        queue: deque[str] = deque()
        node = self.get_skill(skill_id)
        if not node:
            return ()
        for nxt in node.next_skill_ids:
            queue.append(nxt)
        while queue:
            nid = queue.popleft()
            if nid in seen:
                continue
            seen.add(nid)
            nnode = self._by_id.get(nid)
            if not nnode:
                continue
            order.append(nnode)
            for nn in nnode.next_skill_ids:
                queue.append(nn)
        return tuple(order)

    def find_dependency_path(
        self,
        from_skill_id: str,
        to_skill_id: str,
    ) -> tuple[str, ...] | None:
        """Shortest prerequisite path from ``from_skill_id`` up to ``to_skill_id`` if
        ``from_skill_id`` is a transitive prerequisite of ``to_skill_id``.

        Returns skill IDs from prerequisite → dependent (inclusive).
        """
        if from_skill_id == to_skill_id:
            return (from_skill_id,)
        if from_skill_id not in self._by_id or to_skill_id not in self._by_id:
            return None

        # BFS upward from to_skill_id through prerequisites
        parent: dict[str, str | None] = {to_skill_id: None}
        queue: deque[str] = deque([to_skill_id])
        while queue:
            current = queue.popleft()
            if current == from_skill_id:
                path: list[str] = []
                cursor: str | None = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent.get(cursor)
                return tuple(path)
            node = self._by_id.get(current)
            if not node:
                continue
            for prereq in node.prerequisite_skill_ids:
                if prereq not in parent:
                    parent[prereq] = current
                    queue.append(prereq)
        return None

    def find_root_prerequisite_candidates(self, skill_id: str) -> tuple[SpeakingSkillNode, ...]:
        """Root or minimal ancestor nodes in the prerequisite closure."""
        ancestors = self.get_ancestors(skill_id)
        if not ancestors:
            node = self.get_skill(skill_id)
            return (node,) if node else ()
        roots: list[SpeakingSkillNode] = []
        ancestor_ids = {a.skill_id for a in ancestors}
        for anc in ancestors:
            if anc.is_root or not anc.prerequisite_skill_ids:
                roots.append(anc)
            elif not any(p in ancestor_ids for p in anc.prerequisite_skill_ids):
                roots.append(anc)
        return tuple(roots)

    def relationship_between(self, skill_ids: list[str]) -> dict[str, tuple[str, ...]]:
        """Map each skill to its prerequisite intersection with the given set."""
        id_set = set(skill_ids)
        result: dict[str, tuple[str, ...]] = {}
        for sid in skill_ids:
            node = self.get_skill(sid)
            if not node:
                result[sid] = ()
                continue
            prereqs_in_set = tuple(p for p in node.prerequisite_skill_ids if p in id_set)
            result[sid] = prereqs_in_set
        return result
