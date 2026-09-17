"""One-time/idempotent backfill: persist Supertonic audio for reachable Listening bank items.

Problem this solves: every Listening `LanguagePlacementQuestionBankItem` row's `audio_meta_json`
is empty today, so the live exam re-synthesizes audio from scratch on every single attempt
(`_materialize_listening_audio` in app/api/language_exam.py). `_resolve_listening_audio` there
already prefers `audio_meta_json.public_url` over live synthesis -- this module only needs to
populate that column; no runtime selection/resolution code changes.

Default scope: only bank rows with `skill="listening"`, `is_active=True`, `is_verified=True`, and a
transcript resolvable via the exact same logic the live exam trusts
(`app.api.language_exam._listening_text_from_body`, imported directly rather than re-implemented,
so this script and the runtime path can never disagree about which rows are reachable or what
text they'd read aloud). Six known scaffold rows (real recordings were never authored, and they
have no transcript either) resolve to no transcript here exactly as they do at runtime, and are
therefore left untouched -- this is intentional, not a gap.

Scoped targeting (Phase 3A, for not-yet-active draft batches like listening_mvp_60): passing
`stable_key_prefix` and/or `source` to `run_backfill()` narrows the query to that prefix/source and
lifts the is_active/is_verified filter for that narrowed query only, so a still-inactive/unverified
draft batch can have its audio backfilled before a later, separate activation step. There is no way
to broadly include every inactive/unverified listening row without an explicit narrowing scope --
`include_inactive=True` with neither `stable_key_prefix` nor `source` set raises immediately.

Cache location: `UPLOAD_DIR/language_placement_bank_audio/{bank_item_id}/{filename}` -- a
directory that cannot start with `/uploads/language_exam_audio/` or `/uploads/exam_audio/`, the
only two prefixes `_cleanup_exam_audio()` ever deletes (verified by direct read of that function;
it does a per-file string-prefix check against a session's own state, never a directory sweep).

Filenames are deterministic, not random: `{transcript_hash[:16]}_{engine}_{voice}.wav`. A changed
transcript, engine, or voice produces a different expected filename automatically -- no manual
cache invalidation needed, and re-running with unchanged inputs is a true no-op (see
`_is_metadata_current`).

Idempotency/failure-safety: each row is resolved, checked against its *current* `audio_meta_json`
and the actual file on disk (not just trusting the DB), and only synthesized if missing/stale/
forced. Synthesis writes to a temp file in the destination directory first and atomically
replaces the final path only after validating the output exists and clears a trivial-size floor
-- a partially-written file is never visible at the deterministic path. Each successful row is
committed independently immediately after its own write, so a later row's failure can never roll
back an earlier row's success, and a failed row never overwrites a previously-good
`audio_meta_json` entry.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.language_exam import _listening_text_from_body
from app.core.config import get_settings
from app.models.language.catalog import Language
from app.models.language.content import LanguageContentItem
from app.models.language.question_bank import LanguagePlacementQuestionBankItem
from app.services.language_supertonic_service import (
    language_tts_audio_extension,
    synthesize_language_speech,
)
from app.services.tts_service import prepare_synthesis_text

logger = logging.getLogger(__name__)

CACHE_DIRNAME = "language_placement_bank_audio"
ENGINE_NAME = "supertonic"
# Real synthesized speech clips are always many KB; anything this small is a truncated/corrupt
# write, not a legitimately short clip -- matches the spirit of the existing student-audio
# security gate's own duration/size sanity floor without importing that (differently-scoped,
# ffmpeg-normalizing) module.
MIN_VALID_AUDIO_BYTES = 512
_FEMALE_LISTENING_CUES_RE = re.compile(
    r"\b(mrs\.?|ms\.?|miss|layla|leila|laila|nadia|maria|anna|sara|sarah|fatima|"
    r"my husband)\b",
    flags=re.IGNORECASE,
)


def _listening_tts_voice_for_text(text: str | None, default_voice: str) -> str:
    if _FEMALE_LISTENING_CUES_RE.search(str(text or "")):
        return "F1"
    return default_voice


@dataclass
class BackfillItemResult:
    bank_item_id: int
    level: str
    # "synthesized" | "skipped" | "would_synthesize" | "failed" | "no_transcript" | "invalid_body_json"
    status: str
    reason: str = ""
    public_url: str | None = None
    storage_key: str | None = None
    question_type: str = ""


@dataclass
class BackfillSummary:
    apply: bool
    results: list[BackfillItemResult] = field(default_factory=list)

    def _by_status(self, status: str) -> list[BackfillItemResult]:
        return [r for r in self.results if r.status == status]

    @property
    def synthesized(self) -> list[BackfillItemResult]:
        return self._by_status("synthesized")

    @property
    def skipped(self) -> list[BackfillItemResult]:
        return self._by_status("skipped")

    @property
    def would_synthesize(self) -> list[BackfillItemResult]:
        return self._by_status("would_synthesize")

    @property
    def failed(self) -> list[BackfillItemResult]:
        return self._by_status("failed")

    @property
    def no_transcript(self) -> list[BackfillItemResult]:
        return self._by_status("no_transcript")

    @property
    def invalid_body_json(self) -> list[BackfillItemResult]:
        return self._by_status("invalid_body_json")

    @property
    def by_question_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.question_type or "unknown"] = counts.get(r.question_type or "unknown", 0) + 1
        return counts

    @property
    def by_level(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.level] = counts.get(r.level, 0) + 1
        return counts


def _sanitize_path_component(value: str) -> str:
    """Keep only filesystem-safe characters -- engine/voice come from config, but a path segment
    derived from config should never trust it blindly."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_.") else "-" for ch in str(value or "").strip())
    return cleaned.strip("-.") or "unknown"


