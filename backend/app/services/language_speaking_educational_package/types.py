"""Speaking ELP types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.language_educational_package.pipeline import GenerationOutcome
from app.services.language_educational_package.types import EducationalPackage

SPEAKING_ELP_TYPES_VERSION = "1.0.0"


@dataclass(slots=True)
class SpeakingLearningPackageGenerateResult:
    success: bool
    outcome: GenerationOutcome
    package: EducationalPackage | None
    content_item_id: int | None
    audit: dict[str, Any]
    cached: bool = False
    reason: str = ""

    def to_status_dict(self) -> dict[str, Any]:
        pkg = self.package
        return {
            "success": self.success,
            "outcome": self.outcome.value,
            "cached": self.cached,
            "reason": self.reason,
            "content_item_id": self.content_item_id,
            "package_id": pkg.package_id if pkg else None,
            "status": pkg.status.value if pkg else "rejected",
            "constraints_fingerprint": pkg.constraints_fingerprint if pkg else None,
            "content_fingerprint": pkg.content_fingerprint if pkg else None,
            "audit": self.audit,
        }
