"""Wave D integrity errors."""

from __future__ import annotations


class GrammarIntegrityError(Exception):
    """Raised when attested completion / stamp / session checks fail."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
