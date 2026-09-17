"""Grammar package ownership registry (G0) — used by architecture verification.

Grammar is a shared language spine consumed by the four skills — never a fifth Official CEFR skill.
"""

from __future__ import annotations

# Exactly one owner per responsibility. Keys are package directory names under app/services/.
PACKAGE_OWNERSHIP: dict[str, str] = {
    "language_grammar_catalog": (
        "Sole owner of GrammarTopic definitions (file SSOT under "
        "backend/curriculum/{language}/grammar/), prereq DAG, CEFR intro bands, "
        "display_code, best_reinforcement_skills, recommended_contexts, "
        "minimum_context_diversity"
    ),
    "language_grammar_progression": (
        "Deterministic current/next/unlock/candidate/stretch from official_overall_cefr "
        "+ catalog + student grammar snapshot"
    ),
    "language_grammar_mastery": (
        "Internal mastery dimensions + overall_mastery + state; sole scorer of mastery updates"
    ),
    "language_grammar_review": "Review queue order, due dates, and spaced schedule policy",
    "language_grammar_evidence": (
        "Normalize skill-emitted Grammar Evidence; sole translator into mastery update requests"
    ),
    "language_grammar_lesson_planner": (
        "Deterministic GrammarLessonBlueprint including ordered steps (no LLM, no hardcoded skill chain)"
    ),
    "language_grammar_educational_package": (
        "Grammar ELP constraints → Claude author → freeze (reuses language_educational_package)"
    ),
    "language_grammar_activity_provider": (
        "Activity Provider interface/registry/resolution between Runtime and content generation; "
        "Claude is one provider stub, never part of Runtime"
    ),
    "language_grammar_activity_spec": (
        "Canonical ActivitySpecification contract, validation, serialization, and schema registry "
        "between Providers and Skill Executors / Renderers"
    ),
    "language_grammar_activity_authoring": (
        "Activity Authoring Framework — generate ActivitySpecification / adaptive "
        "grammar-aware lesson packages from Grammar Targets + learning snapshot (HOW only); "
        "Grammar is sole learning-goal source of truth; LLM never invents curriculum; "
        "never owns Runtime, Skill execution, Progression, Mastery, or Review"
    ),
    "language_grammar_skill_executor": (
        "Skill Execution Framework / Engine — sole layer that executes ActivitySpecification via "
        "Registry plugins; owns execution session/lifecycle/evidence observations only; "
        "never writes Mastery/Progression/Review; never owns Grammar or Activity Authoring"
    ),
    "language_grammar_speaking": (
        "Speaking Domain Framework — session/attempt/turn/result/evidence business model "
        "for Grammar Speaking activities; no LLM providers, STT, or TTS"
    ),
    "language_grammar_lesson_runtime": (
        "Execute Blueprint.steps only — cursor/handoffs; never decide lesson ordering"
    ),
    "language_grammar_analytics": "Read-only hub/parent projections from mastery/progression snapshots",
    "language_grammar_integration": (
        "Sole facade for GrammarLearningSnapshot and completed-topic sync; "
        "Planner consumes snapshots only — never query engines directly. "
        "Skill Runtime target resolution is owned by language_grammar_target_resolver"
    ),
    "language_grammar_target_resolver": (
        "Sole skill Runtime entry for grammar target resolution "
        "(grammar_id + display_code) used by Reading/Listening/Speaking/"
        "Writing/Vocabulary/Grammar — skills never resolve independently"
    ),
    "language_grammar_legacy_bridge": (
        "Read-only map of speaking gram_* / writing structure_id / BKT grammar.* → grammar_id"
    ),
    "language_grammar_evaluation": (
        "Grammar-Constrained Evaluation — score ONLY Grammar Targets / lesson expected patterns; "
        "emit GrammarEvidenceObservation; never general English scoring; "
        "never writes Mastery / Progression / Review / Planner / Runtime"
    ),
    "language_grammar_pipeline": (
        "Grammar Learning Pipeline — orchestrate existing Grammar Engine packages end-to-end; "
        "transaction boundaries, replay, feature flags, events only; "
        "no educational algorithms; never owns Catalog/Planner/Authoring/Evaluation/Mastery/Review logic"
    ),
    "language_grammar_module": (
        "Student Grammar Module — dashboard + generate-only lesson start + Wave B "
        "completion surface; never scores mastery or unlocks progression itself "
        "(delegates durable writes to language_grammar_pipeline.completion)"
    ),
    "language_grammar_skill_context": (
        "Wave C shared Grammar-Aware Skill Context — resolver-first context builder, "
        "activity stamp/guard, and Wave B completion bridge for "
        "Reading/Listening/Speaking/Writing/Vocabulary; never invents grammar_id; "
        "never writes mastery/progression directly"
    ),
    "language_grammar_integrity": (
        "Wave D production integrity — server-attested completion, signed stamps, "
        "activity sessions, append-only evidence ledger, durable replay protection; "
        "never trusts client grammar_id/score"
    ),
}

