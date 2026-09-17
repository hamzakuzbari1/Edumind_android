"""Verify Phase 2.1.1 — Narrative Ownership Guard.

Ensures student-facing educational copy is produced only under
`app/services/language_learning_narrative/`.

Usage (from backend/):
    python scripts/verify_language_narrative_ownership_guard.py

Regenerate frozen debt manifest (only when intentionally resolving debt):
    python scripts/verify_language_narrative_ownership_guard.py --write-manifest
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.architecture.narrative_ownership_guard import (  # noqa: E402
    NARRATIVE_OWNER_PREFIX,
    build_debt_manifest,
    findings_to_dict,
    load_debt_manifest,
    scan_listening_backend,
)


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    write_manifest = "--write-manifest" in sys.argv

    debt_manifest = load_debt_manifest(backend_root)
    result = scan_listening_backend(backend_root, debt_manifest=debt_manifest)

    if write_manifest:
        manifest = build_debt_manifest(result)
        manifest_path = backend_root / "architecture" / "listening_narrative_debt_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "phase": "2.1.1",
            "description": "Frozen grandfathered educational-copy violations outside narrative owner. Must not grow.",
            "allowed_owner_prefix": NARRATIVE_OWNER_PREFIX,
            "files": manifest,
        }
        manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote debt manifest: {manifest_path.relative_to(backend_root)}")
        print(json.dumps(manifest, indent=2))
        return 0

    print("LISTENING NARRATIVE OWNERSHIP GUARD (Phase 2.1.1)")
    print("=" * 58)
    print(f"Allowed owner prefix: {NARRATIVE_OWNER_PREFIX}")
    print(f"Scanned Python files: {result.scanned_files}")
    print(f"Narrative owner modules: {len(result.narrative_owner_files)}")
    print(f"Total educational-copy findings (excl. owner): {len(result.findings)}")
    print(f"Grandfathered debt findings: {len(result.debt_findings)}")
    print(f"NEW violations: {len(result.new_violations)}")

    checks = [
        ("no_new_violations", len(result.new_violations) == 0),
        ("debt_manifest_stable", len(result.debt_manifest_drift) == 0),
        ("narrative_owner_present", len(result.narrative_owner_files) >= 3),
    ]

    print("\nCHECKS")
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    if result.new_violations:
        print("\nNEW VIOLATIONS (must move copy to language_learning_narrative/):")
        print(json.dumps(findings_to_dict(result.new_violations), indent=2))

    if result.debt_manifest_drift:
        print("\nDEBT MANIFEST DRIFT:")
        for line in result.debt_manifest_drift:
            print(f"  - {line}")

    if result.debt_findings and not result.new_violations:
        print("\nGRANDFATHERED DEBT (frozen — remove in Phase 2.2+):")
        by_file: dict[str, int] = {}
        for f in result.debt_findings:
            by_file[f.rel_path] = by_file.get(f.rel_path, 0) + 1
        for rel, count in sorted(by_file.items()):
            print(f"  - {rel}: {count} string(s)")

    overall = all(ok for _, ok in checks)
    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
