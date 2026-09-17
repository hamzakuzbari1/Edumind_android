from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(teacher|student|parent)$")
    device_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    viewer_mode: str | None = None
    device_name: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    session_id: int | None = None
    token_type: str = "bearer"
    user: "UserOut"
    viewer_mode: str | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime | None = None
    email_verified: bool = False
    email_verified_at: datetime | None = None
    viewer_mode: str | None = None
    onboarding_complete: bool = False
    needs_payment: bool = False
    payment_complete: bool = False
    teacher_setup_complete: bool = False
    onboarding_step: str = "grade"
    grade: int | None = None

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("كلمتا المرور الجديدتان غير متطابقتين")
        return self


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    ok: bool = True
    detail: str = "إذا كان البريد مسجلاً، ستصلك رسالة لإعادة تعيين كلمة المرور"


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("كلمتا المرور الجديدتان غير متطابقتين")
        return self


class ResetPasswordResponse(BaseModel):
    ok: bool = True
    detail: str = "تم تحديث كلمة المرور"


class AccountSecurityOut(BaseModel):
    """Account summary for security UI — no password fields."""

    id: int
    email: str
    role: str
    created_at: datetime | None = None
    email_verified: bool = False
    email_verified_at: datetime | None = None
    name: str
    two_factor_enabled: bool = False
    two_factor_method: str | None = None

    model_config = {"from_attributes": True}


class AuthLoginResponse(BaseModel):
    """Login result — full tokens or 2FA challenge."""

    requires_2fa: bool = False
    access_token: str | None = None
    refresh_token: str | None = None
    session_id: int | None = None
    token_type: str = "bearer"
    user: UserOut | None = None
    viewer_mode: str | None = None
    challenge_token: str | None = None
    expires_in_seconds: int | None = None
    masked_email: str | None = None
    resend_available_in_seconds: int | None = None


class VerifyTwoFactorRequest(BaseModel):
    challenge_token: str = Field(min_length=1, max_length=512)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendTwoFactorRequest(BaseModel):
    challenge_token: str = Field(min_length=1, max_length=512)


class ResendTwoFactorResponse(BaseModel):
    ok: bool = True
    detail: str = "تم إرسال رمز جديد"
    expires_in_seconds: int | None = None
    resend_available_in_seconds: int | None = None


class EnableTwoFactorRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class EnableTwoFactorResponse(BaseModel):
    ok: bool = True
    detail: str
    challenge_token: str
    expires_in_seconds: int
    masked_email: str


class ConfirmEnableTwoFactorRequest(BaseModel):
    challenge_token: str = Field(min_length=1, max_length=512)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class DisableTwoFactorRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class TwoFactorStatusResponse(BaseModel):
    ok: bool = True
    detail: str
    two_factor_enabled: bool
    two_factor_method: str | None = None


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class VerifyEmailResponse(BaseModel):
    ok: bool = True
    detail: str = "تم تأكيد بريدك الإلكتروني بنجاح"
    email: str | None = None


class ResendVerificationResponse(BaseModel):
    ok: bool = True
    detail: str = "تم إرسال رسالة التأكيد — تحقق من بريدك"


class AuthSessionOut(BaseModel):
    id: int
    device_name: str | None = None
    device_type: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    last_seen_at: datetime | None = None
    created_at: datetime | None = None
    is_current: bool = False

    model_config = {"from_attributes": True}


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