# Shared infrastructure — not skill engines; grammar packages may import these.
SHARED_INFRASTRUCTURE: frozenset[str] = frozenset(
    {
        "language_grammar",  # enums + ownership + id canon
        "language_progression_service",
        "language_educational_package",
        "language_learning_facts",
        "language_learning_narrative",
        "language_level_utils",
    }
)

# Allowed direct dependencies between grammar packages (DAG). Empty = leaf package.
ALLOWED_PACKAGE_DEPENDENCIES: dict[str, frozenset[str]] = {
    "language_grammar_catalog": frozenset(),
    "language_grammar_mastery": frozenset(
        {
            "language_grammar_catalog",
            "language_grammar_evidence",
        }
    ),
    "language_grammar_review": frozenset(
        {
            "language_grammar_catalog",
            "language_grammar_mastery",
        }
    ),
    "language_grammar_evidence": frozenset({"language_grammar_catalog"}),
    "language_grammar_progression": frozenset(
        {
            "language_grammar_catalog",
            "language_grammar_legacy_bridge",
        }
    ),
    "language_grammar_integration": frozenset(
        {
            "language_grammar_catalog",
            "language_grammar_progression",
            "language_grammar_mastery",
            "language_grammar_review",
        }
    ),
    "language_grammar_target_resolver": frozenset(
        {
            "language_grammar_catalog",
            "language_grammar_integration",
        }
    ),
    "language_grammar_lesson_planner": frozenset(
        {
            "language_grammar_integration",
        }
    ),
    "language_grammar_educational_package": frozenset(
        {
            "language_grammar_lesson_planner",
            "language_grammar_catalog",
        }
    ),
    # Providers consume Blueprint/step contracts (+ optional ActivitySpecification).
    "language_grammar_activity_provider": frozenset(
        {
            "language_grammar_lesson_planner",
            "language_grammar_activity_spec",
            "language_grammar_activity_authoring",
        }
    ),
    # Leaf contract package — no engine deps (Planner/Runtime/Claude forbidden).
    "language_grammar_activity_spec": frozenset(),
    # Authoring generates ActivitySpecification from Grammar Targets (+ catalog validation).
    "language_grammar_activity_authoring": frozenset(
        {
            "language_grammar_activity_spec",
            "language_grammar_catalog",
        }
    ),
    # Skill executors consume ActivitySpecification + emit evidence observations only.
    "language_grammar_skill_executor": frozenset(
        {
            "language_grammar_activity_spec",
            "language_grammar_evidence",
            "language_grammar_speaking",
        }
    ),
    # Speaking domain models — evidence mapping only; no Runtime/Planner/LLM.
    "language_grammar_speaking": frozenset(
        {
            "language_grammar_evidence",
        }
    ),
    # Runtime executes frozen Blueprint + Activity Provider interface;
    # consumes ActivitySpecification as the sole activity content contract.
    # May discover Skill Executors only via the skill_executor Registry (no skill if-branches).
    "language_grammar_lesson_runtime": frozenset(
        {
            "language_grammar_lesson_planner",
            "language_grammar_activity_provider",
            "language_grammar_activity_spec",
            "language_grammar_skill_executor",
        }
    ),
    "language_grammar_analytics": frozenset(
        {
            "language_grammar_mastery",
            "language_grammar_progression",
        }
    ),
    "language_grammar_legacy_bridge": frozenset({"language_grammar_catalog"}),
    # Evaluation consumes Spec/lesson patterns → evidence observations only.
    "language_grammar_evaluation": frozenset(
        {
            "language_grammar_activity_spec",
            "language_grammar_evidence",
            "language_grammar_catalog",
        }
    ),
    # Pipeline orchestrates existing packages only — no algorithms.
    "language_grammar_pipeline": frozenset(
        {
            "language_grammar_integration",
            "language_grammar_lesson_planner",
            "language_grammar_activity_authoring",
            "language_grammar_activity_spec",
            "language_grammar_skill_executor",
            "language_grammar_evaluation",
            "language_grammar_evidence",
            "language_grammar_mastery",
            "language_grammar_review",
            "language_grammar_progression",
        }
    ),
    # Student product surface — generate-only via pipeline generate path.
    "language_grammar_module": frozenset(
        {
            "language_grammar_integration",
            "language_grammar_lesson_planner",
            "language_grammar_pipeline",
            "language_grammar_integrity",
            "language_grammar_skill_context",
        }
    ),
    # Wave C skill facade — resolver + catalog read + pipeline completion only.
    "language_grammar_skill_context": frozenset(
        {
            "language_grammar_target_resolver",
            "language_grammar_catalog",
            "language_grammar_pipeline",
        }
    ),
    # Wave D integrity — attested completion over pipeline; consumes skill_context types.
    "language_grammar_integrity": frozenset(
        {
            "language_grammar_pipeline",
            "language_grammar_skill_context",
            "language_grammar_catalog",
        }
    ),
}

