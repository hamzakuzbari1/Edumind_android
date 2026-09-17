from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin Audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    _admin: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if action:
        q = q.where(AuditLog.action == action)
    if actor_user_id:
        q = q.where(AuditLog.actor_user_id == actor_user_id)
    result = await db.execute(q)
    return [AuditLogOut.model_validate(row) for row in result.scalars().all()]
