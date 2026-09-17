"""Schemas for Speaking Learning Package E1 APIs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SpeakingLearningPackageCreateIn(BaseModel):
    constraints: dict[str, Any]
    author_mode: Literal["claude", "template", "auto"] = "auto"
    use_cache: bool = True


class SpeakingLearningPackageOut(BaseModel):
    success: bool
    cached: bool = False
    content_item_id: int | None = None
    package_id: str | None = None
    status: str | None = None
    constraints_fingerprint: str | None = None
    content_fingerprint: str | None = None
    outcome: str | None = None
    package: dict[str, Any] | None = None
    audit: dict[str, Any] = Field(default_factory=dict)


class SpeakingLearningPackageStatusOut(BaseModel):
    content_item_id: int | None = None
    package_id: str | None = None
    status: str | None = None
    constraints_fingerprint: str | None = None
    content_fingerprint: str | None = None
    immutable: bool = True
    title: str | None = None
    created_at: str | None = None
    audit: dict[str, Any] = Field(default_factory=dict)
