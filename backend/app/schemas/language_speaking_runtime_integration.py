"""Schemas for speaking runtime integration (Start Learning)."""



from __future__ import annotations



from typing import Any, Literal



from pydantic import BaseModel, Field





class EnsureLearningPackageIn(BaseModel):
    author_mode: Literal["claude", "template", "auto"] = "auto"
    use_cache: bool = True





class EnsureLearningPackageOut(BaseModel):
    success: bool = True
    reused: bool = False
    cached: bool = False
    package_id: str | None = None
    content_item_id: int | None = None
    status: str | None = None
    constraints_fingerprint: str | None = None
    content_fingerprint: str | None = None
    package: dict[str, Any] | None = None





class StartLearningIn(BaseModel):
    author_mode: Literal["claude", "template", "auto"] = "auto"
    use_cache: bool = True
    force_restart_lesson: bool = False





class StartLearningOut(BaseModel):
    success: bool = True
    session: dict[str, Any] = Field(default_factory=dict)
    package: dict[str, Any] = Field(default_factory=dict)
    lesson: dict[str, Any] = Field(default_factory=dict)
