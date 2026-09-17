"""Manual QA for Writing W6 — generate one lesson per goal profile."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.goal_resolver import resolve_writing_goal
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY, WRITING_GENERATION_KEY
from app.services.language_writing_runtime.generation_runtime import generate_writing_lesson
from app.services.language_writing_runtime.model_provider import get_writing_model_provider
from app.services.language_writing_runtime.node_selection import default_node_for_goal
from app.services.language_writing_runtime.persistence import build_body_json


def _check_alignment(body: dict, goal: WritingGoal) -> list[tuple[str, bool, str]]:
    blueprint = body.get(WRITING_BLUEPRINT_KEY) or {}
    canonical = body.get("canonical_lesson") or {}
    audit = body.get(WRITING_GENERATION_KEY) or {}
    checks: list[tuple[str, bool, str]] = []

    bp_grammar = (blueprint.get("grammar_targets") or {}).get("primary", "")
    checks.append(
        (
            "Grammar matches Blueprint",
            bp_grammar.replace("_", " ") in (canonical.get("grammar_display") or "").lower()
            or bp_grammar in json.dumps(canonical).lower(),
            bp_grammar,
        )
    )

    bp_vocab = (blueprint.get("vocabulary_targets") or {}).get("primary") or []
    vocab_text = (canonical.get("vocabulary_display") or "").lower()
    checks.append(
        (
            "Vocabulary matches Blueprint",
            any(v.lower() in vocab_text or v.lower() in json.dumps(canonical).lower() for v in bp_vocab[:4]),
            str(bp_vocab[:4]),
        )
    )

    bp_expected = blueprint.get("expected_writing_output", "")
    checks.append(
        (
            "Expected Output matches Blueprint",
            canonical.get("expected_output") == bp_expected,
            bp_expected,
        )
    )

    bp_criteria = blueprint.get("success_criteria_labels") or []
    lesson_criteria = canonical.get("success_criteria") or []
    checks.append(
        (
            "Success Criteria matches Blueprint",
            list(lesson_criteria) == list(bp_criteria) or set(lesson_criteria) == set(bp_criteria),
            f"{len(bp_criteria)} blueprint labels",
        )
    )

    checks.append(
        (
            "Blueprint hash preserved",
            bool(blueprint.get("blueprint_hash")) and blueprint.get("blueprint_hash") == canonical.get("blueprint_hash"),
            blueprint.get("blueprint_hash", "")[:16],
        )
    )

    checks.append(
        (
            "Generation audit present",
            bool(audit.get("generation_hash")) and bool(audit.get("model_name")) and bool(audit.get("provider_name")),
            audit.get("provider_name", ""),
        )
    )

    checks.append(
        (
            "Goal profile respected",
            blueprint.get("personal_goal") == goal.value,
            goal.value,
        )
    )

    return checks


async def _run(goal_name: str, provider_name: str | None) -> int:
    goal = resolve_writing_goal(goal_name)
    chain_id, node_id, node = default_node_for_goal(goal)
    if node is None:
        print(f"FAIL — node not found for goal {goal_name}: {chain_id}/{node_id}")
        return 1

    provider = get_writing_model_provider(provider=provider_name)
    print(f"Writing W6 Manual QA — goal={goal.value} provider={provider.provider_name} model={provider.model_name}")
    print(f"Node: {chain_id}/{node_id}\n")

    result = await generate_writing_lesson(
        None,
        language_id=1,
        student_id=0,
        goal=goal,
        official_cefr=OfficialWritingCEFR.B1,
        chain_id=chain_id,
        node_id=node_id,
        provider=provider,
        persist=False,
    )

    if not result.success or result.canonical_lesson is None or result.blueprint is None:
        print("Generation FAILED")
        if result.error:
            print(json.dumps(result.error.to_dict(), indent=2))
        return 1

    body = build_body_json(
        blueprint=result.blueprint,
        canonical=result.canonical_lesson,
        audit=result.audit,
        model_name=provider.model_name,
        provider_name=provider.provider_name,
    )

    print(f"Mission: {result.canonical_lesson.mission_title}")
    print(f"Outcome: {result.outcome.value if result.outcome else 'unknown'}")
    print(f"Generation hash: {result.canonical_lesson.generation_hash[:16]}…")
    print()

    all_ok = True
    for name, passed, detail in _check_alignment(body, goal):
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status} — {detail}")
        all_ok = all_ok and passed

    print()
    if all_ok:
        print("QA PASSED — no educational drift detected for this goal.")
        return 0
    print("QA FAILED — review blueprint vs canonical lesson.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual QA for Writing W6 runtime")
    parser.add_argument("--goal", default="travel", help="travel | ielts | business")
    parser.add_argument("--provider", default=None, help="claude | mock (default from settings)")
    args = parser.parse_args()
    return asyncio.run(_run(args.goal, args.provider))


if __name__ == "__main__":
    raise SystemExit(main())
