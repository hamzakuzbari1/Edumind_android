from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

import app.services.language_reading_v2_service as reading_service
from app.models.language.analytics import LanguageAnalytics
from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.reading_v2 import (
    LanguageReadingV2Attempt,
    LanguageReadingV2StageProgress,
    LanguageReadingV2StudentState,
)
from app.models.user import User, UserRole
from app.schemas.language_reading_v2 import GenerationBlueprint
from app.services.language_reading_v2_service import (
    CEFR_LEVELS,
    INTERNAL_STAGES,
    build_generation_blueprint,
    build_reading_v2_overview,
    build_reading_v2_path,
    create_reading_v2_attempt,
    generate_activity_with_ai_provider,
    generate_reading_activity_from_blueprint,
    reading_v2_generation_prompt,
    score_generated_activity,
    select_reading_v2_generation_provider,
    submit_reading_v2_attempt,
    validate_generated_activity,
)

pytestmark = pytest.mark.postgresql


async def _student_and_language(db, *, reading_level: LanguageLevel | None = None) -> tuple[int, int]:
    marker = uuid.uuid4().hex[:10]
    student = User(
        email=f"reading-v2-{marker}@example.com",
        name="Reading V2 Student",
        hashed_password="test",
        role=UserRole.student,
    )
    language = Language(
        code=f"rv{marker[:8]}",
        name_en="Reading V2 English",
        name_ar="Reading V2 English",
        is_active=True,
    )
    db.add_all([student, language])
    await db.flush()
    if reading_level:
        db.add(
            LanguageAnalytics(
                student_id=student.id,
                language_id=language.id,
                reading_level=reading_level,
            )
        )
        await db.flush()
    return student.id, language.id


def _blueprint(**overrides) -> GenerationBlueprint:
    values = {
        "cefr_level": "A2",
        "internal_stage": "Intermediate",
        "mode": "practice",
        "word_count_min": 90,
        "word_count_max": 140,
        "sentence_complexity": "a2_intermediate_sentences",
        "vocabulary_difficulty": "a2_intermediate_vocabulary",
        "target_vocab_tags": ["travel"],
        "required_vocab_items": [],
        "target_grammar_tags": ["past_simple"],
        "banned_above_level_grammar": ["conditionals"],
        "reading_subskills": ["skim_gist", "scan_detail", "vocab_in_context", "literal_comprehension"],
        "question_types": ["mcq", "true_false", "gap_fill", "short_answer"],
        "topic": "safe study habits",
        "difficulty_score": 35.0,
        "inference_depth": "mixed",
        "number_of_questions": 4,
        "safety_topic_restrictions": ["unsafe topics"],
        "prompt_version": reading_service.PROMPT_VERSION,
    }
    values.update(overrides)
    cefr = values["cefr_level"]
    stage = values["internal_stage"]
    if "word_count_min" not in overrides and "word_count_max" not in overrides:
        word_min, word_max = reading_service._WORD_RANGES[cefr][stage]
        values["word_count_min"] = word_min
        values["word_count_max"] = word_max
    if "passage_difficulty_policy" not in overrides:
        values["passage_difficulty_policy"] = dict(reading_service.PASSAGE_DIFFICULTY_POLICY[cefr][stage])
    return GenerationBlueprint(**values)


def _install_unique_mock_generator(monkeypatch):
    counter = {"value": 0}

    async def fake_generate_activity_for_blueprint(blueprint):
        counter["value"] += 1
        activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
        activity["title"] = f"{activity['title']} #{counter['value']}"
        activity["validation_metadata"]["test_unique_marker"] = counter["value"]
        validation = validate_generated_activity(activity, blueprint)
        return reading_service.ReadingV2GenerationOutcome(
            activity=activity,
            validation=validation,
            provider_name="local_mock",
            model_used="local_mock",
            prompt_version=blueprint.prompt_version,
            retry_count=0,
        )

    monkeypatch.setattr(reading_service, "generate_activity_for_blueprint", fake_generate_activity_for_blueprint)


async def _move_to_stage(
    db,
    *,
    student_id: int,
    language_id: int,
    cefr: LanguageLevel = LanguageLevel.A1,
    stage: str = "Beginner",
    readiness_target: LanguageLevel | None = None,
    stage_status: str = "current",
) -> None:
    state = await reading_service.get_or_create_student_state(db, student_id=student_id, language_id=language_id)
    state.current_cefr = cefr
    state.current_stage = stage
    state.status = "active"
    state.unlocked_rank = reading_service.stage_rank(cefr, stage)
    state.readiness_target_level = readiness_target
    progress = await reading_service.get_or_create_stage_progress(
        db,
        student_id=student_id,
        language_id=language_id,
        cefr_level=cefr,
        internal_stage=stage,
    )
    progress.status = stage_status
    await db.flush()


def _answers_for_activity(activity: dict, *, wrong_subskills: set[str] | None = None, wrong_count: int = 0) -> dict:
    wrong_subskills = wrong_subskills or set()
    answers = {}
    wrong_remaining = wrong_count
    for question in activity["questions"]:
        key = question.get("answer_key") or {}
        should_miss = question["subskill"] in wrong_subskills or wrong_remaining > 0
        if should_miss and wrong_remaining > 0:
            wrong_remaining -= 1
        if should_miss:
            answers[question["id"]] = {"choice_id": "__wrong__"} if question["type"] == "mcq" else "__wrong__"
            continue
        if question["type"] == "mcq":
            answers[question["id"]] = {"choice_id": key.get("correct_choice_id")}
        elif question["type"] == "true_false":
            answers[question["id"]] = key.get("correct")
        elif question["type"] in {"gap_fill", "short_answer"}:
            answers[question["id"]] = (key.get("accepted_answers") or key.get("required_key_terms") or [""])[0]
    return answers


def _nested_keys(value) -> set[str]:
    if isinstance(value, list):
        return {key for item in value for key in _nested_keys(item)}
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(_nested_keys(nested))
        return keys
    return set()


def _issue_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


async def _create_and_submit_practice(
    db,
    *,
    student_id: int,
    language_id: int,
    wrong_subskills: set[str] | None = None,
    wrong_count: int = 0,
):
    attempt = await create_reading_v2_attempt(db, student_id=student_id, language_id=language_id, mode="practice")
    stored = (
        await db.execute(select(LanguageReadingV2Attempt).where(LanguageReadingV2Attempt.id == attempt.attempt_id))
    ).scalar_one()
    return await submit_reading_v2_attempt(
        db,
        student_id=student_id,
        language_id=language_id,
        attempt_id=attempt.attempt_id,
        answers=_answers_for_activity(
            stored.generated_activity_json,
            wrong_subskills=wrong_subskills,
            wrong_count=wrong_count,
        ),
    )


