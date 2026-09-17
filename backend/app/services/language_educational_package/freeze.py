"""Freeze a validated package — becomes immutable for the lesson lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.fingerprint import (
    compute_constraints_fingerprint,
    compute_content_fingerprint,
)
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.types import (
    ELP_AUTHOR_VERSION,
    ELP_SCHEMA_VERSION,
    EducationalPackage,
)


def freeze_package(
    package: EducationalPackage,
    constraints: PackageConstraints,
    *,
    author_provider: str,
    package_id: str | None = None,
) -> EducationalPackage:
    """Mark package frozen with fingerprints. Call only after validation passes."""
    package.package_id = package_id or package.package_id or f"elp_{uuid4().hex}"
    package.schema_version = ELP_SCHEMA_VERSION
    package.author_version = ELP_AUTHOR_VERSION
    package.author_provider = author_provider
    package.mission_id = constraints.mission_id
    package.blueprint_hash = constraints.blueprint_hash
    package.constraints_fingerprint = compute_constraints_fingerprint(constraints)
    package.input_material.cefr_check_echo = constraints.official_cefr.upper()
    package.metadata = {
        **dict(package.metadata),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locale": constraints.locale,
        "length_band": constraints.lesson_length_band,
        "scenario_type": constraints.scenario_type,
        "official_cefr": constraints.official_cefr.upper(),
        "learning_stage": constraints.learning_stage,
    }
    package.status = PackageLifecycleStatus.frozen
    package.content_fingerprint = compute_content_fingerprint(package)
    return package