ARCHITECTURE_LAYERS: tuple[str, ...] = (
    "catalog",
    "legacy",
    "evidence",
    "progression",  # unlock only — independent of mastery scores
    "mastery",
    "review",
    "integration",  # facade before planning — Planner depends only on this
    "target_resolver",  # sole skill Runtime entry for grammar targets
    "planning",
    "generation",  # ELP authoring
    "activity_spec",  # canonical activity contracts (before providers)
    "activity_authoring",  # Grammar-target → ActivitySpecification authoring
    "activity",  # activity providers
    "skill_domain",  # speaking/reading/... domain models (no LLM/audio)
    "skill_execution",  # execute ActivitySpecification via Registry plugins
    "evaluation",  # grammar-constrained evaluation → evidence observations
    "runtime",
    "pipeline",  # end-to-end orchestration (Integration Phase 1)
    "skill_context",  # Wave C shared grammar context (bridges resolver + pipeline completion)
    "integrity",  # Wave D attested completion + ledger + stamps
    "product",  # student-facing Grammar module (Milestone A)
    "analytics",
)

PACKAGE_LAYER: dict[str, str] = {
    "language_grammar_catalog": "catalog",
    "language_grammar_legacy_bridge": "legacy",
    "language_grammar_evidence": "evidence",
    "language_grammar_progression": "progression",
    "language_grammar_mastery": "mastery",
    "language_grammar_review": "review",
    "language_grammar_lesson_planner": "planning",
    "language_grammar_educational_package": "generation",
    "language_grammar_activity_spec": "activity_spec",
    "language_grammar_activity_authoring": "activity_authoring",
    "language_grammar_activity_provider": "activity",
    "language_grammar_speaking": "skill_domain",
    "language_grammar_skill_executor": "skill_execution",
    "language_grammar_evaluation": "evaluation",
    "language_grammar_lesson_runtime": "runtime",
    "language_grammar_pipeline": "pipeline",
    "language_grammar_module": "product",
    "language_grammar_integration": "integration",
    "language_grammar_target_resolver": "target_resolver",
    "language_grammar_skill_context": "skill_context",
    "language_grammar_integrity": "integrity",
    "language_grammar_analytics": "analytics",
}

