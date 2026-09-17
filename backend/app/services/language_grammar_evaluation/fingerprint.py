"""Deterministic evaluation request fingerprints (V1.8) — replayability."""

from __future__ import annotations

import hashlib
import json

from app.services.language_grammar_evaluation.types import GrammarEvaluationRequest


def fingerprint_evaluation_request(request: GrammarEvaluationRequest) -> str:
    ctx = request.context
    payload = {
        "grammar_targets": list(ctx.grammar_targets),
        "expected_patterns": list(ctx.expected_patterns),
        "student_response": ctx.student_response,
        "lesson_expected_patterns": list(ctx.lesson_package.expected_patterns),
        "lesson_grammar_focus": ctx.lesson_package.grammar_focus,
        "student_id": ctx.student_id,
        "language_id": ctx.language_id,
        "localization": ctx.localization,
        "source_skill": ctx.source_skill,
        "activity_id": ctx.specification.activity_id if ctx.specification else "",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
