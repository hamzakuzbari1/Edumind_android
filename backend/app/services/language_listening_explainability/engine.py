"""Explainability engine orchestration — read-only (Phase 3.4 / 2.1)."""



from __future__ import annotations



from app.services.language_learning_facts.assembler import assemble_lesson_facts, assemble_progression_facts

from app.services.language_learning_narrative.builder import build_lesson_narrative

from app.services.language_learning_narrative.legacy_adapter import (

    legacy_lesson_explainability,

    legacy_student_summary,

)

from app.services.language_listening_challenge.types import ChallengeState

from app.services.language_listening_confidence.types import ConfidenceState

from app.services.language_listening_explainability.signals import extract_signals

from app.services.language_listening_explainability.facts import build_explainability_facts

from app.services.language_listening_explainability.learning_path import build_learning_path

from app.services.language_listening_explainability.teacher_summary import build_teacher_summary

from app.services.language_listening_explainability.telemetry import measure_explainability

from app.services.language_listening_explainability.types import ExplainabilityResult, ExplainabilityTelemetry





def generate_listening_explainability(

    body_json: dict | None,

    *,

    confidence_state: ConfidenceState | None = None,

    challenge_state: ChallengeState | None = None,

    cefr_level: str = "",

    weak_skills: list[str] | None = None,

    official_level: str | None = None,

    journey_target_level: str | None = None,

    lesson_level: str | None = None,

) -> ExplainabilityResult:

    """Build full explainability from stored lesson metadata and learner state.



    Phase 2.1: facts-first pipeline; legacy prose via Learning Narrative Builder adapters.

    Read-only: never modifies recommendations or learner state.

    """

    signals = extract_signals(body_json, cefr_level=cefr_level, weak_skills=weak_skills)

    level = signals.cefr_level or (confidence_state.level if confidence_state else "B1")



    def _build() -> ExplainabilityResult:

        lesson_facts = assemble_lesson_facts(

            body_json,

            cefr_level=level,

            official_level=official_level,

            journey_target_level=journey_target_level,

            lesson_level=lesson_level,

            weak_skills=weak_skills,

        )

        explain_facts = build_explainability_facts(

            signals,

            confidence_state=confidence_state,

            challenge_state=challenge_state,

            official_level=official_level,

            journey_target_level=journey_target_level,

            lesson_level=lesson_level or level,

        )

        progression = assemble_progression_facts(

            official_level=official_level,

            journey_target_level=journey_target_level,

        )

        narrative = build_lesson_narrative(lesson_facts, explain_facts, progression=progression)

        lesson = legacy_lesson_explainability(narrative, explain_facts)

        learning_path = build_learning_path(confidence_state, level=level)

        teacher = build_teacher_summary(

            signals,

            confidence_state=confidence_state,

            challenge_state=challenge_state,

        )

        student = legacy_student_summary(narrative, explain_facts, confidence_state=confidence_state)

        return ExplainabilityResult(

            lesson=lesson,

            learning_path=learning_path,

            teacher_summary=teacher,

            student_summary=student,

            facts=explain_facts,

            telemetry=ExplainabilityTelemetry(

                generation_time_ms=0.0,

                signals_used=(),

                missing_signals=(),

                coverage_completeness=0.0,

            ),

            cefr_level=level,

        )



    built, telemetry = measure_explainability(_build, signals)

    return ExplainabilityResult(

        lesson=built.lesson,

        learning_path=built.learning_path,

        teacher_summary=built.teacher_summary,

        student_summary=built.student_summary,

        facts=built.facts,

        telemetry=telemetry,

        cefr_level=built.cefr_level,

    )
