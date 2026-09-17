"""Optional: populate grade subject catalog (no demo users). Run once after migrations.

    python scripts/seed_reference_subjects.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.reference_catalog import ensure_reference_subjects
from app.db.session import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as db:
        n = await ensure_reference_subjects(db)
        await db.commit()
    print(f"Reference subjects ready ({n} new rows).")


if __name__ == "__main__":
    asyncio.run(main())
