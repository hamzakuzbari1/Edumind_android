"""Reproduce parent dashboard for a specific parent id (default 23 from logs)."""

from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.parent_link import ParentStudentLink
from app.models.user import User
from app.services.parent_monitoring_service import build_full_parent_dashboard

PARENT_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 23


async def main() -> int:
    async with AsyncSessionLocal() as db:
        parent = await db.get(User, PARENT_ID)
        if not parent:
            print(f"Parent {PARENT_ID} not found")
            return 1
        print(f"parent: id={parent.id} email={parent.email} role={parent.role}")

        links = (
            await db.execute(
                select(ParentStudentLink).where(ParentStudentLink.parent_id == parent.id)
            )
        ).scalars().all()
        print(f"linked students: {len(links)}")
        for link in links:
            student = await db.get(User, link.student_id)
            print(f"  student id={link.student_id} email={student.email if student else '?'}")
            try:
                data = await build_full_parent_dashboard(db, parent, student_id=link.student_id)
                ai = data.get("academic_intelligence")
                dump = ai.model_dump() if hasattr(ai, "model_dump") else ai
                print(f"  OK dashboard — academic has_data={dump.get('has_data') if isinstance(dump, dict) else 'n/a'}")
            except Exception as exc:
                print(f"  FAILED for student {link.student_id}: {exc}")
                traceback.print_exc()
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
