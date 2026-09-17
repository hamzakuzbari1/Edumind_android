"""Speaking runtime integration API twin (orchestration only).

RESPONSIBILITY: Wire existing E1/E2/E3 APIs into a student Start Learning flow.
Does not own package authoring, lesson memory, discussion pedagogy, evaluation,
or promotion. Does not change educational ownership.
"""

from app.services.language_speaking_runtime_api.ensure_learning import (
    RuntimeIntegrationError,
    ensure_learning_package_for_journey,
    start_learning_runtime,
)

__all__ = [
    "RuntimeIntegrationError",
    "ensure_learning_package_for_journey",
    "start_learning_runtime",
]