# Packages that must exist with __init__.py + types.py for G0.
REQUIRED_G0_PACKAGES: frozenset[str] = frozenset(PACKAGE_OWNERSHIP.keys())

# Skills and other packages must not write mastery; Evidence is the only bridge.
MASTERY_WRITE_OWNER: str = "language_grammar_mastery"
# Evidence validates observations; Mastery alone applies scores (bridge = evidence package name).
EVIDENCE_TO_MASTERY_BRIDGE: str = "language_grammar_evidence"


# Packages forbidden from calling mastery write/persist APIs (Mastery is sole scorer).
FORBIDDEN_MASTERY_WRITERS: frozenset[str] = frozenset(
    {
        "language_grammar_catalog",
        "language_grammar_evidence",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_lesson_planner",
        "language_grammar_educational_package",
        "language_grammar_lesson_runtime",
        "language_grammar_activity_provider",
        "language_grammar_activity_spec",
        "language_grammar_activity_authoring",
        "language_grammar_skill_executor",
        "language_grammar_evaluation",
        "language_grammar_speaking",
        "language_grammar_analytics",
        "language_grammar_integration",
        "language_grammar_target_resolver",
        "language_grammar_skill_context",
        "language_grammar_integrity",
        "language_grammar_legacy_bridge",
        "language_grammar_module",
    }
)

# JSONB namespace under LanguageProgression.promotion_readiness_json
GRAMMAR_JSONB_NAMESPACE: str = "grammar"

# Reserved sibling namespace for future Vocabulary spine — must not collide.
VOCABULARY_JSONB_NAMESPACE_RESERVED: str = "vocabulary"

# Reserved sibling namespace for Adaptive Learning Intelligence (Phase 2).
# Adaptive may persist preference/profile data here only — never under grammar.*.
ADAPTIVE_JSONB_NAMESPACE_RESERVED: str = "adaptive_intelligence"

# Adaptive package lives outside REQUIRED_G0_PACKAGES but must never write mastery.
ADAPTIVE_INTELLIGENCE_PACKAGE: str = "language_adaptive_intelligence"

# Reserved sibling namespace for AI Tutor Foundation (Wave E1).
# Tutor may persist conversation memory here only — never under grammar.* or adaptive_intelligence.
AI_TUTOR_JSONB_NAMESPACE_RESERVED: str = "ai_tutor"
AI_TUTOR_PACKAGE: str = "language_ai_tutor"

# Reserved sibling namespace for Conversational Coaching (Wave E2).
# Coaching session state only — never grammar.*, adaptive_intelligence, or ai_tutor memory.
AI_TUTOR_COACHING_JSONB_NAMESPACE_RESERVED: str = "ai_tutor_coaching"
AI_TUTOR_COACHING_PACKAGE: str = "language_ai_tutor_coaching"

# Reserved sibling namespace for Autonomous AI Teacher (Phase F).
# Generated session plans only — never grammar/adaptive/tutor/coaching educational state.
AI_TEACHER_JSONB_NAMESPACE_RESERVED: str = "ai_teacher"
AI_TEACHER_PACKAGE: str = "language_ai_teacher"

# Learning Journey UI projection (Phase G) — compose-only; outside REQUIRED_G0_PACKAGES.
# Never writes mastery/progression; never invents unlocks.
LEARNING_JOURNEY_PACKAGE: str = "language_learning_journey"