async def _create_and_submit_readiness(
    db,
    *,
    student_id: int,
    language_id: int,
    wrong_count: int = 0,
):
    attempt = await create_reading_v2_attempt(db, student_id=student_id, language_id=language_id, mode="readiness")
    stored = (
        await db.execute(select(LanguageReadingV2Attempt).where(LanguageReadingV2Attempt.id == attempt.attempt_id))
    ).scalar_one()
    return await submit_reading_v2_attempt(
        db,
        student_id=student_id,
        language_id=language_id,
        attempt_id=attempt.attempt_id,
        answers=_answers_for_activity(stored.generated_activity_json, wrong_count=wrong_count),
    )


async def _insert_subskill_attempt(
    db,
    *,
    student_id: int,
    language_id: int,
    attempt_index: int,
    results: list[tuple[str, bool]],
    score_percent: float | None = None,
    cefr: LanguageLevel = LanguageLevel.A1,
    stage: str = "Beginner",
) -> None:
    question_results = [
        {
            "question_id": f"q{index}",
            "question_type": reading_service.QUESTION_TYPES[(index - 1) % len(reading_service.QUESTION_TYPES)],
            "subskill": subskill,
            "correct": correct,
            "score": 1.0 if correct else 0.0,
        }
        for index, (subskill, correct) in enumerate(results, start=1)
    ]
    if score_percent is None:
        score_percent = round(
            (sum(1 for _subskill, correct in results if correct) / len(results)) * 100.0,
            2,
        )
    db.add(
        LanguageReadingV2Attempt(
            student_id=student_id,
            language_id=language_id,
            cefr_level=cefr,
            internal_stage=stage,
            mode="practice",
            status="submitted",
            generation_blueprint_json={"cefr_level": cefr.value, "internal_stage": stage},
            generated_activity_json={
                "title": f"Subskill Evidence {attempt_index}",
                "passage": f"Unique passage {attempt_index}",
                "questions": [],
            },
            validation_result_json={"valid": True, "issues": [], "warnings": []},
            model_used="test",
            prompt_version=reading_service.PROMPT_VERSION,
            validator_version="reading_v2_validator_r1",
            score_percent=score_percent,
            question_results_json=question_results,
        )
    )
    await db.flush()


async def _insert_balanced_subskill_attempts(
    db,
    *,
    student_id: int,
    language_id: int,
    skim_results: list[bool],
    scan_results: list[bool] | None = None,
    literal_results: list[bool] | None = None,
    cefr: LanguageLevel = LanguageLevel.A1,
    stage: str = "Beginner",
) -> None:
    scan_results = scan_results or [True, True, True, True, True]
    literal_results = literal_results or [True, True, True, True, True]
    for index in range(5):
        results = [
            ("scan_detail", scan_results[index]),
            ("literal_comprehension", literal_results[index]),
        ]
        if index < len(skim_results):
            results.append(("skim_gist", skim_results[index]))
        await _insert_subskill_attempt(
            db,
            student_id=student_id,
            language_id=language_id,
            attempt_index=index + 1,
            results=results,
            score_percent=100.0 if all(correct for _subskill, correct in results) else 75.0,
            cefr=cefr,
            stage=stage,
        )


def test_generated_activity_validation_passes_for_valid_mock_activity():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint)

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is True
    assert result.issues == []


def test_validator_rejects_passages_outside_word_range():
    blueprint = _blueprint(cefr_level="A1", internal_stage="Beginner")
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["passage"] = "Too short."

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert "word_count_out_of_range" in _issue_codes(result)


def test_validator_rejects_a1_beginner_dense_sentences():
    blueprint = _blueprint(cefr_level="A1", internal_stage="Beginner")
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["passage"] = (
        "Mira carefully studies several complicated explanations about transportation schedules because "
        "her teacher expects detailed answers before the morning lesson begins today. "
        "She opens a book. She sees a picture. She writes a word. Her friend smiles. "
        "The page is short. The story is about a bus."
    )

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert "a1_beginner_sentence_too_long" in _issue_codes(result)


def test_validator_rejects_high_level_repeated_simple_padding():
    blueprint = _blueprint(cefr_level="C1", internal_stage="Advanced")
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    sentence = "Mira reads a simple book at home and writes one new word in her notebook."
    sentences = [sentence for _index in range(110)]
    activity["passage"] = "\n\n".join(
        " ".join(sentences[index : index + 28]) for index in range(0, len(sentences), 28)
    )

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert _issue_codes(result).intersection(
        {"repeated_sentence_ratio_too_high", "repeated_phrase_ratio_too_high", "lexical_diversity_too_low"}
    )


@pytest.mark.parametrize(
    ("cefr", "stage"),
    [
        ("B1", "Intermediate"),
        ("B1", "Advanced"),
        ("B2", "Advanced"),
        ("C1", "Advanced"),
        ("C2", "Advanced"),
    ],
)
def test_local_mock_high_level_passages_follow_difficulty_policy(cefr, stage):
    blueprint = _blueprint(
        cefr_level=cefr,
        internal_stage=stage,
        reading_subskills=reading_service._SUBSKILLS_BY_STAGE[stage],
        question_count=reading_service.get_practice_question_count(cefr, stage),
        number_of_questions=reading_service.get_practice_question_count(cefr, stage),
        question_types=reading_service.question_types_for_count(
            reading_service.get_practice_question_count(cefr, stage),
            mode="practice",
        ),
    )
    activity = generate_reading_activity_from_blueprint(blueprint)

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is True
    assert "Reading Routine" not in activity.title
    assert reading_service._paragraph_count(activity.passage) >= blueprint.passage_difficulty_policy["paragraph_count_min"]
    assert reading_service._repeated_ngram_ratio(reading_service._word_tokens(activity.passage)) <= float(
        blueprint.passage_difficulty_policy["max_repeated_ngram_ratio"]
    )


def test_a2_advanced_readiness_local_mock_passes_difficulty_validation():
    question_count = reading_service.get_readiness_question_count("B1")
    blueprint = _blueprint(
        cefr_level="A2",
        internal_stage="Advanced",
        mode="readiness",
        reading_subskills=reading_service._SUBSKILLS_BY_STAGE["Advanced"],
        question_count=question_count,
        number_of_questions=question_count,
        question_types=reading_service.question_types_for_count(question_count, mode="readiness"),
    )

    activity = generate_reading_activity_from_blueprint(blueprint)
    result = validate_generated_activity(activity, blueprint)
    question_stems = [question.stem for question in activity.questions]

    assert result.valid is True
    assert len(activity.questions) == 12
    assert len(set(question_stems)) > 8
    assert reading_service._repeated_sentence_ratio(reading_service._sentence_texts(activity.passage)) == 0.0


