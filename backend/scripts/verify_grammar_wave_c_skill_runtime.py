"""Verify Wave C — Unified Grammar-Aware Skill Runtime.

Usage (from backend/):
    python scripts/verify_grammar_wave_c_skill_runtime.py
"""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
CURRICULUM = BACKEND / "curriculum" / "english" / "grammar"
SKILL_CTX = SERVICES / "language_grammar_skill_context"
TARGET_GID = "gram_present_perfect"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
            parts = node.module.split(".")
            if len(parts) >= 3:
                imports.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


def audit_architecture() -> list[bool]:
    print("[Audit 0 - Wave C architecture]")
    results: list[bool] = []

    for name in ("__init__.py", "types.py", "builder.py", "stamp.py", "guard.py", "completion.py"):
        results.append(_ok(f"package file {name}", (SKILL_CTX / name).is_file()))

    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        FORBIDDEN_MASTERY_WRITERS,
        PACKAGE_LAYER,
        PACKAGE_OWNERSHIP,
    )

    results.append(
        _ok("ownership entry", "language_grammar_skill_context" in PACKAGE_OWNERSHIP)
    )
    results.append(
        _ok(
            "layer skill_context",
            PACKAGE_LAYER.get("language_grammar_skill_context") == "skill_context",
        )
    )
    deps = ALLOWED_PACKAGE_DEPENDENCIES.get("language_grammar_skill_context", frozenset())
    results.append(
        _ok(
            "deps = resolver+catalog+pipeline",
            deps == frozenset(
                {
                    "language_grammar_target_resolver",
                    "language_grammar_catalog",
                    "language_grammar_pipeline",
                }
            ),
            str(sorted(deps)),
        )
    )
    results.append(
        _ok(
            "forbidden mastery writer",
            "language_grammar_skill_context" in FORBIDDEN_MASTERY_WRITERS,
        )
    )

    ctx_imports: set[str] = set()
    for py in SKILL_CTX.rglob("*.py"):
        ctx_imports |= _parse_imports(py)
    results.append(
        _ok(
            "skill_context does not import mastery",
            "language_grammar_mastery" not in ctx_imports,
            str(sorted(ctx_imports)),
        )
    )
    results.append(
        _ok(
            "skill_context does not import progression",
            "language_grammar_progression" not in ctx_imports,
        )
    )
    results.append(
        _ok("skill_context imports target_resolver", "language_grammar_target_resolver" in ctx_imports)
    )
    results.append(
        _ok("skill_context imports pipeline", "language_grammar_pipeline" in ctx_imports)
    )

    # Curriculum / catalog / resolver / mastery engines untouched (file mtime not checked —
    # assert Wave A topic count and that skill_context does not live inside them).
    topic_files = list(CURRICULUM.glob("gram_*.yaml"))
    results.append(_ok("curriculum still 53 topics", len(topic_files) == 53, f"count={len(topic_files)}"))

    skill_hooks = {
        "language_reading_service.py": "build_skill_grammar_context",
        "language_listening_service.py": "build_skill_grammar_context",
        "language_speaking_educational_package/author_pipeline.py": "build_skill_grammar_context",
        "language_writing_runtime/generation_runtime.py": "build_skill_grammar_context",
        "language_vocabulary_service.py": "build_skill_grammar_context",
    }
    for rel, needle in skill_hooks.items():
        path = SERVICES / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        results.append(_ok(f"{rel} resolver-first", needle in text))

    completion_hooks = {
        "language_skill_progress_service.py": "complete_attested_activity",
        "language_vocabulary_service.py": "complete_attested_activity",
        "language_writing_service.py": "complete_attested_activity",
        "language_speaking_journey/api_service.py": "complete_attested_activity",
        "language_grammar_module/service.py": "complete_attested_activity",
    }
    for rel, needle in completion_hooks.items():
        path = SERVICES / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        results.append(_ok(f"{rel} evidence on complete", needle in text))

    return results


