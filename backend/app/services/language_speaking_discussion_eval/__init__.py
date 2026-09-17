"""Discussion Evaluation Adapter (E4).

RESPONSIBILITY: Map eligible guided-discussion student turns into existing S7
evaluation inputs and forward through the S8 knowledge bridge. Does not score,
does not own mastery, does not write CEFR/stage/promotion, does not call Alex.
Discussion Runtime (E3) stays pedagogically independent.
"""

from app.services.language_speaking_discussion_eval.adapter import (
    maybe_map_discussion_turn_to_evaluation,
)
from app.services.language_speaking_discussion_eval.types import (
    DISCUSSION_EVAL_ADAPTER_VERSION,
    DiscussionEvalHandoffResult,
    DiscussionEvalSkipReason,
)

__all__ = [
    "DISCUSSION_EVAL_ADAPTER_VERSION",
    "DiscussionEvalHandoffResult",
    "DiscussionEvalSkipReason",
    "maybe_map_discussion_turn_to_evaluation",
]