def test_b1_advanced_practice_and_readiness_local_mocks_pass_difficulty_validation():
    practice_count = reading_service.get_practice_question_count("B1", "Advanced")
    readiness_count = reading_service.get_readiness_question_count("B2")
    assert practice_count == 6
    assert readiness_count == 12

    for mode, question_count in (("practice", practice_count), ("readiness", readiness_count)):
        blueprint = _blueprint(
            cefr_level="B1",
            internal_stage="Advanced",
            mode=mode,
            reading_subskills=reading_service._SUBSKILLS_BY_STAGE["Advanced"],
            question_count=question_count,
            number_of_questions=question_count,
            question_types=reading_service.question_types_for_count(question_count, mode=mode),
        )
        activity = generate_reading_activity_from_blueprint(blueprint)
        result = validate_generated_activity(activity, blueprint)
        tokens = reading_service._word_tokens(activity.passage)

        assert result.valid is True, [issue.code for issue in result.issues]
        assert len(activity.questions) == question_count
        assert reading_service._paragraph_count(activity.passage) >= 2
        assert reading_service._repeated_sentence_ratio(reading_service._sentence_texts(activity.passage)) == 0.0
        assert reading_service._repeated_ngram_ratio(tokens) <= float(
            blueprint.passage_difficulty_policy["max_repeated_ngram_ratio"]
        )
        assert "repeated_phrase_ratio_too_high" not in _issue_codes(result)


@pytest.mark.parametrize("cefr", ["B1", "B2", "C1", "C2"])
def test_validator_rejects_repetitive_padded_passages_for_upper_levels(cefr):
    stage = "Advanced"
    blueprint = _blueprint(
        cefr_level=cefr,
        internal_stage=stage,
        reading_subskills=reading_service._SUBSKILLS_BY_STAGE[stage],
        question_count=reading_service.get_practice_question_count(cefr, stage),
        number_of_questions=reading_service.get_practice_question_count(cefr, stage),
        question_types=reading_service.question_types_for_count(
            reading_service.get_practice_question_count(cefr, stage),
            mode="practice",
        ),
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    sentence = "Mira reads a simple book at home and writes one new word in her notebook."
    needed = max(40, int(blueprint.passage_difficulty_policy["sentence_count_min"]) + 10)
    sentences = [sentence for _index in range(needed)]
    paragraph_min = max(1, int(blueprint.passage_difficulty_policy["paragraph_count_min"]))
    chunk = max(1, needed // paragraph_min)
    activity["passage"] = "\n\n".join(
        " ".join(sentences[index : index + chunk]) for index in range(0, len(sentences), chunk)
    )

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert _issue_codes(result).intersection(
        {"repeated_sentence_ratio_too_high", "repeated_phrase_ratio_too_high", "lexical_diversity_too_low"}
    )


@pytest.mark.parametrize(
    ("cefr", "stage", "expected_count"),
    [
        ("A1", "Beginner", 4),
        ("A1", "Intermediate", 4),
        ("A1", "Advanced", 5),
        ("A2", "Intermediate", 5),
        ("B1", "Intermediate", 6),
        ("B2", "Advanced", 7),
        ("C2", "Advanced", 8),
    ],
)
def test_practice_question_count_policy_by_level_and_stage(cefr, stage, expected_count):
    assert reading_service.get_practice_question_count(cefr, stage) == expected_count


@pytest.mark.parametrize(
    ("cefr", "stage", "expected_count"),
    [
        (LanguageLevel.A1, "Beginner", 4),
        (LanguageLevel.A1, "Intermediate", 4),
        (LanguageLevel.A1, "Advanced", 5),
        (LanguageLevel.A2, "Intermediate", 5),
        (LanguageLevel.B1, "Intermediate", 6),
        (LanguageLevel.B2, "Advanced", 7),
        (LanguageLevel.C2, "Advanced", 8),
    ],
)
async def test_generation_blueprint_uses_adaptive_practice_question_count(postgres_session, cefr, stage, expected_count):
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=cefr,
        stage=stage,
    )

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert blueprint.mode == "practice"
    assert blueprint.cefr_level == cefr.value
    assert blueprint.internal_stage == stage
    assert blueprint.question_count == expected_count
    assert blueprint.number_of_questions == expected_count
    assert len(blueprint.question_types) == expected_count
    assert blueprint.passage_difficulty_policy == dict(reading_service.PASSAGE_DIFFICULTY_POLICY[cefr.value][stage])
    assert set(reading_service.REQUIRED_PRACTICE_QUESTION_TYPES).issubset(set(blueprint.question_types))
    assert set(blueprint.question_types).issubset(set(reading_service.QUESTION_TYPES))


def test_practice_question_type_policy_preserves_required_mvp_types_for_extra_questions():
    question_types = reading_service.question_types_for_count(8, mode="practice")

    assert len(question_types) == 8
    assert set(reading_service.REQUIRED_PRACTICE_QUESTION_TYPES).issubset(set(question_types))
    assert set(question_types).issubset(set(reading_service.QUESTION_TYPES))


def test_extra_subskill_priority_keeps_lower_levels_direct():
    blueprint = _blueprint(
        cefr_level="A2",
        internal_stage="Intermediate",
        reading_subskills=["skim_gist", "scan_detail", "literal_comprehension", "infer_meaning"],
        target_subskills=[],
    )

    assert reading_service._prioritized_subskills_for_questions(blueprint)[:3] == [
        "scan_detail",
        "literal_comprehension",
        "skim_gist",
    ]


def test_extra_subskill_priority_targets_higher_level_subskills():
    blueprint = _blueprint(
        cefr_level="C1",
        internal_stage="Advanced",
        reading_subskills=["scan_detail", "vocab_in_context", "infer_meaning", "author_purpose"],
        target_subskills=[],
    )

    assert reading_service._prioritized_subskills_for_questions(blueprint)[:3] == [
        "infer_meaning",
        "author_purpose",
        "vocab_in_context",
    ]


def test_target_subskills_still_take_priority_over_extra_distribution():
    blueprint = _blueprint(
        cefr_level="C1",
        internal_stage="Advanced",
        reading_subskills=["scan_detail", "vocab_in_context", "infer_meaning", "author_purpose"],
        target_subskills=["scan_detail"],
    )

    assert reading_service._prioritized_subskills_for_questions(blueprint)[0] == "scan_detail"


def test_readiness_question_count_policy_preserves_comprehensive_coverage():
    assert reading_service.get_readiness_question_count("B1") == 12
    question_types = reading_service.question_types_for_count(12, mode="readiness")

    assert len(question_types) == 12
    assert set(reading_service.QUESTION_TYPES).issubset(set(question_types))


def test_validation_rejects_malformed_activity():
    result = validate_generated_activity({"passage": ""}, _blueprint())

    assert result.valid is False
    assert any(issue.code == "invalid_shape" for issue in result.issues)


def test_validation_rejects_unsupported_question_type():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["questions"][0]["type"] = "matching_headings"

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "unsupported_question_type" for issue in result.issues)


def test_validator_rejects_wrong_question_counts():
    blueprint = _blueprint(
        question_count=5,
        number_of_questions=5,
        question_types=reading_service.question_types_for_count(5, mode="practice"),
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["questions"] = activity["questions"][:-1]

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "question_count_mismatch" for issue in result.issues)


def test_validator_rejects_missing_required_practice_question_types():
    blueprint = _blueprint(
        question_types=["mcq", "mcq", "true_false", "short_answer"],
        number_of_questions=4,
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "missing_required_question_types" for issue in result.issues)