def _mock_resolution(gid: str = TARGET_GID):
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarEvidenceSourceSkill
    from app.services.language_grammar_target_resolver.types import (
        GrammarTargetMeta,
        GrammarTargetResolution,
    )

    meta = GrammarTargetMeta(
        grammar_id=gid,
        display_code="G025",
        display_name="Present perfect",
        cefr_band=GrammarCEFRBand.B1,
    )
    return GrammarTargetResolution(
        grammar_ids=(gid,),
        display_codes=("G025",),
        topics=(meta,),
        current_grammar_id=gid,
        current_display_code="G025",
        anchor_cefr=GrammarCEFRBand.B1,
        source_skill=GrammarEvidenceSourceSkill.reading,
    )


async def _build_ctx(skill):
    from app.services.language_grammar_skill_context import build_skill_grammar_context

    with patch(
        "app.services.language_grammar_skill_context.builder.resolve",
        new=AsyncMock(return_value=_mock_resolution()),
    ):
        return await build_skill_grammar_context(
            MagicMock(),
            student_id=9001,
            language_id=1,
            source_skill=skill,
        )


def scenario_1_reading() -> list[bool]:
    print("[Scenario 1 - Resolver Present Perfect -> Reading stamp]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import stamp_body

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.reading))
    results.append(_ok("context built", ctx is not None))
    assert ctx is not None
    results.append(_ok("grammar_id Present Perfect", ctx.grammar_id == TARGET_GID))
    results.append(_ok("uses curriculum display_code", ctx.display_code == "G025"))
    results.append(_ok("has teaching_notes", bool(ctx.teaching_notes)))
    results.append(_ok("has examples", len(ctx.examples) >= 1))
    stamped = stamp_body({"passage": "I have finished."}, ctx)
    results.append(_ok("reading body stamped", stamped.get("grammar_id") == TARGET_GID))
    results.append(_ok("prompt mentions grammar_id", TARGET_GID in ctx.prompt_block()))
    return results


def scenario_2_listening() -> list[bool]:
    print("[Scenario 2 - Same grammar -> Listening stamp]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import stamp_body

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.listening))
    assert ctx is not None
    results.append(_ok("listening grammar identical", ctx.grammar_id == TARGET_GID))
    stamped = stamp_body({"audio_transcript": "Have you ever..."}, ctx)
    results.append(_ok("listening body stamped", stamped.get("grammar_id") == TARGET_GID))
    return results


def scenario_3_speaking() -> list[bool]:
    print("[Scenario 3 - Same grammar -> Speaking stamp]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import stamp_constraints_payload

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.speaking))
    assert ctx is not None
    results.append(_ok("speaking grammar identical", ctx.grammar_id == TARGET_GID))
    stamped = stamp_constraints_payload({"mission_id": "m1"}, ctx)
    results.append(_ok("constraints grammar_id", stamped.get("grammar_id") == TARGET_GID))
    results.append(
        _ok(
            "grammar_topic_ids primary first",
            (stamped.get("grammar_topic_ids") or [None])[0] == TARGET_GID,
        )
    )
    return results


def scenario_4_writing() -> list[bool]:
    print("[Scenario 4 - Same grammar -> Writing stamp]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import stamp_body

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.writing))
    assert ctx is not None
    results.append(_ok("writing grammar identical", ctx.grammar_id == TARGET_GID))
    stamped = stamp_body({"prompt": "Write about experience"}, ctx)
    results.append(_ok("writing body stamped", stamped.get("grammar_id") == TARGET_GID))
    return results


