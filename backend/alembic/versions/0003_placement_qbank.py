"""Placement question bank foundation.

Revision ID: 0003_placement_qbank
Revises: 0002_reference_seed
Create Date: 2026-07-07
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

revision = "0003_placement_qbank"
down_revision = "0002_reference_seed"
branch_labels = None
depends_on = None


def _contract():
    # File-relative loading avoids the installed alembic package name collision.
    path = Path(__file__).resolve().parents[1] / "qbank_compat_v1.py"
    spec = spec_from_file_location("edumind_qbank_compat_v1", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    _contract().upgrade()


def downgrade() -> None:
    _contract().downgrade(revision)