def test_validator_rejects_missing_target_subskills():
    blueprint = _blueprint(
        target_subskills=["infer_meaning"],
        reading_subskills=["skim_gist", "scan_detail", "infer_meaning", "literal_comprehension"],
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    for question in activity["questions"]:
        question["subskill"] = "scan_detail"

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "target_subskills_missing" for issue in result.issues)


def test_validation_rejects_missing_answer_keys():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["questions"][0]["answer_key"] = None

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "missing_answer_key" for issue in result.issues)


def test_validation_rejects_answer_leakage():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["questions"][0]["stem"] = "Mira learns helpful ways to read more confidently."

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "answer_leakage" for issue in result.issues)


def test_validation_rejects_gap_fill_without_visible_blank_sentence():
    blueprint = _blueprint(question_types=["gap_fill"], number_of_questions=1)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    question = activity["questions"][0]
    question["stem"] = "Complete the missing word from the passage."
    question["sentence_with_blank"] = None

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "missing_gap_fill_sentence" for issue in result.issues)


def test_validation_rejects_gap_fill_with_multiple_blanks():
    blueprint = _blueprint(question_types=["gap_fill"], number_of_questions=1)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["questions"][0]["sentence_with_blank"] = "Mira checks ____ and writes ____."

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is False
    assert any(issue.code == "invalid_gap_fill_blank" for issue in result.issues)


def test_validation_warns_for_repeated_recent_title_and_topic_tags():
    blueprint = _blueprint(
        recent_titles=["Anna's Daily Study Routine"],
        recent_topics=["daily English study"],
        recent_topic_tags=[["daily_study"]],
        recent_passage_summaries=["Anna studies English in the library and writes new words."],
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["title"] = "Anna Daily Study Routine"
    activity["topic"] = "daily English study"
    activity["topic_tags"] = ["daily_study"]
    activity["diversity_metadata"]["topic_tags"] = ["daily_study"]

    result = validate_generated_activity(activity, blueprint)

    assert result.valid is True
    warning_codes = {warning.code for warning in result.warnings}
    assert "repeated_or_similar_title" in warning_codes
    assert "repeated_topic_tags" in warning_codes
    assert "repeated_study_routine_pattern" in warning_codes


def test_deterministic_scoring_works_for_mvp_question_types():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint)

    score, results = score_generated_activity(
        activity,
        {
            "q1": {"choice_id": "a"},
            "q2": True,
            "q3": "Margin!",
            "q4": "She checks the title first.",
        },
    )

    assert score == 100.0
    assert [result.question_type for result in results] == ["mcq", "true_false", "gap_fill", "short_answer"]
    assert all(result.correct for result in results)
    assert results[0].student_answer == "Mira learns helpful ways to read more confidently."
    assert results[0].expected_answer == "Mira learns helpful ways to read more confidently."
    assert results[2].expected_answer == "margin"
    assert results[3].explanation


def test_post_submit_results_keep_allowed_feedback_fields():
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint)

    score, results = score_generated_activity(
        activity,
        {
            "q1": {"choice_id": "b"},
            "q2": False,
            "q3": "wrong",
            "q4": "wrong",
        },
    )

    assert score < 100.0
    assert any(result.student_answer for result in results)
    assert any(result.expected_answer for result in results)
    assert any(result.explanation for result in results)


