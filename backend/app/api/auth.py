import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import VIEWER_PARENT, AuthContext, get_auth_context
from app.core.request_meta import client_ip, user_agent
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.catalog import TeacherProfile
from app.models.enrollment import OnboardingStep
from app.models.profile import StudentProfile
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccountSecurityOut,
    AuthLoginResponse,
    AuthSessionOut,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ConfirmEnableTwoFactorRequest,
    DisableTwoFactorRequest,
    EnableTwoFactorRequest,
    EnableTwoFactorResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendTwoFactorRequest,
    ResendTwoFactorResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ResendVerificationResponse,
    TokenResponse,
    TwoFactorStatusResponse,
    UserOut,
    VerifyEmailRequest,
    VerifyEmailResponse,
    VerifyTwoFactorRequest,
)
from app.services import auth_session_service, account_security_service, password_reset_service, email_service
from app.services.email_verification_service import is_email_verified, resend_verification_email, verify_email_with_token
from app.services.email_service import EmailDeliveryError
from app.services.two_factor_service import (
    begin_login_challenge,
    confirm_enable_two_factor,
    disable_two_factor,
    is_two_factor_enabled,
    request_enable_two_factor,
    resend_login_challenge,
    verify_login_challenge,
)
from app.services.user_status_service import build_user_extras

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


async def _user_out(db: AsyncSession, user: User, viewer_mode: str | None = None) -> UserOut:
    extras = await build_user_extras(db, user)
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
        email_verified=is_email_verified(user),
        email_verified_at=user.email_verified_at,
        viewer_mode=viewer_mode,
        **extras,
    )


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    request: Request,
    *,
    viewer_mode: str | None = None,
    device_name: str | None = None,
) -> TokenResponse:
    session, access, refresh = await auth_session_service.create_session(
        db,
        user,
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        device_name=device_name,
        viewer_mode=viewer_mode,
    )
    await db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        session_id=session.id,
        user=await _user_out(db, user, viewer_mode),
        viewer_mode=viewer_mode,
    )


async def _login_response(
    db: AsyncSession,
    user: User,
    request: Request,
    *,
    viewer_mode: str | None = None,
    device_name: str | None = None,
) -> AuthLoginResponse:
    tokens = await _issue_tokens(
        db,
        user,
        request,
        viewer_mode=viewer_mode,
        device_name=device_name,
    )
    return AuthLoginResponse(
        requires_2fa=False,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        session_id=tokens.session_id,
        user=tokens.user,
        viewer_mode=tokens.viewer_mode,
    )


@router.get("/me", response_model=UserOut)
async def me(ctx: AuthContext = Depends(get_auth_context), db: AsyncSession = Depends(get_db)):
    return await _user_out(db, ctx.user, ctx.viewer_mode)


@router.get("/account", response_model=AccountSecurityOut)
async def account_summary(ctx: AuthContext = Depends(get_auth_context)):
    user = ctx.user
    return AccountSecurityOut(
        id=user.id,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
        email_verified=is_email_verified(user),
        email_verified_at=user.email_verified_at,
        name=user.name,
        two_factor_enabled=is_two_factor_enabled(user),
        two_factor_method=user.two_factor_method,
    )


