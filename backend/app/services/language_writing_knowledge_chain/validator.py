"""Knowledge chain validation (W1.2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import ChainTopology, WritingArc, WritingTopicId
from app.services.language_writing_knowledge_chain.complexity_rules import complexity_validation_message
from app.services.language_writing_knowledge_chain.types import (
    WritingKnowledgeChain,
    WritingKnowledgeChainNode,
)
from app.services.language_writing_topic_universe.types import WritingUniverseCatalog


@dataclass
class ValidationIssue:
    code: str
    message: str
    chain_id: str = ""
    node_id: str = ""


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, code: str, message: str, *, chain_id: str = "", node_id: str = "") -> None:
        self.issues.append(ValidationIssue(code=code, message=message, chain_id=chain_id, node_id=node_id))
        self.valid = False


def validate_node_metadata(node: WritingKnowledgeChainNode) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not node.label.strip():
        issues.append(ValidationIssue("EMPTY_LABEL", "Node label required", node.chain_id, node.node_id))
    if not node.narrative_why.strip():
        issues.append(ValidationIssue("EMPTY_WHY", "narrative_why required", node.chain_id, node.node_id))
    if not node.grammar_focus_primary.strip():
        issues.append(ValidationIssue("EMPTY_GRAMMAR_PRIMARY", "grammar_focus_primary required", node.chain_id, node.node_id))
    if node.position > 1 and not node.grammar_focus_review.strip():
        issues.append(ValidationIssue("EMPTY_GRAMMAR_REVIEW", "grammar_focus_review required after entry", node.chain_id, node.node_id))
    if not node.learning_objectives:
        issues.append(ValidationIssue("EMPTY_OBJECTIVES", "learning_objectives required", node.chain_id, node.node_id))
    if not node.learning_outcomes:
        issues.append(ValidationIssue("EMPTY_OUTCOMES", "learning_outcomes required", node.chain_id, node.node_id))
    if not node.common_mistakes:
        issues.append(ValidationIssue("EMPTY_MISTAKES", "common_mistakes required", node.chain_id, node.node_id))
    if not node.difficulty_drivers:
        issues.append(ValidationIssue("EMPTY_DRIVERS", "difficulty_drivers required", node.chain_id, node.node_id))
    if not node.prerequisite_skills:
        issues.append(ValidationIssue("EMPTY_PREREQS", "prerequisite_skills required", node.chain_id, node.node_id))
    if not node.suggested_goals:
        issues.append(ValidationIssue("EMPTY_GOALS", "suggested_goals required", node.chain_id, node.node_id))
    if not node.vocabulary_categories:
        issues.append(ValidationIssue("EMPTY_LEXIS_CATS", "vocabulary_categories required", node.chain_id, node.node_id))
    if not node.vocabulary_primary and not node.vocabulary_secondary:
        issues.append(ValidationIssue("EMPTY_VOCABULARY", "vocabulary_primary or secondary required", node.chain_id, node.node_id))
    if node.position > 1 and not node.vocabulary_review:
        issues.append(ValidationIssue("EMPTY_VOCAB_REVIEW", "vocabulary_review required after entry", node.chain_id, node.node_id))
    if not node.time_estimate or node.estimated_total_minutes <= 0:
        issues.append(ValidationIssue("BAD_TIME_ESTIMATE", "time_estimate required with positive minutes", node.chain_id, node.node_id))
    if not node.expected_output:
        issues.append(ValidationIssue("EMPTY_EXPECTED_OUTPUT", "expected_output required", node.chain_id, node.node_id))

    cx_msg = complexity_validation_message(cefr=node.official_cefr, complexity=node.context_complexity)
    if cx_msg:
        issues.append(ValidationIssue("CEFR_COMPLEXITY_MISMATCH", cx_msg, node.chain_id, node.node_id))

    if node.arc_stage not in WritingArc:
        issues.append(ValidationIssue("UNKNOWN_ARC", f"Unknown arc {node.arc_stage}", node.chain_id, node.node_id))
    return issues


def validate_chain(chain: WritingKnowledgeChain) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not chain.nodes:
        result.add("EMPTY_CHAIN", "Chain has no nodes", chain_id=chain.chain_id)
        return result

    if chain.topology == ChainTopology.linear:
        for node in chain.nodes:
            if len(node.next_node_ids) > 1:
                result.add(
                    "LINEAR_MULTI_NEXT",
                    f"linear chain node {node.node_id} has multiple next_node_ids (branching not implemented)",
                    chain_id=chain.chain_id,
                    node_id=node.node_id,
                )

    node_ids = {n.node_id for n in chain.nodes}
    positions = [n.position for n in chain.nodes]
    if positions != list(range(1, len(chain.nodes) + 1)):
        result.add("BAD_POSITIONS", "Node positions must be 1..N sequential", chain_id=chain.chain_id)

    for branch in chain.documented_future_branches:
        if branch.anchor_node_id not in node_ids:
            result.add(
                "BAD_BRANCH_ANCHOR",
                f"branch anchor {branch.anchor_node_id} not in chain",
                chain_id=chain.chain_id,
            )

    for node in chain.nodes:
        for issue in validate_node_metadata(node):
            result.issues.append(issue)
            result.valid = False
        for prev in node.previous_node_ids:
            if prev not in node_ids:
                result.add("BAD_PREV", f"previous_node {prev} not in chain", chain_id=chain.chain_id, node_id=node.node_id)
        for nxt in node.next_node_ids:
            if nxt not in node_ids:
                result.add("BAD_NEXT", f"next_node {nxt} not in chain", chain_id=chain.chain_id, node_id=node.node_id)
        for rev in node.review_node_ids:
            if rev not in node_ids:
                result.add("BAD_REVIEW", f"review_node {rev} not in chain", chain_id=chain.chain_id, node_id=node.node_id)

    by_id = {n.node_id: n for n in chain.nodes}
    for node in chain.nodes:
        for nxt in node.next_node_ids:
            nxt_node = by_id.get(nxt)
            if nxt_node and node.node_id not in nxt_node.previous_node_ids:
                result.add(
                    "ASYMMETRIC_LINK",
                    f"{node.node_id} -> {nxt} but reverse prev missing",
                    chain_id=chain.chain_id,
                    node_id=node.node_id,
                )

    if not any(n.arc_stage == chain.primary_arc for n in chain.nodes):
        result.add(
            "ARC_MISMATCH",
            f"primary_arc {chain.primary_arc} not reflected in any node",
            chain_id=chain.chain_id,
        )

    return result


def validate_universe(catalog: WritingUniverseCatalog) -> ValidationResult:
    result = ValidationResult(valid=True)
    topic_ids = {t.topic_id for t in catalog.topics}
    if len(topic_ids) != len(catalog.topics):
        result.add("DUPLICATE_TOPIC", "Duplicate topic ids in catalog")

    chain_ids: set[str] = set()
    for chain in catalog.chains:
        if chain.chain_id in chain_ids:
            result.add("DUPLICATE_CHAIN", f"Duplicate chain_id {chain.chain_id}", chain_id=chain.chain_id)
        chain_ids.add(chain.chain_id)
        if chain.topic_id not in topic_ids:
            result.add("ORPHAN_CHAIN", f"Chain topic {chain.topic_id} not in topics", chain_id=chain.chain_id)
        chain_result = validate_chain(chain)
        if not chain_result.valid:
            result.valid = False
            result.issues.extend(chain_result.issues)

    for topic in catalog.topics:
        chains = catalog.chains_for_topic(topic.topic_id)
        if len(chains) < 2:
            result.add(
                "INSUFFICIENT_CHAINS",
                f"Topic {topic.topic_id} has {len(chains)} chains (minimum 2)",
            )
        actual = {c.chain_id for c in chains}
        if set(topic.chain_ids) != actual:
            result.add(
                "TOPIC_CHAIN_MISMATCH",
                f"Topic {topic.topic_id} chain_ids mismatch registered chains",
            )

    return result