def test_generated_practice_with_extra_questions_uses_supported_types_and_scores():
    blueprint = _blueprint(
        cefr_level="B2",
        internal_stage="Advanced",
        question_count=7,
        number_of_questions=7,
        question_types=reading_service.question_types_for_count(7, mode="practice"),
        reading_subskills=["scan_detail", "vocab_in_context", "infer_meaning", "author_purpose"],
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()

    result = validate_generated_activity(activity, blueprint)
    answers = _answers_for_activity(activity)
    score, question_results = score_generated_activity(activity, answers)
    question_type_summary = reading_service._aggregate_results(question_results, "question_type")

    assert result.valid is True
    assert len(activity["questions"]) == 7
    assert set(reading_service.REQUIRED_PRACTICE_QUESTION_TYPES).issubset(
        {question["type"] for question in activity["questions"]}
    )
    assert {question["type"] for question in activity["questions"]}.issubset(set(reading_service.QUESTION_TYPES))
    assert score == 100.0
    assert len(question_results) == 7
    assert question_type_summary["mcq"]["total"] > 1
    assert question_type_summary["short_answer"]["total"] > 1


def test_answer_key_stripping_works_with_adaptive_question_counts():
    blueprint = _blueprint(
        cefr_level="C2",
        internal_stage="Advanced",
        question_count=8,
        number_of_questions=8,
        question_types=reading_service.question_types_for_count(8, mode="practice"),
        reading_subskills=["scan_detail", "vocab_in_context", "infer_meaning", "author_purpose"],
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()

    stripped = reading_service.strip_answer_keys(activity)

    assert len(stripped["questions"]) == 8
    assert "answer_key" not in str(stripped)
    assert "accepted_answers" not in str(stripped)
    assert "required_key_terms" not in str(stripped)


def test_pre_submit_payload_strips_answer_help_fields_and_choice_markers():
    blueprint = _blueprint(
        cefr_level="C2",
        internal_stage="Advanced",
        question_count=8,
        number_of_questions=8,
        question_types=reading_service.question_types_for_count(8, mode="practice"),
        reading_subskills=["scan_detail", "vocab_in_context", "infer_meaning", "author_purpose"],
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    activity["validation_metadata"]["private_generation_metadata"] = {"seed": "hidden"}
    activity["questions"][0].update(
        {
            "feedback": "Private feedback before submit",
            "rationale": "The first option is correct.",
            "expected_answer": "The hidden answer",
            "correct_answer": "The hidden answer",
            "correct_option": "a",
            "correct_option_index": 0,
            "rubric": {"private": True},
            "scoring": {"private": True},
            "scoring_metadata": {"private": True},
            "private_generation_metadata": {"private": True},
        }
    )
    activity["questions"][0]["choices"][0].update(
        {
            "correct": True,
            "is_correct": True,
            "correct_option": True,
            "scoring_metadata": {"private": True},
        }
    )

    stripped = reading_service.strip_answer_keys(activity)
    stripped_keys = _nested_keys(stripped)
    stripped_gap_fill = next(question for question in stripped["questions"] if question["type"] == "gap_fill")

    assert len(stripped["questions"]) == 8
    assert stripped["questions"][0]["choices"][0] == {
        "id": "a",
        "text": "Mira learns helpful ways to read more confidently.",
    }
    assert stripped_gap_fill["sentence_with_blank"].count("____") == 1
    assert not stripped_keys.intersection(reading_service.PRE_SUBMIT_ANSWER_HELP_FIELDS)
    assert "validation_metadata" not in stripped
    assert "diversity_metadata" not in stripped


def test_missing_answers_are_scored_incorrect_with_adaptive_question_counts():
    blueprint = _blueprint(
        question_count=5,
        number_of_questions=5,
        question_types=reading_service.question_types_for_count(5, mode="practice"),
    )
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    answers = _answers_for_activity(activity)
    answers.pop("q5")

    score, question_results = score_generated_activity(activity, answers)

    assert len(question_results) == 5
    assert question_results[-1].correct is False
    assert score < 100.0


def test_short_answer_scoring_accepts_meaningful_phrase_variants():
    blueprint = _blueprint(question_types=["short_answer"], number_of_questions=1)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    question = activity["questions"][0]
    question["stem"] = "Where does the student study English?"
    question["answer_key"] = {
        "accepted_answers": ["at home", "the student studies at home", "she studies at home"],
        "required_key_terms": ["home"],
    }

    score, results = score_generated_activity(activity, {"q1": "home"})

    assert score == 100.0
    assert results[0].correct is True
    assert results[0].student_answer == "home"
    assert results[0].expected_answer == "at home / the student studies at home / she studies at home"


def test_short_answer_scoring_accepts_simple_inflection_variants():
    blueprint = _blueprint(question_types=["short_answer"], number_of_questions=1)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    question = activity["questions"][0]
    question["stem"] = "What does the family do after Ben helps put the food away?"
    question["answer_key"] = {
        "accepted_answers": ["eat a snack and rest", "they eat a snack and rest", "eat a snack"],
        "required_key_terms": ["eat snack", "rest"],
    }

    score, results = score_generated_activity(activity, {"q1": "the family eats a snack and rests."})

    assert score == 100.0
    assert results[0].correct is True


def test_short_answer_scoring_rejects_unrelated_answers():
    blueprint = _blueprint(question_types=["short_answer"], number_of_questions=1)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    question = activity["questions"][0]
    question["stem"] = "What does the family do after Ben helps put the food away?"
    question["answer_key"] = {
        "accepted_answers": ["eat a snack and rest", "they eat a snack and rest", "eat a snack"],
        "required_key_terms": ["eat snack", "rest"],
    }

    score, results = score_generated_activity(activity, {"q1": "They clean the table."})

    assert score == 0.0
    assert results[0].correct is False


def test_provider_selection_defaults_to_safe_local_mock(monkeypatch):
    monkeypatch.setattr(reading_service.settings, "READING_V2_GENERATION_PROVIDER", "local_mock")

    assert select_reading_v2_generation_provider() == "local_mock"

    monkeypatch.setattr(reading_service.settings, "READING_V2_GENERATION_PROVIDER", "ai")
    assert select_reading_v2_generation_provider() == "ai"

    monkeypatch.setattr(reading_service.settings, "READING_V2_GENERATION_PROVIDER", "unknown")
    assert select_reading_v2_generation_provider() == "local_mock"


def test_ai_prompt_contains_required_blueprint_controls():
    prompt = reading_v2_generation_prompt(
        _blueprint(
            recent_titles=["Mia's Daily English Study"],
            recent_topics=["daily English study"],
            recent_topic_tags=[["school_study_routine"]],
            recent_passage_summaries=["Mia studies English in the library."],
            recent_character_names=["Mia"],
            recent_question_stems=["Where does Mia study English?"],
            preferred_topic_rotation=["family meal", "bus ride"],
            target_subskills=["skim_gist"],
            under_sampled_subskills=["skim_gist"],
            weak_subskills=[],
            subskill_targeting_reason="Prioritize core reading subskills that need more evidence.",
        )
    )
    prompt_text = f"{prompt['system']}\n{prompt['user']}"

    for required in [
        "cefr_level",
        "internal_stage",
        "word_count_min",
        "word_count_max",
        "sentence_complexity",
        "vocabulary_difficulty",
        "target_vocab_tags",
        "required_vocab_items",
        "target_grammar_tags",
        "banned_above_level_grammar",
        "reading_subskills",
        "question_types",
        "student_interest",
        "difficulty_score",
        "inference_depth",
        "question_count",
        "number_of_questions",
        "passage_difficulty_policy",
        "safety_topic_restrictions",
        "sentence count",
        "lexical diversity",
        "For B1",
        "For B2",
        "For C1",
        "For C2",
        "Do not pad the passage",
        "sentence_with_blank",
        "exactly one visible ____ marker",
        "For A1 Beginner",
        "avoid abstract wording",
        "common natural variants",
        "required_key_terms like \"eat snack\" and \"rest\"",
        "eat/eats",
        "rest/rests",
        "recent_titles",
        "recent_topics",
        "recent_topic_tags",
        "recent_character_names",
        "preferred_topic_rotation",
        "Do not repeat recent topics",
        "Do not reuse the same character names",
        "Do not generate another school/study/library/new-words routine",
        "family meal",
        "bus ride",
        "topic_tags",
        "diversity_metadata",
        "target_subskills",
        "under_sampled_subskills",
        "weak_subskills",
        "subskill_targeting_reason",
        "What is the passage mainly about?",
        "What is the best title?",
        "Return valid JSON only",
    ]:
        assert required in prompt_text


async def test_valid_ai_json_becomes_usable_generation(monkeypatch):
    blueprint = _blueprint()
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()

    async def fake_generate_llm_json(*_args, **_kwargs):
        return json.dumps(activity)

    monkeypatch.setattr(reading_service, "generate_llm_json", fake_generate_llm_json)

    outcome = await generate_activity_with_ai_provider(blueprint)

    assert outcome.validation.valid is True
    assert outcome.provider_name == "ai"
    assert outcome.model_used == reading_service.reading_v2_ai_model_name()
    assert outcome.retry_count == 0
    assert outcome.activity
    assert outcome.activity["validation_metadata"]["provider"] == "ai"


async def test_invalid_ai_json_triggers_retry_then_valid_generation(monkeypatch):
    blueprint = _blueprint()
    valid_activity = generate_reading_activity_from_blueprint(blueprint).model_dump()
    calls = []

    async def fake_generate_llm_json(prompt, **kwargs):
        calls.append({"prompt": prompt, "kwargs": kwargs})
        if len(calls) == 1:
            invalid = dict(valid_activity)
            invalid["cefr_level"] = "B1"
            return json.dumps(invalid)
        return json.dumps(valid_activity)

    monkeypatch.setattr(reading_service.settings, "READING_V2_AI_MAX_RETRIES", 2)
    monkeypatch.setattr(reading_service, "generate_llm_json", fake_generate_llm_json)

    outcome = await generate_activity_with_ai_provider(blueprint)

    assert outcome.validation.valid is True
    assert outcome.retry_count == 1
    assert len(calls) == 2
    assert "Validation errors from the previous generated JSON" in calls[1]["prompt"]


async def test_invalid_ai_json_after_max_retries_fails_gracefully(monkeypatch):
    blueprint = _blueprint()

    async def fake_generate_llm_json(*_args, **_kwargs):
        return "not json"

    monkeypatch.setattr(reading_service.settings, "READING_V2_AI_MAX_RETRIES", 1)
    monkeypatch.setattr(reading_service, "generate_llm_json", fake_generate_llm_json)

    outcome = await generate_activity_with_ai_provider(blueprint)

    assert outcome.validation.valid is False
    assert outcome.retry_count == 1
    assert outcome.activity is None
    assert any(issue.code == "invalid_json" for issue in outcome.validation.issues)


async def test_initial_overview_creates_safe_state(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Beginner"
    assert overview.next_action == "practice"
    stored = (
        await postgres_session.execute(
            select(LanguageReadingV2StudentState).where(
                LanguageReadingV2StudentState.student_id == student_id,
                LanguageReadingV2StudentState.language_id == language_id,
            )
        )
    ).scalar_one()
    assert stored.status == "active"


async def test_path_returns_all_cefr_levels_and_stages(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)

    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)

    assert len(path.stages) == len(CEFR_LEVELS) * len(INTERNAL_STAGES)
    assert {(stage.cefr_level, stage.internal_stage) for stage in path.stages} == {
        (level, internal_stage) for level in CEFR_LEVELS for internal_stage in INTERNAL_STAGES
    }


async def test_parallel_overview_and_path_create_initial_state_once(postgres_session_factory):
    async with postgres_session_factory() as setup:
        student_id, language_id = await _student_and_language(setup)
        await setup.commit()

    async def load_overview():
        async with postgres_session_factory() as db:
            result = await build_reading_v2_overview(db, student_id=student_id, language_id=language_id)
            await db.commit()
            return result

    async def load_path():
        async with postgres_session_factory() as db:
            result = await build_reading_v2_path(db, student_id=student_id, language_id=language_id)
            await db.commit()
            return result

    overview, path = await asyncio.gather(load_overview(), load_path())

    assert overview.current_cefr == "A1"
    assert len(path.stages) == len(CEFR_LEVELS) * len(INTERNAL_STAGES)
    async with postgres_session_factory() as db:
        rows = (
            await db.execute(
                select(LanguageReadingV2StudentState).where(
                    LanguageReadingV2StudentState.student_id == student_id,
                    LanguageReadingV2StudentState.language_id == language_id,
                )
            )
        ).scalars().all()
    assert len(rows) == 1


async def test_generation_blueprint_matches_student_level_and_stage(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.B1)

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert blueprint.cefr_level == "B1"
    assert blueprint.internal_stage == "Beginner"
    assert blueprint.word_count_min < blueprint.word_count_max
    assert set(["mcq", "gap_fill", "true_false", "short_answer"]).issubset(set(blueprint.question_types))


async def test_a1_beginner_blueprint_uses_short_simple_constraints(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A1)

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert blueprint.cefr_level == "A1"
    assert blueprint.internal_stage == "Beginner"
    assert blueprint.word_count_min == 55
    assert blueprint.word_count_max == 80
    assert "simple_present" in blueprint.sentence_complexity
    assert "concrete" in blueprint.vocabulary_difficulty
    assert "family meal" in blueprint.preferred_topic_rotation


async def test_generation_blueprint_includes_recent_activity_context(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A1)
    await reading_service.get_or_create_student_state(postgres_session, student_id=student_id, language_id=language_id)
    activity = generate_reading_activity_from_blueprint(_blueprint(cefr_level="A1", internal_stage="Beginner")).model_dump()
    activity.update(
        {
            "title": "Mia's Daily English Study",
            "topic": "daily English study",
            "topic_tags": ["school_study_routine"],
            "diversity_metadata": {
                "topic_tags": ["school_study_routine"],
                "character_names": ["Mia"],
                "passage_summary": "Mia studies English at school and writes new words.",
            },
        }
    )
    activity["questions"][0]["stem"] = "Where does Mia study English?"
    postgres_session.add(
        LanguageReadingV2Attempt(
            student_id=student_id,
            language_id=language_id,
            cefr_level=LanguageLevel.A1,
            internal_stage="Beginner",
            mode="practice",
            status="submitted",
            generation_blueprint_json={"cefr_level": "A1", "internal_stage": "Beginner"},
            generated_activity_json=activity,
            validation_result_json={"valid": True, "issues": [], "warnings": []},
            model_used="test",
            prompt_version=reading_service.PROMPT_VERSION,
            validator_version="reading_v2_validator_r1",
            score_percent=80,
        )
    )
    await postgres_session.flush()

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert "Mia's Daily English Study" in blueprint.recent_titles
    assert "daily English study" in blueprint.recent_topics
    assert ["school_study_routine"] in blueprint.recent_topic_tags
    assert "Mia" in blueprint.recent_character_names
    assert "Where does Mia study English?" in blueprint.recent_question_stems


async def test_attempt_creation_stores_snapshots_and_strips_student_keys(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A2)

    out = await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id)

    stored = (
        await postgres_session.execute(
            select(LanguageReadingV2Attempt).where(LanguageReadingV2Attempt.id == out.attempt_id)
        )
    ).scalar_one()
    assert stored.generation_blueprint_json["cefr_level"] == "A2"
    assert stored.generation_blueprint_json["generation_provider"] == "local_mock"
    assert stored.generation_blueprint_json["generation_retry_count"] == 0
    assert stored.generated_activity_json["questions"]
    assert stored.validation_result_json["valid"] is True
    assert stored.validation_result_json["generation_provider"] == "local_mock"
    assert stored.model_used == "local_mock"
    assert any(question.get("answer_key") for question in stored.generated_activity_json["questions"])
    assert any(question.get("explanation") for question in stored.generated_activity_json["questions"])
    assert all("answer_key" not in question for question in out.activity["questions"])
    assert not _nested_keys(out.activity).intersection(reading_service.PRE_SUBMIT_ANSWER_HELP_FIELDS)
    assert all(set(choice) == {"id", "text"} for question in out.activity["questions"] for choice in question.get("choices", []))


async def test_attempt_creation_uses_configured_ai_provider_with_mocked_ai(monkeypatch, postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A2)
    blueprint = await build_generation_blueprint(postgres_session, student_id=student_id, language_id=language_id)
    activity = generate_reading_activity_from_blueprint(blueprint).model_dump()

    async def fake_generate_llm_json(*_args, **_kwargs):
        return json.dumps(activity)

    monkeypatch.setattr(reading_service.settings, "READING_V2_GENERATION_PROVIDER", "ai")
    monkeypatch.setattr(reading_service.settings, "READING_V2_AI_MAX_RETRIES", 1)
    monkeypatch.setattr(reading_service.settings, "READING_V2_AI_MODEL", "test-ai-model")
    monkeypatch.setattr(reading_service, "generate_llm_json", fake_generate_llm_json)

    out = await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id)

    stored = (
        await postgres_session.execute(
            select(LanguageReadingV2Attempt).where(LanguageReadingV2Attempt.id == out.attempt_id)
        )
    ).scalar_one()
    assert stored.status == "ready"
    assert stored.model_used == "test-ai-model"
    assert stored.generation_blueprint_json["generation_provider"] == "ai"
    assert stored.validation_result_json["generation_provider"] == "ai"
    assert all("answer_key" not in question for question in out.activity["questions"])


async def test_failed_generation_does_not_create_usable_attempt(monkeypatch, postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A2)

    async def fake_generate_llm_json(*_args, **_kwargs):
        return "not json"

    monkeypatch.setattr(reading_service.settings, "READING_V2_GENERATION_PROVIDER", "ai")
    monkeypatch.setattr(reading_service.settings, "READING_V2_AI_MAX_RETRIES", 0)
    monkeypatch.setattr(reading_service, "generate_llm_json", fake_generate_llm_json)

    with pytest.raises(HTTPException):
        await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id)

    rows = (
        await postgres_session.execute(
            select(LanguageReadingV2Attempt).where(
                LanguageReadingV2Attempt.student_id == student_id,
                LanguageReadingV2Attempt.language_id == language_id,
            )
        )
    ).scalars().all()
    assert rows
    assert all(row.status == "generation_failed" for row in rows)
    assert all(row.submitted_at is None for row in rows)


