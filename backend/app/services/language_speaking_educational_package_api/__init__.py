"""Speaking Learning Package API twin (E1).

RESPONSIBILITY: HTTP-facing create/retrieve/status for frozen Learning Packages.
"""

from app.services.language_speaking_educational_package_api.service import (
    SpeakingLearningPackageApiError,
    create_speaking_learning_package_api,
    get_speaking_learning_package_api,
    get_speaking_learning_package_status_api,
)

__all__ = [
    "SpeakingLearningPackageApiError",
    "create_speaking_learning_package_api",
    "get_speaking_learning_package_api",
    "get_speaking_learning_package_status_api",
]
