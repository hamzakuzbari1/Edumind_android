"""Authoring adapters for the offline canonical grammar workflow."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
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
from app.services.language_grammar_activity_authoring.llm.flags import (
    configured_llm_authoring_provider_id,
    llm_authoring_timeout_seconds,
)
from app.services.language_grammar_activity_authoring.llm.parser import extract_json_object
from app.services.language_grammar_activity_authoring.llm.prompt_builder import build_prompt_bundle
from app.services.language_grammar_activity_authoring.llm.registry import get_default_llm_authoring_registry
from app.services.language_grammar_activity_spec import ActivityDifficulty, ActivityType
from app.services.language_grammar_canonical_authoring.types import (
    CanonicalAuthoringAdapterRequest,
    CanonicalAuthoringAdapterResult,
    SectionedAuthoringUnitResult,
)
from app.services.language_grammar_canonical_authoring.section_prompts import (
    build_sectioned_prompt_bundle,
)


class FixtureCanonicalAuthoringAdapter:
    """Local fixture adapter for tests and dry operator runs. Never calls a network provider."""

    def __init__(self, fixture: dict[str, Any] | str | Path) -> None:
        if isinstance(fixture, dict):
            self.fixture = dict(fixture)
        else:
            self.fixture = json.loads(Path(fixture).read_text(encoding="utf-8"))

    def generate(self, request: CanonicalAuthoringAdapterRequest) -> CanonicalAuthoringAdapterResult:
        raw_response = self.fixture.get("raw_response_text")
        if raw_response is None and "student_content" in self.fixture:
            raw_response = json.dumps(
                {
                    "student_content": self.fixture.get("student_content"),
                    "server_teaching_metadata": self.fixture.get("server_teaching_metadata"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        return CanonicalAuthoringAdapterResult(
            success=bool(self.fixture.get("success", True)),
            student_content_json=self.fixture.get("student_content"),
            server_teaching_metadata_json=self.fixture.get("server_teaching_metadata"),
            raw_response_text=raw_response,
            provider_id=str(self.fixture.get("provider_id") or "fixture"),
            authoring_model=str(self.fixture.get("authoring_model") or "fixture"),
            schema_version=str(self.fixture.get("schema_version") or request.schema_version),
            prompt_version=str(self.fixture.get("prompt_version") or request.prompt_version),
            catalog_version=str(self.fixture.get("catalog_version") or request.catalog_version),
            stop_reason=self.fixture.get("stop_reason"),
            input_tokens=self.fixture.get("input_tokens"),
            output_tokens=self.fixture.get("output_tokens"),
            raw_artifact_ref=self.fixture.get("raw_artifact_ref"),
            diagnostics_json=dict(self.fixture.get("diagnostics_json") or {}),
            generated_at=datetime.now(timezone.utc),
        )


class ExistingLLMCanonicalAuthoringAdapter:
    """Adapter around the current grammar LLM authoring provider registry.

    This is intentionally not used by tests. It returns raw provider text so the
    offline workflow owns parser/validator and persistence boundaries.
    """

    def __init__(self, *, provider_id: str | None = None) -> None:
        self.provider_id = (provider_id or configured_llm_authoring_provider_id()).strip().lower()

    def generate(self, request: CanonicalAuthoringAdapterRequest) -> CanonicalAuthoringAdapterResult:
        registry = get_default_llm_authoring_registry()
        provider = registry.get(self.provider_id)
        provider_id = str(getattr(provider, "provider_id", self.provider_id))
        provider_version = str(getattr(provider, "provider_version", "1.0.0") or "1.0.0")
        authoring_request = _build_authoring_request(request)
        prompts = build_prompt_bundle(
            authoring_request,
            provider_id=provider_id,
            provider_version=provider_version,
        )
        raw = provider.generate_json(prompts, timeout_seconds=llm_authoring_timeout_seconds())
        settings = get_settings()
        model = settings.CLAUDE_MODEL if provider_id == "claude" else provider_id
        return CanonicalAuthoringAdapterResult(
            success=True,
            raw_response_text=raw,
            provider_id=provider_id,
            authoring_model=model,
            schema_version=request.schema_version,
            prompt_version=prompts.prompt_version,
            catalog_version=request.catalog_version,
            stop_reason="unknown",
            generated_at=datetime.now(timezone.utc),
        )


class FixtureSectionedCanonicalAuthoringAdapter:
    """Fixture-backed sectioned adapter. Never calls a network provider."""

    def __init__(self, fixture: dict[str, Any] | str | Path) -> None:
        self.calls: list[str] = []
        if isinstance(fixture, dict):
            self.fixture = dict(fixture)
        else:
            self.fixture = json.loads(Path(fixture).read_text(encoding="utf-8"))

    def generate_blueprint(self, request: CanonicalAuthoringAdapterRequest) -> SectionedAuthoringUnitResult:
        self.calls.append("blueprint")
        return self._result_for("blueprint", request)

    def generate_unit(
        self,
        unit_key: str,
        blueprint: dict[str, Any],
        accepted_prior_units: dict[str, dict[str, Any]],
        request: CanonicalAuthoringAdapterRequest,
    ) -> SectionedAuthoringUnitResult:
        self.calls.append(unit_key)
        return self._result_for(unit_key, request)

    def _result_for(self, unit_key: str, request: CanonicalAuthoringAdapterRequest) -> SectionedAuthoringUnitResult:
        units = self.fixture.get("units") if isinstance(self.fixture.get("units"), dict) else self.fixture
        item = dict(units.get(unit_key) or {})
        return SectionedAuthoringUnitResult(
            success=bool(item.get("success", True)),
            structured_payload=item.get("blueprint") or item.get("public_payload") or item.get("structured_payload"),
            private_metadata_json=item.get("private_metadata"),
            raw_response_text=item.get("raw_response_text"),
            provider_id=str(item.get("provider_id") or "fixture"),
            authoring_model=str(item.get("authoring_model") or "fixture"),
            prompt_version=str(item.get("prompt_version") or f"sectioned_fixture:{unit_key}"),
            stop_reason=item.get("stop_reason"),
            input_tokens=item.get("input_tokens"),
            output_tokens=item.get("output_tokens"),
            raw_artifact_ref=item.get("raw_artifact_ref"),
            diagnostics_json=dict(item.get("diagnostics_json") or {}),
            generated_at=datetime.now(timezone.utc),
        )


class ExistingLLMSectionedCanonicalAuthoringAdapter:
    """Sectioned adapter around the configured Claude authoring provider.

    Outbound calls require explicit construction with allow_outbound=True. This
    keeps ordinary CLI usage and tests from calling Claude accidentally.
    """

    def __init__(
        self,
        *,
        allow_outbound: bool = False,
        max_calls: int = 6,
        provider_id: str | None = None,
        json_result_generator: Any | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.allow_outbound = bool(allow_outbound)
        self.max_calls = int(max_calls)
        self.call_count = 0
        self.provider_id = (provider_id or configured_llm_authoring_provider_id()).strip().lower()
        self._json_result_generator = json_result_generator
        self._timeout_seconds = timeout_seconds

    def generate_blueprint(self, request: CanonicalAuthoringAdapterRequest) -> SectionedAuthoringUnitResult:
        return self._generate("blueprint", request=request, blueprint=None, accepted_prior_units={})

    def generate_unit(
        self,
        unit_key: str,
        blueprint: dict[str, Any],
        accepted_prior_units: dict[str, dict[str, Any]],
        request: CanonicalAuthoringAdapterRequest,
    ) -> SectionedAuthoringUnitResult:
        return self._generate(
            unit_key,
            request=request,
            blueprint=blueprint,
            accepted_prior_units=accepted_prior_units,
        )

    def _generate(
        self,
        unit_key: str,
        *,
        request: CanonicalAuthoringAdapterRequest,
        blueprint: dict[str, Any] | None,
        accepted_prior_units: dict[str, dict[str, Any]],
    ) -> SectionedAuthoringUnitResult:
        model = _configured_authoring_model(self.provider_id)
        if not self.allow_outbound:
            return SectionedAuthoringUnitResult(
                success=False,
                provider_id=self.provider_id,
                authoring_model=model,
                diagnostics_json={
                    "code": "outbound_not_confirmed",
                    "message": "Sectioned real-provider authoring requires explicit outbound confirmation",
                },
            )
        if self.provider_id != "claude":
            return SectionedAuthoringUnitResult(
                success=False,
                provider_id=self.provider_id,
                authoring_model=model,
                diagnostics_json={
                    "code": "unsupported_sectioned_provider",
                    "message": "Sectioned canonical authoring currently supports the configured Claude provider only",
                },
            )
        if self.call_count >= self.max_calls:
            return SectionedAuthoringUnitResult(
                success=False,
                provider_id=self.provider_id,
                authoring_model=model,
                diagnostics_json={
                    "code": "sectioned_call_limit_exceeded",
                    "message": f"Sectioned authoring call limit exceeded: {self.max_calls}",
                },
            )

        prompts = build_sectioned_prompt_bundle(
            unit_key=unit_key,
            request=request,
            blueprint=blueprint,
            accepted_prior_units=accepted_prior_units,
        )
        self.call_count += 1
        try:
            if self._json_result_generator is None:
                from app.services.claude_service import generate_claude_json_result_sync

                generator = generate_claude_json_result_sync
            else:
                generator = self._json_result_generator

            result = generator(
                prompts.user_prompt,
                system=prompts.system_prompt,
                temperature=0.2,
                max_output_tokens=prompts.max_tokens,
                timeout=self._timeout_seconds if self._timeout_seconds is not None else llm_authoring_timeout_seconds(),
            )
        except Exception as exc:  # noqa: BLE001
            return SectionedAuthoringUnitResult(
                success=False,
                raw_response_text=None,
                provider_id=self.provider_id,
                authoring_model=model,
                prompt_version=prompts.prompt_version,
                diagnostics_json={
                    "code": "provider_failure",
                    "message": str(exc)[:300],
                    "unit_key": unit_key,
                    "parse_stage": "provider_call",
                },
                generated_at=datetime.now(timezone.utc),
            )

        stop_reason = result.stop_reason
        truncated = stop_reason == "max_tokens"
        diagnostics_base = {
            "unit_key": unit_key,
            "provider": self.provider_id,
            "model": result.model or model,
            "stop_reason": stop_reason,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "truncated": truncated,
            "prompt_version": prompts.prompt_version,
        }
        if stop_reason != "end_turn":
            return SectionedAuthoringUnitResult(
                success=False,
                raw_response_text=result.text,
                provider_id=self.provider_id,
                authoring_model=result.model or model,
                prompt_version=prompts.prompt_version,
                stop_reason=stop_reason,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                truncated=truncated,
                json_parse_passed=False,
                diagnostics_json={
                    **diagnostics_base,
                    "code": "provider_incomplete_stop",
                    "message": "Claude did not finish with end_turn",
                    "json_parse_passed": False,
                    "parse_stage": "provider_stop",
                },
                generated_at=datetime.now(timezone.utc),
            )

        try:
            parsed = extract_json_object(result.text)
        except Exception as exc:  # noqa: BLE001
            return SectionedAuthoringUnitResult(
                success=False,
                raw_response_text=result.text,
                provider_id=self.provider_id,
                authoring_model=result.model or model,
                prompt_version=prompts.prompt_version,
                stop_reason=stop_reason,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                truncated=truncated,
                json_parse_passed=False,
                diagnostics_json={
                    **diagnostics_base,
                    "code": str(getattr(exc, "code", "invalid_json")),
                    "message": str(exc)[:300],
                    "json_parse_passed": False,
                    "parse_stage": "json_extract_parse",
                },
                generated_at=datetime.now(timezone.utc),
            )

        structured_payload, private_metadata, schema_error = _sectioned_payload_from_parsed(unit_key, parsed)
        if schema_error:
            return SectionedAuthoringUnitResult(
                success=False,
                raw_response_text=result.text,
                provider_id=self.provider_id,
                authoring_model=result.model or model,
                prompt_version=prompts.prompt_version,
                stop_reason=stop_reason,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                truncated=truncated,
                json_parse_passed=True,
                diagnostics_json={
                    **diagnostics_base,
                    "code": schema_error,
                    "message": "Claude returned the wrong sectioned unit envelope",
                    "json_parse_passed": True,
                    "parse_stage": "sectioned_envelope",
                    "top_level_keys": sorted(parsed.keys()),
                },
                generated_at=datetime.now(timezone.utc),
            )

        return SectionedAuthoringUnitResult(
            success=True,
            structured_payload=structured_payload,
            private_metadata_json=private_metadata,
            raw_response_text=result.text,
            provider_id=self.provider_id,
            authoring_model=result.model or model,
            prompt_version=prompts.prompt_version,
            stop_reason=stop_reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            truncated=truncated,
            json_parse_passed=True,
            diagnostics_json={
                **diagnostics_base,
                "status": "parsed",
                "json_parse_passed": True,
                "parse_stage": "sectioned_payload_ready",
                "top_level_keys": sorted(parsed.keys()),
            },
            generated_at=datetime.now(timezone.utc),
        )


def _sectioned_payload_from_parsed(
    unit_key: str,
    parsed: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    if unit_key == "blueprint":
        payload = parsed.get("blueprint") if isinstance(parsed.get("blueprint"), dict) else parsed
        if not isinstance(payload, dict):
            return None, None, "invalid_blueprint_envelope"
        return dict(payload), None, ""
    public = parsed.get("public_payload")
    private = parsed.get("private_metadata")
    if not isinstance(public, dict):
        return None, None, "missing_public_payload"
    if private is not None and not isinstance(private, dict):
        return None, None, "invalid_private_metadata"
    return dict(public), dict(private or {}), ""


def _configured_authoring_model(provider_id: str) -> str:
    if provider_id != "claude":
        return provider_id
    try:
        return get_settings().CLAUDE_MODEL
    except Exception:  # noqa: BLE001
        return "claude"


def _build_authoring_request(request: CanonicalAuthoringAdapterRequest) -> AuthoringRequest:
    objective = "; ".join(str(item) for item in request.grammar_profile.get("learning_objectives") or [])
    if not objective:
        objective = f"Author a canonical grammar lesson for {request.display_name}."
    ctx = AuthoringContext(
        grammar_targets=(request.grammar_id,),
        student_cefr=request.cefr_level,
        learning_objective=objective,
        teacher_persona=TeacherPersona(),
        student_profile=StudentProfile(
            student_id=0,
            language_id=0,
            overall_cefr=request.cefr_level,
            locale=request.locale,
            extras={"synthetic": "true"},
        ),
        lesson_context=LessonContext(
            lesson_id=f"canonical:{request.grammar_id}:{request.cefr_level}:{request.locale}",
            step_id="canonical_lesson",
        ),
        activity_type=ActivityType.free_text.value,
        localization=request.locale,
        difficulty=ActivityDifficulty.guided,
        adaptive=AdaptiveAuthoringContext(learning_snapshot=empty_learning_snapshot()),
        versions=AuthoringVersionBundle(
            catalog_version=request.catalog_version,
            grammar_schema_version=1,
            blueprint_version=request.methodology_version,
            activity_schema_version=1,
            planner_version="offline_canonical_authoring",
        ),
        extras={
            "grammar_profile_json": json.dumps(
                request.grammar_profile,
                ensure_ascii=True,
                sort_keys=True,
            ),
            "learner_signals_json": json.dumps(
                request.learner_signals,
                ensure_ascii=True,
                sort_keys=True,
            ),
        },
    )
    return AuthoringRequest(
        context=ctx,
        request_id=f"offline:{request.grammar_id}:{request.cefr_level}:{request.locale}",
    )
