"""Development utilities — gated by DEBUG."""

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.email import TestEmailRequest, TestEmailResponse
from app.services import email_service
from app.services.email_service import EmailDeliveryError

router = APIRouter(prefix="/dev", tags=["Development"])
settings = get_settings()


def _require_dev() -> None:
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/test-email", response_model=TestEmailResponse)
async def test_email(body: TestEmailRequest):
    """Send a branded test email via Resend (DEBUG mode only)."""
    _require_dev()
    if not email_service.is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="أضف RESEND_API_KEY و EMAIL_FROM إلى البيئة",
        )
    try:
        result = await email_service.send_test_email(body.to)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"فشل إرسال البريد: {exc}",
        ) from exc

    message_id = result.get("id") if isinstance(result, dict) else None
    return TestEmailResponse(ok=True, message_id=message_id, detail="تم إرسال البريد بنجاح")
