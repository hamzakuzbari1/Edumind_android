"""Server-issued signed grammar stamps (Wave D).

Only the integrity layer may issue stamps. Clients never generate stamp tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.services.language_grammar_integrity.errors import GrammarIntegrityError


STAMP_VERSION = 1
DEFAULT_TTL_SECONDS = 86_400


def _secret() -> bytes:
    settings = get_settings()
    raw = (getattr(settings, "LANG_GRAMMAR_STAMP_SECRET", None) or "").strip()
    if not raw:
        raw = (settings.JWT_SECRET or "").strip() or "dev-grammar-stamp-insecure"
    return raw.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


@dataclass(frozen=True, slots=True)
class GrammarStampClaims:
    session_id: str
    student_id: int
    language_id: int
    grammar_id: str
    skill: str
    activity_type: str
    lesson_id: str
    content_item_id: int | None
    curriculum_version: str
    exp: int
    iat: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "v": STAMP_VERSION,
            "sid": self.session_id,
            "student_id": int(self.student_id),
            "language_id": int(self.language_id),
            "grammar_id": self.grammar_id,
            "skill": self.skill,
            "activity_type": self.activity_type,
            "lesson_id": self.lesson_id,
            "content_item_id": self.content_item_id,
            "curriculum_version": self.curriculum_version,
            "exp": int(self.exp),
            "iat": int(self.iat),
        }


def issue_signed_stamp(
    *,
    session_id: str,
    student_id: int,
    language_id: int,
    grammar_id: str,
    skill: str,
    activity_type: str = "",
    lesson_id: str = "",
    content_item_id: int | None = None,
    curriculum_version: str,
    ttl_seconds: int | None = None,
    now: int | None = None,
) -> str:
    """Issue an HMAC-signed stamp. Resolver/session layer is the sole issuer."""
    ttl = int(ttl_seconds if ttl_seconds is not None else DEFAULT_TTL_SECONDS)
    ttl = max(60, min(ttl, 7 * 86_400))
    iat = int(now if now is not None else time.time())
    claims = GrammarStampClaims(
        session_id=str(session_id),
        student_id=int(student_id),
        language_id=int(language_id),
        grammar_id=str(grammar_id).strip().lower(),
        skill=str(skill).strip().lower(),
        activity_type=str(activity_type or "").strip().lower(),
        lesson_id=str(lesson_id or "").strip(),
        content_item_id=int(content_item_id) if content_item_id is not None else None,
        curriculum_version=str(curriculum_version).strip() or "1.1.0",
        exp=iat + ttl,
        iat=iat,
    )
    body = _b64url_encode(json.dumps(claims.as_dict(), separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64url_encode(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_signed_stamp(
    token: str,
    *,
    expected_session_id: str | None = None,
    expected_student_id: int | None = None,
    expected_grammar_id: str | None = None,
    now: int | None = None,
) -> GrammarStampClaims:
    """Verify stamp integrity + optional ownership bindings. Rejects forgeries."""
    parts = (token or "").split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise GrammarIntegrityError("invalid_stamp", "Malformed grammar stamp token")
    body, sig = parts
    expected_sig = _b64url_encode(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected_sig):
        raise GrammarIntegrityError("stamp_forged", "Grammar stamp signature mismatch")
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise GrammarIntegrityError("invalid_stamp", "Stamp payload is not valid JSON") from exc
    if int(payload.get("v") or 0) != STAMP_VERSION:
        raise GrammarIntegrityError("invalid_stamp", "Unsupported stamp version")
    ts = int(now if now is not None else time.time())
    exp = int(payload.get("exp") or 0)
    if exp and ts > exp:
        raise GrammarIntegrityError("stamp_expired", "Grammar stamp has expired")
    claims = GrammarStampClaims(
        session_id=str(payload.get("sid") or ""),
        student_id=int(payload.get("student_id") or 0),
        language_id=int(payload.get("language_id") or 0),
        grammar_id=str(payload.get("grammar_id") or "").strip().lower(),
        skill=str(payload.get("skill") or "").strip().lower(),
        activity_type=str(payload.get("activity_type") or "").strip().lower(),
        lesson_id=str(payload.get("lesson_id") or "").strip(),
        content_item_id=(
            int(payload["content_item_id"])
            if payload.get("content_item_id") is not None
            else None
        ),
        curriculum_version=str(payload.get("curriculum_version") or "").strip(),
        exp=exp,
        iat=int(payload.get("iat") or 0),
    )
    if not claims.session_id or claims.student_id <= 0 or not claims.grammar_id:
        raise GrammarIntegrityError("invalid_stamp", "Stamp missing required claims")
    if expected_session_id and claims.session_id != str(expected_session_id):
        raise GrammarIntegrityError("stamp_session_mismatch", "Stamp does not match activity session")
    if expected_student_id is not None and claims.student_id != int(expected_student_id):
        raise GrammarIntegrityError("stamp_student_mismatch", "Stamp student ownership failed")
    if expected_grammar_id and claims.grammar_id != str(expected_grammar_id).strip().lower():
        raise GrammarIntegrityError("stamp_grammar_mismatch", "Stamp grammar ownership failed")
    return claims