async def test_xp_alone_does_not_progress_stage(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)

    await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    progress = (
        await postgres_session.execute(
            select(LanguageReadingV2StageProgress).where(
                LanguageReadingV2StageProgress.student_id == student_id,
                LanguageReadingV2StageProgress.language_id == language_id,
                LanguageReadingV2StageProgress.cefr_level == LanguageLevel.A1,
                LanguageReadingV2StageProgress.internal_stage == "Beginner",
            )
        )
    ).scalar_one()
    progress.status = "current"
    progress.attempts_completed = 99
    progress.mastery_score = 100.0
    progress.subskill_mastery_json = {}
    progress.question_type_mastery_json = {}
    progress.recent_attempt_ids_json = []
    await postgres_session.flush()

    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    current = [stage for stage in path.stages if stage.status == "current"]
    assert [(stage.cefr_level, stage.internal_stage) for stage in current] == [("A1", "Beginner")]
    assert overview.current_stage == "Beginner"
    assert "min_5_submitted_practice_attempts" in overview.recent_mastery["current_stage_evidence"]["blocking_reasons"]


async def test_fewer_than_5_attempts_cannot_progress(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)

    for _ in range(4):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Beginner"
    assert overview.recent_mastery["evidence_sufficient"] is False
    assert "min_5_submitted_practice_attempts" in overview.recent_mastery["current_stage_evidence"]["blocking_reasons"]


