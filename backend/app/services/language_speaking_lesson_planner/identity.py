"""Speaking session / mission / task / attempt identity semantics (S10.1, contracts only).

This module DEFINES identity semantics required before S11 durable persistence. It does
not persist anything and does not own the runtime ids of other packages (live_turn_id is
owned by live_conversation; evaluation_id by the evaluator). It documents how those ids
compose and which must stay stable vs be minted fresh.

Vocabulary
----------
SESSION     A complete educational Speaking session.            -> session_id
BLUEPRINT   The planned blueprint for a session.                -> blueprint_id
MISSION     An educational-purpose container in the session.    -> mission_id
TASK        The executable student assignment/prompt/context.   -> task_id
ATTEMPT     One student execution of one task.                  -> attempt_id
TURN        One student conversational turn in a live EVI task. -> live_turn_id
EVALUATION  One canonical evaluation submission/result.         -> evaluation_id

EVI attempt granularity (decision)
----------------------------------
one live_conversation mission
  -> one executable live task
    -> ONE attempt for the conversation execution
      -> MANY live_turn_id values
        -> potentially MANY canonical evaluations

Reconnect/resume of the SAME logical conversation (same live_session_id) MUST reuse the
existing attempt_id. Starting the task again after completion/failure MUST mint a new
attempt_id.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

IDENTITY_SEMANTICS_VERSION = "10.1.0"

# Human/agent-readable stability contract for each identity.
SPEAKING_IDENTITY_SEMANTICS: dict[str, str] = {
    "session_id": "stable for the educational session",
    "blueprint_id": "stable for the planned blueprint",
    "mission_id": "unique within a blueprint/session",
    "task_id": "stable for the executable task definition (blueprint-scoped)",
    "attempt_id": "fresh for each execution/re-execution of a task",
    "live_session_id": "stable for one live conversation runtime",
    "live_turn_id": "fresh per student conversational turn",
    "evaluation_id": "fresh/idempotent per evaluation submission (evaluator-owned)",
}

# Identities that must survive a resume/reconnect of the same logical work.
STABLE_ACROSS_RESUME: frozenset[str] = frozenset(
    {"session_id", "blueprint_id", "mission_id", "task_id", "attempt_id", "live_session_id"}
)
# Identity minted fresh for every canonical evaluation submission.
FRESH_PER_EVALUATION: frozenset[str] = frozenset({"evaluation_id"})
# Identity minted fresh for every student conversational turn.
FRESH_PER_TURN: frozenset[str] = frozenset({"live_turn_id"})


def make_task_id(blueprint_id: str, mission_kind: str, task_index: int) -> str:
    """Deterministic, blueprint-scoped task definition identity."""
    raw = f"{blueprint_id}:{mission_kind}:{task_index}"
    return f"spk-task-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def new_attempt_id(task_id: str) -> str:
    """Mint a fresh attempt identity for a new execution of a task."""
    return f"spk-att-{task_id[-8:]}-{uuid.uuid4().hex[:10]}"


@dataclass(frozen=True, slots=True)
class SpeakingAttemptIdentity:
    """Typed identity envelope for one execution of one task (contract only, not persisted).

    For a live EVI task this collects MANY `live_turn_ids` and potentially MANY
    `evaluation_ids` under a SINGLE `attempt_id` tied to one `live_session_id`.
    """

    session_id: str
    blueprint_id: str
    mission_id: str
    task_id: str
    attempt_id: str
    live_session_id: str = ""
    live_turn_ids: tuple[str, ...] = ()
    evaluation_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "blueprint_id": self.blueprint_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "live_session_id": self.live_session_id,
            "live_turn_ids": list(self.live_turn_ids),
            "evaluation_ids": list(self.evaluation_ids),
        }

    def with_turn(self, live_turn_id: str) -> "SpeakingAttemptIdentity":
        """Attach another live turn to THIS attempt (attempt_id unchanged)."""
        from dataclasses import replace

        return replace(self, live_turn_ids=self.live_turn_ids + (live_turn_id,))

    def with_evaluation(self, evaluation_id: str) -> "SpeakingAttemptIdentity":
        from dataclasses import replace

        return replace(self, evaluation_ids=self.evaluation_ids + (evaluation_id,))


def should_start_new_attempt(*, is_resume: bool, previous_attempt_completed: bool) -> bool:
    """Attempt-granularity policy for EVI and recorded tasks.

    - A resume/reconnect of the same logical conversation reuses the attempt (False).
    - Restarting a task after it completed or failed mints a new attempt (True).
    - Otherwise a brand-new execution mints a new attempt (True).

    `previous_attempt_completed` is accepted for call-site clarity; both non-resume cases
    (fresh start and restart-after-complete/fail) intentionally yield a new attempt.
    """
    _ = previous_attempt_completed
    return not is_resume