@router.post("/2fa/enable", response_model=EnableTwoFactorResponse)
async def enable_two_factor_request(
    body: EnableTwoFactorRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    result = await request_enable_two_factor(
        db,
        ctx.user,
        body.password,
        ip_address=client_ip(request),
    )
    await db.commit()
    return EnableTwoFactorResponse(**result)


@router.post("/2fa/enable/confirm", response_model=TwoFactorStatusResponse)
async def enable_two_factor_confirm(
    body: ConfirmEnableTwoFactorRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await confirm_enable_two_factor(
        db,
        ctx.user,
        body.challenge_token,
        body.code,
        ip_address=client_ip(request),
    )
    await db.commit()
    return TwoFactorStatusResponse(
        detail="تم تفعيل المصادقة الثنائية",
        two_factor_enabled=True,
        two_factor_method=user.two_factor_method,
    )


@router.post("/2fa/disable", response_model=TwoFactorStatusResponse)
async def disable_two_factor_endpoint(
    body: DisableTwoFactorRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await disable_two_factor(
        db,
        ctx.user,
        body.password,
        ip_address=client_ip(request),
    )
    await db.commit()
    return TwoFactorStatusResponse(
        detail="تم إيقاف المصادقة الثنائية",
        two_factor_enabled=False,
        two_factor_method=user.two_factor_method,
    )


@router.post("/verify-2fa", response_model=AuthLoginResponse)
async def verify_two_factor_login(
    body: VerifyTwoFactorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user, challenge = await verify_login_challenge(
        db,
        body.challenge_token,
        body.code,
        ip_address=client_ip(request),
    )
    await db.commit()
    return await _login_response(
        db,
        user,
        request,
        device_name=challenge.device_name,
    )


@router.post("/resend-2fa", response_model=ResendTwoFactorResponse)
async def resend_two_factor_code(
    body: ResendTwoFactorRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await resend_login_challenge(db, body.challenge_token)
    await db.commit()
    return ResendTwoFactorResponse(**result)


@router.post("/change-password", response_model=UserOut)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await account_security_service.change_password(
        db,
        ctx.user,
        body,
        current_session_id=ctx.session_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return user


@router.post("/change-email", response_model=UserOut)
async def change_email(
    body: ChangeEmailRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await account_security_service.change_email(
        db,
        ctx.user,
        body,
        ip_address=client_ip(request),
    )
    await db.commit()
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await password_reset_service.request_password_reset(
        db,
        body.email,
        ip_address=client_ip(request),
    )
    await db.commit()
    return ForgotPasswordResponse(**result)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await password_reset_service.reset_password_with_token(
        db,
        body,
        ip_address=client_ip(request),
    )
    await db.commit()
    return ResetPasswordResponse(**result)


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await verify_email_with_token(db, body.token, ip_address=client_ip(request))
    await db.commit()
    return VerifyEmailResponse(ok=True, email=user.email)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    result = await resend_verification_email(
        db,
        ctx.user,
        ip_address=client_ip(request),
    )
    await db.commit()
    return ResendVerificationResponse(**result)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البريد الإلكتروني مستخدم مسبقاً")

    role_map = {
        "teacher": UserRole.teacher,
        "student": UserRole.student,
        "parent": UserRole.parent,
    }
    role = role_map.get(body.role)
    if not role:
        raise HTTPException(status_code=400, detail="نوع الحساب غير مدعوم")

    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        hashed_password=hash_password(body.password),
        role=role,
    )
    db.add(user)
    await db.flush()

    if role == UserRole.student:
        db.add(
            StudentProfile(
                user_id=user.id,
                interests_json="[]",
                difficulty="medium",
                onboarding_step=OnboardingStep.grade,
                onboarding_completed_at=None,
                payment_completed_at=None,
            )
        )
    elif role == UserRole.teacher:
        db.add(
            TeacherProfile(
                user_id=user.id,
                full_name=body.name.strip(),
                bio=None,
                rating=0.0,
                student_count=0,
                active=True,
            )
        )

    await db.flush()
    if email_service.is_email_configured():
        try:
            await email_service.send_verification_email(db, user)
        except EmailDeliveryError:
            pass
    return await _issue_tokens(db, user, request, device_name=body.device_name)


@router.post("/login", response_model=AuthLoginResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    user_found = user is not None
    password_ok = bool(user and verify_password(body.password, user.hashed_password))

    if not user_found or not password_ok:
        logger.info("login_failed user_found=%s", user_found)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد أو كلمة المرور غير صحيحة",
        )

    viewer_mode = None
    if body.viewer_mode == VIEWER_PARENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="استخدم حساب ولي الأمر — ربط الطلاب من لوحة ولي الأمر",
        )

    if is_two_factor_enabled(user):
        challenge = await begin_login_challenge(
            db,
            user,
            ip_address=client_ip(request),
            device_name=body.device_name,
        )
        await db.commit()
        return AuthLoginResponse(**challenge)

    return await _login_response(
        db,
        user,
        request,
        viewer_mode=viewer_mode,
        device_name=body.device_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    session, user, access, refresh = await auth_session_service.rotate_refresh_token(
        db,
        body.refresh_token,
    )
    response = TokenResponse(
        access_token=access,
        refresh_token=refresh,
        session_id=session.id,
        user=await _user_out(db, user),
    )
    await db.commit()
    return response


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.session_id:
        await auth_session_service.revoke_session(db, ctx.user.id, ctx.session_id)
    if body.refresh_token:
        await auth_session_service.revoke_by_refresh_token(db, body.refresh_token)
    await db.commit()
    return {"ok": True}


@router.delete("/sessions")
async def logout_all_sessions(
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    count = await auth_session_service.revoke_all_sessions(db, ctx.user.id)
    await db.commit()
    return {"ok": True, "revoked": count}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    await auth_session_service.revoke_session(db, ctx.user.id, session_id)
    await db.commit()
    return {"ok": True}


@router.get("/sessions", response_model=list[AuthSessionOut])
async def list_sessions(
    ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await auth_session_service.list_active_sessions(db, ctx.user.id)
    return [
        AuthSessionOut(
            id=s.id,
            device_name=s.device_name,
            device_type=s.device_type,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            last_seen_at=s.last_seen_at,
            created_at=s.created_at,
            is_current=ctx.session_id == s.id,
        )
        for s in rows
    ]
