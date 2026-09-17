from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services import auth_session_service

bearer_scheme = HTTPBearer(auto_error=False)

VIEWER_PARENT = "parent"


@dataclass
class AuthContext:
    user: User
    viewer_mode: str | None = None
    session_id: int | None = None

    @property
    def is_parent_viewer(self) -> bool:
        return self.viewer_mode == VIEWER_PARENT


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="غير مصرح — يرجى تسجيل الدخول")
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز الدخول غير صالح")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="المستخدم غير موجود")
    viewer_mode = payload.get("viewer_mode")
    session_id = int(payload["sid"]) if payload.get("sid") else None
    if session_id:
        await auth_session_service.get_active_session(db, session_id, user.id)
        await db.commit()
    return AuthContext(user=user, viewer_mode=viewer_mode, session_id=session_id)


async def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


def require_role(role: UserRole):
    async def checker(ctx: AuthContext = Depends(get_auth_context)) -> User:
        if ctx.is_parent_viewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="وضع ولي الأمر للقراءة فقط — لا يمكن تنفيذ هذا الإجراء",
            )
        if ctx.user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك صلاحية لهذا الإجراء")
        return ctx.user

    return checker


def require_student_actor():
    """Student write access — blocked in parent viewer mode."""

    async def checker(ctx: AuthContext = Depends(get_auth_context)) -> User:
        if ctx.is_parent_viewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="وضع ولي الأمر للقراءة فقط — لا يمكن تعديل الخطة أو إرسال الاختبارات",
            )
        if ctx.user.role != UserRole.student:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا الإجراء للطلاب فقط")
        return ctx.user

    return checker


def require_parent():
    """Parent account with linked students."""

    async def checker(ctx: AuthContext = Depends(get_auth_context)) -> User:
        if ctx.user.role != UserRole.parent:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا القسم لأولياء الأمور فقط")
        return ctx.user

    return checker


def require_parent_viewer():
    """Alias — parent accounts only (viewer_mode removed)."""

    return require_parent()


async def _user_has_admin_role(db: AsyncSession, user_id: int) -> bool:
    from app.models.role import Role, UserRoleAssignment

    result = await db.execute(
        select(UserRoleAssignment)
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(UserRoleAssignment.user_id == user_id, Role.slug == "admin")
    )
    return result.scalar_one_or_none() is not None


def require_admin():
    async def checker(
        ctx: AuthContext = Depends(get_auth_context),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await _user_has_admin_role(db, ctx.user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="صلاحيات المسؤول مطلوبة")
        return ctx.user

    return checker
