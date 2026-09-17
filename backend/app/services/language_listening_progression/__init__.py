"""Listening progression runtime integration (PR-1)."""

from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_listening_progression.locking import lock_listening_progression_row

__all__ = [
    "lock_listening_progression_row",
    "mutate_listening_progression_json",
    "run_listening_progression_after_submit",
]


def __getattr__(name: str):
    if name == "run_listening_progression_after_submit":
        from app.services.language_listening_progression.runtime import run_listening_progression_after_submit

        return run_listening_progression_after_submit
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
