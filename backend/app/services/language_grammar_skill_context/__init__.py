"""Wave C — Shared Grammar-Aware Skill Context.

Sole facade for skills to:
1. Resolve grammar targets (via language_grammar_target_resolver)
2. Load curriculum metadata into one shared SkillGrammarContext
3. Stamp / guard generated activities
4. Complete activities into Wave B evidence → mastery → progression

Skills must NOT invent grammar_id, call the resolver bypass, or write mastery.
"""

from app.services.language_grammar_skill_context.builder import (
    build_skill_grammar_context,
    context_from_grammar_id,
)
from app.services.language_grammar_skill_context.completion import (
    complete_current_skill_activity_async,
    complete_from_stamped_payload_async,
    complete_skill_activity_async,
)
from app.services.language_grammar_skill_context.guard import (
    assert_grammar_id_matches,
    assert_payload_matches_stamp,
)
from app.services.language_grammar_skill_context.stamp import (
    extract_stamped_grammar_id,
    merge_prompt_context,
    stamp_body,
    stamp_constraints_payload,
)
from app.services.language_grammar_skill_context.types import (
    SkillGrammarContext,
    SkillGrammarContextError,
    SkillGrammarStamp,
)

PACKAGE = "language_grammar_skill_context"
RESPONSIBILITY = (
    "Shared Grammar-Aware Skill Context — resolver-first SkillGrammarContext, "
    "stamp/guard, and Wave B completion bridge for Reading/Listening/Speaking/"
    "Writing/Vocabulary; never invents grammar; never writes mastery directly"
)

__all__ = [
    "PACKAGE",
    "RESPONSIBILITY",
    "SkillGrammarContext",
    "SkillGrammarContextError",
    "SkillGrammarStamp",
    "build_skill_grammar_context",
    "context_from_grammar_id",
    "stamp_body",
    "stamp_constraints_payload",
    "extract_stamped_grammar_id",
    "merge_prompt_context",
    "assert_grammar_id_matches",
    "assert_payload_matches_stamp",
    "complete_skill_activity_async",
    "complete_from_stamped_payload_async",
    "complete_current_skill_activity_async",
]