def compute_transcript_hash(transcript: str) -> str:
    """Hash the same normalized text that will actually be sent to the TTS engine (see
    prepare_synthesis_text in tts_service.py), so trivial whitespace differences in the source
    never produce a spurious cache miss, and a real content edit reliably produces a new hash."""
    normalized = prepare_synthesis_text(transcript)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def expected_storage_key(*, bank_item_id: int, transcript_hash: str, engine: str, voice: str) -> str:
    engine_s = _sanitize_path_component(engine)
    voice_s = _sanitize_path_component(voice)
    ext = language_tts_audio_extension()
    filename = f"{transcript_hash[:16]}_{engine_s}_{voice_s}{ext}"
    return f"{CACHE_DIRNAME}/{bank_item_id}/{filename}"


def _is_metadata_current(meta: dict | None, *, transcript_hash: str, engine: str, voice: str) -> bool:
    if not isinstance(meta, dict):
        return False
    return (
        meta.get("transcript_hash") == transcript_hash
        and meta.get("engine") == engine
        and meta.get("voice") == voice
        and bool(meta.get("storage_key"))
        and bool(meta.get("public_url"))
    )


def _resolve_transcript(
    row: LanguagePlacementQuestionBankItem, content_by_id: dict[int, LanguageContentItem | None]
) -> str | None:
    """Mirrors _question_bank_pool's/_resolve_listening_audio_text's own resolution order exactly:
    the bank row's own body_json first, then its linked LanguageContentItem's body_json."""
    text = _listening_text_from_body(row.body_json or {})
    if text:
        return text
    content_item_id = (row.body_json or {}).get("content_item_id")
    if content_item_id:
        content = content_by_id.get(content_item_id)
        if content:
            text = _listening_text_from_body(content.body_json or {})
            if text:
                return text
    return None


def _wav_duration_seconds(path: Path) -> float | None:
    """Best-effort only -- stdlib wave module, no new dependency, no ffmpeg. Never raises."""
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if frames <= 0 or rate <= 0:
                return None
            return round(frames / float(rate), 3)
    except (wave.Error, OSError, EOFError):
        return None


