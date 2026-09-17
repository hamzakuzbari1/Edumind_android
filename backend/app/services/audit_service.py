"""Structured audit logging for production."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    actor_user_id: int | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    if commit:
        await db.commit()
    return entry
