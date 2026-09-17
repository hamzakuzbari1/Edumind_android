"""Student / API projections for Learning Packages."""

from __future__ import annotations

from typing import Any

from app.services.language_educational_package.types import EducationalPackage


def project_package_for_student(package: EducationalPackage) -> dict[str, Any]:
    return package.to_student_dict()


def project_package_for_inspect(package: EducationalPackage, *, audit: dict[str, Any] | None = None) -> dict[str, Any]:
    data = package.to_dict()
    if audit:
        data["generation_audit"] = dict(audit)
    return data
