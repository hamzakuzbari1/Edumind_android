"""Storage provider protocol (A6.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResolvedDownload:
    url: str
    expires_in: int | None
    provider: str
    is_signed: bool
    bucket: str | None = None


class StorageProviderClient(Protocol):
    name: str

    def public_object_url(self, *, bucket: str, storage_key: str) -> str: ...

    def create_signed_download_url(
        self,
        *,
        bucket: str,
        storage_key: str,
        expires_in: int,
    ) -> str: ...
