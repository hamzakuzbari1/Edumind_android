"""Dry-run (parse/validate) and apply (DB-backed insert/update) for the Reading MVP v1
draft-to-bank import.

Dry-run parses and validates backend/content_drafts/reading_mvp_v1_draft.md and builds in-memory
candidate rows for LanguagePlacementQuestionBankItem (build_dry_run_summary()) -- this path never
opens a database session and never writes anything.

apply_seed_batch() adds the actual DB insert/update path, used only when a caller explicitly
passes a real AsyncSession and apply=True. It is idempotent by stable_key
("reading_mvp_v1:<draft_id>"): a stable_key match updates content fields only and never resets
is_active/is_verified, and never touches usage_count/correct_count/difficulty_estimate/
discrimination_estimate (mirroring language_listening_bank_seed_service.py's own
_apply_candidate_fields safety invariant, so a later human activation decision or accrued
calibration data can never be silently reset by a routine content-sync re-run); a brand-new row is
inserted with is_active=False, is_verified=False, source="reading_mvp_v1_draft". Activation --
and retiring the old 21 content_seed Reading rows -- is a deliberate, separate, later cutover step,
never performed by this module.

Kept importable/testable under app/services/ (backend/scripts/ is excluded from the test Docker
image), matching the established pattern from language_listening_bank_seed_service.py.
backend/scripts/seed_reading_bank_mvp_v1.py is a thin CLI wrapper around
build_dry_run_summary()/apply_seed_batch() below.

draft_id (e.g. "RDG-A1-01") is an authoring-time identifier only. It is never written to any
database ID column -- it is used solely to build the stable_key above.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem

DEFAULT_DRAFT_PATH = (
    Path(__file__).resolve().parents[2] / "content_drafts" / "reading_mvp_v1_draft.md"
)

STABLE_KEY_PREFIX = "reading_mvp_v1"
SOURCE = "reading_mvp_v1_draft"
BOUNDARY_STABLE_KEY_PREFIX = "reading_boundary_v1"
BOUNDARY_SOURCE = "reading_boundary_v1"
SKILL = "reading"
QUESTION_TYPE = "mcq"
REVIEW_STATUS = "mvp_approved_pending_full_review"

EXPECTED_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
EXPECTED_PER_LEVEL = 10
EXPECTED_TOTAL = 60
READING_BUNDLE_SUBQUESTION_COUNT = 4
READING_DIFFICULTY_PROFILES = {
    "A1": {
        "word_count_range": (35, 65),
        "expected_question_focus": ("specific_detail", "main_idea", "purpose", "inference", "vocabulary_in_context"),
        "description": "short everyday texts with simple clauses and concrete vocabulary",
    },
    "A2": {
        "word_count_range": (70, 105),
        "expected_question_focus": ("specific_detail", "main_idea", "purpose", "inference", "vocabulary_in_context"),
        "description": "longer everyday texts with simple sequencing, reasons, and familiar past/future forms",
    },
    "B1": {
        "word_count_range": (115, 170),
        "expected_question_focus": ("main_idea", "specific_detail", "inference", "vocabulary_in_context", "purpose"),
        "description": "connected texts with reasons, contrast, opinions, and moderate lexical range",
    },
    "B2": {
        "word_count_range": (150, 230),
        "expected_question_focus": ("main_idea", "specific_detail", "inference", "vocabulary_in_context", "purpose", "tone"),
        "description": "denser texts with argument, nuance, stronger distractors, and less direct answers",
    },
    "C1": {
        "word_count_range": (185, 260),
        "expected_question_focus": (
            "main_idea", "inference", "vocabulary_in_context", "purpose", "tone",
            "argument_structure", "implication", "rhetorical_function",
        ),
        "description": "advanced texts with abstract claims, implicit meaning, and argument structure",
    },
    "C2": {
        "word_count_range": (220, 320),
        "expected_question_focus": (
            "inference", "vocabulary_in_context", "tone", "argument_structure",
            "implication", "rhetorical_function", "author_purpose",
        ),
        "description": "high-density argumentative prose with subtle rhetorical and lexical demands",
    },
}
READING_RESPONSE_TYPE_POLICY = {
    "A1": {"mcq": 2, "gap_fill": 1, "matching": 0, "short_answer": 1},
    "A2": {"mcq": 2, "gap_fill": 1, "matching": 0, "short_answer": 1},
    "B1": {"mcq": 1, "gap_fill": 1, "matching": 1, "short_answer": 1},
    "B2": {"mcq": 1, "gap_fill": 0, "matching": 1, "short_answer": 2},
    "C1": {"mcq": 1, "gap_fill": 0, "matching": 1, "short_answer": 2},
    "C2": {"mcq": 1, "gap_fill": 0, "matching": 1, "short_answer": 2},
}
_READING_TEXT_RESPONSE_TYPES = {"short_answer", "constructed_response", "gap_fill"}
_READING_MATCHING_RESPONSE_TYPES = {"matching"}

REQUIRED_FIELDS = (
    "draft_id", "cefr_level", "question_type", "reading_subskill", "topic_domain",
    "title", "passage", "question", "correct_answer", "explanation",
    "distractor_rationale", "review_status", "human_reviewed",
)

_DRAFT_ID_RE = re.compile(r"^RDG-(A1|A2|B1|B2|C1|C2)-(0[1-9]|10)$")
_PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bFIXME\b|\bTBD\b", re.IGNORECASE)
_PLACEHOLDER_CHECK_FIELDS = ("title", "passage", "question", "explanation", "distractor_rationale")
# body_json_candidate keys that must agree with the corresponding visible bullet-list field --
# catches the authoring mistake of editing one and forgetting the other.
_BODY_JSON_CROSS_CHECK_FIELDS = ("title", "topic_domain", "reading_subskill", "review_status", "human_reviewed")
_KNOWN_READING_SUBSKILLS = {
    "main_idea",
    "specific_detail",
    "inference",
    "vocabulary_in_context",
    "purpose",
    "tone",
    "argument_structure",
    "implication",
    "rhetorical_function",
    "author_purpose",
}
_WORD_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)?|\d+")
_SENTENCE_RE = re.compile(r"[.!?]+")


@dataclass
class ValidationIssue:
    draft_id: str | None
    field: str
    message: str
    severity: str = "error"  # "error" blocks apply; "warning" is advisory only


@dataclass
class SeedCandidate:
    """An in-memory, not-yet-inserted row shape for LanguagePlacementQuestionBankItem."""

    draft_id: str
    stable_key: str
    cefr_level: str
    subskill: str
    passage: str
    prompt_text: str
    options_json: list | None
    correct_index: int | None
    explanation: str
    body_json: dict
    skill: str = SKILL
    question_type: str = QUESTION_TYPE
    source: str = SOURCE
    is_active: bool = False
    is_verified: bool = False


@dataclass(frozen=True)
class BoundaryReadingCandidate:
    boundary_id: str
    stable_key: str
    cefr_level: str
    boundary_low_level: str
    boundary_high_level: str
    subskill: str
    title: str
    topic_domain: str
    passage: str
    prompt_text: str
    options_json: list[str]
    correct_index: int
    explanation: str
    body_json: dict
    skill: str = SKILL
    question_type: str = QUESTION_TYPE
    source: str = BOUNDARY_SOURCE
    is_active: bool = True
    is_verified: bool = True


@dataclass
class DryRunSummary:
    total_parsed: int
    candidates: list[SeedCandidate]
    issues: list[ValidationIssue]
    distribution: dict[str, int]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _reading_metrics(passage: str) -> dict:
    words = _WORD_RE.findall(passage or "")
    sentences = [s for s in _SENTENCE_RE.split(passage or "") if s.strip()]
    word_count = len(words)
    sentence_count = max(1, len(sentences))
    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_words": round(word_count / sentence_count, 1) if sentence_count else 0.0,
    }


def _difficulty_profile(level: str) -> dict:
    profile = READING_DIFFICULTY_PROFILES.get(level, {})
    low, high = profile.get("word_count_range", (0, 9999))
    return {
        "word_count_min": low,
        "word_count_max": high,
        "expected_question_focus": list(profile.get("expected_question_focus", ())),
        "description": profile.get("description", ""),
    }


def _boundary_candidate(
    *,
    boundary_id: str,
    level: str,
    low: str,
    high: str,
    subskill: str,
    title: str,
    topic_domain: str,
    passage: str,
    question: str,
    options: list[str],
    correct_index: int,
    explanation: str,
) -> BoundaryReadingCandidate:
    metrics = _reading_metrics(passage)
    body = {
        "title": title,
        "topic_domain": topic_domain,
        "reading_subskill": subskill,
        "boundary_low_level": low,
        "boundary_high_level": high,
        "review_status": REVIEW_STATUS,
        "human_reviewed": False,
        "placement_metrics": {
            **metrics,
            "cefr_level": level,
            "subskill": subskill,
            "difficulty_profile": _difficulty_profile(level),
        },
    }
    return BoundaryReadingCandidate(
        boundary_id=boundary_id,
        stable_key=f"{BOUNDARY_STABLE_KEY_PREFIX}:{boundary_id}",
        cefr_level=level,
        boundary_low_level=low,
        boundary_high_level=high,
        subskill=subskill,
        title=title,
        topic_domain=topic_domain,
        passage=passage,
        prompt_text=question,
        options_json=options,
        correct_index=correct_index,
        explanation=explanation,
        body_json=body,
    )


BOUNDARY_READING_CANDIDATES: tuple[BoundaryReadingCandidate, ...] = (
    _boundary_candidate(
        boundary_id="A1_A2_01",
        level="A2",
        low="A1",
        high="A2",
        subskill="specific_detail",
        title="Club Notice",
        topic_domain="school_life",
        passage=(
            "The school photo club meets on Tuesday after class in Room 12. New students can "
            "come to the first meeting without signing up. The teacher will show how to use the "
            "small cameras, and students will take pictures of objects in the classroom. Students "
            "who want to join for the term should bring a signed form by Friday."
        ),
        question="What should students bring if they want to join for the term?",
        options=["A signed form", "A small camera", "A classroom object", "A photo album"],
        correct_index=0,
        explanation="The passage says students who want to join for the term should bring a signed form by Friday.",
    ),
    _boundary_candidate(
        boundary_id="A1_A2_02",
        level="A2",
        low="A1",
        high="A2",
        subskill="purpose",
        title="Library Message",
        topic_domain="daily_services",
        passage=(
            "The town library is closing one hour early this Saturday because workers will repair "
            "the front door. Visitors can still return books through the outside box after 4 p.m. "
            "People who planned to use a computer should come before lunch, because the computer "
            "room will be busy in the afternoon."
        ),
        question="Why is the library closing early on Saturday?",
        options=["Workers will repair the front door", "The computer room is closed all day", "Visitors returned too many books", "The library has no staff before lunch"],
        correct_index=0,
        explanation="The reason given for the early closing is repair work on the front door.",
    ),
    _boundary_candidate(
        boundary_id="A2_B1_01",
        level="B1",
        low="A2",
        high="B1",
        subskill="inference",
        title="A Change at Work",
        topic_domain="workplace",
        passage=(
            "Marina usually eats lunch at her desk, but last month her manager asked everyone to "
            "take a real break away from the office area. At first Marina thought this would make "
            "her finish later. After two weeks, she noticed that she answered emails faster in the "
            "afternoon and made fewer small mistakes. Now she walks to the park with two colleagues "
            "when the weather is good."
        ),
        question="What can we infer about Marina's opinion of the new lunch rule?",
        options=["She has become more positive about it", "She thinks it makes her work worse", "She wants to eat alone every day", "She believes it is only useful in winter"],
        correct_index=0,
        explanation="Her later productivity and new habit suggest that she now sees value in the rule.",
    ),
    _boundary_candidate(
        boundary_id="A2_B1_02",
        level="B1",
        low="A2",
        high="B1",
        subskill="main_idea",
        title="Community Garden",
        topic_domain="community",
        passage=(
            "A group of neighbors started a small garden behind their apartment building. The first "
            "season was difficult because the soil was poor and nobody knew how much water the plants "
            "needed. Instead of giving up, the group asked an older gardener for advice and agreed on "
            "a weekly schedule. By the end of summer, the garden had become a place where neighbors "
            "talked, shared vegetables, and planned improvements for next year."
        ),
        question="What is the main idea of the passage?",
        options=["A difficult project helped neighbors build a stronger community", "An older gardener owned an apartment building", "Vegetables grow best with very little water", "The garden failed because the soil was poor"],
        correct_index=0,
        explanation="The whole passage shows how a challenging garden project became a community activity.",
    ),
    _boundary_candidate(
        boundary_id="B1_B2_01",
        level="B2",
        low="B1",
        high="B2",
        subskill="tone",
        title="Remote Meeting Policy",
        topic_domain="workplace",
        passage=(
            "The company says its new remote-meeting policy will save time, but the first month has "
            "shown a more mixed picture. Short updates are certainly quicker online, and fewer people "
            "travel between offices. However, complex planning meetings often end with unclear tasks, "
            "especially when several departments are involved. The policy may be useful, but it needs "
            "rules about which meetings actually belong online."
        ),
        question="Which option best describes the writer's tone toward the policy?",
        options=["Cautiously critical", "Completely enthusiastic", "Angrily dismissive", "Uninterested and neutral"],
        correct_index=0,
        explanation="The writer notes benefits but also points out problems and calls for clearer rules.",
    ),
    _boundary_candidate(
        boundary_id="B1_B2_02",
        level="B2",
        low="B1",
        high="B2",
        subskill="vocabulary_in_context",
        title="Museum Volunteers",
        topic_domain="culture",
        passage=(
            "The museum expected its volunteer program to attract mainly retired visitors, but the "
            "response was broader. University students joined to gain experience, parents joined "
            "because weekend shifts were flexible, and several local artists offered to run workshops. "
            "This range of volunteers has made the program more resilient: when one group is busy, "
            "another can usually cover the schedule."
        ),
        question="In the passage, what does 'resilient' mean?",
        options=["Able to continue despite difficulties", "More expensive than expected", "Limited to one type of person", "Strictly controlled by artists"],
        correct_index=0,
        explanation="'Resilient' refers to the program's ability to keep working when one group is unavailable.",
    ),
    _boundary_candidate(
        boundary_id="B2_C1_01",
        level="C1",
        low="B2",
        high="C1",
        subskill="argument_structure",
        title="Public Data",
        topic_domain="technology",
        passage=(
            "Advocates of public data portals often present transparency as an automatic public good. "
            "Yet information does not become useful merely because it is released. If datasets are "
            "poorly documented, updated irregularly, or published in formats that ordinary users cannot "
            "interpret, openness may serve institutions more than citizens. A credible transparency "
            "policy therefore requires investment in explanation, maintenance, and public feedback, not "
            "only a larger archive of downloadable files."
        ),
        question="How is the argument mainly structured?",
        options=["It challenges a simple assumption and then states conditions for success", "It lists unrelated examples of technology projects", "It praises public data portals without qualification", "It compares two historical periods in detail"],
        correct_index=0,
        explanation="The passage questions the assumption that release equals usefulness, then explains what transparency requires.",
    ),
    _boundary_candidate(
        boundary_id="B2_C1_02",
        level="C1",
        low="B2",
        high="C1",
        subskill="implication",
        title="Urban Quiet",
        topic_domain="urban_design",
        passage=(
            "City planners often treat quiet as the absence of noise, something achieved by moving "
            "traffic away or installing better windows. But quiet also has a social dimension. A public "
            "square can be acoustically calm and still feel tense if people are discouraged from staying. "
            "Conversely, a lively street may feel restful when its sounds are predictable and its spaces "
            "invite people to pause without pressure to buy anything."
        ),
        question="What does the passage imply about designing quiet urban spaces?",
        options=["Social comfort matters as much as reducing sound levels", "All lively streets should be made silent", "Windows are the only practical solution", "Public squares are naturally calmer than streets"],
        correct_index=0,
        explanation="The writer argues that quiet depends on social conditions as well as acoustic ones.",
    ),
    _boundary_candidate(
        boundary_id="C1_C2_01",
        level="C2",
        low="C1",
        high="C2",
        subskill="rhetorical_function",
        title="Precision in Forecasts",
        topic_domain="science",
        passage=(
            "Forecasts gain authority from numbers, but numerical precision can conceal fragile "
            "assumptions. A prediction that growth will reach 2.7 percent may appear more trustworthy "
            "than one that says 'around three percent', although both may rest on the same uncertain "
            "model. The problem is not quantification itself; it is the habit of treating decimal points "
            "as evidence that uncertainty has been mastered rather than merely formatted."
        ),
        question="What is the rhetorical function of the final phrase 'merely formatted'?",
        options=["It sharpens the contrast between real certainty and the appearance of certainty", "It introduces a new statistical method", "It admits that precise forecasts are always accurate", "It shifts the topic from economics to graphic design"],
        correct_index=0,
        explanation="The phrase emphasizes that presentation can disguise, rather than solve, uncertainty.",
    ),
    _boundary_candidate(
        boundary_id="C1_C2_02",
        level="C2",
        low="C1",
        high="C2",
        subskill="author_purpose",
        title="The Limits of Efficiency",
        topic_domain="society",
        passage=(
            "Efficiency is often invoked as though it were an end in itself, a neutral principle that "
            "settles disputes by removing waste. Yet the question of what counts as waste is never "
            "purely technical. A hospital that shortens consultations may process more patients, but "
            "it may also lose the pauses in which trust, hesitation, and unexpected symptoms surface. "
            "The point is not to romanticize delay, but to ask what human purposes speed is meant to serve."
        ),
        question="What is the author's main purpose?",
        options=["To question treating efficiency as a value independent of human aims", "To argue that hospitals should always work more slowly", "To show that technical decisions never affect people", "To recommend removing all measures of productivity"],
        correct_index=0,
        explanation="The author challenges efficiency as an independent goal and asks what purposes it should serve.",
    ),
)


def build_boundary_candidates() -> list[BoundaryReadingCandidate]:
    return list(BOUNDARY_READING_CANDIDATES)


def _split_items(text: str) -> list[str]:
    parts = re.split(r"(?=^### ITEM RDG-)", text, flags=re.MULTILINE)
    return [p for p in parts if p.startswith("### ITEM")]


def _extract_scalar(block: str, name: str) -> str | None:
    m = re.search(rf"^- {re.escape(name)}: (.+)$", block, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_json_value(block: str, name: str):
    """For fields written as a JSON array literal on a single bullet line."""
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_int(block: str, name: str) -> int | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_bool(block: str, name: str) -> bool | None:
    raw = _extract_scalar(block, name)
    if raw is None:
        return None
    return raw.strip().lower() == "true"


def _extract_json_fence(block: str) -> dict | None:
    m = re.search(r"```json\s*\n(.*?)\n```", block, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_item_block(block: str) -> dict:
    parsed: dict = {}
    parsed["draft_id"] = _extract_scalar(block, "draft_id")
    parsed["cefr_level"] = _extract_scalar(block, "cefr_level")
    parsed["question_type"] = _extract_scalar(block, "question_type")
    parsed["reading_subskill"] = _extract_scalar(block, "reading_subskill")
    parsed["topic_domain"] = _extract_scalar(block, "topic_domain")
    parsed["title"] = _extract_scalar(block, "title")
    parsed["passage"] = _extract_scalar(block, "passage")
    parsed["question"] = _extract_scalar(block, "question")
    parsed["options"] = _extract_json_value(block, "options")
    parsed["correct_index"] = _extract_int(block, "correct_index")
    parsed["correct_answer"] = _extract_scalar(block, "correct_answer")
    parsed["explanation"] = _extract_scalar(block, "explanation")
    parsed["distractor_rationale"] = _extract_scalar(block, "distractor_rationale")
    parsed["review_status"] = _extract_scalar(block, "review_status")
    parsed["human_reviewed"] = _extract_bool(block, "human_reviewed")
    parsed["body_json_candidate"] = _extract_json_fence(block)
    return parsed


def _normalize_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip().lower()


def _validate_item(raw: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    draft_id = raw.get("draft_id")

    for f in REQUIRED_FIELDS:
        value = raw.get(f)
        missing = value is None or (isinstance(value, str) and not value.strip())
        if f == "human_reviewed" and value is False:
            missing = False  # a real, present boolean value -- not "missing"
        if missing:
            issues.append(ValidationIssue(draft_id, f, f"missing or empty required field '{f}'"))

    if raw.get("question_type") != QUESTION_TYPE:
        issues.append(ValidationIssue(draft_id, "question_type", f"expected '{QUESTION_TYPE}', got {raw.get('question_type')!r}"))

    opts = raw.get("options")
    ci = raw.get("correct_index")
    if not isinstance(opts, list) or len(opts) != 4:
        issues.append(ValidationIssue(draft_id, "options", "must have exactly 4 options"))
        opts = None
    if not isinstance(ci, int) or not (0 <= ci <= 3):
        issues.append(ValidationIssue(draft_id, "correct_index", "must be an integer from 0 to 3"))
        ci = None
    if opts is not None and ci is not None:
        correct_answer = raw.get("correct_answer") or ""
        if _normalize_text(opts[ci]) != _normalize_text(correct_answer):
            issues.append(ValidationIssue(
                draft_id, "correct_answer",
                f"correct_answer {correct_answer!r} does not match options[{ci}] = {opts[ci]!r}",
            ))

    body = raw.get("body_json_candidate")
    if body is None or not isinstance(body, dict):
        issues.append(ValidationIssue(draft_id, "body_json_candidate", "missing or invalid JSON fence block"))
        body = {}
    else:
        for tag_field in _BODY_JSON_CROSS_CHECK_FIELDS:
            visible = raw.get(tag_field)
            in_body = body.get(tag_field)
            if visible is None:
                continue
            if isinstance(visible, str) and _normalize_text(in_body) != _normalize_text(visible):
                issues.append(ValidationIssue(draft_id, f"body_json_candidate.{tag_field}", f"body_json {tag_field} does not match visible {tag_field}"))
            elif isinstance(visible, bool) and in_body != visible:
                issues.append(ValidationIssue(draft_id, f"body_json_candidate.{tag_field}", f"body_json {tag_field} does not match visible {tag_field}"))
        issues.extend(_validate_subquestions(raw, body))

    if raw.get("review_status") not in (None, REVIEW_STATUS):
        issues.append(ValidationIssue(draft_id, "review_status", f"expected '{REVIEW_STATUS}', got {raw.get('review_status')!r}"))
    if raw.get("human_reviewed") not in (None, False):
        issues.append(ValidationIssue(draft_id, "human_reviewed", f"expected false, got {raw.get('human_reviewed')!r}"))

    passage = raw.get("passage")
    level = raw.get("cefr_level")
    if isinstance(passage, str) and level in READING_DIFFICULTY_PROFILES:
        metrics = _reading_metrics(passage)
        low, high = READING_DIFFICULTY_PROFILES[level]["word_count_range"]
        if not (low <= metrics["word_count"] <= high):
            issues.append(
                ValidationIssue(
                    draft_id,
                    "passage.word_count",
                    (
                        f"{level} passage has {metrics['word_count']} words; "
                        f"expected {low}-{high} for this placement band"
                    ),
                )
            )
        subskill = raw.get("reading_subskill")
        expected_focus = READING_DIFFICULTY_PROFILES[level]["expected_question_focus"]
        if isinstance(subskill, str) and subskill not in expected_focus:
            issues.append(
                ValidationIssue(
                    draft_id,
                    "reading_subskill",
                    f"{subskill!r} is unusual for {level}; expected one of {', '.join(expected_focus)}",
                    severity="warning",
                )
            )

    for pf in _PLACEHOLDER_CHECK_FIELDS:
        value = raw.get(pf)
        if isinstance(value, str) and _PLACEHOLDER_RE.search(value):
            issues.append(ValidationIssue(draft_id, pf, f"placeholder text (TODO/FIXME/TBD) found in field '{pf}'"))

    if draft_id:
        m = _DRAFT_ID_RE.match(draft_id)
        if not m:
            issues.append(ValidationIssue(draft_id, "draft_id", f"draft_id {draft_id!r} does not match RDG-<LEVEL>-NN pattern"))
        else:
            id_level = m.group(1)
            cefr_level = raw.get("cefr_level")
            if cefr_level != id_level:
                issues.append(ValidationIssue(draft_id, "cefr_level", f"cefr_level {cefr_level!r} does not match draft_id level {id_level!r}"))

    return issues


def _validate_subquestions(raw: dict, body: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    draft_id = raw.get("draft_id")
    subquestions = body.get("subquestions")
    if subquestions is None:
        return issues
    if not isinstance(subquestions, list) or len(subquestions) != READING_BUNDLE_SUBQUESTION_COUNT:
        return [
            ValidationIssue(
                draft_id,
                "body_json_candidate.subquestions",
                f"must contain exactly {READING_BUNDLE_SUBQUESTION_COUNT} reading subquestions when present",
            )
        ]

    top_question = raw.get("question")
    top_options = raw.get("options")
    top_correct_index = raw.get("correct_index")
    response_type_counts: Counter = Counter()
    for idx, sq in enumerate(subquestions):
        prefix = f"body_json_candidate.subquestions[{idx}]"
        if not isinstance(sq, dict):
            issues.append(ValidationIssue(draft_id, prefix, "must be an object"))
            continue
        question = sq.get("question")
        options = sq.get("options")
        correct_index = sq.get("correct_index")
        subskill = sq.get("subskill")
        response_type = str(sq.get("response_type") or "mcq").strip() or "mcq"
        response_type_counts[response_type] += 1
        if not isinstance(question, str) or not question.strip():
            issues.append(ValidationIssue(draft_id, f"{prefix}.question", "missing or empty question"))
        if response_type == "mcq":
            if not isinstance(options, list) or len(options) != 4 or not all(isinstance(o, str) and o.strip() for o in options):
                issues.append(ValidationIssue(draft_id, f"{prefix}.options", "must contain exactly 4 non-empty string options"))
            if not isinstance(correct_index, int) or isinstance(correct_index, bool) or not (0 <= correct_index <= 3):
                issues.append(ValidationIssue(draft_id, f"{prefix}.correct_index", "must be an integer from 0 to 3"))
        elif response_type in _READING_TEXT_RESPONSE_TYPES:
            accepted = sq.get("accepted_answers")
            max_words = sq.get("max_words", 12)
            if not isinstance(accepted, list) or not any(isinstance(a, str) and a.strip() for a in accepted):
                issues.append(ValidationIssue(draft_id, f"{prefix}.accepted_answers", "short-answer questions need accepted_answers"))
            if not isinstance(max_words, int) or isinstance(max_words, bool) or not (1 <= max_words <= 30):
                issues.append(ValidationIssue(draft_id, f"{prefix}.max_words", "must be an integer from 1 to 30"))
            elif isinstance(accepted, list):
                longest_accepted = max(
                    (_reading_metrics(a)["word_count"] for a in accepted if isinstance(a, str) and a.strip()),
                    default=0,
                )
                if longest_accepted > max_words:
                    issues.append(
                        ValidationIssue(
                            draft_id,
                            f"{prefix}.max_words",
                            f"max_words {max_words} is lower than accepted answer length {longest_accepted}",
                        )
                    )
        elif response_type in _READING_MATCHING_RESPONSE_TYPES:
            matching_items = sq.get("matching_items")
            match_options = sq.get("match_options")
            correct_indices = sq.get("correct_indices")
            if not isinstance(matching_items, list) or not (2 <= len(matching_items) <= 5):
                issues.append(ValidationIssue(draft_id, f"{prefix}.matching_items", "must contain 2-5 matching prompts"))
            elif not all(isinstance(i, str) and i.strip() for i in matching_items):
                issues.append(ValidationIssue(draft_id, f"{prefix}.matching_items", "must contain non-empty strings"))
            if not isinstance(match_options, list) or len(match_options) < len(matching_items or []):
                issues.append(ValidationIssue(draft_id, f"{prefix}.match_options", "must contain at least as many options as matching_items"))
            elif not all(isinstance(o, str) and o.strip() for o in match_options):
                issues.append(ValidationIssue(draft_id, f"{prefix}.match_options", "must contain non-empty strings"))
            if not isinstance(correct_indices, list) or len(correct_indices) != len(matching_items or []):
                issues.append(ValidationIssue(draft_id, f"{prefix}.correct_indices", "must match matching_items length"))
            elif isinstance(match_options, list) and any(
                not isinstance(i, int) or isinstance(i, bool) or not (0 <= i < len(match_options))
                for i in correct_indices
            ):
                issues.append(ValidationIssue(draft_id, f"{prefix}.correct_indices", "must contain valid match option indices"))
        else:
            issues.append(ValidationIssue(draft_id, f"{prefix}.response_type", "must be mcq, gap_fill, matching, or short_answer"))
        if not isinstance(subskill, str) or subskill not in _KNOWN_READING_SUBSKILLS:
            issues.append(
                ValidationIssue(
                    draft_id,
                    f"{prefix}.subskill",
                    f"must be one of {', '.join(sorted(_KNOWN_READING_SUBSKILLS))}",
                )
            )
        if idx == 0 and isinstance(top_question, str) and isinstance(top_options, list) and isinstance(top_correct_index, int):
            if response_type != "mcq":
                issues.append(ValidationIssue(draft_id, f"{prefix}.response_type", "first subquestion must be mcq"))
            if _normalize_text(question) != _normalize_text(top_question):
                issues.append(ValidationIssue(draft_id, f"{prefix}.question", "first subquestion must match the visible question field"))
            if options != top_options:
                issues.append(ValidationIssue(draft_id, f"{prefix}.options", "first subquestion options must match the visible options field"))
            if correct_index != top_correct_index:
                issues.append(ValidationIssue(draft_id, f"{prefix}.correct_index", "first subquestion correct_index must match the visible correct_index field"))
    level = raw.get("cefr_level")
    policy = READING_RESPONSE_TYPE_POLICY.get(level)
    if policy:
        short_count = sum(response_type_counts[t] for t in ("short_answer", "constructed_response"))
        gap_count = response_type_counts["gap_fill"]
        matching_count = sum(response_type_counts[t] for t in _READING_MATCHING_RESPONSE_TYPES)
        if (
            response_type_counts["mcq"] != policy["mcq"]
            or gap_count != policy["gap_fill"]
            or matching_count != policy["matching"]
            or short_count != policy["short_answer"]
        ):
            issues.append(
                ValidationIssue(
                    draft_id,
                    "body_json_candidate.subquestions.response_type_distribution",
                    (
                        f"{level} needs {policy['mcq']} mcq, {policy['gap_fill']} gap_fill, "
                        f"{policy['matching']} matching, and {policy['short_answer']} short_answer questions; "
                        f"got {response_type_counts['mcq']} mcq, {gap_count} gap_fill, "
                        f"{matching_count} matching, and {short_count} short_answer"
                    ),
                )
            )
    return issues


def _build_candidate(raw: dict) -> SeedCandidate:
    draft_id = raw.get("draft_id") or "UNKNOWN"
    body = dict(raw.get("body_json_candidate") or {})
    # Defensive: draft_id (an authoring-time identifier) and any database-ID-shaped key must never
    # leak into body_json -- the draft file has never included these, but strip defensively anyway.
    for key in ("id", "draft_id", "bank_item_id"):
        body.pop(key, None)
    metrics = _reading_metrics(raw.get("passage") or "")
    body["placement_metrics"] = {
        **metrics,
        "cefr_level": raw.get("cefr_level") or "",
        "subskill": raw.get("reading_subskill") or "",
        "difficulty_profile": _difficulty_profile(raw.get("cefr_level") or ""),
    }

    return SeedCandidate(
        draft_id=draft_id,
        stable_key=f"{STABLE_KEY_PREFIX}:{draft_id}",
        cefr_level=raw.get("cefr_level") or "",
        subskill=raw.get("reading_subskill") or "",
        passage=raw.get("passage") or "",
        prompt_text=raw.get("question") or "",
        options_json=raw.get("options"),
        correct_index=raw.get("correct_index"),
        explanation=raw.get("explanation") or "",
        body_json=body,
    )


def parse_draft_file(draft_path: Path | None = None) -> list[dict]:
    """Read and parse the draft markdown into raw per-item field dicts. Read-only; no DB access."""
    path = draft_path or DEFAULT_DRAFT_PATH
    text = path.read_text(encoding="utf-8")
    return [_parse_item_block(block) for block in _split_items(text)]


def build_dry_run_summary(draft_path: Path | None = None, *, enforce_batch_totals: bool = True) -> DryRunSummary:
    """Parse + validate the draft file and build in-memory candidates. Never touches a database.

    enforce_batch_totals=False skips only the whole-batch 60/10-per-level checks (every per-item
    validation rule still runs). This exists solely so apply tests can exercise real insert/update/
    idempotency behavior against small synthetic fixtures without needing to replicate the full
    60-item MVP batch; the CLI and the real 60-item draft always use the default (True), so
    production/dry-run behavior is completely unchanged.
    """
    raw_items = parse_draft_file(draft_path)

    issues: list[ValidationIssue] = []
    seen_ids: Counter = Counter()
    seen_titles: Counter = Counter()
    candidates: list[SeedCandidate] = []
    distribution: Counter = Counter()

    for raw in raw_items:
        draft_id = raw.get("draft_id")
        if draft_id:
            seen_ids[draft_id] += 1
        title = raw.get("title")
        if title:
            seen_titles[title] += 1
        issues.extend(_validate_item(raw))
        level = raw.get("cefr_level")
        if level:
            distribution[level] += 1
        candidates.append(_build_candidate(raw))

    for draft_id, count in seen_ids.items():
        if count > 1:
            issues.append(ValidationIssue(draft_id, "draft_id", f"duplicate draft_id appears {count} times"))

    for title, count in seen_titles.items():
        if count > 1:
            issues.append(ValidationIssue(None, "title", f"duplicate title {title!r} appears {count} times"))

    if enforce_batch_totals:
        if len(raw_items) != EXPECTED_TOTAL:
            issues.append(ValidationIssue(None, "total_count", f"expected {EXPECTED_TOTAL} items, parsed {len(raw_items)}"))

        expected_distribution = {lvl: EXPECTED_PER_LEVEL for lvl in EXPECTED_LEVELS}
        if dict(distribution) != expected_distribution:
            issues.append(ValidationIssue(None, "distribution", f"distribution mismatch: expected {expected_distribution}, got {dict(distribution)}"))
        if len(raw_items) == EXPECTED_TOTAL:
            missing_bundles = [
                c.draft_id
                for c in candidates
                if len(c.body_json.get("subquestions") or []) != READING_BUNDLE_SUBQUESTION_COUNT
            ]
            if missing_bundles:
                issues.append(
                    ValidationIssue(
                        None,
                        "subquestions",
                        (
                            f"expected every Reading MVP item to have {READING_BUNDLE_SUBQUESTION_COUNT} "
                            f"subquestions; missing/invalid for {', '.join(missing_bundles)}"
                        ),
                    )
                )

    return DryRunSummary(
        total_parsed=len(raw_items),
        candidates=candidates,
        issues=issues,
        distribution=dict(distribution),
    )


# ---------------------------------------------------------------------------
# Apply-mode implementation. Only executes DB writes when a caller explicitly passes a real
# AsyncSession and apply=True -- never invoked by the dry-run code above.
# ---------------------------------------------------------------------------


@dataclass
class ApplyResult:
    inserted: int
    updated: int
    stable_keys: list[str] = field(default_factory=list)


@dataclass
class BoundaryApplyResult:
    inserted: int
    updated: int
    activated_rows: int
    active_boundary_rows: int
    stable_keys: list[str] = field(default_factory=list)


@dataclass
class CutoverResult:
    inserted: int
    updated: int
    activated_mvp_rows: int
    retired_content_seed_rows: int
    active_mvp_rows: int
    active_content_seed_rows: int
    stable_keys: list[str] = field(default_factory=list)
    boundary_inserted: int = 0
    boundary_updated: int = 0
    boundary_activated_rows: int = 0
    active_boundary_rows: int = 0


async def _language_id(db: AsyncSession, code: str) -> int | None:
    return (
        await db.execute(select(Language.id).where(Language.code == code, Language.is_active.is_(True)).limit(1))
    ).scalar_one_or_none()


async def _existing_by_stable_key(db: AsyncSession, keys: list[str]) -> dict[str, LanguagePlacementQuestionBankItem]:
    if not keys:
        return {}
    rows = (
        await db.execute(select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key.in_(keys)))
    ).scalars().all()
    return {r.stable_key: r for r in rows if r.stable_key}


def _apply_candidate_fields(row: LanguagePlacementQuestionBankItem, candidate: SeedCandidate, *, language_id: int) -> None:
    """Populate every field this seed step owns except is_active/is_verified, which the caller
    handles separately (see module docstring for the safety reasoning -- mirrors
    language_listening_bank_seed_service.py's _apply_candidate_fields)."""
    row.language_id = language_id
    row.skill = candidate.skill
    row.level = LanguageLevel(candidate.cefr_level)
    row.subskill = candidate.subskill
    row.question_type = candidate.question_type
    row.prompt_text = candidate.prompt_text
    row.passage = candidate.passage
    row.situation = None  # Reading has no "situation" concept; only Listening ever reads it.
    row.options_json = candidate.options_json
    row.correct_index = candidate.correct_index
    row.explanation = candidate.explanation
    row.body_json = dict(candidate.body_json)
    row.source = candidate.source
    # Deliberately never touched here: boundary_low_level/boundary_high_level (this draft has no
    # boundary items), media_object_id/audio_meta_json (Reading has no audio), is_active,
    # is_verified (see caller), usage_count/correct_count/difficulty_estimate/
    # discrimination_estimate (accrued calibration data must survive a routine content-sync
    # re-run untouched).


def _apply_boundary_candidate_fields(
    row: LanguagePlacementQuestionBankItem,
    candidate: BoundaryReadingCandidate,
    *,
    language_id: int,
) -> None:
    row.language_id = language_id
    row.skill = candidate.skill
    row.level = LanguageLevel(candidate.cefr_level)
    row.boundary_low_level = LanguageLevel(candidate.boundary_low_level)
    row.boundary_high_level = LanguageLevel(candidate.boundary_high_level)
    row.subskill = candidate.subskill
    row.question_type = candidate.question_type
    row.prompt_text = candidate.prompt_text
    row.passage = candidate.passage
    row.situation = None
    row.options_json = list(candidate.options_json)
    row.correct_index = candidate.correct_index
    row.explanation = candidate.explanation
    row.body_json = dict(candidate.body_json)
    row.source = candidate.source


async def _apply_boundary_candidates(
    db: AsyncSession,
    *,
    language_id: int,
    activate: bool = True,
) -> BoundaryApplyResult:
    candidates = build_boundary_candidates()
    keys = [c.stable_key for c in candidates]
    existing = await _existing_by_stable_key(db, keys)
    inserted = updated = activated = 0
    for candidate in candidates:
        row = existing.get(candidate.stable_key)
        if row is None:
            row = LanguagePlacementQuestionBankItem(stable_key=candidate.stable_key)
            db.add(row)
            inserted += 1
        else:
            updated += 1
        _apply_boundary_candidate_fields(row, candidate, language_id=language_id)
        if activate:
            if not row.is_active or not row.is_verified:
                activated += 1
            row.is_active = True
            row.is_verified = True
        else:
            row.is_active = candidate.is_active
            row.is_verified = candidate.is_verified

    await db.flush()
    active_boundary_rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem.id).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.source == BOUNDARY_SOURCE,
                LanguagePlacementQuestionBankItem.is_active.is_(True),
                LanguagePlacementQuestionBankItem.is_verified.is_(True),
            )
        )
    ).scalars().all()
    return BoundaryApplyResult(
        inserted=inserted,
        updated=updated,
        activated_rows=activated,
        active_boundary_rows=len(active_boundary_rows),
        stable_keys=keys,
    )