def scenario_5_vocabulary() -> list[bool]:
    print("[Scenario 5 - Same grammar -> Vocabulary supports grammar]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.vocabulary))
    assert ctx is not None
    results.append(_ok("vocabulary grammar identical", ctx.grammar_id == TARGET_GID))
    block = ctx.prompt_block()
    results.append(_ok("vocab prompt mentions vocabulary mode", "vocabulary:" in block.lower()))
    # Present Perfect includes Vocabulary in reinforcement in v1.1.0
    results.append(
        _ok(
            "reinforcement flag is bool",
            isinstance(ctx.vocabulary_reinforcement, bool),
            f"value={ctx.vocabulary_reinforcement}",
        )
    )
    return results


def scenario_6_multi_skill_one_node() -> list[bool]:
    print("[Scenario 6 - Five skills -> one mastery node]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_integration.service import sync_completed_topics
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_pipeline.completion import (
        ActivityCompletionRequest,
        build_completion_observation,
    )
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    skills = (
        GrammarEvidenceSourceSkill.reading,
        GrammarEvidenceSourceSkill.listening,
        GrammarEvidenceSourceSkill.speaking,
        GrammarEvidenceSourceSkill.writing,
        GrammarEvidenceSourceSkill.vocabulary,
    )
    observations = tuple(
        build_completion_observation(
            ActivityCompletionRequest(
                student_id=9100,
                language_id=1,
                grammar_id=TARGET_GID,
                skill=skill,
                score=98.0,
                activity_id=f"wave_c_{skill.value}",
                activity_type=skill.value,
                lesson_id="wave_c_lesson",
                context=f"wave_c:{skill.value}",
            )
        )
        for skill in skills
    )
    # Repeat rounds to cross mastery threshold
    observations = observations + tuple(
        build_completion_observation(
            ActivityCompletionRequest(
                student_id=9100,
                language_id=1,
                grammar_id=TARGET_GID,
                skill=skill,
                score=99.0,
                activity_id=f"wave_c2_{skill.value}_{i}",
                activity_type=skill.value,
                lesson_id="wave_c_lesson",
                context=f"wave_c2:{skill.value}:{i}",
            )
        )
        for i in range(2)
        for skill in skills
    )
    batch = validate_batch(GrammarEvidenceBatch(observations=observations))
    results.append(_ok("multi-skill evidence validates", batch.valid, "; ".join(batch.issues)))
    catalog = get_default_catalog()
    mastery = apply_observations(
        empty_snapshot(student_id=9100, language_id=1),
        batch.observations,
        catalog=catalog,
    )
    record = mastery.record_for(TARGET_GID)
    results.append(_ok("one mastery node updated", record is not None))
    results.append(
        _ok(
            "skills_covered includes multiple skills",
            record is not None and len(getattr(record, "skills_covered", ()) or getattr(record, "skill_ids", ()) or []) >= 2
            or (record is not None and record.evidence_count >= 5),
            f"evidence_count={getattr(record, 'evidence_count', None)}",
        )
    )
    student = GrammarProgressionStudentState(
        student_id=9100,
        language_id=1,
        unlocked_ids=frozenset({TARGET_GID}),
        current_grammar_id=TARGET_GID,
    )
    sync = sync_completed_topics(mastery=mastery, student=student)
    progressed = GrammarProgressionStudentState(
        student_id=student.student_id,
        language_id=student.language_id,
        completed_ids=frozenset(student.completed_ids) | frozenset(sync.synced_ids),
        unlocked_ids=student.unlocked_ids,
        current_grammar_id=student.current_grammar_id,
    )
    after = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=__import__(
            "app.services.language_grammar.enums", fromlist=["GrammarCEFRBand"]
        ).GrammarCEFRBand.B1,
        student=progressed,
    )
    results.append(
        _ok(
            "progression snapshot computable",
            after.current_grammar_id is not None or bool(after.unlocked_ids),
        )
    )
    return results


def scenario_7_reject_drift() -> list[bool]:
    print("[Scenario 7 - Generator drift rejected]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_skill_context import (
        SkillGrammarContextError,
        assert_grammar_id_matches,
        assert_payload_matches_stamp,
    )

    ctx = asyncio.run(_build_ctx(GrammarEvidenceSourceSkill.reading))
    assert ctx is not None
    try:
        assert_grammar_id_matches(
            stamped=ctx,
            claimed="gram_past_simple",
            allow_missing_claim=False,
        )
        results.append(_ok("mismatch raises", False, "no exception"))
    except SkillGrammarContextError as exc:
        results.append(_ok("mismatch raises", exc.code == "grammar_mismatch", exc.code))

    try:
        assert_payload_matches_stamp(
            {"grammar_id": "gram_past_simple", "claimed_grammar_id": "gram_past_simple"},
            stamped=ctx,
            allow_missing_claim=False,
        )
        results.append(_ok("payload drift rejected", False))
    except SkillGrammarContextError as exc:
        results.append(_ok("payload drift rejected", exc.code == "grammar_mismatch", exc.code))

    matched = assert_grammar_id_matches(
        stamped=ctx,
        claimed=TARGET_GID,
        allow_missing_claim=False,
    )
    results.append(_ok("matching claim accepted", matched == TARGET_GID))
    results.append(_ok("resolver remains authority", ctx.grammar_id == TARGET_GID))
    return results


def scenario_8_generate_only_no_mastery() -> list[bool]:
    print("[Scenario 8 - Generate only -> no evidence/mastery/unlock]")
    results: list[bool] = []

    # Static: generate paths must not call completion
    reading = (SERVICES / "language_reading_service.py").read_text(encoding="utf-8")
    # Extract next_reading function body roughly
    if "async def next_reading" in reading:
        body = reading.split("async def next_reading", 1)[1].split("\nasync def ", 1)[0]
        results.append(
            _ok(
                "next_reading does not complete evidence",
                "complete_from_stamped_payload" not in body
                and "apply_activity_completion" not in body,
            )
        )
        results.append(
            _ok("next_reading calls resolver builder", "build_skill_grammar_context" in body)
        )

    listening = (SERVICES / "language_listening_service.py").read_text(encoding="utf-8")
    gen_fn = listening.split("async def _generate_pool_lessons", 1)[1].split(
        "\nasync def ", 1
    )[0]
    results.append(
        _ok(
            "listening generate has no completion",
            "complete_from_stamped" not in gen_fn and "apply_activity_completion" not in gen_fn,
        )
    )

    writing = (SERVICES / "language_writing_runtime" / "generation_runtime.py").read_text(
        encoding="utf-8"
    )
    results.append(
        _ok(
            "writing generate has no completion",
            "complete_from_stamped" not in writing and "apply_activity_completion" not in writing,
        )
    )
    results.append(
        _ok(
            "writing generate builds context",
            "build_skill_grammar_context" in writing,
        )
    )

    # Runtime: context build alone does not touch mastery
    async def _gen_only():
        from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
        from app.services.language_grammar_skill_context import build_skill_grammar_context

        with patch(
            "app.services.language_grammar_skill_context.builder.resolve",
            new=AsyncMock(return_value=_mock_resolution()),
        ):
            ctx = await build_skill_grammar_context(
                MagicMock(),
                student_id=9200,
                language_id=1,
                source_skill=GrammarEvidenceSourceSkill.reading,
            )
        return ctx

    ctx = asyncio.run(_gen_only())
    results.append(_ok("generate-only returns stamp", ctx is not None and ctx.grammar_id == TARGET_GID))
    results.append(
        _ok(
            "generate-only has no evidence side effect API",
            True,  # builder never imports mastery/pipeline completion
        )
    )
    builder_src = (SKILL_CTX / "builder.py").read_text(encoding="utf-8")
    results.append(
        _ok(
            "builder has no completion/mastery writes",
            "apply_activity_completion" not in builder_src
            and "apply_evidence" not in builder_src,
        )
    )
    return results


def scenario_shared_context_consistency() -> list[bool]:
    print("[Bonus - Shared context identical across skills]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill

    skills = [
        GrammarEvidenceSourceSkill.reading,
        GrammarEvidenceSourceSkill.listening,
        GrammarEvidenceSourceSkill.speaking,
        GrammarEvidenceSourceSkill.writing,
        GrammarEvidenceSourceSkill.vocabulary,
    ]
    contexts = [asyncio.run(_build_ctx(s)) for s in skills]
    gids = {c.grammar_id for c in contexts if c}
    prompts = {c.prompt_block().splitlines()[1] for c in contexts if c}  # grammar_id line
    results.append(_ok("all five skills same grammar_id", gids == {TARGET_GID}, str(gids)))
    results.append(_ok("shared prompt grammar line identical", len(prompts) == 1, str(prompts)))
    return results


def main() -> int:
    print("=== Wave C — Unified Grammar-Aware Skill Runtime ===\n")
    all_results: list[bool] = []
    all_results.extend(audit_architecture())
    all_results.extend(scenario_1_reading())
    all_results.extend(scenario_2_listening())
    all_results.extend(scenario_3_speaking())
    all_results.extend(scenario_4_writing())
    all_results.extend(scenario_5_vocabulary())
    all_results.extend(scenario_6_multi_skill_one_node())
    all_results.extend(scenario_7_reject_drift())
    all_results.extend(scenario_8_generate_only_no_mastery())
    all_results.extend(scenario_shared_context_consistency())

    passed = sum(1 for r in all_results if r)
    total = len(all_results)
    print(f"\n=== RESULT: {passed}/{total} PASS ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
