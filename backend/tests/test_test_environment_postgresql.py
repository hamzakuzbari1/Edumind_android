"""Guardrail proving the official test command is backed by real PostgreSQL."""

from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.postgresql
async def test_official_suite_uses_dedicated_postgresql(postgres_engine) -> None:
    async with postgres_engine.connect() as connection:
        row = (
            await connection.execute(
                text("SELECT current_database(), current_setting('server_version_num')::int")
            )
        ).one()

    assert row[0].endswith("_test")
    assert row[1] >= 160000
