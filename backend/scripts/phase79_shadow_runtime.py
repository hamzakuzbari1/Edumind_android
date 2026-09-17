"""Runtime checks for Phase 7.9 shadowing routes."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> int:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        openapi = await client.get("/openapi.json")
        spec = openapi.json()
        paths = list(spec.get("paths", {}).keys())
        shadow_paths = [p for p in paths if "shadow" in p]
        print("shadow_openapi_paths:", json.dumps(shadow_paths, indent=2))
        print("total_openapi_routes:", len(paths))

        for path in (
            "/api/student/languages/speaking/shadow/sentences",
            "/api/student/languages/speaking/shadow",
        ):
            method = "get" if path.endswith("sentences") else "post"
            r = await client.request(method, path)
            print(f"{method.upper()} {path} -> {r.status_code}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
