"""Live Speaking Bridge types — Educational Case continuity into GPT rehearsal + Hume EVI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LIVE_BRIDGE_VERSION = "1.0.0"
SPEAKING_LIVE_BRIDGE_KEY = "speaking_live_bridge"


@dataclass(frozen=True, slots=True)
class SpeakingScenario:
    """Student-facing speaking preparation for THIS Educational Case continuation."""

    scenario_id: str
    package_id: str
    student_role: str
    student_brief: str
    setting: str
    story_title: str
    story_world: str
    characters: tuple[str, ...]
    stakes: str
    decision_point: str
    continuation_hook: str
    must_do: tuple[str, ...]
    vocabulary_focus: tuple[str, ...]
    grammar_focus: tuple[str, ...]
    objectives: tuple[str, ...]
    case_category: str = ""
    case_archetype: str = ""
    stakeholders: tuple[str, ...] = ()
    continuity_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "package_id": self.package_id,
            "student_role": self.student_role,
            "student_brief": self.student_brief,
            "setting": self.setting,
            "story_title": self.story_title,
            "story_world": self.story_world,
            "characters": list(self.characters),
            "stakes": self.stakes,
            "decision_point": self.decision_point,
            "continuation_hook": self.continuation_hook,
            "must_do": list(self.must_do),
            "vocabulary_focus": list(self.vocabulary_focus),
            "grammar_focus": list(self.grammar_focus),
            "objectives": list(self.objectives),
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
            "stakeholders": list(self.stakeholders),
            "continuity_fingerprint": self.continuity_fingerprint,
            "bridge_version": LIVE_BRIDGE_VERSION,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> SpeakingScenario | None:
        if not isinstance(raw, dict) or not raw.get("scenario_id"):
            return None
        return SpeakingScenario(
            scenario_id=str(raw.get("scenario_id") or ""),
            package_id=str(raw.get("package_id") or ""),
            student_role=str(raw.get("student_role") or ""),
            student_brief=str(raw.get("student_brief") or ""),
            setting=str(raw.get("setting") or ""),
            story_title=str(raw.get("story_title") or ""),
            story_world=str(raw.get("story_world") or ""),
            characters=tuple(str(x) for x in (raw.get("characters") or []) if str(x).strip()),
            stakes=str(raw.get("stakes") or ""),
            decision_point=str(raw.get("decision_point") or ""),
            continuation_hook=str(raw.get("continuation_hook") or ""),
            must_do=tuple(str(x) for x in (raw.get("must_do") or []) if str(x).strip()),
            vocabulary_focus=tuple(
                str(x) for x in (raw.get("vocabulary_focus") or []) if str(x).strip()
            ),
            grammar_focus=tuple(
                str(x) for x in (raw.get("grammar_focus") or []) if str(x).strip()
            ),
            objectives=tuple(str(x) for x in (raw.get("objectives") or []) if str(x).strip()),
            case_category=str(raw.get("case_category") or ""),
            case_archetype=str(raw.get("case_archetype") or ""),
            stakeholders=tuple(
                str(x) for x in (raw.get("stakeholders") or []) if str(x).strip()
            ),
            continuity_fingerprint=str(raw.get("continuity_fingerprint") or ""),
        )


@dataclass(frozen=True, slots=True)
class LiveConversationContext:
    """Hume EVI entry context — same Educational Case, never a fresh chat."""

    context_id: str
    package_id: str
    story_world: str
    story_title: str
    characters: tuple[str, ...]
    stakes: str
    decision_point: str
    continuation_hook: str
    opening_line: str
    student_summary: str
    grammar_focus: tuple[str, ...]
    vocabulary_focus: tuple[str, ...]
    objectives: tuple[str, ...]
    student_confidence: str = "building"
    remaining_weaknesses: tuple[str, ...] = ()
    case_category: str = ""
    case_archetype: str = ""
    stakeholders: tuple[str, ...] = ()
    continuity_fingerprint: str = ""
    rehearsal_notes: tuple[str, ...] = ()
    journey_phases: tuple[str, ...] = (
        "educational_case",
        "discussion",
        "preparation",
        "gpt_rehearsal",
        "live_evi",
        "evaluation",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "package_id": self.package_id,
            "story_world": self.story_world,
            "story_title": self.story_title,
            "characters": list(self.characters),
            "stakes": self.stakes,
            "decision_point": self.decision_point,
            "continuation_hook": self.continuation_hook,
            "opening_line": self.opening_line,
            "student_summary": self.student_summary,
            "grammar_focus": list(self.grammar_focus),
            "vocabulary_focus": list(self.vocabulary_focus),
            "objectives": list(self.objectives),
            "student_confidence": self.student_confidence,
            "remaining_weaknesses": list(self.remaining_weaknesses),
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
            "stakeholders": list(self.stakeholders),
            "continuity_fingerprint": self.continuity_fingerprint,
            "rehearsal_notes": list(self.rehearsal_notes),
            "journey_phases": list(self.journey_phases),
            "bridge_version": LIVE_BRIDGE_VERSION,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> LiveConversationContext | None:
        if not isinstance(raw, dict) or not raw.get("context_id"):
            return None
        return LiveConversationContext(
            context_id=str(raw.get("context_id") or ""),
            package_id=str(raw.get("package_id") or ""),
            story_world=str(raw.get("story_world") or ""),
            story_title=str(raw.get("story_title") or ""),
            characters=tuple(str(x) for x in (raw.get("characters") or []) if str(x).strip()),
            stakes=str(raw.get("stakes") or ""),
            decision_point=str(raw.get("decision_point") or ""),
            continuation_hook=str(raw.get("continuation_hook") or ""),
            opening_line=str(raw.get("opening_line") or ""),
            student_summary=str(raw.get("student_summary") or ""),
            grammar_focus=tuple(
                str(x) for x in (raw.get("grammar_focus") or []) if str(x).strip()
            ),
            vocabulary_focus=tuple(
                str(x) for x in (raw.get("vocabulary_focus") or []) if str(x).strip()
            ),
            objectives=tuple(str(x) for x in (raw.get("objectives") or []) if str(x).strip()),
            student_confidence=str(raw.get("student_confidence") or "building"),
            remaining_weaknesses=tuple(
                str(x) for x in (raw.get("remaining_weaknesses") or []) if str(x).strip()
            ),
            case_category=str(raw.get("case_category") or ""),
            case_archetype=str(raw.get("case_archetype") or ""),
            stakeholders=tuple(
                str(x) for x in (raw.get("stakeholders") or []) if str(x).strip()
            ),
            continuity_fingerprint=str(raw.get("continuity_fingerprint") or ""),
            rehearsal_notes=tuple(
                str(x) for x in (raw.get("rehearsal_notes") or []) if str(x).strip()
            ),
            journey_phases=tuple(
                str(x)
                for x in (
                    raw.get("journey_phases")
                    or (
                        "educational_case",
                        "discussion",
                        "preparation",
                        "gpt_rehearsal",
                        "live_evi",
                        "evaluation",
                    )
                )
                if str(x).strip()
            ),
        )


@dataclass(slots=True)
class RehearsalState:
    """GPT rehearsal session (coaching only — no grading)."""

    rehearsal_id: str
    package_id: str
    scenario: SpeakingScenario
    gpt_role: str
    turns: list[dict[str, str]] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    coaching_notes: list[str] = field(default_factory=list)
    completed: bool = False
    provider: str = "template_fallback"
    # M12 Claude Scene Director: silent per-turn evaluations + current scene beat.
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    scene_beat: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rehearsal_id": self.rehearsal_id,
            "package_id": self.package_id,
            "scenario": self.scenario.to_dict(),
            "gpt_role": self.gpt_role,
            "turns": list(self.turns),
            "corrections": list(self.corrections),
            "coaching_notes": list(self.coaching_notes),
            "completed": self.completed,
            "provider": self.provider,
            "evaluations": list(self.evaluations),
            "scene_beat": dict(self.scene_beat),
            "bridge_version": LIVE_BRIDGE_VERSION,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> RehearsalState | None:
        if not isinstance(raw, dict) or not raw.get("rehearsal_id"):
            return None
        scenario = SpeakingScenario.from_dict(raw.get("scenario") if isinstance(raw.get("scenario"), dict) else None)
        if scenario is None:
            return None
        turns_raw = raw.get("turns") or []
        turns: list[dict[str, str]] = []
        if isinstance(turns_raw, list):
            for t in turns_raw:
                if isinstance(t, dict):
                    turn = {
                        "role": str(t.get("role") or ""),
                        "text": str(t.get("text") or ""),
                    }
                    if str(t.get("speaker") or "").strip():
                        turn["speaker"] = str(t["speaker"]).strip()
                    turns.append(turn)
        return RehearsalState(
            rehearsal_id=str(raw.get("rehearsal_id") or ""),
            package_id=str(raw.get("package_id") or ""),
            scenario=scenario,
            gpt_role=str(raw.get("gpt_role") or ""),
            turns=turns,
            corrections=[str(x) for x in (raw.get("corrections") or []) if str(x).strip()],
            coaching_notes=[
                str(x) for x in (raw.get("coaching_notes") or []) if str(x).strip()
            ],
            completed=bool(raw.get("completed")),
            provider=str(raw.get("provider") or "template_fallback"),
            evaluations=[e for e in (raw.get("evaluations") or []) if isinstance(e, dict)],
            scene_beat=raw.get("scene_beat") if isinstance(raw.get("scene_beat"), dict) else {},
        )


@dataclass(slots=True)
class LiveBridgeBundle:
    """Persisted bridge state under speaking bucket."""

    package_id: str = ""
    scenario: SpeakingScenario | None = None
    rehearsal: RehearsalState | None = None
    live_context: LiveConversationContext | None = None
    discussion_summary: str = ""
    journey_phase: str = "idle"

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "scenario": self.scenario.to_dict() if self.scenario else None,
            "rehearsal": self.rehearsal.to_dict() if self.rehearsal else None,
            "live_context": self.live_context.to_dict() if self.live_context else None,
            "discussion_summary": self.discussion_summary,
            "journey_phase": self.journey_phase,
            "bridge_version": LIVE_BRIDGE_VERSION,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> LiveBridgeBundle:
        if not isinstance(raw, dict):
            return LiveBridgeBundle()
        return LiveBridgeBundle(
            package_id=str(raw.get("package_id") or ""),
            scenario=SpeakingScenario.from_dict(
                raw.get("scenario") if isinstance(raw.get("scenario"), dict) else None
            ),
            rehearsal=RehearsalState.from_dict(
                raw.get("rehearsal") if isinstance(raw.get("rehearsal"), dict) else None
            ),
            live_context=LiveConversationContext.from_dict(
                raw.get("live_context") if isinstance(raw.get("live_context"), dict) else None
            ),
            discussion_summary=str(raw.get("discussion_summary") or ""),
            journey_phase=str(raw.get("journey_phase") or "idle"),
        )
