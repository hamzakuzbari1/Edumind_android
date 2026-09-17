"""Canonical EducationalPackage types and draft helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.language_educational_package.evidence_policy import (
    CorrectionMode,
    DiscussionEvidenceRole,
)
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.material_kinds import BodyBlockKind, InputMaterialKind
from app.services.language_educational_package.question_ladder import QuestionBand

ELP_SCHEMA_VERSION = "2.0.0"
ELP_AUTHOR_VERSION = "2.1.0"


@dataclass(slots=True)
class BodyBlock:
    kind: BodyBlockKind
    text: str
    block_ref: str = ""
    speaker: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "block_ref": self.block_ref,
            "speaker": self.speaker,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> BodyBlock:
        kind_raw = str(raw.get("kind") or "paragraph")
        try:
            kind = BodyBlockKind(kind_raw)
        except ValueError:
            kind = BodyBlockKind.other
        return BodyBlock(
            kind=kind,
            text=str(raw.get("text") or ""),
            block_ref=str(raw.get("block_ref") or ""),
            speaker=str(raw.get("speaker") or ""),
        )


@dataclass(slots=True)
class InputMaterial:
    kind: InputMaterialKind
    title: str
    body_blocks: list[BodyBlock]
    media_refs: list[str] = field(default_factory=list)
    cefr_check_echo: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "title": self.title,
            "body_blocks": [b.to_dict() for b in self.body_blocks],
            "media_refs": list(self.media_refs),
            "cefr_check_echo": self.cefr_check_echo,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> InputMaterial:
        kind_raw = str(raw.get("kind") or "story")
        try:
            kind = InputMaterialKind(kind_raw)
        except ValueError:
            kind = InputMaterialKind.custom
        blocks_raw = raw.get("body_blocks") or []
        blocks = [BodyBlock.from_dict(b) for b in blocks_raw if isinstance(b, dict)]
        media = raw.get("media_refs") or []
        return InputMaterial(
            kind=kind,
            title=str(raw.get("title") or ""),
            body_blocks=blocks,
            media_refs=[str(m) for m in media] if isinstance(media, list) else [],
            cefr_check_echo=str(raw.get("cefr_check_echo") or ""),
        )


@dataclass(slots=True)
class StoryCharacter:
    """Named participant in an Educational Case."""

    name: str
    background: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "background": self.background}

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> StoryCharacter:
        return StoryCharacter(
            name=str(raw.get("name") or ""),
            background=str(raw.get("background") or ""),
        )


@dataclass(slots=True)
class StorySpine:
    """Educational Case spine — Claude-authored under curriculum constraints.

    Narrative prose lives in ``input_material.body_blocks``; this structure carries
    the educational case (conflict, decisions, continuation) for discussion + Alex.
    """

    title: str = ""
    context: str = ""
    setting: str = ""
    characters: list[StoryCharacter] = field(default_factory=list)
    stakeholders: list[str] = field(default_factory=list)
    problem: str = ""
    conflict: str = ""
    timeline: str = ""
    events: list[str] = field(default_factory=list)
    decision_point: str = ""
    consequences: str = ""
    ending: str = ""
    ending_type: str = ""
    hidden_emotions: str = ""
    moral: str = ""
    discussion_hooks: list[str] = field(default_factory=list)
    continuation_hook: str = ""
    case_category: str = ""
    case_archetype: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "context": self.context,
            "setting": self.setting,
            "characters": [c.to_dict() for c in self.characters],
            "stakeholders": list(self.stakeholders),
            "problem": self.problem,
            "conflict": self.conflict,
            "timeline": self.timeline,
            "events": list(self.events),
            "decision_point": self.decision_point,
            "consequences": self.consequences,
            "ending": self.ending,
            "ending_type": self.ending_type,
            "hidden_emotions": self.hidden_emotions,
            "moral": self.moral,
            "discussion_hooks": list(self.discussion_hooks),
            "continuation_hook": self.continuation_hook,
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> StorySpine:
        if not isinstance(raw, dict):
            return StorySpine()
        chars_raw = raw.get("characters") or []
        characters: list[StoryCharacter] = []
        if isinstance(chars_raw, list):
            for item in chars_raw:
                if isinstance(item, dict) and str(item.get("name") or "").strip():
                    characters.append(StoryCharacter.from_dict(item))
                elif isinstance(item, str) and item.strip():
                    characters.append(StoryCharacter(name=item.strip()))
        events = raw.get("events") or []
        hooks = raw.get("discussion_hooks") or []
        stakeholders = raw.get("stakeholders") or []
        return StorySpine(
            title=str(raw.get("title") or ""),
            context=str(raw.get("context") or ""),
            setting=str(raw.get("setting") or ""),
            characters=characters,
            stakeholders=[str(s) for s in stakeholders] if isinstance(stakeholders, list) else [],
            problem=str(raw.get("problem") or ""),
            conflict=str(raw.get("conflict") or ""),
            timeline=str(raw.get("timeline") or ""),
            events=[str(e) for e in events] if isinstance(events, list) else [],
            decision_point=str(raw.get("decision_point") or ""),
            consequences=str(raw.get("consequences") or ""),
            ending=str(raw.get("ending") or ""),
            ending_type=str(raw.get("ending_type") or ""),
            hidden_emotions=str(raw.get("hidden_emotions") or ""),
            moral=str(raw.get("moral") or ""),
            discussion_hooks=[str(h) for h in hooks] if isinstance(hooks, list) else [],
            continuation_hook=str(raw.get("continuation_hook") or ""),
            case_category=str(raw.get("case_category") or ""),
            case_archetype=str(raw.get("case_archetype") or ""),
        )

    def is_substantive(self) -> bool:
        """True when the case has enough spine for speaking Educational Case packages."""
        return bool(
            self.conflict.strip()
            and len(self.events) >= 1
            and self.ending.strip()
            and self.continuation_hook.strip()
            and self.decision_point.strip()
        )


@dataclass(slots=True)
class VocabularyEntry:
    vocabulary_id: str
    surface: str
    context_span_ref: str
    brief_gloss: str
    example_reuse: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "vocabulary_id": self.vocabulary_id,
            "surface": self.surface,
            "context_span_ref": self.context_span_ref,
            "brief_gloss": self.brief_gloss,
            "example_reuse": self.example_reuse,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> VocabularyEntry:
        return VocabularyEntry(
            vocabulary_id=str(raw.get("vocabulary_id") or ""),
            surface=str(raw.get("surface") or ""),
            context_span_ref=str(raw.get("context_span_ref") or ""),
            brief_gloss=str(raw.get("brief_gloss") or ""),
            example_reuse=str(raw.get("example_reuse") or ""),
        )


@dataclass(slots=True)
class VocabularyInContext:
    entries: list[VocabularyEntry]
    highlight_map: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "highlight_map": list(self.highlight_map),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> VocabularyInContext:
        if not isinstance(raw, dict):
            return VocabularyInContext(entries=[])
        entries_raw = raw.get("entries") or []
        entries = [VocabularyEntry.from_dict(e) for e in entries_raw if isinstance(e, dict)]
        highlights = raw.get("highlight_map") or []
        clean_h: list[dict[str, str]] = []
        if isinstance(highlights, list):
            for h in highlights:
                if isinstance(h, dict):
                    clean_h.append({str(k): str(v) for k, v in h.items()})
        return VocabularyInContext(entries=entries, highlight_map=clean_h)


@dataclass(slots=True)
class AuthoredTeachingBlock:
    block_id: str
    kind: str
    title: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> AuthoredTeachingBlock:
        return AuthoredTeachingBlock(
            block_id=str(raw.get("block_id") or ""),
            kind=str(raw.get("kind") or ""),
            title=str(raw.get("title") or ""),
            body=str(raw.get("body") or ""),
        )


@dataclass(slots=True)
class DiscussionStep:
    step_id: str
    ladder_band: QuestionBand
    prompt: str
    success_cues: list[str]
    evidence_role: DiscussionEvidenceRole
    allowed_correction_mode: CorrectionMode
    max_assistant_turns: int = 3
    vocabulary_ids: list[str] = field(default_factory=list)
    grammar_topic_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "ladder_band": self.ladder_band.value,
            "prompt": self.prompt,
            "success_cues": list(self.success_cues),
            "evidence_role": self.evidence_role.value,
            "allowed_correction_mode": self.allowed_correction_mode.value,
            "max_assistant_turns": self.max_assistant_turns,
            "vocabulary_ids": list(self.vocabulary_ids),
            "grammar_topic_ids": list(self.grammar_topic_ids),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> DiscussionStep:
        try:
            band = QuestionBand(str(raw.get("ladder_band") or "literal"))
        except ValueError:
            band = QuestionBand.literal
        try:
            role = DiscussionEvidenceRole(str(raw.get("evidence_role") or "none"))
        except ValueError:
            role = DiscussionEvidenceRole.none
        try:
            mode = CorrectionMode(str(raw.get("allowed_correction_mode") or "micro"))
        except ValueError:
            mode = CorrectionMode.micro
        cues = raw.get("success_cues") or []
        vids = raw.get("vocabulary_ids") or []
        gids = raw.get("grammar_topic_ids") or []
        return DiscussionStep(
            step_id=str(raw.get("step_id") or ""),
            ladder_band=band,
            prompt=str(raw.get("prompt") or ""),
            success_cues=[str(c) for c in cues] if isinstance(cues, list) else [],
            evidence_role=role,
            allowed_correction_mode=mode,
            max_assistant_turns=max(1, int(raw.get("max_assistant_turns") or 3)),
            vocabulary_ids=[str(v) for v in vids] if isinstance(vids, list) else [],
            grammar_topic_ids=[str(g) for g in gids] if isinstance(gids, list) else [],
        )


@dataclass(slots=True)
class DiscussionFlow:
    flow_id: str
    opening_move: str
    steps: list[DiscussionStep]
    closing_move: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "opening_move": self.opening_move,
            "steps": [s.to_dict() for s in self.steps],
            "closing_move": self.closing_move,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> DiscussionFlow:
        if not isinstance(raw, dict):
            return DiscussionFlow(flow_id="", opening_move="", steps=[], closing_move="")
        steps_raw = raw.get("steps") or []
        steps = [DiscussionStep.from_dict(s) for s in steps_raw if isinstance(s, dict)]
        return DiscussionFlow(
            flow_id=str(raw.get("flow_id") or ""),
            opening_move=str(raw.get("opening_move") or ""),
            steps=steps,
            closing_move=str(raw.get("closing_move") or ""),
        )


@dataclass(slots=True)
class MiniPractice:
    task_id: str
    prompt: str
    scaffold: str
    evidence_intent_echo: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "scaffold": self.scaffold,
            "evidence_intent_echo": self.evidence_intent_echo,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> MiniPractice:
        if not isinstance(raw, dict):
            return MiniPractice(task_id="", prompt="", scaffold="", evidence_intent_echo="none")
        return MiniPractice(
            task_id=str(raw.get("task_id") or ""),
            prompt=str(raw.get("prompt") or ""),
            scaffold=str(raw.get("scaffold") or ""),
            evidence_intent_echo=str(raw.get("evidence_intent_echo") or "none"),
        )


@dataclass(slots=True)
class ReflectionSection:
    prompts: list[str]
    self_check_cues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompts": list(self.prompts),
            "self_check_cues": list(self.self_check_cues),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> ReflectionSection:
        if not isinstance(raw, dict):
            return ReflectionSection(prompts=[], self_check_cues=[])
        prompts = raw.get("prompts") or []
        cues = raw.get("self_check_cues") or []
        return ReflectionSection(
            prompts=[str(p) for p in prompts] if isinstance(prompts, list) else [],
            self_check_cues=[str(c) for c in cues] if isinstance(cues, list) else [],
        )


@dataclass(slots=True)
class EducationalPackage:
    """Canonical immutable Learning Package after freeze."""

    package_id: str
    schema_version: str
    author_version: str
    author_provider: str
    constraints_fingerprint: str
    content_fingerprint: str
    blueprint_hash: str
    mission_id: str
    status: PackageLifecycleStatus
    input_material: InputMaterial
    vocabulary_in_context: VocabularyInContext
    teaching_blocks_authored: list[AuthoredTeachingBlock]
    discussion: DiscussionFlow
    mini_practice: MiniPractice
    reflection: ReflectionSection
    story_spine: StorySpine = field(default_factory=StorySpine)
    teacher_notes: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    progression_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "schema_version": self.schema_version,
            "author_version": self.author_version,
            "author_provider": self.author_provider,
            "constraints_fingerprint": self.constraints_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "blueprint_hash": self.blueprint_hash,
            "mission_id": self.mission_id,
            "status": self.status.value,
            "input_material": self.input_material.to_dict(),
            "story_spine": self.story_spine.to_dict(),
            "vocabulary_in_context": self.vocabulary_in_context.to_dict(),
            "teaching_blocks_authored": [b.to_dict() for b in self.teaching_blocks_authored],
            "discussion": self.discussion.to_dict(),
            "mini_practice": self.mini_practice.to_dict(),
            "reflection": self.reflection.to_dict(),
            "teacher_notes": dict(self.teacher_notes),
            "metadata": dict(self.metadata),
            "progression_metadata": dict(self.progression_metadata),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> EducationalPackage:
        status_raw = str(raw.get("status") or "draft")
        try:
            status = PackageLifecycleStatus(status_raw)
        except ValueError:
            status = PackageLifecycleStatus.draft
        blocks_raw = raw.get("teaching_blocks_authored") or []
        blocks = [
            AuthoredTeachingBlock.from_dict(b) for b in blocks_raw if isinstance(b, dict)
        ]
        notes = raw.get("teacher_notes") if isinstance(raw.get("teacher_notes"), dict) else {}
        meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        prog = (
            raw.get("progression_metadata")
            if isinstance(raw.get("progression_metadata"), dict)
            else {}
        )
        return EducationalPackage(
            package_id=str(raw.get("package_id") or ""),
            schema_version=str(raw.get("schema_version") or ELP_SCHEMA_VERSION),
            author_version=str(raw.get("author_version") or ELP_AUTHOR_VERSION),
            author_provider=str(raw.get("author_provider") or "unknown"),
            constraints_fingerprint=str(raw.get("constraints_fingerprint") or ""),
            content_fingerprint=str(raw.get("content_fingerprint") or ""),
            blueprint_hash=str(raw.get("blueprint_hash") or ""),
            mission_id=str(raw.get("mission_id") or ""),
            status=status,
            input_material=InputMaterial.from_dict(
                raw.get("input_material") if isinstance(raw.get("input_material"), dict) else {}
            ),
            story_spine=StorySpine.from_dict(
                raw.get("story_spine")
                if isinstance(raw.get("story_spine"), dict)
                else raw.get("educational_case")
                if isinstance(raw.get("educational_case"), dict)
                else None
            ),
            vocabulary_in_context=VocabularyInContext.from_dict(
                raw.get("vocabulary_in_context")  # type: ignore[arg-type]
            ),
            teaching_blocks_authored=blocks,
            discussion=DiscussionFlow.from_dict(
                raw.get("discussion") if isinstance(raw.get("discussion"), dict) else None
            ),
            mini_practice=MiniPractice.from_dict(
                raw.get("mini_practice") if isinstance(raw.get("mini_practice"), dict) else None
            ),
            reflection=ReflectionSection.from_dict(
                raw.get("reflection") if isinstance(raw.get("reflection"), dict) else None
            ),
            teacher_notes=dict(notes),
            metadata=dict(meta),
            progression_metadata=dict(prog),
        )

    def to_student_dict(self) -> dict[str, Any]:
        """Student-safe projection — strip teacher notes and internal fingerprints internals."""
        data = self.to_dict()
        data.pop("teacher_notes", None)
        data.pop("progression_metadata", None)
        # Keep fingerprints for client cache keys but hide author internals minimally
        return data
