"""Speaking Educational Learning Package (E1).

RESPONSIBILITY: Build constraints, author Learning Packages via Claude (or template
fallback), run shared ELP pipeline, persist frozen packages. Never writes CEFR,
mastery, promotion, or discussion turns. Never imports evaluation / journey / SPA.
"""

from app.services.language_speaking_educational_package.author_pipeline import (
    SPEAKING_ELP_VERSION,
    generate_speaking_learning_package,
    sync_package_into_elp_index,
)
from app.services.language_speaking_educational_package.types import (
    SpeakingLearningPackageGenerateResult,
)

__all__ = [
    "SPEAKING_ELP_VERSION",
    "SpeakingLearningPackageGenerateResult",
    "generate_speaking_learning_package",
    "sync_package_into_elp_index",
]
