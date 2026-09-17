"""Probe historical-report as parent linked to student 5."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import urllib.error
import urllib.request

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.parent_link import ParentStudentLink
from app.models.user import User

OUT = Path(__file__).resolve().parent / "_probe_parent23.out.json"
BASE = "http://127.0.0.1:8000/api"


async def parent_email() -> tuple[int, str, int]:
    async with AsyncSessionLocal() as db:
        link = await db.scalar(select(ParentStudentLink).where(ParentStudentLink.parent_id == 23))
        user = await db.get(User, 23)
        return 23, user.email if user else "", link.student_id if link else 0


def http_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "len": len(body), "preview": body[:200]}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "preview": exc.read(400).decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"status": -1, "error": f"{type(exc).__name__}: {exc}"}


async def main() -> None:
    pid, email, sid = await parent_email()
    out = {"parent_id": pid, "email": email, "student_id": sid}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