async def seed_reading_boundary_v1(
    db: AsyncSession,
    *,
    language_code: str = "en",
    activate: bool = True,
) -> BoundaryApplyResult | None:
    language_id = await _language_id(db, language_code)
    if language_id is None:
        return None
    result = await _apply_boundary_candidates(db, language_id=language_id, activate=activate)
    await db.commit()
    return result


async def apply_seed_batch(
    db: AsyncSession,
    *,
    language_code: str = "en",
    apply: bool = True,
    draft_path: Path | None = None,
    enforce_batch_totals: bool = True,
) -> tuple[DryRunSummary, ApplyResult | None]:
    """Validate the draft and, only if apply=True and validation is clean, insert/update every
    candidate idempotently by stable_key. Returns (summary, apply_result); apply_result is None
    whenever nothing was written (apply=False, validation failed, or the language code could not
    be resolved) -- callers should always check summary.is_valid / apply_result is not None rather
    than assume success.

    Insert: is_active=False, is_verified=False, source="reading_mvp_v1_draft" -- brand-new rows are
    never active or verified; the old 21 content_seed Reading rows are never touched by this
    function at all (it only ever inserts/updates rows matched by this batch's own stable_keys).
    Update: an existing row's is_active/is_verified/usage_count/correct_count/difficulty_estimate/
    discrimination_estimate are left completely untouched, so this can be re-run at any time (e.g.
    to fix a content typo) without ever resetting a human reviewer's later activation decision or
    accrued calibration data.
    """
    summary = build_dry_run_summary(draft_path, enforce_batch_totals=enforce_batch_totals)
    if not apply or not summary.is_valid:
        return summary, None

    language_id = await _language_id(db, language_code)
    if language_id is None:
        summary.issues.append(ValidationIssue(None, "language_id", f"language code {language_code!r} not found or inactive"))
        return summary, None

    keys = [c.stable_key for c in summary.candidates]
    existing = await _existing_by_stable_key(db, keys)
    inserted = updated = 0
    for candidate in summary.candidates:
        row = existing.get(candidate.stable_key)
        if row is None:
            row = LanguagePlacementQuestionBankItem(stable_key=candidate.stable_key)
            _apply_candidate_fields(row, candidate, language_id=language_id)
            row.is_active = False
            row.is_verified = False
            db.add(row)
            inserted += 1
        else:
            _apply_candidate_fields(row, candidate, language_id=language_id)
            updated += 1
    await db.commit()
    return summary, ApplyResult(inserted=inserted, updated=updated, stable_keys=keys)


