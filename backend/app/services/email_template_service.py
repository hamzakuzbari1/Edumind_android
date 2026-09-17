"""Render branded HTML email templates."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "email"


@lru_cache(maxsize=16)
def _load_template(name: str) -> str:
    path = _TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def _replace(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def render_email(*, subject: str, body_template: str, values: dict[str, str]) -> str:
    body_html = _replace(_load_template(body_template), values)
    return _replace(
        _load_template("base.html"),
        {
            "subject": subject,
            "content": body_html,
            "year": str(datetime.now(timezone.utc).year),
        },
    )


def render_welcome_email(*, name: str, dashboard_url: str) -> str:
    return render_email(
        subject="مرحباً بك في EduSpark",
        body_template="welcome.html",
        values={"name": name, "dashboard_url": dashboard_url},
    )


def render_verify_email(*, name: str, verify_url: str, expires_hours: int) -> str:
    return render_email(
        subject="تأكيد بريدك الإلكتروني — EduSpark",
        body_template="verify_email.html",
        values={
            "name": name,
            "verify_url": verify_url,
            "expires_hours": str(expires_hours),
        },
    )


def render_reset_password_email(*, name: str, reset_url: str, expires_hours: int) -> str:
    return render_email(
        subject="إعادة تعيين كلمة المرور — EduSpark",
        body_template="reset_password.html",
        values={
            "name": name,
            "reset_url": reset_url,
            "expires_hours": str(expires_hours),
        },
    )


def render_two_factor_code_email(*, name: str, code: str, expires_minutes: int) -> str:
    return render_email(
        subject="رمز التحقق — EduSpark",
        body_template="two_factor_code.html",
        values={
            "name": name,
            "code": code,
            "expires_minutes": str(expires_minutes),
        },
    )


def render_test_email(*, recipient: str) -> str:
    content = (
        f'<h1 style="margin:0 0 12px;font-size:22px;color:#ffffff;">اختبار البريد ✉️</h1>'
        f'<p style="margin:0 0 16px;">تم إرسال هذا البريد من EduSpark إلى '
        f'<strong style="color:#22d3ee;">{recipient}</strong>.</p>'
        f'<p style="margin:0;color:rgba(232,236,244,0.7);">إذا وصلتك هذه الرسالة، فإعداد Resend يعمل بشكل صحيح.</p>'
    )
    return _replace(
        _load_template("base.html"),
        {
            "subject": "اختبار EduSpark Email",
            "content": content,
            "year": str(datetime.now(timezone.utc).year),
        },
    )
