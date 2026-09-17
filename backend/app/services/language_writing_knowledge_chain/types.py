"""Types for Writing Knowledge Chains (W1.2 — enriched node metadata)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import (
    ChainTopology,
    ContextComplexity,
    ExpectedWritingOutput,
    LexisCategory,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingTopicId,
)


@dataclass(frozen=True, slots=True)
class FutureBranchPoint:
    """Documented future branch — not active until graph branching is implemented."""

    anchor_node_id: str
    branch_label: str
    option_a_chain_id: str
    option_b_chain_id: str
    description: str


@dataclass(frozen=True, slots=True)
class WritingTimeEstimate:
    """Estimated minutes for drafting, revision, and total lesson time."""

    writing_minutes: int
    revision_minutes: int
    total_minutes: int


@dataclass(frozen=True, slots=True)
class WritingKnowledgeChainNode:
    """Layer 3 — single node in a knowledge chain (W1.1 enriched metadata)."""

    chain_id: str
    node_id: str
    topic_id: WritingTopicId
    label: str
    narrative_why: str
    official_cefr: OfficialWritingCEFR
    arc_stage: WritingArc
    context_complexity: ContextComplexity
    position: int
    # Graph links (v1.1: linear — at most one next node)
    previous_node_ids: tuple[str, ...] = ()
    next_node_ids: tuple[str, ...] = ()
    review_node_ids: tuple[str, ...] = ()
    future_node_ids: tuple[str, ...] = ()
    # Grammar (primary / secondary / review)
    grammar_focus_primary: str = ""
    grammar_focus_secondary: str = ""
    grammar_focus_review: str = ""
    # Vocabulary (primary / secondary / review + categories)
    vocabulary_primary: tuple[str, ...] = ()
    vocabulary_secondary: tuple[str, ...] = ()
    vocabulary_review: tuple[str, ...] = ()
    vocabulary_categories: tuple[LexisCategory, ...] = ()
    # Time & output
    time_estimate: WritingTimeEstimate | None = None
    expected_output: ExpectedWritingOutput = ExpectedWritingOutput.paragraph
    # Goals & pedagogy
    suggested_goals: tuple[WritingGoal, ...] = ()
    learning_objectives: tuple[str, ...] = ()
    learning_outcomes: tuple[str, ...] = ()
    common_mistakes: tuple[str, ...] = ()
    difficulty_drivers: tuple[str, ...] = ()
    prerequisite_skills: tuple[str, ...] = ()
    carry_forward_template: str = ""
    task_type: str = ""
    genre: str = ""

    @property
    def prerequisite_node_ids(self) -> tuple[str, ...]:
        """Alias for W0 compatibility."""
        return self.previous_node_ids

    @property
    def vocabulary_seeds(self) -> tuple[str, ...]:
        """Legacy alias — primary + secondary lemmas."""
        return self.vocabulary_primary + self.vocabulary_secondary

    @property
    def estimated_writing_minutes(self) -> int:
        return self.time_estimate.writing_minutes if self.time_estimate else 0

    @property
    def estimated_revision_minutes(self) -> int:
        return self.time_estimate.revision_minutes if self.time_estimate else 0

    @property
    def estimated_total_minutes(self) -> int:
        return self.time_estimate.total_minutes if self.time_estimate else 0


@dataclass(frozen=True, slots=True)
class WritingKnowledgeChain:
    """Full chain definition within a topic."""

    chain_id: str
    topic_id: WritingTopicId
    label: str
    description: str
    primary_arc: WritingArc
    nodes: tuple[WritingKnowledgeChainNode, ...]
    topology: ChainTopology = ChainTopology.linear
    documented_future_branches: tuple[FutureBranchPoint, ...] = ()

    def node_by_id(self, node_id: str) -> WritingKnowledgeChainNode | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    @property
    def entry_node(self) -> WritingKnowledgeChainNode | None:
        if not self.nodes:
            return None
        for node in self.nodes:
            if not node.previous_node_ids:
                return node
        return self.nodes[0]

    @property
    def terminal_nodes(self) -> tuple[WritingKnowledgeChainNode, ...]:
        return tuple(n for n in self.nodes if not n.next_node_ids)

    @property
    def is_linear(self) -> bool:
        return self.topology == ChainTopology.linear


@dataclass
class WritingChainProgress:
    """Per-student chain position (persistence contract)."""

    student_id: int
    language_id: int
    chain_id: str
    current_node_id: str
    completed_node_ids: list[str] = field(default_factory=list)
    last_completed_at: str | None = None
