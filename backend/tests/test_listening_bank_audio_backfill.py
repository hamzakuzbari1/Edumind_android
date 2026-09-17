"""Tests for the Listening bank-audio backfill service (persistent audio_meta_json caching).

Synthesis is always mocked here -- no real model download or real Supertonic call is required
to run this suite. The mock writes a small dummy file to whatever output_path it's given, exactly
matching the real synthesize_language_speech contract (write to output_path, return bool), so the
service's own post-synthesis validation (file exists, non-trivial size) exercises real code.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.api.language_exam import _cleanup_exam_audio
from app.core.config import get_settings
from app.models.language.catalog import Language
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services import language_listening_bank_audio_backfill_service as backfill_service
from app.services.language_listening_bank_audio_backfill_service import (
    compute_transcript_hash,
    expected_storage_key,
    run_backfill,
)

DUMMY_AUDIO_BYTES = b"RIFF" + b"\x00" * 600  # > MIN_VALID_AUDIO_BYTES, cheap fake "wav"


async def _make_language(postgres_session_factory) -> int:
    marker = uuid.uuid4().hex[:12]
    async with postgres_session_factory() as db:
        language = Language(code=f"lst-{marker}", name_en="English", name_ar="English", is_active=True)
        db.add(language)
        await db.commit()
        return language.id


async def _insert_listening_item(
    postgres_session_factory,
    *,
    language_id: int,
    level: str = "A2",
    transcript: str | None = "A short listening passage about daily routines.",
    is_active: bool = True,
    is_verified: bool = True,
    skill: str = "listening",
    audio_meta_json: dict | None = None,
    content_item_id: int | None = None,
    stray_audio_url: str | None = None,
    stable_key: str | None = None,
    source: str = "content_seed",
    question_type: str = "mcq",
    raw_body_json: object = None,
) -> int:
    if raw_body_json is not None:
        body: object = raw_body_json
    else:
        body = {}
        if transcript is not None:
            body["audio_transcript"] = transcript
        if content_item_id is not None:
            body["content_item_id"] = content_item_id
        if stray_audio_url is not None:
            body["audio_url"] = stray_audio_url
    async with postgres_session_factory() as db:
        item = LanguagePlacementQuestionBankItem(
            language_id=language_id,
            skill=skill,
            level=LanguageLevel(level),
            question_type=question_type,
            prompt_text="What is this text mainly about?",
            options_json=["Daily life", "Space travel", "Ancient history", "Cooking"] if question_type == "mcq" else None,
            correct_index=0 if question_type == "mcq" else None,
            source=source,
            stable_key=stable_key,
            is_verified=is_verified,
            is_active=is_active,
            body_json=body,
            audio_meta_json=audio_meta_json,
        )
        db.add(item)
        await db.commit()
        return item.id


async def _insert_content_item(postgres_session_factory, *, language_id: int, transcript: str | None) -> int:
    async with postgres_session_factory() as db:
        content = LanguageContentItem(
            language_id=language_id,
            skill=LanguageSkill.listening,
            level=LanguageLevel.A2,
            content_type="lesson",
            title="Listening lesson",
            body_json=({"audio_transcript": transcript} if transcript else {}),
        )
        db.add(content)
        await db.commit()
        return content.id


async def _get_item(postgres_session_factory, item_id: int) -> LanguagePlacementQuestionBankItem:
    async with postgres_session_factory() as db:
        return await db.get(LanguagePlacementQuestionBankItem, item_id)


async def _get_language_code(postgres_session_factory, language_id: int) -> str:
    async with postgres_session_factory() as db:
        return (await db.get(Language, language_id)).code


def _fake_synth(*, fail_marker: str | None = None, calls: list | None = None):
    async def _fake(text, *, language, output_path, voice_name=None):
        if calls is not None:
            calls.append(text)
        if fail_marker and fail_marker in text:
            return False
        output_path.write_bytes(DUMMY_AUDIO_BYTES)
        return True

    return _fake


# 1. Valid cached metadata + existing file -> skipped, no synthesis call.
@pytest.mark.postgresql
async def test_valid_cached_metadata_and_existing_file_is_skipped(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    transcript = "Valid cache hit passage."
    transcript_hash = compute_transcript_hash(transcript)
    settings = get_settings()
    voice = settings.LANGUAGE_SUPERTONIC_VOICE or "M1"
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript=transcript)
    storage_key = expected_storage_key(bank_item_id=item_id, transcript_hash=transcript_hash, engine="supertonic", voice=voice)
    dest = Path(settings.UPLOAD_DIR) / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(DUMMY_AUDIO_BYTES)
    async with postgres_session_factory() as db:
        row = await db.get(LanguagePlacementQuestionBankItem, item_id)
        row.audio_meta_json = {
            "public_url": "/uploads/" + storage_key,
            "storage_key": storage_key,
            "transcript_hash": transcript_hash,
            "engine": "supertonic",
            "voice": voice,
        }
        await db.commit()

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=(await db.get(Language, language_id)).code, apply=True)

    assert len(calls) == 0
    matching = [r for r in summary.results if r.bank_item_id == item_id]
    assert matching and matching[0].status == "skipped"
    dest.unlink(missing_ok=True)


# 2. A second identical run performs zero new synthesis calls.
@pytest.mark.postgresql
async def test_second_identical_run_performs_zero_synthesis_calls(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = (await _get_language_code(postgres_session_factory, language_id))
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Rerun idempotency passage.")

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))

    async with postgres_session_factory() as db:
        first = await run_backfill(db, language_code=language_code, apply=True)
    assert len(calls) == 1
    assert first.synthesized and first.synthesized[0].bank_item_id == item_id

    async with postgres_session_factory() as db:
        second = await run_backfill(db, language_code=language_code, apply=True)
    assert len(calls) == 1  # no new call on the second run
    assert second.skipped and second.skipped[0].bank_item_id == item_id


# 3. Missing metadata causes synthesis and metadata population.
@pytest.mark.postgresql
async def test_missing_metadata_causes_synthesis_and_population(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Fresh passage, no cache yet.")

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth())

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert summary.synthesized and summary.synthesized[0].bank_item_id == item_id
    row = await _get_item(postgres_session_factory, item_id)
    meta = row.audio_meta_json
    assert meta["public_url"].startswith("/uploads/language_placement_bank_audio/")
    assert meta["storage_key"].startswith("language_placement_bank_audio/")
    assert meta["engine"] == "supertonic"
    assert meta["voice"]
    assert meta["transcript_hash"]
    assert meta["source"] == "synthesized"


# 4. Stale transcript hash causes regeneration.
@pytest.mark.postgresql
async def test_stale_transcript_hash_causes_regeneration(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    item_id = await _insert_listening_item(
        postgres_session_factory,
        language_id=language_id,
        transcript="Current transcript text.",
        audio_meta_json={
            "public_url": "/uploads/language_placement_bank_audio/old/stale.wav",
            "storage_key": "language_placement_bank_audio/old/stale.wav",
            "transcript_hash": "deadbeef" * 8,  # deliberately wrong/stale
            "engine": "supertonic",
            "voice": get_settings().LANGUAGE_SUPERTONIC_VOICE or "M1",
        },
    )
    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert len(calls) == 1
    assert summary.synthesized and summary.synthesized[0].bank_item_id == item_id
    row = await _get_item(postgres_session_factory, item_id)
    assert row.audio_meta_json["transcript_hash"] != "deadbeef" * 8


# 5. Missing physical file causes regeneration even when metadata "matches".
@pytest.mark.postgresql
async def test_missing_physical_file_causes_regeneration(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    transcript = "Metadata present but file missing."
    transcript_hash = compute_transcript_hash(transcript)
    voice = get_settings().LANGUAGE_SUPERTONIC_VOICE or "M1"
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript=transcript)
    storage_key = expected_storage_key(bank_item_id=item_id, transcript_hash=transcript_hash, engine="supertonic", voice=voice)
    async with postgres_session_factory() as db:
        row = await db.get(LanguagePlacementQuestionBankItem, item_id)
        row.audio_meta_json = {
            "public_url": "/uploads/" + storage_key,
            "storage_key": storage_key,
            "transcript_hash": transcript_hash,
            "engine": "supertonic",
            "voice": voice,
        }
        await db.commit()
    # Deliberately do NOT create the file on disk.

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert len(calls) == 1
    assert summary.synthesized and summary.synthesized[0].bank_item_id == item_id


# 6. --force causes intentional regeneration even when cache is already valid.
@pytest.mark.postgresql
async def test_force_flag_causes_intentional_regeneration(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Force regen passage.")

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth())
    async with postgres_session_factory() as db:
        await run_backfill(db, language_code=language_code, apply=True)  # establish a valid cache first

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True, force=True)

    assert len(calls) == 1
    assert summary.synthesized and summary.synthesized[0].bank_item_id == item_id


# 7. A synthesis failure does not create invalid metadata.
@pytest.mark.postgresql
async def test_synthesis_failure_does_not_write_metadata(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="FAIL_ME passage.")

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(fail_marker="FAIL_ME"))
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert summary.failed and summary.failed[0].bank_item_id == item_id
    row = await _get_item(postgres_session_factory, item_id)
    assert row.audio_meta_json is None


# 8 & 9. A failure on one row does not block later rows, and earlier successes stay committed.
@pytest.mark.postgresql
async def test_failure_on_one_row_does_not_block_or_unwind_others(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    # Lower id (processed first, order_by id) is the one that fails.
    failing_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, level="A1", transcript="FAIL_ME first row.")
    succeeding_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, level="B1", transcript="Succeeds second row.")
    assert failing_id < succeeding_id

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(fail_marker="FAIL_ME"))
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert any(r.bank_item_id == failing_id for r in summary.failed)
    assert any(r.bank_item_id == succeeding_id for r in summary.synthesized)

    # Re-read from a brand new session/transaction -- proves the success was truly committed,
    # not just held in the in-memory ORM object from the same run.
    succeeding_row = await _get_item(postgres_session_factory, succeeding_id)
    assert succeeding_row.audio_meta_json is not None
    failing_row = await _get_item(postgres_session_factory, failing_id)
    assert failing_row.audio_meta_json is None


# 10. Generated bank-cache paths never match the two cleanup-managed prefixes.
def test_generated_paths_never_match_cleanup_prefixes():
    storage_key = expected_storage_key(bank_item_id=42, transcript_hash="a" * 64, engine="supertonic", voice="M1")
    public_url = "/uploads/" + storage_key
    assert not public_url.startswith("/uploads/language_exam_audio/")
    assert not public_url.startswith("/uploads/exam_audio/")
    assert storage_key.startswith("language_placement_bank_audio/42/")


# 11. _cleanup_exam_audio() does not delete a file under language_placement_bank_audio/.
def test_cleanup_exam_audio_does_not_delete_bank_cache_files():
    upload_dir = Path(get_settings().UPLOAD_DIR)
    storage_key = expected_storage_key(bank_item_id=777, transcript_hash="b" * 64, engine="supertonic", voice="M1")
    dest = upload_dir / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(DUMMY_AUDIO_BYTES)
    try:
        state = {"listening": {"pool": {"A2": {"audio_url": "/uploads/" + storage_key}}}}
        _cleanup_exam_audio(state)
        assert dest.exists()
    finally:
        dest.unlink(missing_ok=True)


# 12. Only active, verified Listening rows with valid transcripts are processed.
@pytest.mark.postgresql
async def test_only_active_verified_listening_rows_with_transcript_are_processed(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    eligible_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Eligible passage.")
    inactive_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Inactive passage.", is_active=False)
    unverified_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Unverified passage.", is_verified=False)
    other_skill_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript="Reading passage.", skill="reading")

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth())
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    processed_ids = {r.bank_item_id for r in summary.results}
    assert eligible_id in processed_ids
    assert inactive_id not in processed_ids
    assert unverified_id not in processed_ids
    assert other_skill_id not in processed_ids


# 13. The six incomplete scaffold rows (real shape: audio_url to an unreachable prefix, no
# transcript) remain unchanged -- resolved as no_transcript, never touched.
@pytest.mark.postgresql
async def test_scaffold_rows_without_a_transcript_remain_unchanged(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    scaffold_id = await _insert_listening_item(
        postgres_session_factory,
        language_id=language_id,
        transcript=None,
        stray_audio_url="/language-assets/en/lessons/listening/a1-01.mp3",
    )

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert len(calls) == 0
    matching = [r for r in summary.results if r.bank_item_id == scaffold_id]
    assert matching and matching[0].status == "no_transcript"
    row = await _get_item(postgres_session_factory, scaffold_id)
    assert row.audio_meta_json is None
    assert row.is_active is True and row.is_verified is True  # left completely untouched


# Content-item transcript fallback path (same resolution order the live exam trusts).
@pytest.mark.postgresql
async def test_transcript_resolves_via_linked_content_item_when_bank_row_has_none(monkeypatch, postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    content_id = await _insert_content_item(postgres_session_factory, language_id=language_id, transcript="Transcript lives on the content item.")
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript=None, content_item_id=content_id)

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth())
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, apply=True)

    assert summary.synthesized and summary.synthesized[0].bank_item_id == item_id


# 14. The state API still never exposes the transcript or correct answer -- and the new
# audio_meta_json fields (storage_key etc.) never leak into the client-facing payload either.
@pytest.mark.postgresql
@pytest.mark.integration
async def test_state_api_still_hides_transcript_and_new_metadata_fields(
    monkeypatch, postgres_session_factory, api_client, asgi_app
):
    from types import SimpleNamespace

    from app.db.session import get_db
    from app.models.language.exam import LanguageExamSession
    from app.models.user import User, UserRole

    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    transcript = "Secret transcript that must never reach the client."
    item_id = await _insert_listening_item(postgres_session_factory, language_id=language_id, transcript=transcript)

    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth())
    async with postgres_session_factory() as db:
        await run_backfill(db, language_code=language_code, apply=True)
    row = await _get_item(postgres_session_factory, item_id)
    assert row.audio_meta_json and row.audio_meta_json.get("storage_key")

    state = {
        "version": 3,
        "state_revision": 1,
        "sections": ["listening"],
        "cursor": 0,
        "listening": {
            "ready": True,
            "pool": {
                "A2": {
                    "level": "A2",
                    "question": "What is this text mainly about?",
                    "options": ["Daily life", "Space travel", "Ancient history", "Cooking"],
                    "correct_index": 0,
                    "audio_text": transcript,
                    "audio_url": row.audio_meta_json["public_url"],
                    "bank_item_id": item_id,
                    "question_token": "listening-backfill-test-token-0001",
                }
            },
            "current_level": "A2",
            "asked": [],
            "max_steps": 1,
            "done": False,
        },
    }
    marker = uuid.uuid4().hex[:12]
    async with postgres_session_factory() as db:
        user = User(email=f"backfill-{marker}@example.test", name="Backfill Student", hashed_password="not-used", role=UserRole.student)
        db.add(user)
        await db.flush()
        session = LanguageExamSession(student_id=user.id, language_id=language_id, exam_state=state, status="in_progress")
        db.add(session)
        await db.commit()
        student_id, session_id = user.id, session.id

    async def student_override():
        return SimpleNamespace(id=student_id, role=UserRole.student)

    async def db_override():
        async with postgres_session_factory() as db:
            yield db

    dependency_calls: set = set()
    for route in asgi_app.routes:
        if not getattr(route, "path", "").startswith("/api/student/languages/exam/"):
            continue
        for dep in getattr(route, "dependant", SimpleNamespace(dependencies=[])).dependencies:
            if dep.name == "student":
                dependency_calls.add(dep.call)
    for call in dependency_calls:
        asgi_app.dependency_overrides[call] = student_override
    asgi_app.dependency_overrides[get_db] = db_override
    try:
        response = await api_client.get(f"/api/student/languages/exam/{session_id}/state")
    finally:
        for call in dependency_calls:
            asgi_app.dependency_overrides.pop(call, None)
        asgi_app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body_text = response.text
    assert transcript not in body_text
    assert "correct_index" not in body_text
    # audio_url (the public URL) is legitimately exposed to play the clip -- it naturally contains
    # the storage_key as a substring, so check for the internal *metadata key names* instead
    # (proving the richer audio_meta dict itself was never serialized into the response), and use
    # transcript_hash's actual value, which has no legitimate relationship to any exposed field.
    assert '"storage_key"' not in body_text
    assert '"transcript_hash"' not in body_text
    assert '"audio_meta"' not in body_text
    assert row.audio_meta_json["transcript_hash"] not in body_text


# ---------------------------------------------------------------------------
# Phase 3A: scoped targeting (stable_key_prefix / source) for not-yet-active draft batches like
# the listening_mvp_60 rows. Every test below stays dry-run (apply=False, the default) unless
# explicitly noted -- no real Supertonic call is required.
# ---------------------------------------------------------------------------

_MVP60_PREFIX = "listening_mvp_60:"
_MVP60_SOURCE = "listening_mvp_60_draft"


def _mvp60_key(marker: str, suffix: str = "LST-A1-01") -> str:
    # stable_key has a global-uniqueness DB constraint (not scoped per test), so every test below
    # mixes in its own uuid marker to guarantee no collision with any other test or real row.
    return f"{_MVP60_PREFIX}{marker}-{suffix}"


# 15. stable_key_prefix finds an inactive/unverified row that the default query would never see.
@pytest.mark.postgresql
async def test_stable_key_prefix_targets_inactive_unverified_rows(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    target_id = await _insert_listening_item(
        postgres_session_factory,
        language_id=language_id,
        transcript="A draft batch passage.",
        is_active=False,
        is_verified=False,
        source=_MVP60_SOURCE,
        stable_key=_mvp60_key(marker),
    )

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX)

    processed_ids = {r.bank_item_id for r in summary.results}
    assert target_id in processed_ids
    result = next(r for r in summary.results if r.bank_item_id == target_id)
    assert result.status == "would_synthesize"


# 16. Scoped targeting excludes unrelated listening rows (a normal active/verified row with no
# matching stable_key, and an inactive row with an unrelated stable_key).
@pytest.mark.postgresql
async def test_scoped_targeting_excludes_unrelated_listening_rows(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    target_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Target passage.",
        is_active=False, is_verified=False, source=_MVP60_SOURCE, stable_key=_mvp60_key(marker),
    )
    unrelated_active_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Unrelated existing passage.",
    )
    unrelated_inactive_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Unrelated inactive passage.",
        is_active=False, is_verified=False, stable_key=f"some_other_batch:{marker}-ITEM-01",
    )

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX)

    processed_ids = {r.bank_item_id for r in summary.results}
    assert processed_ids == {target_id}
    assert unrelated_active_id not in processed_ids
    assert unrelated_inactive_id not in processed_ids


# 17. Source safety check: when both stable_key_prefix and source are supplied, a row matching the
# prefix but with a different source is excluded.
@pytest.mark.postgresql
async def test_scoped_targeting_excludes_rows_with_different_source(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    matching_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Matches both scope fields.",
        is_active=False, is_verified=False, source=_MVP60_SOURCE, stable_key=_mvp60_key(marker, "LST-A1-01"),
    )
    wrong_source_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Same prefix, different source.",
        is_active=False, is_verified=False, source="some_other_source", stable_key=_mvp60_key(marker, "LST-A1-02"),
    )

    async with postgres_session_factory() as db:
        summary = await run_backfill(
            db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX, source=_MVP60_SOURCE
        )

    processed_ids = {r.bank_item_id for r in summary.results}
    assert processed_ids == {matching_id}
    assert wrong_source_id not in processed_ids


# 18. Default query behavior (no scope flags) is unchanged even when a listening_mvp_60-style
# inactive row happens to exist -- it must not leak in without an explicit scope.
@pytest.mark.postgresql
async def test_default_scope_excludes_inactive_unverified_rows_even_with_matching_prefix(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    draft_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Draft batch passage.",
        is_active=False, is_verified=False, source=_MVP60_SOURCE, stable_key=_mvp60_key(marker),
    )

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code)  # no stable_key_prefix/source

    processed_ids = {r.bank_item_id for r in summary.results}
    assert draft_id not in processed_ids


# 19. A broad include_inactive=True with no narrowing scope is rejected outright.
@pytest.mark.postgresql
async def test_include_inactive_without_scope_is_rejected(postgres_session_factory):
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)

    async with postgres_session_factory() as db:
        with pytest.raises(ValueError, match="requires an explicit stable_key_prefix or source scope"):
            await run_backfill(db, language_code=language_code, include_inactive=True)


# 20. Scoped dry-run never writes an audio file and never updates audio_meta_json.
@pytest.mark.postgresql
async def test_scoped_dry_run_does_not_write_audio_or_update_db(monkeypatch, postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    target_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id, transcript="Draft batch passage.",
        is_active=False, is_verified=False, source=_MVP60_SOURCE, stable_key=_mvp60_key(marker),
    )

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))
    async with postgres_session_factory() as db:
        summary = await run_backfill(
            db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX, apply=False
        )

    assert len(calls) == 0  # no synthesis call at all in dry-run
    result = next(r for r in summary.results if r.bank_item_id == target_id)
    assert result.status == "would_synthesize"
    row = await _get_item(postgres_session_factory, target_id)
    assert row.audio_meta_json is None
    assert row.is_active is False and row.is_verified is False  # untouched


# 21. question_type and CEFR-level distribution are reported correctly for a scoped batch.
@pytest.mark.postgresql
async def test_scoped_summary_reports_question_type_and_level_distribution(postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    await _insert_listening_item(
        postgres_session_factory, language_id=language_id, level="A1", question_type="mcq",
        transcript="MCQ one.", is_active=False, is_verified=False,
        source=_MVP60_SOURCE, stable_key=_mvp60_key(marker, "LST-A1-01"),
    )
    await _insert_listening_item(
        postgres_session_factory, language_id=language_id, level="A1", question_type="mcq",
        transcript="MCQ two.", is_active=False, is_verified=False,
        source=_MVP60_SOURCE, stable_key=_mvp60_key(marker, "LST-A1-02"),
    )
    await _insert_listening_item(
        postgres_session_factory, language_id=language_id, level="B1", question_type="gap_fill",
        transcript="Gap fill one.", is_active=False, is_verified=False,
        source=_MVP60_SOURCE, stable_key=_mvp60_key(marker, "LST-B1-01"),
    )

    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX)

    assert summary.by_question_type == {"mcq": 2, "gap_fill": 1}
    assert summary.by_level == {"A1": 2, "B1": 1}


# 22. A row with invalid (non-object) body_json is reported distinctly and left untouched.
@pytest.mark.postgresql
async def test_invalid_body_json_is_reported_and_skipped(monkeypatch, postgres_session_factory):
    marker = uuid.uuid4().hex[:8]
    language_id = await _make_language(postgres_session_factory)
    language_code = await _get_language_code(postgres_session_factory, language_id)
    bad_id = await _insert_listening_item(
        postgres_session_factory, language_id=language_id,
        is_active=False, is_verified=False, source=_MVP60_SOURCE, stable_key=_mvp60_key(marker),
        raw_body_json=["not", "a", "dict"],
    )

    calls: list = []
    monkeypatch.setattr(backfill_service, "synthesize_language_speech", _fake_synth(calls=calls))
    async with postgres_session_factory() as db:
        summary = await run_backfill(db, language_code=language_code, stable_key_prefix=_MVP60_PREFIX)

    assert len(calls) == 0
    result = next(r for r in summary.results if r.bank_item_id == bad_id)
    assert result.status == "invalid_body_json"
    assert bad_id in {r.bank_item_id for r in summary.invalid_body_json}