async def test_low_recent_score_blocks_progression(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)

    for _ in range(4):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)
    await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id, wrong_count=2)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert overview.current_stage == "Beginner"
    reasons = overview.recent_mastery["current_stage_evidence"]["blocking_reasons"]
    assert "no_recent_attempt_below_70" in reasons


async def test_one_weak_subskill_blocks_progression(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)

    await _create_and_submit_practice(
        postgres_session, student_id=student_id, language_id=language_id, wrong_subskills={"skim_gist"}
    )
    await _create_and_submit_practice(
        postgres_session, student_id=student_id, language_id=language_id, wrong_subskills={"skim_gist"}
    )
    for _ in range(3):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert overview.current_stage == "Beginner"
    evidence = overview.recent_mastery["current_stage_evidence"]
    assert evidence["core_subskill_scores"]["skim_gist"] < 70.0
    assert "each_core_subskill_at_least_70" in evidence["blocking_reasons"]


async def test_one_wrong_under_sampled_subskill_is_not_marked_weak(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False],
    )

    evidence = await reading_service.evaluate_stage_evidence(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level="A1",
        internal_stage="Beginner",
    )

    assert "skim_gist" in {item["name"] for item in evidence["under_sampled_subskills"]}
    assert "skim_gist" not in {item["name"] for item in evidence["weak_subskills"]}
    assert "each_core_subskill_has_min_evidence" in evidence["advisory_reasons"]
    assert "each_core_subskill_has_min_evidence" not in evidence["blocking_reasons"]
    assert "each_core_subskill_at_least_70" not in evidence["blocking_reasons"]


async def test_two_question_subskill_is_under_sampled_not_weak(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False, True],
    )

    evidence = await reading_service.evaluate_stage_evidence(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level="A1",
        internal_stage="Beginner",
    )

    assert "skim_gist" in {item["name"] for item in evidence["under_sampled_subskills"]}
    assert "skim_gist" not in {item["name"] for item in evidence["weak_subskills"]}
    assert "each_core_subskill_has_min_evidence" in evidence["advisory_reasons"]
    assert "each_core_subskill_has_min_evidence" not in evidence["blocking_reasons"]


async def test_sufficient_low_subskill_evidence_blocks_as_weak(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False, False, True],
    )

    evidence = await reading_service.evaluate_stage_evidence(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level="A1",
        internal_stage="Beginner",
    )

    assert "skim_gist" not in {item["name"] for item in evidence["under_sampled_subskills"]}
    assert "skim_gist" in {item["name"] for item in evidence["weak_subskills"]}
    assert "each_core_subskill_at_least_70" in evidence["blocking_reasons"]


async def test_sufficient_passing_subskill_evidence_does_not_block(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[True, True, True, False],
    )

    evidence = await reading_service.evaluate_stage_evidence(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level="A1",
        internal_stage="Beginner",
    )

    assert "skim_gist" not in {item["name"] for item in evidence["under_sampled_subskills"]}
    assert "skim_gist" not in {item["name"] for item in evidence["weak_subskills"]}
    assert "each_core_subskill_has_min_evidence" not in evidence["advisory_reasons"]
    assert "each_core_subskill_has_min_evidence" not in evidence["blocking_reasons"]
    assert "each_core_subskill_at_least_70" not in evidence["blocking_reasons"]


async def test_under_sampled_subskills_target_next_generation_blueprint(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False],
    )

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert "skim_gist" in blueprint.under_sampled_subskills
    assert "skim_gist" in blueprint.target_subskills
    assert "more evidence" in (blueprint.subskill_targeting_reason or "")


async def test_weak_subskills_target_next_generation_blueprint(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False, False, True],
    )

    blueprint = await build_generation_blueprint(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )

    assert "skim_gist" in blueprint.weak_subskills
    assert "skim_gist" in blueprint.target_subskills
    assert "low scores" in (blueprint.subskill_targeting_reason or "")


async def test_enough_evidence_unlocks_next_internal_stage(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)

    result = None
    for _ in range(5):
        result = await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)

    assert result is not None
    assert result.state["current_stage"] == "Intermediate"
    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Intermediate"
    by_stage = {(stage.cefr_level, stage.internal_stage): stage for stage in path.stages}
    assert by_stage[("A1", "Beginner")].status == "mastered"
    assert by_stage[("A1", "Intermediate")].status == "current"
    assert by_stage[("A1", "Advanced")].status == "locked"
    assert overview.readiness_available is False
    assert overview.readiness_blocked_reason == "advanced_stage_not_mastered"


