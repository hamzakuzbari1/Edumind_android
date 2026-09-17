"""Ownership guard for official_speaking_cefr.

The Speaking Official Promotion engine is the ONLY runtime writer of
``official_speaking_cefr``. Initial placement / exam bulk-write happens once in
``language_progression_service`` (not a runtime progression path).
"""

from __future__ import annotations

import re
from pathlib import Path

AUTHORIZED_SPEAKING_CEFR_WRITERS: dict[str, str] = {
    "app.services.language_speaking_official_promotion.engine": (
        "Sole runtime writer — applies official promotion after a PASS SPA attempt (S18+)."
    ),
    "app.services.language_progression_service": (
        "Initial placement / exam bulk write (upsert_official_levels), not runtime progression."
    ),
}

_ASSIGN_RE = re.compile(r"\.official_speaking_cefr\s*=(?!=)")


def _module_name(path: Path, services_root: Path) -> str:
    rel = path.relative_to(services_root.parents[1]).with_suffix("")
    return ".".join(("app",) + rel.parts[rel.parts.index("services"):])


def find_official_speaking_cefr_writers(app_root: Path) -> set[str]:
    """Return the set of modules that assign official_speaking_cefr."""
    services_root = app_root / "services"
    writers: set[str] = set()
    for py in services_root.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        if _ASSIGN_RE.search(text):
            writers.add(_module_name(py, services_root))
    return writers


def verify_speaking_cefr_ownership(app_root: Path) -> tuple[bool, set[str], set[str]]:
    """Verify only authorized modules write official_speaking_cefr.

    Returns (ok, unauthorized_writers, missing_authorized_writers).
    """
    found = find_official_speaking_cefr_writers(app_root)
    authorized = set(AUTHORIZED_SPEAKING_CEFR_WRITERS)
    unauthorized = found - authorized
    missing = authorized - found
    return (not unauthorized), unauthorized, missing
