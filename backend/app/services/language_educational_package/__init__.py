"""Educational Learning Package (ELP) — skill-agnostic contracts and pipeline stages.

RESPONSIBILITY: Shared EducationalPackage / PackageConstraints contracts, normalize,
validate, repair, freeze, fingerprints, and lifecycle. Never decides curriculum.
Never calls LLM providers. Never scores students or writes CEFR/mastery.
"""

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

__all__ = [
    "ELP_AUTHOR_VERSION",
    "ELP_SCHEMA_VERSION",
    "EducationalPackage",
    "PackageConstraints",
    "PackageLifecycleStatus",
    "compute_constraints_fingerprint",
    "compute_content_fingerprint",
]
