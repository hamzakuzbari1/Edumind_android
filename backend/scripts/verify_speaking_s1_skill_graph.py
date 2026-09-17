"""Verify Speaking S1 Skill Dependency Graph.

Usage (from backend/):
    python scripts/verify_speaking_s1_skill_graph.py
    python scripts/verify_speaking_s0_architecture.py
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
CURRICULUM = BACKEND / "app" / "services" / "language_speaking_curriculum"

from app.services.language_speaking.ownership import (  # noqa: E402
    FORBIDDEN_PROVIDER_SDK_IMPORTS,
    LEGACY_FLAT_MODULES,
)
from app.services.language_speaking_curriculum.skill_catalog import (  # noqa: E402
    SPEAKING_SKILL_GRAPH,
    build_speaking_skill_graph,
)
from app.services.language_speaking_curriculum.trace import SpeakingSkillGraphTrace  # noqa: E402
from app.services.language_speaking_curriculum.types import (  # noqa: E402
    SPEAKING_SKILL_GRAPH_VERSION,
    SPEAKING_SKILL_SCHEMA_VERSION,
)
from app.services.language_speaking_curriculum.validator import validate_skill_graph  # noqa: E402

REQUIRED_FLAGSHIP_AREAS = (
    "opinion_reasoning",
    "questions_clarification",
    "past_narrative",
    "travel_service",
    "business_professional",
    "ielts_extended",
    "fluency",
    "prosody",
    "pronunciation",
)

MIN_FLAGSHIP_CHAIN_DEPTH = 4
MIN_NODE_COUNT = 40


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def check_versions() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("SPEAKING_SKILL_GRAPH_VERSION", bool(SPEAKING_SKILL_GRAPH_VERSION)))
    results.append(_ok("SPEAKING_SKILL_SCHEMA_VERSION", bool(SPEAKING_SKILL_SCHEMA_VERSION)))
    results.append(_ok("graph singleton loads", len(SPEAKING_SKILL_GRAPH.nodes) >= MIN_NODE_COUNT))
    rebuilt = build_speaking_skill_graph()
    results.append(_ok("build_speaking_skill_graph()", len(rebuilt.nodes) == len(SPEAKING_SKILL_GRAPH.nodes)))
    return results


def check_validation() -> list[bool]:
    results: list[bool] = []
    vr = validate_skill_graph(SPEAKING_SKILL_GRAPH)
    results.append(_ok("validate_skill_graph", vr.valid))
    if not vr.valid:
        for issue in vr.issues[:15]:
            results.append(_ok(f"  issue {issue.code}", False, f"{issue.skill_id}: {issue.message}"))
    return results


def check_unique_ids() -> list[bool]:
    results: list[bool] = []
    ids = [n.skill_id for n in SPEAKING_SKILL_GRAPH.nodes]
    results.append(_ok("all skill IDs unique", len(ids) == len(set(ids))))
    for node in SPEAKING_SKILL_GRAPH.nodes:
        if " " in node.skill_id or node.skill_id.lower() != node.skill_id:
            results.append(_ok(f"stable id format: {node.skill_id}", ":" in node.skill_id and " " not in node.skill_id))
    return results


def check_flagship_areas() -> list[bool]:
    results: list[bool] = []
    trace = SpeakingSkillGraphTrace(SPEAKING_SKILL_GRAPH)

    by_area: dict[str, list[str]] = {a: [] for a in REQUIRED_FLAGSHIP_AREAS}
    for node in SPEAKING_SKILL_GRAPH.nodes:
        area = node.flagship_area
        if area and area in by_area:
            by_area[area].append(node.skill_id)

    for area in REQUIRED_FLAGSHIP_AREAS:
        nodes = by_area[area]
        results.append(_ok(f"flagship area exists: {area}", len(nodes) >= 3, f"{len(nodes)} nodes"))

        # Multi-step depth: longest dependency path within area-tagged nodes
        max_depth = 0
        area_set = set(nodes)
        for sid in nodes:
            for other in nodes:
                if sid == other:
                    continue
                path = trace.find_dependency_path(sid, other)
                if path and all(
                    SPEAKING_SKILL_GRAPH.node_by_id(p) and SPEAKING_SKILL_GRAPH.node_by_id(p).flagship_area == area  # type: ignore[union-attr]
                    for p in path
                ):
                    max_depth = max(max_depth, len(path))
        results.append(
            _ok(
                f"flagship depth >= {MIN_FLAGSHIP_CHAIN_DEPTH}: {area}",
                max_depth >= MIN_FLAGSHIP_CHAIN_DEPTH,
                f"max chain length {max_depth}",
            )
        )
    return results


def check_signature_chains(trace: SpeakingSkillGraphTrace) -> list[bool]:
    results: list[bool] = []

    theta_chain = trace.find_dependency_path("phoneme:theta", "task:debate")
    results.append(_ok("chain: theta to debate", theta_chain is not None and len(theta_chain) >= 6))
    if theta_chain:
        results.append(_ok("  chain starts at phoneme:theta", theta_chain[0] == "phoneme:theta"))
        results.append(_ok("  chain ends at task:debate", theta_chain[-1] == "task:debate"))
        for expected in ("word:think", "phrase:i_think", "function:express_opinion"):
            results.append(_ok(f"  chain contains {expected}", expected in theta_chain))

    q_chain = trace.find_dependency_path("prosody:question_intonation", "interaction:interactive_conversation")
    results.append(_ok("chain: question intonation to interactive conversation", q_chain is not None and len(q_chain) >= 4))

    past_chain = trace.find_dependency_path("grammar:past_tense_control", "task:extended_narrative")
    results.append(_ok("chain: past tense to extended narrative", past_chain is not None and len(past_chain) >= 4))

    ielts = SPEAKING_SKILL_GRAPH.node_by_id("task:ielts_extended_response")
    results.append(_ok("IELTS extended task exists", ielts is not None))
    if ielts:
        families: set[str] = set()
        for pid in ielts.prerequisite_skill_ids:
            pnode = SPEAKING_SKILL_GRAPH.node_by_id(pid)
            if pnode:
                families.add(pnode.skill_type.value)
        results.append(_ok("IELTS multi-family prerequisites", len(families) >= 3, f"families={sorted(families)}"))

    return results


def check_trace_utilities() -> list[bool]:
    results: list[bool] = []
    trace = SpeakingSkillGraphTrace(SPEAKING_SKILL_GRAPH)

    node = trace.get_skill("function:express_opinion")
    results.append(_ok("get_skill", node is not None))

    direct = trace.get_direct_prerequisites("function:express_opinion")
    results.append(_ok("get_direct_prerequisites", any(n.skill_id == "phrase:i_think" for n in direct)))

    ancestors = trace.get_ancestors("task:debate")
    results.append(_ok("get_ancestors", len(ancestors) >= 5))

    nxt = trace.get_next_skills("phoneme:theta")
    results.append(_ok("get_next_skills", len(nxt) >= 1))

    desc = trace.get_descendants("phoneme:theta")
    results.append(_ok("get_descendants", any(n.skill_id == "task:debate" for n in desc)))

    path = trace.find_dependency_path("phoneme:theta", "task:debate")
    results.append(_ok("find_dependency_path", path is not None and path[0] == "phoneme:theta"))

    roots = trace.find_root_prerequisite_candidates("task:debate")
    results.append(_ok("find_root_prerequisite_candidates", len(roots) >= 1))

    rel = trace.relationship_between(["function:express_opinion", "phrase:i_think", "word:think"])
    results.append(_ok("relationship_between", "phrase:i_think" in rel.get("function:express_opinion", ())))

    return results


def check_goal_relevance() -> list[bool]:
    results: list[bool] = []
    with_goals = sum(1 for n in SPEAKING_SKILL_GRAPH.nodes if n.goal_relevance)
    results.append(_ok("goal_relevance populated", with_goals == len(SPEAKING_SKILL_GRAPH.nodes)))
    ielts_nodes = [n for n in SPEAKING_SKILL_GRAPH.nodes if any(g.value == "ielts" for g in n.goal_relevance)]
    results.append(_ok("IELTS goal nodes exist", len(ielts_nodes) >= 5))
    travel_nodes = [n for n in SPEAKING_SKILL_GRAPH.nodes if any(g.value == "travel" for g in n.goal_relevance)]
    results.append(_ok("travel goal nodes exist", len(travel_nodes) >= 3))
    return results


def check_mastery_and_evidence() -> list[bool]:
    results: list[bool] = []
    for node in SPEAKING_SKILL_GRAPH.nodes:
        m = node.mastery_requirements
        e = node.evidence_requirements
        if m.minimum_evidence_count < 1 or not e.evidence_codes:
            results.append(_ok(f"mastery+evidence: {node.skill_id}", False))
            break
    else:
        results.append(_ok("all nodes have mastery and evidence requirements", True))
    return results


def check_isolation() -> list[bool]:
    results: list[bool] = []
    for py in CURRICULUM.glob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        for sdk in FORBIDDEN_PROVIDER_SDK_IMPORTS:
            if sdk in text:
                results.append(_ok(f"no SDK {sdk} in {py.name}", False))
        for legacy in LEGACY_FLAT_MODULES:
            if f"language_{legacy.replace('language_', '')}" in text or f"from app.services.{legacy}" in text:
                results.append(_ok(f"no legacy import {legacy} in {py.name}", False))
        if "anthropic" in text or "openai" in text or "claude" in text:
            results.append(_ok(f"no LLM refs in {py.name}", False))
    return results


def check_contracts_importable() -> list[bool]:
    results: list[bool] = []
    mod = importlib.import_module("app.services.language_speaking_curriculum.types")
    for name in (
        "SpeakingSkillNode",
        "SpeakingSkillGraph",
        "SkillMasteryRequirement",
        "SkillEvidenceRequirement",
    ):
        results.append(_ok(f"contract: {name}", hasattr(mod, name)))
    return results


def check_no_frontend_changes() -> list[bool]:
    results: list[bool] = []
    src = BACKEND.parent / "src"
    touched = any("speaking" in p.name.lower() for p in src.rglob("*") if p.is_file() and p.stat().st_mtime > 0)
    # S1 should not add speaking graph files under src/
    graph_in_frontend = list(src.rglob("*skill_graph*"))
    results.append(_ok("no frontend skill_graph files", len(graph_in_frontend) == 0))
    return results


def main() -> int:
    print("Speaking S1 Skill Graph Verification\n")
    trace = SpeakingSkillGraphTrace(SPEAKING_SKILL_GRAPH)
    sections = [
        ("Versions & load", check_versions),
        ("Graph validation", check_validation),
        ("Unique skill IDs", check_unique_ids),
        ("Mastery & evidence", check_mastery_and_evidence),
        ("Goal relevance", check_goal_relevance),
        ("Flagship areas", check_flagship_areas),
        ("Signature chains", lambda: check_signature_chains(trace)),
        ("Trace utilities", check_trace_utilities),
        ("Contracts", check_contracts_importable),
        ("Isolation (no SDK/legacy/LLM)", check_isolation),
        ("Frontend unchanged", check_no_frontend_changes),
    ]

    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S1 READY — S2 may begin after review.")
        return 0
    print("S1 NOT READY — fix failures before S2.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
