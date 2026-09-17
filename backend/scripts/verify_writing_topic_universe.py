"""Verify Writing Topic Universe catalog (W1.2).

Usage (from backend/):
    python scripts/verify_writing_topic_universe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import (
    ChainTopology,
    ExpectedWritingOutput,
    OfficialWritingCEFR,
    WritingArc,
    WritingTopicId,
)
from app.services.language_writing_curriculum.arc_catalog import WRITING_ARC_CATALOG, arc_stages_ordered
from app.services.language_writing_knowledge_chain.complexity_rules import (
    CEFR_COMPLEXITY_RANGES,
    is_complexity_valid_for_cefr,
)
from app.services.language_writing_knowledge_chain.progression_rules import can_access_node, recommend_next_node
from app.services.language_writing_knowledge_chain.validator import validate_universe
from app.services.language_writing_topic_universe.catalog_v1 import CATALOG_VERSION
from app.services.language_writing_topic_universe.registry import get_universe_catalog


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def main() -> int:
    print("Writing W1.2 Topic Universe Verification\n")
    results: list[bool] = []

    catalog = get_universe_catalog()
    validation = validate_universe(catalog)
    results.append(_ok("universe catalog validates", validation.valid, f"{len(validation.issues)} issues"))
    if not validation.valid:
        for issue in validation.issues[:10]:
            print(f"    [{issue.code}] {issue.message} ({issue.chain_id}/{issue.node_id})")

    results.append(_ok("catalog version 1.2.0", CATALOG_VERSION == "1.2.0"))

    results.append(_ok("20 canonical topics", len(catalog.topics) == 20, f"count={len(catalog.topics)}"))
    results.append(_ok("all WritingTopicId enum covered", len(catalog.topics) == len(WritingTopicId)))

    results.append(_ok("7 curriculum arcs defined", len(WRITING_ARC_CATALOG) == 7))
    expected_arcs = {
        WritingArc.sentence_building,
        WritingArc.paragraph_writing,
        WritingArc.narrative_writing,
        WritingArc.opinion_writing,
        WritingArc.formal_writing,
        WritingArc.professional_writing,
        WritingArc.academic_writing,
    }
    results.append(_ok("arc enum matches catalog", set(arc_stages_ordered()) == expected_arcs))

    min_chains = min(len(catalog.chains_for_topic(t.topic_id)) for t in catalog.topics)
    max_chains = max(len(catalog.chains_for_topic(t.topic_id)) for t in catalog.topics)
    results.append(_ok("every topic has >=2 chains", min_chains >= 2, f"min={min_chains}"))
    results.append(_ok("chain depth quality (<=3 per topic)", max_chains <= 3, f"max={max_chains}"))

    total_nodes = sum(len(c.nodes) for c in catalog.chains)
    results.append(_ok("total nodes >= 100", total_nodes >= 100, f"nodes={total_nodes}"))
    results.append(_ok("total chains >= 40", len(catalog.chains) >= 40, f"chains={len(catalog.chains)}"))

    # Linear topology
    non_linear = [c.chain_id for c in catalog.chains if c.topology != ChainTopology.linear]
    results.append(_ok("all chains linear topology", len(non_linear) == 0, str(non_linear[:3])))

    travel = catalog.chain_by_id("travel_airport_journey")
    results.append(_ok("travel_airport_journey exists", travel is not None))
    if travel:
        ids = [n.node_id for n in travel.nodes]
        results.append(_ok("travel chain has 7 nodes", len(ids) == 7))
        results.append(_ok("travel chain includes complaint_email", "complaint_email" in ids))
        results.append(_ok("travel documented future branch at check_in", any(b.anchor_node_id == "check_in" for b in travel.documented_future_branches)))
        complaint = travel.node_by_id("complaint_email")
        if complaint:
            results.append(_ok("complaint_email has explicit outcomes", "Write a formal email" in complaint.learning_outcomes))
            results.append(_ok("complaint_email has difficulty drivers", len(complaint.difficulty_drivers) >= 2))
            results.append(_ok("complaint_email common_mistakes tagged", any(m.startswith("tone:") for m in complaint.common_mistakes)))

    # W1.1+ enriched metadata
    missing_grammar_review = sum(
        1 for c in catalog.chains for n in c.nodes if n.position > 1 and not n.grammar_focus_review
    )
    missing_vocab_review = sum(
        1 for c in catalog.chains for n in c.nodes if n.position > 1 and not n.vocabulary_review
    )
    missing_time = sum(1 for c in catalog.chains for n in c.nodes if n.estimated_total_minutes <= 0)
    missing_output = sum(1 for c in catalog.chains for n in c.nodes if not n.expected_output)
    missing_outcomes = sum(1 for c in catalog.chains for n in c.nodes if not n.learning_outcomes)
    missing_mistakes = sum(1 for c in catalog.chains for n in c.nodes if not n.common_mistakes)
    missing_drivers = sum(1 for c in catalog.chains for n in c.nodes if not n.difficulty_drivers)
    missing_prereqs = sum(1 for c in catalog.chains for n in c.nodes if not n.prerequisite_skills)
    results.append(_ok("grammar_focus_review on non-entry nodes", missing_grammar_review == 0, f"missing={missing_grammar_review}"))
    results.append(_ok("vocabulary_review on non-entry nodes", missing_vocab_review == 0, f"missing={missing_vocab_review}"))
    results.append(_ok("time estimates on all nodes", missing_time == 0, f"missing={missing_time}"))
    results.append(_ok("expected_output on all nodes", missing_output == 0, f"missing={missing_output}"))
    results.append(_ok("learning_outcomes on all nodes", missing_outcomes == 0, f"missing={missing_outcomes}"))
    results.append(_ok("common_mistakes on all nodes", missing_mistakes == 0, f"missing={missing_mistakes}"))
    results.append(_ok("difficulty_drivers on all nodes", missing_drivers == 0, f"missing={missing_drivers}"))
    results.append(_ok("prerequisite_skills on all nodes", missing_prereqs == 0, f"missing={missing_prereqs}"))

    # CEFR complexity rules
    cx_violations = sum(
        1
        for c in catalog.chains
        for n in c.nodes
        if not is_complexity_valid_for_cefr(cefr=n.official_cefr, complexity=n.context_complexity)
    )
    results.append(_ok("CEFR complexity ranges", cx_violations == 0, f"violations={cx_violations}"))
    results.append(_ok("complexity rules documented for 6 CEFR bands", len(CEFR_COMPLEXITY_RANGES) == 6))

    # Expected output enum coverage
    outputs_used = {n.expected_output for c in catalog.chains for n in c.nodes}
    results.append(_ok("expected_output uses canonical enum", all(isinstance(o, ExpectedWritingOutput) for o in outputs_used)))

    if travel:
        entry = travel.entry_node
        dec = can_access_node(
            chain=travel,
            node_id=entry.node_id if entry else "",
            completed_node_ids=frozenset(),
            official_cefr=OfficialWritingCEFR.A1,
        )
        results.append(_ok("entry node accessible at A1", dec.allowed))
        dec2 = recommend_next_node(
            chain=travel,
            completed_node_ids=frozenset({"airport_arrival", "check_in", "security", "delayed_flight"}),
            official_cefr=OfficialWritingCEFR.A2,
        )
        results.append(_ok("recommend next after delay", dec2.allowed and dec2.next_node_id == "complaint_email"))

    mismatch = sum(1 for c in catalog.chains for n in c.nodes if n.topic_id != c.topic_id)
    results.append(_ok("node topic matches chain topic", mismatch == 0))

    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("W1.2 REFINEMENT COMPLETE — Topic Universe pedagogy metadata enriched.")
        return 0
    print("W1.2 REFINEMENT FAILED — fix catalog before W2.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
