"""Manual QA for Writing W7 — generate, evaluate, revise, complete per goal."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
from app.services.language_writing_curriculum.goal_resolver import resolve_writing_goal
from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn_sync
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY, WRITING_GENERATION_KEY
from app.services.language_writing_revision.persistence import (
    WRITING_COACH_PLAN_KEY,
    WRITING_EVALUATION_FACTS_KEY,
    WRITING_REVISION_SESSION_KEY,
)
from app.services.language_writing_runtime.generation_runtime import generate_writing_lesson
from app.services.language_writing_runtime.model_provider import get_writing_model_provider
from app.services.language_writing_runtime.node_selection import default_node_for_goal
from app.services.language_writing_runtime.persistence import build_body_json

_DRAFTS: dict[str, tuple[str, str]] = {
    "travel": (
        "Dear Sir or Madam, I am writing about my delayed flight. Because it was late I missed my connection. "
        "I would like a refund. The announcement was unclear.",
        "Dear Sir or Madam, I am writing to complain about my delayed flight on 12 May. Because the flight was "
        "late, I missed my connection and arrived after midnight. I would like a full refund and a written apology. "
        "The boarding announcement was unclear and the staff were unhelpful when I asked for assistance.",
    ),
    "ielts": (
        "I am interested in this major because it connects to my career goals.",
        "I am interested in studying computer science because it connects directly to my career goals in software "
        "engineering. During school I completed programming projects and internships that strengthened my analytical "
        "skills. Therefore, this major will help me contribute to technology solutions in my community.",
    ),
    "business": (
        "Dear team, I would like to schedule a meeting to discuss the agenda.",
        "Dear team, I would like to schedule a meeting next Tuesday to discuss the quarterly agenda and budget "
        "priorities. Could you please confirm your available times by Friday? I will circulate a draft agenda in advance.",
    ),
}


def _separation_checks(body: dict) -> list[tuple[str, bool, str]]:
    facts = body.get(WRITING_EVALUATION_FACTS_KEY) or {}
    coach = body.get(WRITING_COACH_PLAN_KEY) or {}
    facts_text = json.dumps(facts).lower()
    coach_text = json.dumps(coach).lower()
    checks: list[tuple[str, bool, str]] = []
    checks.append(
        (
            "Evaluator facts have no coaching copy",
            "encouragement" not in facts_text and "revision_mission" not in facts_text,
            "writing_evaluation_facts",
        )
    )
    checks.append(
        (
            "Coach plan has no dimension scores",
            "grammar_result" not in coach_text and "overall_readiness" not in coach_text,
            WRITING_COACH_PLAN_KEY,
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
    print(f"Writing W7 Manual QA — goal={goal.value} provider={provider.provider_name}")
    print(f"Node: {chain_id}/{node_id}\n")

    gen = await generate_writing_lesson(
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
    if not gen.success or gen.canonical_lesson is None or gen.blueprint is None:
        print("Generation FAILED")
        if gen.error:
            print(json.dumps(gen.error.to_dict(), indent=2))
        return 1

    body = build_body_json(
        blueprint=gen.blueprint,
        canonical=gen.canonical_lesson,
        audit=gen.audit,
        model_name=provider.model_name,
        provider_name=provider.provider_name,
    )
    blueprint_hash = (body.get(WRITING_BLUEPRINT_KEY) or {}).get("blueprint_hash", "")
    generation_hash = (body.get(WRITING_GENERATION_KEY) or {}).get("generation_hash", "")

    draft1, draft2 = _DRAFTS.get(goal.value, _DRAFTS["travel"])
    content_item_id = 9000 + hash(goal.value) % 1000

    r1, body = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=content_item_id,
        draft_text=draft1,
        body_json=body,
    )
    r2, body = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=content_item_id,
        draft_text=draft2,
        body_json=body,
    )

    checks: list[tuple[str, bool, str]] = [
        ("First evaluation succeeds", r1.success, f"revision={r1.revision_number}"),
        ("Coach encouragement present", bool(r1.revision_plan.encouragement.strip()), r1.revision_plan.encouragement[:40]),
        ("Second evaluation succeeds", r2.success, f"revision={r2.revision_number}"),
        ("Comparison on second turn", r2.comparison is not None, "comparison object"),
        (
            "Structured comparison buckets",
            r2.comparison is not None
            and hasattr(r2.comparison, "improved")
            and hasattr(r2.comparison, "unchanged")
            and hasattr(r2.comparison, "regressed"),
            "improved/unchanged/regressed",
        ),
        (
            "Blueprint hash preserved",
            (body.get(WRITING_BLUEPRINT_KEY) or {}).get("blueprint_hash") == blueprint_hash,
            blueprint_hash[:16],
        ),
        (
            "Generation hash preserved",
            (body.get(WRITING_GENERATION_KEY) or {}).get("generation_hash") == generation_hash,
            generation_hash[:16],
        ),
        (
            "Revision session tracks drafts",
            len((body.get(WRITING_REVISION_SESSION_KEY) or {}).get("drafts") or []) >= 2,
            "drafts>=2",
        ),
        (
            "Completion uses criteria (not revision count)",
            "criteria" in json.dumps((body.get("writing_completion") or {})).lower()
            or "word" in json.dumps((body.get("writing_completion") or {})).lower(),
            "writing_completion",
        ),
    ]
    checks.extend(_separation_checks(body))

    all_ok = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status} — {detail}")
        all_ok = all_ok and passed

    print()
    if all_ok:
        print("QA PASSED - evaluate -> revise -> compare flow OK for this goal.")
        return 0
    print("QA FAILED — review W7 evaluation/revision output.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual QA for Writing W7 evaluation runtime")
    parser.add_argument("--goal", default="travel", help="travel | ielts | business")
    parser.add_argument("--provider", default="mock", help="claude | mock (default mock)")
    args = parser.parse_args()
    return asyncio.run(_run(args.goal, args.provider))


if __name__ == "__main__":
    raise SystemExit(main())
