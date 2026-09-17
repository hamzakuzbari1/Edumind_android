"""Package lifecycle statuses."""

from __future__ import annotations

from enum import StrEnum


class PackageLifecycleStatus(StrEnum):
    draft = "draft"
    validated = "validated"
    frozen = "frozen"
    bound = "bound"
    rejected = "rejected"
    expired = "expired"
