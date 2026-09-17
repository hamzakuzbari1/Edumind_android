"""Phase 5.2.2 local Claude authoring forensics.

This script is verification-only. It captures raw provider metadata and parser /
validator boundaries for the two approved grammar targets without changing the
student API or production logging.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from app.services.claude_service import generate_claude_json_result
from app.services.language_grammar_activity_authoring import (
    AdaptiveAuthoringContext,
    AuthoringContext,
    AuthoringRequest,
    AuthoringVersionBundle,
    LessonContext,
    StudentProfile,
    TeacherPersona,
    empty_learning_snapshot,
)
from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMInvalidJSONError,
    LLMSchemaError,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    METHODOLOGY_SECTIONS,
    normalize_canonical_lesson_output,
)
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    _validate_arabic_first_teaching_model,
    _validate_metadata_links,
    _validate_practice_progression,
    _validate_section_limits,
    _validate_tasks,
    _walk_student_keys,
    detect_unsupported_grammar,
    validate_canonical_lesson_output,
)
from app.services.language_grammar_activity_authoring.llm.parser import (
    extract_json_object,
    parse_activity_specification_json,
)
from app.services.language_grammar_activity_authoring.llm.prompt_builder import (
    build_prompt_bundle,
)
from app.services.language_grammar_activity_spec import ActivityType
from app.services.language_grammar_pipeline.generate import lesson_dict_from_generation
from app.services.language_grammar_pipeline.lesson_package_fallback import (
    ensure_lesson_package_on_specification,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile
from app.services.language_grammar_pipeline.types import (
    PipelineObservability,
    PipelineOutcome,
    PipelineStatus,
    WriteGate,
)


TARGETS = {
    "present_perfect_b1": ("gram_present_perfect", "B1"),
    "third_conditional_b2": ("gram_third_conditional", "B2"),
}
OUT_DIR = Path("runtime-verification/grammar-phase-522")


def _safe_value(value: Any, *, limit: int = 220) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def _path_from_message(message: str) -> str | None:
    candidates = (
        r"(student_content(?:\.[A-Za-z0-9_]+|\[[0-9]+\])+)",
        r"([A-Za-z_]+(?:\.[A-Za-z0-9_]+|\[[0-9]+\])+)",
        r"\b([A-Za-z_]+)\s+required",
    )
    for pattern in candidates:
        match = re.search(pattern, message)
        if match:
            path = match.group(1)
            return path if path.startswith("student_content") else f"student_content.{path}"
    return None


def _lookup_path(root: Any, path: str | None) -> Any:
    if not path:
        return None
    current = root
    raw = path.removeprefix("student_content.")
    raw = raw.removeprefix("server_teaching_metadata.")
    for part in re.split(r"\.", raw):
        if not part:
            continue
        match = re.match(r"([A-Za-z0-9_]+)(?:\[([0-9]+)\])?", part)
        if not match:
            return None
        key = match.group(1)
        index = match.group(2)
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        if index is not None:
            if isinstance(current, list) and int(index) < len(current):
                current = current[int(index)]
            else:
                return None
    return current


def _error_record(stage: str, exc: BaseException, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    code = getattr(exc, "code", type(exc).__name__)
    message = getattr(exc, "message", str(exc))
    path = _path_from_message(str(message))
    root = raw.get("student_content") if raw and path and path.startswith("student_content") else raw
    return {
        "validator": stage,
        "code": code,
        "reason": str(message),
        "path": path,
        "rejected_value": _safe_value(_lookup_path(root, path)) if root is not None else None,
    }


def _request_for(target: str, cefr: str) -> AuthoringRequest:
    profile = _grammar_authoring_profile((target,))
    ctx = AuthoringContext(
        grammar_targets=(target,),
        student_cefr=cefr,
        learning_objective=f"Practice {target}",
        teacher_persona=TeacherPersona(),
        student_profile=StudentProfile(
            student_id=999001,
            language_id=1,
            overall_cefr=cefr,
            locale="ar",
        ),
        lesson_context=LessonContext(lesson_id=f"phase_522_{target}", step_id="practice"),
        activity_type=ActivityType.voice_recording.value,
        localization="ar",
        adaptive=AdaptiveAuthoringContext(learning_snapshot=empty_learning_snapshot()),
        versions=AuthoringVersionBundle(
            catalog_version="1.0.0",
            grammar_schema_version=1,
            blueprint_version="1.0.0",
            activity_schema_version=1,
            planner_version="1.0.0",
        ),
        extras={
            "grammar_profile_json": json.dumps(profile, ensure_ascii=True, sort_keys=True)
        },
    )
    return AuthoringRequest(context=ctx, request_id=f"phase_522_{target}")


def _run_boundary(
    name: str,
    func: Callable[[], Any],
    *,
    raw: dict[str, Any] | None,
    errors: list[dict[str, Any]],
) -> tuple[bool, Any]:
    try:
        return True, func()
    except Exception as exc:  # noqa: BLE001 - diagnostics need exact boundary
        errors.append(_error_record(name, exc, raw))
        return False, None


def _diagnose_raw(raw_text: str, request: AuthoringRequest) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    raw: dict[str, Any] | None = None
    extracted_ok, extracted_value = _run_boundary(
        "json_extraction",
        lambda: extract_json_object(raw_text),
        raw=None,
        errors=errors,
    )
    parsed_ok = False
    if extracted_ok and isinstance(extracted_value, dict):
        parsed_ok = True
        raw = extracted_value

    top_keys = sorted(raw.keys()) if isinstance(raw, dict) else []
    normalized_ok = False
    structural_ok = False
    projected_status = None
    projection_stop = None

    if raw is not None:
        student = raw.get("student_content") if isinstance(raw.get("student_content"), dict) else {}
        metadata = raw.get("server_teaching_metadata") if isinstance(raw.get("server_teaching_metadata"), dict) else {}
        support = tuple(_grammar_authoring_profile(request.context.grammar_targets).get("support_grammar_targets") or ())

        _run_boundary("top_level_student_content", lambda: raw["student_content"], raw=raw, errors=errors)
        _run_boundary("top_level_server_teaching_metadata", lambda: raw["server_teaching_metadata"], raw=raw, errors=errors)
        _run_boundary(
            "methodology_sections",
            lambda: (_ for _ in ()).throw(
                LLMSchemaError(
                    "missing_methodology_sections",
                    "Missing methodology sections: "
                    + ", ".join(section for section in METHODOLOGY_SECTIONS if section not in student),
                )
            )
            if any(section not in student for section in METHODOLOGY_SECTIONS)
            else True,
            raw=raw,
            errors=errors,
        )
        _run_boundary("student_server_key_exposure", lambda: _walk_student_keys(student), raw=raw, errors=errors)
        _run_boundary(
            "section_limits",
            lambda: _validate_section_limits(student, cefr_level=request.context.student_cefr),
            raw=raw,
            errors=errors,
        )
        _run_boundary(
            "arabic_first_teaching_model",
            lambda: _validate_arabic_first_teaching_model(
                student,
                cefr_level=request.context.student_cefr,
                allowed_targets=request.context.grammar_targets,
            ),
            raw=raw,
            errors=errors,
        )
        _run_boundary("practice_progression", lambda: _validate_practice_progression(student), raw=raw, errors=errors)
        _run_boundary("task_payloads", lambda: _validate_tasks(student), raw=raw, errors=errors)
        normalized_ok, canonical = _run_boundary(
            "schema_normalization",
            lambda: normalize_canonical_lesson_output(raw),
            raw=raw,
            errors=errors,
        )
        if canonical is not None:
            _run_boundary(
                "metadata_links",
                lambda: _validate_metadata_links(canonical.student_content, canonical.server_teaching_metadata),
                raw=raw,
                errors=errors,
            )
            _run_boundary(
                "grammar_target_fidelity",
                lambda: (_ for _ in ()).throw(
                    LLMSchemaError(
                        "unsupported_grammar_detected",
                        "Lesson introduces grammar outside provided targets: "
                        + ", ".join(
                            detect_unsupported_grammar(
                                json.dumps(canonical.student_content, ensure_ascii=True, sort_keys=True),
                                allowed_targets=tuple(dict.fromkeys([*request.context.grammar_targets, *support])),
                            )
                        ),
                    )
                )
                if detect_unsupported_grammar(
                    json.dumps(canonical.student_content, ensure_ascii=True, sort_keys=True),
                    allowed_targets=tuple(dict.fromkeys([*request.context.grammar_targets, *support])),
                )
                else True,
                raw=raw,
                errors=errors,
            )
        structural_ok, spec = _run_boundary(
            "structural_parser",
            lambda: parse_activity_specification_json(raw_text, request, provider_id="claude"),
            raw=raw,
            errors=errors,
        )
        if spec is not None:
            try:
                spec = ensure_lesson_package_on_specification(
                    spec,
                    blueprint=None,
                    grammar_target=request.context.grammar_targets[0],
                )
                lesson = lesson_dict_from_generation(
                    PipelineOutcome(
                        status=PipelineStatus.completed,
                        observability=PipelineObservability(pipeline_id=f"phase_522_{request.context.grammar_targets[0]}"),
                        write_gate=WriteGate(),
                        grammar_targets=request.context.grammar_targets,
                        specification=spec,
                    )
                )
                projected_status = {
                    "generation_mode": lesson.get("generation_mode"),
                    "authoring_status": lesson.get("authoring_status"),
                    "section_count": len((lesson.get("student_content") or {}).keys()),
                    "private_projection": not any(
                        term in json.dumps(lesson, ensure_ascii=False)
                        for term in (
                            "server_teaching_metadata",
                            "expected_answer",
                            "sample_answer",
                            "feedback_reasoning",
                            "validation_metadata",
                        )
                    ),
                }
            except Exception as exc:  # noqa: BLE001
                projection_stop = _error_record("canonical_projection", exc, raw)

    return {
        "json_extraction_result": "passed" if extracted_ok else "failed",
        "json_parsing_result": "passed" if raw is not None else "failed",
        "top_level_keys": top_keys,
        "schema_normalization_result": "passed" if normalized_ok else "failed",
        "structural_parser_result": "passed" if structural_ok else "failed",
        "validation_errors": errors,
        "first_failing_boundary": errors[0] if errors else None,
        "canonical_projection": projected_status,
        "canonical_projection_stop": projection_stop,
    }


async def _run_target(name: str, target: str, cefr: str) -> dict[str, Any]:
    request = _request_for(target, cefr)
    prompts = build_prompt_bundle(request, provider_id="claude", provider_version="1.0.0")
    system = f"{prompts.system_prompt}\n\n{prompts.developer_prompt}".strip()
    raw_path = OUT_DIR / f"{name}_raw.txt"
    report_path = OUT_DIR / f"{name}_diagnostic.json"
    try:
        result = await generate_claude_json_result(
            prompts.user_prompt,
            system=system,
            temperature=0.3,
            max_output_tokens=8000,
            timeout=90,
        )
        raw_path.write_text(result.text, encoding="utf-8")
        provider = {
            "provider_request": "completed",
            "provider_result": "completed",
            "model": result.model,
            "stop_reason": result.stop_reason,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "truncated": result.stop_reason == "max_tokens",
            "raw_response_text_length": len(result.text or ""),
        }
        diagnostic = _diagnose_raw(result.text or "", request)
    except Exception as exc:  # noqa: BLE001
        provider = {
            "provider_request": "failed",
            "provider_result": type(exc).__name__,
            "provider_error": str(exc)[:260],
            "stop_reason": None,
            "input_tokens": None,
            "output_tokens": None,
            "truncated": None,
            "raw_response_text_length": 0,
        }
        diagnostic = {}

    report = {
        "target": target,
        "cefr": cefr,
        "provider": provider,
        **diagnostic,
        "raw_artifact": str(raw_path),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**report, "report_artifact": str(report_path)}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        action="append",
        choices=sorted(TARGETS),
        required=True,
        help="Approved target key. Pass once or twice.",
    )
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for key in args.target:
        target, cefr = TARGETS[key]
        reports.append(await _run_target(key, target, cefr))
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
