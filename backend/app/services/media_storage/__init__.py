"""EduMind media storage foundation (A6.0) — local + Supabase providers."""

from app.services.media_storage.constants import (
    PRIVATE_BUCKET,
    PRIVATE_PREFIXES,
    PUBLIC_BUCKET,
    PROVIDER_LOCAL,
    PROVIDER_SUPABASE,
    bucket_for_access_scope,
    is_allowed_private_key,
    normalize_storage_key,
)
from app.services.media_storage.config import (
    effective_storage_provider,
    supabase_configured,
    supabase_storage_enabled,
)
from app.services.media_storage.download import (
    get_media_or_404,
    resolve_media_download_url,
    resolve_media_download_url_authorized,
    resolved_download_payload,
)
from app.services.media_storage.upload import (
    StoredUpload,
    build_object_key,
    client_url_for_media,
    store_and_register_media,
)
from app.services.media_storage.validation import (
    AUDIO_MIMES,
    DOCUMENT_MIMES,
    IMAGE_MIMES,
    PDF_MIMES,
    VIDEO_MIMES,
    default_max_bytes_for_mime,
    validate_upload_bytes,
)

__all__ = [
    "AUDIO_MIMES",
    "DOCUMENT_MIMES",
    "IMAGE_MIMES",
    "PDF_MIMES",
    "PRIVATE_BUCKET",
    "PRIVATE_PREFIXES",
    "PROVIDER_LOCAL",
    "PROVIDER_SUPABASE",
    "PUBLIC_BUCKET",
    "StoredUpload",
    "VIDEO_MIMES",
    "bucket_for_access_scope",
    "build_object_key",
    "client_url_for_media",
    "default_max_bytes_for_mime",
    "effective_storage_provider",
    "get_media_or_404",
    "is_allowed_private_key",
    "normalize_storage_key",
    "resolve_media_download_url",
    "resolve_media_download_url_authorized",
    "resolved_download_payload",
    "store_and_register_media",
    "supabase_configured",
    "supabase_storage_enabled",
    "validate_upload_bytes",
]
