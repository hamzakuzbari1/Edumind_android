import asyncio
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse, Response

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def _is_placement_audio_request(scope: dict) -> bool:
    if scope.get("type") != "http" or str(scope.get("method") or "").upper() != "POST":
        return False
    path = str(scope.get("path") or "").rstrip("/")
    prefix = str(settings.API_PREFIX or "").rstrip("/")
    return path.startswith(f"{prefix}/student/languages/exam/") and path.endswith(
        "/speaking/turn"
    )


class PlacementAudioBodyLimitMiddleware:
    """Reject oversized placement audio requests before multipart parsing/spooling.

    The file validator still enforces the exact audio-byte limit.  This outer bound includes a
    small allowance for multipart headers and the revision/token fields, and also counts streamed
    bodies whose Content-Length is absent or dishonest.
    """

    def __init__(self, app, *, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max(1, int(max_body_bytes))

    @staticmethod
    def _too_large_response() -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "code": "audio_request_too_large",
                    "message": "The placement audio request is too large.",
                }
            },
        )

    async def __call__(self, scope, receive, send):
        if not _is_placement_audio_request(scope):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                if int(raw_length) > self.max_body_bytes:
                    await self._too_large_response()(scope, receive, send)
                    return
            except ValueError:
                # A malformed/missing length cannot bypass the streamed byte counter below.
                pass

        # Pre-read the bounded request before FastAPI invokes python-multipart.  A receive-wrapper
        # exception would be converted by the multipart parser into a generic 400, so buffering to a
        # spooled temp file is what guarantees an explicit 413 for chunked/dishonest streams.  Only
        # the first MiB stays in RAM; larger accepted bodies spill to an auto-cleaned temporary file.
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as buffered:
            received = 0
            while True:
                message = await receive()
                if message.get("type") == "http.disconnect":
                    return
                if message.get("type") != "http.request":
                    continue
                body = message.get("body") or b""
                received += len(body)
                if received > self.max_body_bytes:
                    await self._too_large_response()(scope, receive, send)
                    return
                buffered.write(body)
                if not message.get("more_body", False):
                    break

            buffered.seek(0)

            async def replay_receive():
                chunk = buffered.read(64 * 1024)
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": buffered.tell() < received,
                }

            await self.app(scope, replay_receive, send)


def _decoded_upload_path_variants(path: str | bytes) -> list[str]:
    """Return every meaningful URL-decoding layer for a public upload path."""
    current = path.decode("latin-1", errors="replace") if isinstance(path, bytes) else str(path)
    variants: list[str] = []
    for _ in range(8):
        normalized_separators = current.replace("\\", "/")
        if normalized_separators not in variants:
            variants.append(normalized_separators)
        decoded = unquote(current, errors="replace")
        if decoded == current:
            break
        current = decoded
    return variants


def _is_unsafe_public_upload_path(path: str | bytes) -> bool:
    """Reject traversal and private placement folders at every decoding layer."""
    for variant in _decoded_upload_path_variants(path):
        parts = [part.casefold() for part in variant.split("/") if part]
        if any(part in {".", "..", "language_placement"} for part in parts):
            return True
    return False


class ProtectedUploadsStaticFiles(StaticFiles):
    """Static mount that cannot expose historical placement recordings."""

    async def get_response(self, path: str, scope):
        raw_path = scope.get("raw_path", b"")
        if _is_unsafe_public_upload_path(raw_path) or _is_unsafe_public_upload_path(scope.get("path", "")):
            return Response(status_code=404)
        return await super().get_response(path, scope)

    def lookup_path(self, path: str):
        if _is_unsafe_public_upload_path(path):
            return "", None
        full_path, stat_result = super().lookup_path(path)
        if not full_path:
            return full_path, stat_result

        upload_root = Path(self.directory).resolve()
        resolved = Path(full_path).resolve()
        try:
            relative = resolved.relative_to(upload_root)
        except ValueError:
            return "", None
        if _is_unsafe_public_upload_path(relative.as_posix()):
            return "", None
        return full_path, stat_result


async def _subscription_expiration_loop() -> None:
    from app.services.language_subscription_expiration_service import run_language_expiration_check
    from app.services.subscription_expiration_service import run_expiration_check

    interval = max(300, int(settings.SUBSCRIPTION_CHECK_INTERVAL_SECONDS))
    while True:
        try:
            async with AsyncSessionLocal() as db:
                stats = await run_expiration_check(db)
                lang_stats = await run_language_expiration_check(db)
                await db.commit()
                if stats.get("warnings") or stats.get("expired"):
                    logger.info("Subscription expiration check: %s", stats)
                if lang_stats.get("warnings") or lang_stats.get("expired"):
                    logger.info("Language subscription expiration check: %s", lang_stats)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Subscription expiration check failed")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    Path(settings.VECTOR_INDEX_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TTS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Uploads: %s", upload_path.resolve())
    logger.info("PostgreSQL: %s", settings.database_display)
    logger.info(
        "pgvector=%s embeddings=%s (keyword RAG when off)",
        settings.ENABLE_PGVECTOR,
        settings.ENABLE_EMBEDDINGS,
    )

    await init_db()
    expiration_task = asyncio.create_task(_subscription_expiration_loop())
    logger.info("%s ready — http://127.0.0.1:8000/docs", settings.APP_NAME)
    try:
        yield
    finally:
        expiration_task.cancel()
        try:
            await expiration_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description="EduSpark — منصة تعليم ذكية | FastAPI + PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# This middleware must sit outside request parsing.  One MiB is ample for multipart metadata while
# keeping ingress bounded even when a client omits Content-Length and streams the request.
app.add_middleware(
    PlacementAudioBodyLimitMiddleware,
    max_body_bytes=(max(1, int(settings.GENAI_EXAM_MAX_AUDIO_MB)) + 1) * 1024 * 1024,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", ProtectedUploadsStaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "database": settings.database_display,
        "pgvector": settings.ENABLE_PGVECTOR,
        "embeddings": settings.ENABLE_EMBEDDINGS,
    }
