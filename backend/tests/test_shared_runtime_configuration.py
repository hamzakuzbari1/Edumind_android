from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.media_storage.config import effective_storage_provider


def _strong_test_secret() -> str:
    return "centralization-test-secret-1234567890"


def test_shared_runtime_rejects_implicit_local_database() -> None:
    with pytest.raises(ValueError, match="hosted PostgreSQL"):
        Settings(APP_ENV="shared", DEBUG=False, JWT_SECRET=_strong_test_secret())


def test_local_runtime_requires_explicit_local_mode_for_local_storage() -> None:
    settings = Settings(
        APP_ENV="local",
        DEBUG=True,
        JWT_SECRET=_strong_test_secret(),
        MEDIA_STORAGE_PROVIDER="local",
    )

    assert effective_storage_provider(settings) == "local"


def test_unknown_runtime_environment_is_rejected() -> None:
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings(APP_ENV="mystery", DEBUG=True, JWT_SECRET=_strong_test_secret())
