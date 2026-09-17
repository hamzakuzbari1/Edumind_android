"""Safe, categorized errors for lesson-video transcription."""

from __future__ import annotations


class VideoTranscriptionError(Exception):
    """Raised when video transcription fails without a configured fallback.

    ``user_message`` is safe for API/DB storage. Never include API keys,
    auth headers, or raw provider payloads.
    """

    def __init__(
        self,
        user_message: str,
        *,
        category: str,
        retryable: bool = False,
        http_status: int | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.category = category
        self.retryable = retryable
        self.http_status = http_status
        self.provider = provider


# Stable category codes for logs / tests (not shown as secrets).
CATEGORY_MISSING_API_KEY = "missing_api_key"
CATEGORY_INVALID_API_KEY = "invalid_api_key"
CATEGORY_AUTH = "auth_error"
CATEGORY_UNSUPPORTED_MEDIA = "unsupported_media"
CATEGORY_EMPTY_AUDIO = "empty_audio"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_NETWORK = "network_failure"
CATEGORY_HTTP_400 = "http_400"
CATEGORY_HTTP_403 = "http_403"
CATEGORY_HTTP_413 = "http_413"
CATEGORY_HTTP_429 = "http_429"
CATEGORY_HTTP_5XX = "http_5xx"
CATEGORY_MALFORMED_RESPONSE = "malformed_response"
CATEGORY_EMPTY_TRANSCRIPT = "empty_transcript"
CATEGORY_CANCELLED = "job_cancelled"
CATEGORY_PROVIDER_CONFIG = "provider_config"
CATEGORY_UNKNOWN = "unknown"


_USER_MESSAGES: dict[str, str] = {
    CATEGORY_MISSING_API_KEY: "خدمة تحويل الصوت إلى نص غير مهيأة — أضف مفتاح Deepgram.",
    CATEGORY_INVALID_API_KEY: "مفتاح Deepgram غير صالح.",
    CATEGORY_AUTH: "فشل التحقق من خدمة التحويل الصوتي.",
    CATEGORY_UNSUPPORTED_MEDIA: "صيغة الصوت المستخرج غير مدعومة للتحويل.",
    CATEGORY_EMPTY_AUDIO: "لم يُعثر على صوت صالح في الفيديو.",
    CATEGORY_TIMEOUT: "انتهت مهلة تحويل صوت الفيديو. حاول مرة أخرى.",
    CATEGORY_NETWORK: "تعذر الاتصال بخدمة التحويل الصوتي.",
    CATEGORY_HTTP_400: "طلب تحويل الصوت غير صالح.",
    CATEGORY_HTTP_403: "لا يوجد إذن لاستخدام خدمة التحويل الصوتي.",
    CATEGORY_HTTP_413: "ملف الصوت كبير جداً للتحويل.",
    CATEGORY_HTTP_429: "خدمة التحويل مشغولة مؤقتاً. حاول لاحقاً.",
    CATEGORY_HTTP_5XX: "خدمة التحويل الصوتي غير متاحة مؤقتاً.",
    CATEGORY_MALFORMED_RESPONSE: "استجابة خدمة التحويل غير مكتملة.",
    CATEGORY_EMPTY_TRANSCRIPT: "تعذر استخراج نص من صوت الفيديو.",
    CATEGORY_CANCELLED: "تم إلغاء مهمة التحويل الصوتي.",
    CATEGORY_PROVIDER_CONFIG: "إعداد مزود تحويل الفيديو غير صالح.",
    CATEGORY_UNKNOWN: "تعذر تحويل صوت الفيديو.",
}


def user_message_for(category: str) -> str:
    return _USER_MESSAGES.get(category, _USER_MESSAGES[CATEGORY_UNKNOWN])


def error_from_http_status(status: int, *, provider: str = "deepgram") -> VideoTranscriptionError:
    if status == 400:
        category = CATEGORY_HTTP_400
        retryable = False
    elif status in (401,):
        category = CATEGORY_INVALID_API_KEY
        retryable = False
    elif status == 403:
        category = CATEGORY_HTTP_403
        retryable = False
    elif status == 413:
        category = CATEGORY_HTTP_413
        retryable = False
    elif status == 429:
        category = CATEGORY_HTTP_429
        retryable = True
    elif status >= 500:
        category = CATEGORY_HTTP_5XX
        retryable = True
    else:
        category = CATEGORY_UNKNOWN
        retryable = False
    return VideoTranscriptionError(
        user_message_for(category),
        category=category,
        retryable=retryable,
        http_status=status,
        provider=provider,
    )
