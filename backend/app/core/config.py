"""Application settings with explicit local and shared runtime modes."""

import os
from functools import lru_cache
from pathlib import Path
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Dev-only placeholder. Rejected at startup when DEBUG is off (see apply_local_defaults).
_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _project_root() -> Path:
    return _backend_dir().parent


def _discover_env_files() -> tuple[str, ...]:
    candidates = [
        _project_root() / ".env",
        _backend_dir() / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    seen: set[str] = set()
    found: list[str] = []
    for p in candidates:
        if p.is_file():
            resolved = str(p.resolve())
            if resolved not in seen:
                seen.add(resolved)
                found.append(str(p))
    return tuple(found) if found else (str(_project_root() / ".env"),)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_discover_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "EduSpark API"
    API_PREFIX: str = "/api"
    # shared/staging/production require hosted PostgreSQL and Supabase Storage.
    # local/test keep explicit local development fallbacks.
    APP_ENV: str = "shared"
    DEBUG: bool | str = False

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "eduspark"
    POSTGRES_PASSWORD: str = "eduspark"
    POSTGRES_DB: str = "eduspark_syria"

    DATABASE_URL: str = ""
    # Sync driver for Alembic / scripts (postgresql+psycopg2). Alias: SYNC_DATABASE_URL.
    DATABASE_URL_SYNC: str = ""
    SYNC_DATABASE_URL: str = ""

    # pgvector / embeddings (off by default for local Windows Postgres)
    ENABLE_PGVECTOR: bool = False
    ENABLE_EMBEDDINGS: bool = False

    # Mistral OCR (documents) + minimum extracted text threshold for lesson PDFs
    MISTRAL_API_KEY: str = ""
    MISTRAL_OCR_MODEL: str = "mistral-ocr-latest"
    MIN_EXTRACTED_TEXT_CHARS: int = 120
    ENABLE_FAISS: bool = True
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    VECTOR_INDEX_DIR: str = ""

    ENABLE_WHISPER: bool = True
    WHISPER_MODEL: str = "turbo"
    WHISPER_MODEL_PATH: str = ""
    LESSON_VIDEO_WHISPER_LANGUAGE: str = "ar"
    LESSON_VIDEO_FASTER_WHISPER_MODEL: str = ""
    LESSON_VIDEO_GEMINI_TIMEOUT_SECONDS: int = 600
    # Uploaded lesson-video STT only (not Speaking / placement / student chat).
    # deepgram (default) | whisper (explicit rollback)
    VIDEO_TRANSCRIPTION_PROVIDER: str = "deepgram"
    VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK: bool = False
    VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK: bool = False

    LLM_PROVIDER: str = "claude"  # claude | ollama (local dev fallback)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gemma3"

    # Claude LLM (primary provider for all text/JSON generation)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-5"

    # Gemini — retained only for STT fallbacks (student chat, teacher/lesson audio/video)

    # Gemini — STT fallbacks (student chat, teacher/lesson audio/video) + vocabulary word images
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Vocabulary word illustrations — generated on-demand per word, cached on the content item.
    ENABLE_VOCABULARY_IMAGES: bool = True
    LANGUAGE_VOCABULARY_IMAGE_MODEL: str = "gemini-2.5-flash-image"

    ENABLE_TTS: bool = False
    TTS_PROVIDER: str = "elevenlabs"
    TTS_REQUEST_TIMEOUT_SECONDS: int = 120
    TTS_LANGUAGE: str = "ar"
    TTS_ALLOWED_LANGUAGES: str = "ar,en,fr"
    TTS_OUTPUT_DIR: str = ""
    TTS_MAX_TEXT_CHARS: int = 1200

    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    ELEVENLABS_OUTPUT_FORMAT: str = "mp3_44100_128"
    ELEVENLABS_VOICE_NAME_PREFIX: str = "EduSpark Teacher"
    ELEVENLABS_DEFAULT_VOICE_ID: str = ""
    ELEVENLABS_STABILITY: float = 0.45
    ELEVENLABS_SIMILARITY_BOOST: float = 0.85
    ELEVENLABS_STYLE: float = 0.0
    ELEVENLABS_USE_SPEAKER_BOOST: bool = True

    JWT_SECRET: str = _DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Per-course subscription term (days) after payment
    SUBSCRIPTION_TERM_DAYS: int = 30
    SUBSCRIPTION_EXPIRING_SOON_DAYS: int = 7
    SUBSCRIPTION_CHECK_INTERVAL_SECONDS: int = 3600

    # Language Learning module
    LANGUAGE_SUBSCRIPTION_TERM_DAYS: int = 365
    LANGUAGE_SUBSCRIPTION_EXPIRING_SOON_DAYS: int = 7
    LANGUAGE_PLACEMENT_RETAKE_DAYS: int = 90
    LANGUAGE_INACTIVITY_ALERT_DAYS: int = 7
    LANGUAGE_STREAK_MILESTONES: str = "7,14,30,60"
    LANGUAGE_CONVERSATION_MOCK_AI: bool = False
    LANGUAGE_CONVERSATION_SPEAKER_WAV: str = ""
    LANGUAGE_CONVERSATION_HISTORY_TURNS: int = 12
    LANGUAGE_TTS_PROVIDER: str = "supertonic"
    LANGUAGE_SUPERTONIC_VOICE: str = "F1"
    LANGUAGE_SUPERTONIC_VOICE_FEMALE: str = "F1"
    LANGUAGE_SUPERTONIC_VOICE_MALE: str = "M1"
    LANGUAGE_SUPERTONIC_AUTO_DOWNLOAD: bool = True
    LANGUAGE_CONVERSATION_LEVEL_WINDOW: int = 30
    LANGUAGE_CONVERSATION_WHISPER_MODEL: str = "small.en"
    LANGUAGE_CONVERSATION_WHISPER_COMPUTE_TYPE: str = "float32"
    LANGUAGE_CONVERSATION_WHISPER_BEAM_SIZE: int = 5
    LANGUAGE_CONVERSATION_WHISPER_VAD: bool = False
    LANGUAGE_CONVERSATION_WHISPER_INITIAL_PROMPT: str = ""
    LANGUAGE_CONVERSATION_ASYNC_TTS: bool = True
    OPENAI_API_KEY: str = ""
    LANGUAGE_OPENAI_TTS_VOICE: str = "nova"
    SPEAKING_TTS_MODEL: str = "gpt-4o-mini-tts"
    SPEAKING_TTS_VOICE: str = "verse"
    SPEAKING_TTS_TIMEOUT_SECONDS: int = 30
    LANGUAGE_STT_PROVIDER: str = "openai"  # openai | whisper
    LANGUAGE_STT_MODEL: str = "gpt-4o-transcribe"
    LANGUAGE_STT_ALLOW_WHISPER_FALLBACK: bool = False
    SPEAKING_OPENAI_STT_MODEL: str = "gpt-4o-transcribe"
    LANGUAGE_FFMPEG_TIMEOUT_SECONDS: int = 20
    LANGUAGE_AUDIO_DECODE_MAX_SECONDS: int = 181
    GENAI_EXAM_MAX_AUDIO_MB: int = 10
    # Optional comma-separated overrides, e.g. "placement_start=5/60,placement_poll=60/60".
    # The limiter remains intentionally process-local and is safe only for the current single-worker topology.
    LANGUAGE_PLACEMENT_RATE_LIMITS: str = ""
    LANGUAGE_RATE_LIMIT_CLEANUP_SECONDS: int = 60
    LANGUAGE_MASTERY_WINDOW_SIZE: int = 8
    LANGUAGE_MASTERY_UP_THRESHOLD: float = 82.0
    LANGUAGE_MASTERY_DOWN_THRESHOLD: float = 40.0
    LANG_PROGRESSION_ENABLED: bool = False
    LANG_PROGRESSION_DUAL_READ: bool = False
    LANG_PROGRESSION_OFFICIAL_SELECT: bool = False
    READING_V2_GENERATION_PROVIDER: str = "local_mock"  # local_mock | ai
    READING_V2_AI_MODEL: str = ""
    READING_V2_AI_MAX_RETRIES: int = 2
    READING_V2_AI_MAX_OUTPUT_TOKENS: int = 8192
    WRITING_MODEL_PROVIDER: str = "claude"
    WRITING_GENERATION_TEMPERATURE: float = 0.2
    WRITING_GENERATION_MAX_TOKENS: int = 2048
    WRITING_GENERATION_TIMEOUT_SECONDS: float = 60.0
    WRITING_EDUCATIONAL_ANALYZER: str = "claude"

    # Grammar spine (G0+) - shared language engine, not a fifth Official CEFR skill.
    LANG_GRAMMAR_ENGINE_ENABLED: bool = False
    LANG_GRAMMAR_ENGINE_SELECT: bool = False
    LANG_GRAMMAR_STAMP_SECRET: str = ""
    LANG_GRAMMAR_STAMP_TTL_SECONDS: int = 86400
    LANG_GRAMMAR_ACTIVITY_PROVIDER: str = "template"
    LANG_GRAMMAR_ACTIVITY_SPEC_STRICT: bool = True
    LANG_GRAMMAR_SKILL_EXECUTOR_ENABLED: bool = False
    LANG_GRAMMAR_SKILL_EXECUTOR_STRICT: bool = True
    LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED: bool = True
    LANG_GRAMMAR_SPEAKING_DOMAIN_ENABLED: bool = True
    LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED: bool = True
    LANG_GRAMMAR_ACTIVITY_AUTHORING_STRICT: bool = True
    LANG_GRAMMAR_LLM_AUTHORING_ENABLED: bool = False
    LANG_GRAMMAR_LLM_AUTHORING_PROVIDER: str = "claude"  # claude | gemini | gpt | local
    LANG_GRAMMAR_LLM_AUTHORING_FALLBACK: bool = True
    LANG_GRAMMAR_LLM_AUTHORING_MAX_RETRIES: int = 3
    LANG_GRAMMAR_LLM_AUTHORING_TIMEOUT_SECONDS: float = 60.0
    LANG_GRAMMAR_EVALUATION_ENABLED: bool = True
    LANG_GRAMMAR_EVALUATION_STRICT: bool = True
    LANG_GRAMMAR_PIPELINE_ENABLED: bool = False
    LANG_GRAMMAR_PIPELINE_STRICT: bool = True
    LANG_GRAMMAR_MODULE_ENABLED: bool = False
    LANG_GRAMMAR_CANONICAL_PREVIEW_ENABLED: bool = False
    LANG_GRAMMAR_LESSON_CHAT_MAX_USER_CHARS: int = 800
    LANG_GRAMMAR_LESSON_CHAT_RECENT_MESSAGES: int = 10
    LANG_GRAMMAR_LESSON_CHAT_MAX_SESSION_MESSAGES: int = 60
    LANG_GRAMMAR_LESSON_CHAT_TIMEOUT_SECONDS: float = 30.0
    LANG_GRAMMAR_LESSON_CHAT_MAX_OUTPUT_TOKENS: int = 900
    LANG_ADAPTIVE_INTELLIGENCE_ENABLED: bool = False
    LANG_ADAPTIVE_PROFILE_PERSIST: bool = True
    LANG_AI_TUTOR_ENABLED: bool = False
    LANG_AI_TUTOR_MEMORY_PERSIST: bool = True
    LANG_AI_TUTOR_LLM_ENABLED: bool = True
    LANG_AI_TUTOR_COACHING_ENABLED: bool = False
    LANG_AI_TUTOR_COACHING_PERSIST: bool = True
    LANG_AI_TUTOR_COACHING_LLM_ENABLED: bool = True
    LANG_AI_TEACHER_ENABLED: bool = False
    LANG_AI_TEACHER_PERSIST: bool = True

    # Speaking assessment evidence pipeline — config only, no runtime wired yet (see
    # backend/.env.example for placeholder values; real secrets belong only in an ignored local
    # .env or a deployment secret manager, never here and never committed).
    SPEAKING_TRANSCRIPTION_PROVIDER: str = "openai"  # openai | faster_whisper | mock
    SPEAKING_TRANSCRIPTION_TIMEOUT_SECONDS: int = 120
    # Pronunciation evidence (wav2vec2 | mock)
    SPEAKING_PRONUNCIATION_PROVIDER: str = "wav2vec2"
    SPEAKING_PRONUNCIATION_MODEL: str = "facebook/wav2vec2-lv-60-espeak-cv-ft"
    SPEAKING_PRONUNCIATION_TIMEOUT_SECONDS: int = 120
    SPEAKING_PRONUNCIATION_MIN_CONFIDENCE: float = 0.15
    # Prosody/delivery evidence (acoustic | hume | mock) — MVP must stay "acoustic" (local,
    # numpy-derived; no external API). Hume Expression Measurement is not used for MVP scoring.
    SPEAKING_PROSODY_PROVIDER: str = "acoustic"
    HUME_API_KEY: str = ""
    SPEAKING_PROSODY_TIMEOUT_SECONDS: int = 120
    SPEAKING_PROSODY_POLL_INTERVAL_SECONDS: int = 2
    # Hume EVI live-conversation runtime — for a FUTURE live-conversation feature, not the
    # current 3-turn placement flow. HUME_SECRET_KEY is server-side only (mints short-lived
    # browser access tokens) and must never be exposed to the frontend.
    SPEAKING_LIVE_CONVERSATION_PROVIDER: str = "hume_evi"
    HUME_SECRET_KEY: str = ""
    HUME_EVI_CONFIG_ID: str = ""
    SPEAKING_EVI_TIMEOUT_SECONDS: int = 60
    SPEAKING_EVI_RECONNECT_ENABLED: bool = False
    SPEAKING_EVI_MAX_TURN_SECONDS: int = 120
    SPEAKING_EVI_MAX_TURN_BYTES: int = 25_000_000
    SPEAKING_EVI_TOKEN_TTL_SECONDS: int = 1500

    # Speaking live transcript preview (MVP, display-only) — mints short-lived OpenAI Realtime
    # ephemeral client secrets so the browser can show partial captions while the student is
    # still recording. Never the grading source of truth: the official transcript remains
    # SPEAKING_TRANSCRIPTION_PROVIDER's own post-submit pipeline. Disabled by default; the real
    # OPENAI_API_KEY (above) is used only server-side to mint each ephemeral secret and never
    # reaches the frontend.
    SPEAKING_LIVE_TRANSCRIPTION_ENABLED: bool = False
    SPEAKING_LIVE_TRANSCRIPTION_PROVIDER: str = "openai_realtime"
    SPEAKING_LIVE_TRANSCRIPTION_MODEL: str = "gpt-realtime-whisper"
    SPEAKING_LIVE_TRANSCRIPTION_TOKEN_TTL_SECONDS: int = 60

    # Deepgram STT — student lesson voice chat AND uploaded lesson-video when
    # VIDEO_TRANSCRIPTION_PROVIDER=deepgram. Not used by Language Speaking module.
    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_STT_MODEL: str = "nova-3"
    DEEPGRAM_STT_LANGUAGE: str = "ar-SY"
    DEEPGRAM_STT_TIMEOUT_SECONDS: int = 300
    DEEPGRAM_STT_SMART_FORMAT: bool = True

    UPLOAD_DIR: str = ""
    MAX_PDF_BYTES: int = 500 * 1024 * 1024
    MAX_AUDIO_BYTES: int = 10 * 1024 * 1024
    MAX_VOICE_SAMPLE_BYTES: int = 50 * 1024 * 1024

    # A6.0 — local storage is allowed only for explicit local/test environments.
    MEDIA_STORAGE_PROVIDER: str = "supabase"
    SUPABASE_URL: str = ""
    # Server-side only. Never expose to Android / API responses / client bundles.
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_PUBLIC_BUCKET: str = "edumind-public"
    SUPABASE_PRIVATE_BUCKET: str = "edumind-private"
    SUPABASE_SIGNED_URL_TTL_SECONDS: int = 300

    VOICE_SAMPLE_MIN_SECONDS: int = 60
    VOICE_CLONE_MIN_QUALITY_SCORE: int = 65
    VOICE_CLONE_MIN_CLONE_CONFIDENCE: int = 60
    VOICE_CLONE_MIN_TRANSCRIPT_QUALITY: int = 50
    VOICE_CLONE_AUTO_REJECT_QUALITY: int = 45

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Transactional email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "EduSpark <onboarding@resend.dev>"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 1
    TWO_FACTOR_CODE_EXPIRE_MINUTES: int = 10
    TWO_FACTOR_MAX_ATTEMPTS: int = 5
    TWO_FACTOR_RESEND_COOLDOWN_SECONDS: int = 60
    TWO_FACTOR_MAX_RESENDS: int = 3

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5
    QUIZ_COUNT: int = 5

    DB_CONNECT_TIMEOUT: int = 10

    # Legacy ALTER/CREATE patches on startup — disable in production (use Alembic only).
    APPLY_LEGACY_SCHEMA_PATCHES: bool = False

    @model_validator(mode="after")
    def apply_local_defaults(self) -> Self:
        if isinstance(self.DEBUG, str):
            self.DEBUG = self.DEBUG.strip().lower() in ("1", "true", "yes", "on", "debug")

        runtime = (self.APP_ENV or "").strip().lower()
        if runtime not in {"local", "test", "shared", "staging", "production"}:
            raise ValueError(
                "APP_ENV must be one of local, test, shared, staging, or production."
            )

        # Never allow an insecure JWT secret in production (DEBUG off).
        secret = (self.JWT_SECRET or "").strip()
        insecure_secret = (
            not secret
            or secret == _DEV_JWT_SECRET
            or "change-me" in secret.lower()
            or "change-me-in-production" in secret.lower()
        )
        if not self.DEBUG and insecure_secret:
            raise ValueError(
                "JWT_SECRET is missing or set to an insecure placeholder. "
                "Set a strong, random JWT_SECRET (e.g. `python -c \"import secrets; "
                "print(secrets.token_urlsafe(64))\"`) in your environment before "
                "starting with DEBUG=false."
            )

        provider = (self.TTS_PROVIDER or "elevenlabs").strip().lower()
        if provider != "elevenlabs":
            provider = "elevenlabs"
        self.TTS_PROVIDER = provider

        language_tts_provider = (self.LANGUAGE_TTS_PROVIDER or "supertonic").strip().lower()
        if language_tts_provider not in {"supertonic", "disabled"}:
            language_tts_provider = "supertonic"
        self.LANGUAGE_TTS_PROVIDER = language_tts_provider

        language_stt_provider = (self.LANGUAGE_STT_PROVIDER or "openai").strip().lower()
        if language_stt_provider not in {"openai", "whisper"}:
            language_stt_provider = "openai"
        self.LANGUAGE_STT_PROVIDER = language_stt_provider

        reading_v2_provider = (self.READING_V2_GENERATION_PROVIDER or "local_mock").strip().lower()
        if reading_v2_provider not in {"local_mock", "ai"}:
            reading_v2_provider = "local_mock"
        self.READING_V2_GENERATION_PROVIDER = reading_v2_provider
        self.READING_V2_AI_MAX_RETRIES = max(0, min(int(self.READING_V2_AI_MAX_RETRIES or 0), 5))
        self.READING_V2_AI_MAX_OUTPUT_TOKENS = max(1024, int(self.READING_V2_AI_MAX_OUTPUT_TOKENS or 8192))

        in_docker = os.getenv("DOCKER_COMPOSE", "").lower() in ("1", "true", "yes")
        host = (self.POSTGRES_HOST or "localhost").strip()
        # Outside Docker, map compose service names to localhost for local Postgres
        if not in_docker and host in ("db", "postgres"):
            host = "localhost"

        if not self.DATABASE_URL.strip():
            self.DATABASE_URL = self._build_async_url(host)
        elif not in_docker:
            self.DATABASE_URL = self._ensure_localhost(self.DATABASE_URL)

        sync_raw = (self.SYNC_DATABASE_URL or self.DATABASE_URL_SYNC or "").strip()
        if not sync_raw:
            if self.DATABASE_URL.strip():
                sync_raw = self._async_to_sync_url(self.DATABASE_URL)
            else:
                sync_raw = self._build_sync_url(host)
        elif not in_docker:
            sync_raw = self._ensure_localhost(sync_raw)
        self.DATABASE_URL_SYNC = self._normalize_sync_url(sync_raw)

        hosted_runtime = runtime in {"shared", "staging", "production"} and not self.DEBUG
        if hosted_runtime:
            if not self.DATABASE_URL.strip():
                raise ValueError(
                    "DATABASE_URL is required for hosted runtime; refusing the localhost PostgreSQL default."
                )
            if self._is_local_database_url(self.DATABASE_URL):
                raise ValueError(
                    "DATABASE_URL must point to the shared hosted PostgreSQL database in hosted runtime."
                )
            provider = (self.MEDIA_STORAGE_PROVIDER or "").strip().lower()
            if provider != "supabase":
                raise ValueError(
                    "MEDIA_STORAGE_PROVIDER=supabase is required for hosted runtime."
                )
            if not self.SUPABASE_URL.strip() or not self.SUPABASE_SERVICE_ROLE_KEY.strip():
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for hosted media storage."
                )

        if not self.UPLOAD_DIR.strip():
            self.UPLOAD_DIR = str(_backend_dir() / "uploads")
        elif not in_docker and self.UPLOAD_DIR.replace("\\", "/").startswith("/app/"):
            self.UPLOAD_DIR = str(_backend_dir() / "uploads")

        if not self.VECTOR_INDEX_DIR.strip():
            self.VECTOR_INDEX_DIR = str(Path(self.UPLOAD_DIR) / "indexes")
        elif not in_docker and self.VECTOR_INDEX_DIR.replace("\\", "/").startswith("/app/"):
            self.VECTOR_INDEX_DIR = str(Path(self.UPLOAD_DIR) / "indexes")

        if not self.TTS_OUTPUT_DIR.strip():
            self.TTS_OUTPUT_DIR = str(Path(self.UPLOAD_DIR) / "answers")
        elif not in_docker and self.TTS_OUTPUT_DIR.replace("\\", "/").startswith("/app/"):
            self.TTS_OUTPUT_DIR = str(Path(self.UPLOAD_DIR) / "answers")

        if not self.LANGUAGE_CONVERSATION_SPEAKER_WAV.strip():
            bundled = _backend_dir() / "scripts" / "_tts_verify_out" / "arabic_test.wav"
            if bundled.is_file():
                self.LANGUAGE_CONVERSATION_SPEAKER_WAV = str(bundled.resolve())

        self.POSTGRES_HOST = host
        # Embeddings require pgvector in DB
        if not self.ENABLE_PGVECTOR:
            self.ENABLE_EMBEDDINGS = False
        return self

    def _build_async_url(self, host: str) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def _build_sync_url(self, host: str) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @staticmethod
    def _is_local_database_url(url: str) -> bool:
        from sqlalchemy.engine import make_url

        parsed = make_url(url)
        return parsed.get_backend_name() != "postgresql" or parsed.host in {
            "localhost",
            "127.0.0.1",
            "::1",
            "db",
            "postgres",
        }

    @staticmethod
    def _async_to_sync_url(url: str) -> str:
        """Convert runtime async URL to a sync Alembic URL."""
        normalized = url.strip()
        if "+asyncpg" in normalized:
            return normalized.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if normalized.startswith("postgresql://"):
            return normalized.replace("postgresql://", "postgresql+psycopg2://", 1)
        return normalized

    @staticmethod
    def _normalize_sync_url(url: str) -> str:
        """Ensure Alembic never receives asyncpg."""
        if "+asyncpg" in url:
            return Settings._async_to_sync_url(url)
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @staticmethod
    def _ensure_localhost(url: str) -> str:
        return (
            url.replace("@db:", "@localhost:")
            .replace("@db/", "@localhost/")
            .replace("@postgres:", "@localhost:")
        )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_display(self) -> str:
        return f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic migrations (psycopg2)."""
        return self.DATABASE_URL_SYNC


@lru_cache
def get_settings() -> Settings:
    return Settings()
