import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Hash with bcrypt (compatible with existing passlib-generated hashes)."""
    digest = bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt())
    return digest.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify bcrypt hash — uses bcrypt directly (passlib+bcrypt 4.x safe)."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        logger.debug("verify_password failed for malformed hash")
        return False


def create_access_token(subject: dict[str, Any], *, session_id: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {**subject, "iat": now, "exp": expire, "jti": secrets.token_urlsafe(16)}
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