async def activate_reading_mvp_v1_cutover(
    db: AsyncSession,
    *,
    language_code: str = "en",
    draft_path: Path | None = None,
    enforce_batch_totals: bool = True,
) -> tuple[DryRunSummary, CutoverResult | None]:
    """Make Reading MVP v1 the active placement bank for one language.

    This is the explicit cutover step intentionally kept out of apply_seed_batch():
    1. validate and idempotently insert/update the 60 draft rows,
    2. mark exactly those Reading MVP v1 rows active+verified,
    3. soft-retire old active Reading content_seed rows by setting is_active=False.

    Rows are never hard-deleted, and no non-Reading or non-target-language rows are touched.
    """

    summary, apply_result = await apply_seed_batch(
        db,
        language_code=language_code,
        apply=True,
        draft_path=draft_path,
        enforce_batch_totals=enforce_batch_totals,
    )
    if not summary.is_valid or apply_result is None:
        return summary, None

    language_id = await _language_id(db, language_code)
    if language_id is None:
        summary.issues.append(ValidationIssue(None, "language_id", f"language code {language_code!r} not found or inactive"))
        return summary, None

    keys = [c.stable_key for c in summary.candidates]
    rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.stable_key.in_(keys),
            )
        )
    ).scalars().all()
    if len(rows) != len(keys):
        summary.issues.append(
            ValidationIssue(
                None,
                "stable_keys",
                f"expected {len(keys)} Reading MVP rows after apply, found {len(rows)}",
            )
        )
        return summary, None

    activated = 0
    for row in rows:
        if row.source != SOURCE or not str(row.stable_key or "").startswith(f"{STABLE_KEY_PREFIX}:"):
            summary.issues.append(
                ValidationIssue(
                    str(row.stable_key),
                    "source",
                    "refusing cutover because an MVP stable_key row has an unexpected source",
                )
            )
            return summary, None
        if not row.is_active or not row.is_verified:
            activated += 1
        row.is_active = True
        row.is_verified = True

    old_rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.source == "content_seed",
                LanguagePlacementQuestionBankItem.is_active.is_(True),
            )
        )
    ).scalars().all()
    retired = 0
    for row in old_rows:
        if row.stable_key in keys:
            continue
        row.is_active = False
        retired += 1

    boundary_result = await _apply_boundary_candidates(db, language_id=language_id, activate=True)

    await db.commit()

    active_mvp_rows = len(
        [
            row
            for row in rows
            if row.is_active and row.is_verified and row.source == SOURCE
        ]
    )
    active_content_seed_rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem.id).where(
                LanguagePlacementQuestionBankItem.language_id == language_id,
                LanguagePlacementQuestionBankItem.skill == SKILL,
                LanguagePlacementQuestionBankItem.source == "content_seed",
                LanguagePlacementQuestionBankItem.is_active.is_(True),
            )
        )
    ).scalars().all()

    return summary, CutoverResult(
        inserted=apply_result.inserted,
        updated=apply_result.updated,
        activated_mvp_rows=activated,
        retired_content_seed_rows=retired,
        active_mvp_rows=active_mvp_rows,
        active_content_seed_rows=len(active_content_seed_rows),
        stable_keys=keys,
        boundary_inserted=boundary_result.inserted,
        boundary_updated=boundary_result.updated,
        boundary_activated_rows=boundary_result.activated_rows,
        active_boundary_rows=boundary_result.active_boundary_rows,
    )