async def _synthesize_to_path(transcript: str, *, dest: Path, voice: str) -> bool:
    """Write to a temp file in dest's own directory, validate, then atomically publish -- a
    partially-written file is never observable at the deterministic destination path.

    The temp file must keep the real audio extension (not a generic .tmp): the underlying
    Supertonic engine's save_audio infers the output container format from the path's own
    suffix, so a non-audio extension makes synthesis itself fail. tempfile's randomized name
    (tmpXXXXXXXX) already makes it unambiguously distinct from the deterministic final filename,
    even with a matching extension.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), suffix=language_tts_audio_extension())
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        ok = await synthesize_language_speech(
            transcript, language="en", output_path=tmp_path, voice_name=voice
        )
        if not ok:
            return False
        if not tmp_path.exists() or tmp_path.stat().st_size < MIN_VALID_AUDIO_BYTES:
            return False
        os.replace(tmp_path, dest)  # atomic: same directory => same filesystem
        return True
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:  # pragma: no cover - best-effort cleanup only
                pass


async def run_backfill(
    db: AsyncSession,
    *,
    language_code: str = "en",
    apply: bool = False,
    force: bool = False,
    item_id: int | None = None,
    stable_key_prefix: str | None = None,
    source: str | None = None,
    include_inactive: bool = False,
) -> BackfillSummary:
    """Scan reachable Listening bank rows and (only if apply=True) synthesize+persist audio for
    any that are missing it or whose cached entry is stale/missing-on-disk. Always dry-run unless
    apply=True. Never raises on a single row's failure -- logs and continues to the next row.

    Default scope (stable_key_prefix, source, include_inactive all unset/False) is completely
    unchanged from before: skill="listening", is_active=True, is_verified=True only.

    Scoped targeting (added for the listening_mvp_60 draft-bank rows, which are intentionally
    is_active=False/is_verified=False until a separate, later activation step): passing
    stable_key_prefix and/or source narrows the query to just that prefix/source and, because a
    real caller only reaches for this when they specifically want to backfill audio for a known,
    named batch of not-yet-active rows, also lifts the is_active/is_verified filter for that scoped
    query only. include_inactive=True with neither stable_key_prefix nor source set is rejected
    outright -- there is no way to broadly pull in every inactive/unverified listening row without
    an explicit narrowing scope.
    """
    if include_inactive and not (stable_key_prefix or source):
        raise ValueError(
            "include_inactive=True requires an explicit stable_key_prefix or source scope; "
            "refusing to broadly include inactive/unverified listening rows."
        )
    scoped = bool(stable_key_prefix or source)

    settings = get_settings()
    default_voice = (settings.LANGUAGE_SUPERTONIC_VOICE or "M1").strip() or "M1"
    upload_dir = Path(settings.UPLOAD_DIR)
    summary = BackfillSummary(apply=apply)

    language = (
        await db.execute(select(Language).where(Language.code == language_code))
    ).scalar_one_or_none()
    if language is None:
        logger.warning("Listening backfill: language code %r not found", language_code)
        return summary

    query = select(LanguagePlacementQuestionBankItem).where(
        LanguagePlacementQuestionBankItem.language_id == language.id,
        LanguagePlacementQuestionBankItem.skill == "listening",
    )
    if stable_key_prefix:
        query = query.where(LanguagePlacementQuestionBankItem.stable_key.like(f"{stable_key_prefix}%"))
    if source:
        query = query.where(LanguagePlacementQuestionBankItem.source == source)
    if not scoped:
        # Default (and any use of include_inactive without a scope, which is rejected above) --
        # exact prior behavior.
        query = query.where(
            LanguagePlacementQuestionBankItem.is_active.is_(True),
            LanguagePlacementQuestionBankItem.is_verified.is_(True),
        )
    if item_id is not None:
        query = query.where(LanguagePlacementQuestionBankItem.id == item_id)
    rows = (
        await db.execute(query.order_by(LanguagePlacementQuestionBankItem.id))
    ).scalars().all()

    content_ids = {
        cid for row in rows
        if isinstance(row.body_json, dict) and (cid := row.body_json.get("content_item_id"))
    }
    content_by_id: dict[int, LanguageContentItem | None] = {}
    for cid in content_ids:
        content_by_id[cid] = await db.get(LanguageContentItem, cid)

    for row in rows:
        if row.body_json is not None and not isinstance(row.body_json, dict):
            summary.results.append(
                BackfillItemResult(
                    row.id, row.level.value, "invalid_body_json", "body_json is not a JSON object",
                    question_type=row.question_type,
                )
            )
            continue

        transcript = _resolve_transcript(row, content_by_id)
        if not transcript:
            summary.results.append(
                BackfillItemResult(
                    row.id, row.level.value, "no_transcript", "no resolvable transcript",
                    question_type=row.question_type,
                )
            )
            continue

        voice = _listening_tts_voice_for_text(transcript, default_voice)
        transcript_hash = compute_transcript_hash(transcript)
        storage_key = expected_storage_key(
            bank_item_id=row.id, transcript_hash=transcript_hash, engine=ENGINE_NAME, voice=voice
        )
        dest = upload_dir / storage_key
        meta = row.audio_meta_json or {}
        metadata_current = _is_metadata_current(
            meta, transcript_hash=transcript_hash, engine=ENGINE_NAME, voice=voice
        )
        file_ok = dest.is_file() and dest.stat().st_size >= MIN_VALID_AUDIO_BYTES

        if metadata_current and file_ok and not force:
            summary.results.append(
                BackfillItemResult(
                    row.id, row.level.value, "skipped", "valid cached audio",
                    meta.get("public_url"), meta.get("storage_key"),
                    question_type=row.question_type,
                )
            )
            continue

        if not apply:
            reason = "would regenerate (--force)" if force and metadata_current and file_ok else (
                "cached audio missing/stale" if (metadata_current or file_ok) else "no cached audio yet"
            )
            summary.results.append(
                BackfillItemResult(row.id, row.level.value, "would_synthesize", reason, question_type=row.question_type)
            )
            continue

        ok = await _synthesize_to_path(transcript, dest=dest, voice=voice)
        if not ok:
            logger.warning("Listening backfill: synthesis failed bank_item_id=%s", row.id)
            summary.results.append(
                BackfillItemResult(
                    row.id, row.level.value, "failed", "synthesis failed or produced an invalid file",
                    question_type=row.question_type,
                )
            )
            continue

        public_url = "/uploads/" + storage_key
        row.audio_meta_json = {
            "public_url": public_url,
            "storage_key": storage_key,
            "transcript_hash": transcript_hash,
            "engine": ENGINE_NAME,
            "voice": voice,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "synthesized",
            "duration_seconds": _wav_duration_seconds(dest),
        }
        # Commit this row's success immediately -- a later row's failure must never roll this back.
        await db.commit()
        summary.results.append(
            BackfillItemResult(
                row.id, row.level.value, "synthesized", "", public_url, storage_key,
                question_type=row.question_type,
            )
        )

    return summary