async def test_under_sampled_subskill_does_not_block_stage_advancement(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _insert_balanced_subskill_attempts(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        skim_results=[False, True],
    )

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    by_stage = {(stage.cefr_level, stage.internal_stage): stage for stage in path.stages}

    assert overview.current_stage == "Intermediate"
    assert by_stage[("A1", "Beginner")].status == "mastered"
    assert by_stage[("A1", "Intermediate")].status == "current"


async def test_stale_mastered_beginner_state_is_reconciled_to_intermediate(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)

    for _ in range(5):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    state = await reading_service.get_or_create_student_state(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
    )
    state.current_cefr = LanguageLevel.A1
    state.current_stage = "Beginner"
    state.readiness_target_level = None
    state.unlocked_rank = reading_service.stage_rank(LanguageLevel.A1, "Beginner")
    beginner = await reading_service.get_or_create_stage_progress(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level=LanguageLevel.A1,
        internal_stage="Beginner",
    )
    beginner.status = "current"
    beginner.mastered_at = None
    intermediate = await reading_service.get_or_create_stage_progress(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr_level=LanguageLevel.A1,
        internal_stage="Intermediate",
    )
    intermediate.status = "locked"
    await postgres_session.flush()

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    by_stage = {(stage.cefr_level, stage.internal_stage): stage for stage in path.stages}

    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Intermediate"
    assert overview.readiness_available is False
    assert by_stage[("A1", "Beginner")].status == "mastered"
    assert by_stage[("A1", "Intermediate")].status == "current"
    assert by_stage[("A1", "Advanced")].status == "locked"
    assert by_stage[("A2", "Beginner")].status == "locked"


async def test_intermediate_mastery_advances_to_advanced(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Intermediate",
    )

    for _ in range(5):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    by_stage = {(stage.cefr_level, stage.internal_stage): stage for stage in path.stages}

    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Advanced"
    assert overview.readiness_available is False
    assert overview.readiness_blocked_reason == "advanced_stage_not_mastered"
    assert by_stage[("A1", "Intermediate")].status == "mastered"
    assert by_stage[("A1", "Advanced")].status == "current"


async def test_advanced_mastery_unlocks_readiness(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Advanced",
    )

    for _ in range(5):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    advanced = [stage for stage in path.stages if stage.cefr_level == "A1" and stage.internal_stage == "Advanced"][0]
    a2_beginner = [stage for stage in path.stages if stage.cefr_level == "A2" and stage.internal_stage == "Beginner"][0]

    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Advanced"
    assert overview.readiness_available is True
    assert overview.readiness_target_level == "A2"
    assert overview.next_action == "readiness"
    assert advanced.status == "mastered"
    assert a2_beginner.status == "locked"


async def test_readiness_unavailable_before_advanced_mastery(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)

    with pytest.raises(HTTPException) as exc:
        await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id, mode="readiness")

    assert exc.value.status_code == 409
    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    assert overview.readiness_available is False
    assert overview.readiness_blocked_reason == "advanced_stage_not_mastered"


async def test_readiness_pass_unlocks_next_cefr_beginner(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Advanced",
        readiness_target=LanguageLevel.A2,
        stage_status="mastered",
    )

    result = await _create_and_submit_readiness(postgres_session, student_id=student_id, language_id=language_id)
    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert result.passed is True
    assert overview.current_cefr == "A2"
    assert overview.current_stage == "Beginner"
    assert overview.readiness_target_level is None


async def test_readiness_fail_keeps_advanced_and_blocks_retake(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Advanced",
        readiness_target=LanguageLevel.A2,
        stage_status="mastered",
    )

    result = await _create_and_submit_readiness(
        postgres_session, student_id=student_id, language_id=language_id, wrong_count=4
    )
    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert result.passed is False
    assert overview.current_cefr == "A1"
    assert overview.current_stage == "Advanced"
    assert overview.readiness_available is False
    assert overview.readiness_blocked_reason == "readiness_retake_requires_more_practice"

    with pytest.raises(HTTPException) as exc:
        await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id, mode="readiness")
    assert exc.value.status_code == 409


async def test_readiness_retake_blocked_until_3_more_advanced_practice_attempts(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Advanced",
        readiness_target=LanguageLevel.A2,
        stage_status="mastered",
    )
    await _create_and_submit_readiness(postgres_session, student_id=student_id, language_id=language_id, wrong_count=4)

    for _ in range(2):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)
    with pytest.raises(HTTPException):
        await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id, mode="readiness")

    await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)
    readiness = await create_reading_v2_attempt(postgres_session, student_id=student_id, language_id=language_id, mode="readiness")

    assert readiness.mode == "readiness"
    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    assert overview.readiness_available is True


async def test_c2_advanced_mastery_marks_final_mastered_state(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.C2,
        stage="Advanced",
    )

    for _ in range(5):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)

    assert overview.current_cefr == "C2"
    assert overview.current_stage == "Advanced"
    assert overview.status == "mastered"
    assert overview.readiness_available is False
    assert overview.recent_mastery["readiness"]["blocked_reason"] == "reading_v2_mastered"


async def test_overview_and_path_reflect_readiness_and_locked_states(monkeypatch, postgres_session):
    _install_unique_mock_generator(monkeypatch)
    student_id, language_id = await _student_and_language(postgres_session)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A1,
        stage="Advanced",
    )

    for _ in range(5):
        await _create_and_submit_practice(postgres_session, student_id=student_id, language_id=language_id)

    overview = await build_reading_v2_overview(postgres_session, student_id=student_id, language_id=language_id)
    path = await build_reading_v2_path(postgres_session, student_id=student_id, language_id=language_id)
    by_stage = {(stage.cefr_level, stage.internal_stage): stage for stage in path.stages}

    assert overview.recent_mastery["readiness"]["available"] is True
    assert by_stage[("A1", "Advanced")].status == "mastered"
    assert by_stage[("A2", "Beginner")].status == "locked"
    assert by_stage[("A2", "Beginner")].recent_mastery["locked_reason"] == "previous_stage_not_mastered"


async def test_readiness_mode_is_stored_separately_from_practice_mode(postgres_session):
    student_id, language_id = await _student_and_language(postgres_session, reading_level=LanguageLevel.A2)
    await _move_to_stage(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        cefr=LanguageLevel.A2,
        stage="Advanced",
        readiness_target=LanguageLevel.B1,
        stage_status="mastered",
    )

    readiness = await create_reading_v2_attempt(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        mode="readiness",
    )
    practice = await create_reading_v2_attempt(
        postgres_session,
        student_id=student_id,
        language_id=language_id,
        mode="practice",
    )

    rows = (
        await postgres_session.execute(
            select(LanguageReadingV2Attempt).where(
                LanguageReadingV2Attempt.id.in_([readiness.attempt_id, practice.attempt_id])
            )
        )
    ).scalars().all()
    by_id = {row.id: row for row in rows}
    assert by_id[readiness.attempt_id].mode == "readiness"
    assert by_id[readiness.attempt_id].target_next_cefr == LanguageLevel.B1
    assert by_id[practice.attempt_id].mode == "practice"
    assert by_id[practice.attempt_id].target_next_cefr is None
