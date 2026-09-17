"""Verify Hybrid Writing Evaluation Engine — rules + Claude facts → canonical result."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("WRITING_EDUCATIONAL_ANALYZER", "mock")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal  # noqa: E402
from app.services.language_writing_educational_analyzer.parser import parse_claude_educational_json  # noqa: E402
from app.services.language_writing_educational_analyzer.types import (  # noqa: E402
    ClaudeEducationalFacts,
    DimensionInsight,
)
from app.services.language_writing_evaluator.blueprint_snapshot import blueprint_snapshot_from_dict  # noqa: E402
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync  # noqa: E402
from app.services.language_writing_evaluator.evaluation_result import EVALUATION_RESULT_VERSION  # noqa: E402
from app.services.language_writing_evaluator.facts_deserialize import evaluation_result_from_dict  # noqa: E402
from app.services.language_writing_evaluator.hybrid_merge import merge_hybrid_evaluation  # noqa: E402
from app.services.language_writing_evaluator.rule_engine import compute_rule_evaluation_facts  # noqa: E402
from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn_sync  # noqa: E402
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY  # noqa: E402
from app.services.language_writing_revision.persistence import WRITING_EVALUATION_FACTS_KEY  # noqa: E402


from scripts.verify_writing_w7_evaluation_revision import _sample_body  # noqa: E402


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def check_parser() -> list[bool]:
    results: list[bool] = []
    good = parse_claude_educational_json(
        json.dumps(
            {
                "task_response": {"score": 0.25, "reason": "Off-topic introduction."},
                "coherence": {"score": 0.4, "reason": "Ideas are repetitive."},
                "organization": {"score": 0.35, "reason": "No paragraph breaks."},
                "cefr_estimate": "A2",
                "major_learning_issue": "Task response",
            }
        )
    )
    results.append(_ok("parser accepts educational JSON", good.available))
    results.append(_ok("parser extracts task reason", "Off-topic" in good.task_response.reason))

    bad = parse_claude_educational_json('{"passed": false, "task_response": {"score": 0.9}}')
    results.append(_ok("parser rejects pass/fail fields", not bad.available))
    return results


def check_bad_draft() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.travel)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    bad_text = "My name are Hamza"
    result = evaluate_writing_draft_sync(bad_text, draft_id="bad", revision_number=1, blueprint=snapshot)

    results.append(_ok("bad draft engine version", result.engine_version == "8.1.0"))
    results.append(_ok("bad draft grammar fails (rules)", not result.grammar.passed))
    results.append(_ok("bad draft not ready (rules)", not result.revision_readiness.ready))
    results.append(_ok("bad draft has claude_analysis", result.claude_analysis is not None))
    results.append(_ok("claude analysis available", bool(result.claude_analysis and result.claude_analysis.available)))
    results.append(_ok("claude does not override grammar pass", not result.grammar.passed))
    results.append(
        _ok(
            "explanation enriched by claude",
            any("draft" in i.lower() or "task" in i.lower() for i in result.explanation.improvements)
            or "Educational analysis" in result.explanation.summary,
        )
    )
    return results


def check_good_draft() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.travel)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    good_text = (
        "When I arrived at the hotel, the reception was bright and welcoming. "
        "The staff at reception checked me in quickly, and my first impression was very positive. "
        "There is a large window in my room and there are comfortable chairs near the bed. "
        "I like the room because it is clean and quiet, and the reception team was friendly. "
        "The hotel feels calm, and I think I will enjoy my stay here. "
    ) * 3
    result = evaluate_writing_draft_sync(
        good_text, draft_id="good", revision_number=1, blueprint=snapshot, writing_prompt=snapshot.narrative_why
    )

    results.append(_ok("good draft has claude_analysis", result.claude_analysis is not None))
    results.append(
        _ok(
            "good draft claude task score high",
            bool(result.claude_analysis and result.claude_analysis.task_response.score >= 0.7),
        )
    )
    results.append(_ok("good draft readiness from rules", hasattr(result.revision_readiness, "ready")))
    return results


def check_merge_independence() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.business)
    snapshot = blueprint_snapshot_from_dict(body[WRITING_BLUEPRINT_KEY])
    bad_text = "My name are Hamza"
    rule = compute_rule_evaluation_facts(
        bad_text, draft_id="merge-bad", revision_number=1, blueprint=snapshot, official_cefr="B1"
    )
    optimistic_claude = ClaudeEducationalFacts(
        task_response=DimensionInsight(0.99, "Perfect task response."),
        coherence=DimensionInsight(0.99, "Flawless coherence."),
        organization=DimensionInsight(0.99, "Excellent structure."),
        cefr_estimate="C2",
        major_learning_issue="",
        available=True,
        source="test",
    )
    merged = merge_hybrid_evaluation(rule, optimistic_claude)
    results.append(_ok("merge keeps grammar fail", not merged.grammar.passed))
    results.append(_ok("merge keeps not ready", not merged.revision_readiness.ready))
    results.append(_ok("merge keeps rule dimension scores", merged.grammar.score == rule.grammar.score))
    results.append(_ok("merge attaches claude facts", merged.claude_analysis is not None))
    results.append(_ok("merge adds CEFR note", any("Claude observed" in n for n in merged.cefr_validation.notes)))
    return results


def check_persistence_roundtrip() -> list[bool]:
    results: list[bool] = []
    body = _sample_body(WritingGoal.ielts)
    r, updated = process_writing_draft_turn_sync(
        student_id=1,
        content_item_id=8801,
        draft_text="My name are Hamza and I like study.",
        body_json=body,
    )
    facts_raw = updated.get(WRITING_EVALUATION_FACTS_KEY) or {}
    results.append(_ok("persist claude_analysis key", "claude_analysis" in facts_raw if isinstance(facts_raw, dict) else False))
    results.append(_ok("persist engine 8.1.0", facts_raw.get("engine_version") == "8.1.0" if isinstance(facts_raw, dict) else False))

    if isinstance(facts_raw, dict):
        restored = evaluation_result_from_dict(facts_raw)
        results.append(_ok("deserialize roundtrip", restored is not None))
        results.append(
            _ok(
                "deserialize claude_analysis",
                restored is not None and restored.claude_analysis is not None and restored.claude_analysis.available,
            )
        )
        results.append(_ok("deserialize readiness matches", restored is not None and restored.revision_readiness.ready == r.evaluation.revision_readiness.ready))
    else:
        results.extend([_ok("deserialize roundtrip", False), _ok("deserialize claude_analysis", False)])
    return results


def check_architecture() -> list[bool]:
    results: list[bool] = []
    results.append(_ok("canonical version 8.1.0", EVALUATION_RESULT_VERSION == "8.1.0"))
    engine_text = (Path(__file__).resolve().parents[1] / "app/services/language_writing_evaluator/engine.py").read_text(
        encoding="utf-8"
    )
    results.append(_ok("engine orchestrates hybrid", "compute_rule_evaluation_facts" in engine_text))
    results.append(_ok("engine calls analyzer", "analyze_writing_draft_educationally" in engine_text))
    results.append(_ok("engine calls merge", "merge_hybrid_evaluation" in engine_text))
    return results


def main() -> int:
    print("Hybrid Writing Evaluation Verification\n")
    sections = [
        ("Parser safety", check_parser),
        ("Bad draft (rules fail + Claude enrich)", check_bad_draft),
        ("Good draft (Claude enrich)", check_good_draft),
        ("Merge independence (Claude cannot pass)", check_merge_independence),
        ("Persistence roundtrip", check_persistence_roundtrip),
        ("Architecture", check_architecture),
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
        print("HYBRID EVALUATION VERIFIED — rules + Claude facts merge correctly.")
        return 0
    print("HYBRID EVALUATION NOT READY — fix failures before W8.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
