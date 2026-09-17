"""Learning Journey projection (Phase G).

RESPONSIBILITY: Read-only compose of Grammar catalog + progression + mastery into
a CEFR stage graph for the English Journey UI. No educational algorithms, unlocks,
or writes.
"""

from __future__ import annotations

from app.services.language_learning_journey.flags import learning_journey_enabled
from app.services.language_learning_journey.projection import project_journey_graph
from app.services.language_learning_journey.service import build_learning_journey_graph
from app.services.language_learning_journey.types import (
    LEARNING_JOURNEY_PACKAGE,
    LEARNING_JOURNEY_SCHEMA_VERSION,
    JourneyGraph,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = (
    "Learning Journey projection — compose-only CEFR stage graph for UI; "
    "never writes mastery/progression/curriculum"
)

__all__ = [
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "LEARNING_JOURNEY_SCHEMA_VERSION",
    "LEARNING_JOURNEY_PACKAGE",
    "JourneyGraph",
    "learning_journey_enabled",
    "project_journey_graph",
    "build_learning_journey_graph",
]
