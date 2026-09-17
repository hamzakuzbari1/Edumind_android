"""Account credential changes — email and password."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangeEmailRequest, ChangePasswordRequest, UserOut
from app.services import auth_session_service, email_service
from app.services.audit_service import log_audit
from app.services.email_service import EmailDeliveryError
from app.services.email_verification_service import is_email_verified
from app.services.user_status_service import build_user_extras


def _security_fields(user: User) -> dict:
    return {
        "email_verified": is_email_verified(user),
        "email_verified_at": user.email_verified_at,
    }


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    extras = await build_user_extras(db, user)
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
        **_security_fields(user),
        **extras,
    )


async def change_password(
    db: AsyncSession,
    user: User,
    body: ChangePasswordRequest,
    *,
    current_session_id: int | None = None,
    ip_address: str | None = None,
) -> UserOut:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الحالية غير صحيحة",
        )
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمتا المرور الجديدتان غير متطابقتين",
        )
    if verify_password(body.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الجديدة يجب أن تختلف عن الحالية",
        )

    user.hashed_password = hash_password(body.new_password)
    await db.flush()

    revoked = await auth_session_service.revoke_all_sessions(
        db, user.id, except_session_id=current_session_id
    )

    await log_audit(
        db,
        action="change_password",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        new_values={"sessions_revoked": revoked},
        ip_address=ip_address,
    )
    return await _user_out(db, user)


async def change_email(
    db: AsyncSession,
    user: User,
    body: ChangeEmailRequest,
    *,
    ip_address: str | None = None,
) -> UserOut:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الحالية غير صحيحة",
        )

    new_email = body.new_email.strip().lower()
    if new_email == user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الجديد مطابق للبريد الحالي",
        )

    existing = await db.execute(select(User.id).where(User.email == new_email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مستخدم مسبقاً",
        )

    old_email = user.email
    user.email = new_email
    user.email_verified_at = None
    await db.flush()

    try:
        await email_service.send_verification_email(db, user)
    except (EmailDeliveryError, HTTPException):
        pass

    await log_audit(
        db,
        action="change_email",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        old_values={"email": old_email},
        new_values={"email": new_email},
        ip_address=ip_address,
    )
    return await _user_out(db, user)
