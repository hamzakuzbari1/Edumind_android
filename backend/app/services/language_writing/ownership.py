"""Writing package ownership registry (W0) — used by architecture verification."""

from __future__ import annotations

# Exactly one owner per responsibility. Keys are package directory names under app/services/.
PACKAGE_OWNERSHIP: dict[str, str] = {
    "language_writing_topic_universe": "Canonical topic catalog, topic nodes, complexity curves per topic",
    "language_writing_knowledge_chain": "Knowledge chain registry, chain nodes, prerequisites, chain progression",
    "language_writing_grammar_progression": "Grammar structure tracking and 4-state mastery",
    "language_writing_lexis_progression": "Lemma + category tracking and balancing rules",
    "language_writing_curriculum": "Lesson selection, anti-repetition, goal-aware blended scoring",
    "language_writing_lesson_planner": "Deterministic lesson planning — educational targets and Lesson Blueprint (no LLM)",
    "language_writing_generation": "Writing generation pipeline — Mission Builder, Prompt Builder, Normalizer, Validator, Repair, Audit",
    "language_writing_runtime": "Writing generation runtime — Claude provider and full pipeline orchestration (W6)",
    "language_writing_explainability": "Writing-specific facts assembly (internal signals only)",
    "language_writing_evaluator": "Draft evaluation and educational fact computation — no coach copy",
    "language_writing_educational_analyzer": "Claude educational analysis for writing drafts — structured JSON facts only (no pass/fail)",
    "language_writing_revision": "Draft/revision lifecycle orchestration and persistence contracts",
    "language_writing_coach": "AI coach output contract, trend detection, personality rendering",
    "language_writing_portfolio": "Educational portfolio snapshots (no scoring/progression influence)",
    "language_writing_lesson_experience": "Student Lesson Experience assembly and LessonExperienceBundle (W4 student lesson)",
    "language_writing_journey": "JourneyBundle assembly for writing",
    "language_writing_progression": "Post-completion progression runtime (confidence/evidence/challenge hooks)",
    "language_writing_learning_stage": "Writing learning stage engine (Stage 1–3, gate-gated transitions)",
    "language_writing_transition_gate": "Writing stage transition gate (grammar, vocab, revision, confidence, evidence, stability)",
    "language_writing_promotion_readiness": "Writing promotion readiness scoring (0–100, never promotes CEFR)",
    "language_writing_promotion_stability": "Writing promotion stability — rolling readiness history",
    "language_writing_promotion_test": "WPA task bundles, sessions, goal-specific assessments",
    "language_writing_official_promotion": "Official writing CEFR promotion ceremony (only writer of official_writing_cefr)",
    "language_writing_evaluation_runtime": "Writing evaluation and revision runtime — evaluator, narrative, coach, revision loop (W7)",
}

# Shared infrastructure — not skill engines; writing packages may import these.
SHARED_INFRASTRUCTURE: frozenset[str] = frozenset(
    {
        "language_writing",  # enums.py only for W0
        "language_learning_facts",
        "language_learning_narrative",
        "language_learning_goal",
        "language_progression_service",
    }
)

# Allowed direct dependencies between writing packages (DAG). Empty = leaf package.
ALLOWED_PACKAGE_DEPENDENCIES: dict[str, frozenset[str]] = {
    "language_writing_topic_universe": frozenset({"language_writing_knowledge_chain"}),
    "language_writing_knowledge_chain": frozenset({"language_writing_topic_universe"}),
    "language_writing_grammar_progression": frozenset(),
    "language_writing_lexis_progression": frozenset(),
    "language_writing_curriculum": frozenset(
        {
            "language_writing_topic_universe",
            "language_writing_knowledge_chain",
            "language_writing_grammar_progression",
            "language_writing_lexis_progression",
        }
    ),
    "language_writing_generation": frozenset({"language_writing_lesson_planner"}),
    "language_writing_runtime": frozenset(
        {
            "language_writing_generation",
            "language_writing_lesson_planner",
            "language_writing_curriculum",
            "language_writing_topic_universe",
            "language_writing_knowledge_chain",
            "language_writing_progression",
        }
    ),
    "language_writing_lesson_planner": frozenset(
        {
            "language_writing_topic_universe",
            "language_writing_knowledge_chain",
            "language_writing_curriculum",
            "language_writing_grammar_progression",
            "language_writing_lexis_progression",
        }
    ),
    "language_writing_explainability": frozenset(
        {
            "language_writing_topic_universe",
            "language_writing_knowledge_chain",
            "language_writing_grammar_progression",
            "language_writing_lexis_progression",
            "language_writing_curriculum",
            "language_writing_evaluator",
        }
    ),
    "language_writing_evaluator": frozenset(
        {
            "language_writing_knowledge_chain",
            "language_writing_grammar_progression",
            "language_writing_lexis_progression",
            "language_writing_curriculum",
            "language_writing_educational_analyzer",
        }
    ),
    "language_writing_educational_analyzer": frozenset(),
    "language_writing_revision": frozenset({"language_writing_coach", "language_writing_evaluator"}),
    "language_writing_coach": frozenset(
        {
            "language_writing_grammar_progression",
            "language_writing_lexis_progression",
            "language_writing_evaluator",
            "language_writing_curriculum",
        }
    ),
    "language_writing_portfolio": frozenset(
        {
            "language_writing_revision",
            "language_writing_coach",
        }
    ),
    "language_writing_lesson_experience": frozenset(
        {
            "language_writing_explainability",
            "language_writing_revision",
            "language_writing_coach",
            "language_writing_generation",
        }
    ),
    "language_writing_journey": frozenset(
        {
            "language_writing_explainability",
            "language_writing_coach",
            "language_writing_progression",
            "language_writing_promotion_test",
            "language_writing_curriculum",
            "language_writing_runtime",
        }
    ),
    "language_writing_progression": frozenset(
        {
            "language_writing_explainability",
            "language_writing_evaluator",
            "language_writing_revision",
        }
    ),
    "language_writing_promotion_test": frozenset(
        {
            "language_writing_topic_universe",
            "language_writing_curriculum",
        }
    ),
    "language_writing_evaluation_runtime": frozenset(
        {
            "language_writing_evaluator",
            "language_writing_explainability",
            "language_writing_coach",
            "language_writing_revision",
            "language_writing_curriculum",
            "language_writing_generation",
            "language_writing_progression",
        }
    ),
    "language_writing_official_promotion": frozenset(
        {
            "language_writing_promotion_test",
            "language_writing_progression",
        }
    ),
}
ARCHITECTURE_LAYERS: tuple[str, ...] = (
    "catalog",  # topic_universe, knowledge_chain, arc, grammar, lexis
    "selection",  # curriculum
    "planning",  # lesson_planner
    "generation",  # generation (presentation transform)
    "runtime",  # writing_runtime (W6 LLM orchestration)
    "evaluation",  # evaluator
    "facts",  # explainability
    "pedagogy",  # revision, coach
    "evaluation_runtime",  # W7 evaluation + revision orchestration
    "experience",  # lesson_experience
    "journey",  # journey
    "progression",  # progression, promotion_test, official_promotion
    "portfolio",  # portfolio (read-only sidecar)
)

PACKAGE_LAYER: dict[str, str] = {
    "language_writing_topic_universe": "catalog",
    "language_writing_knowledge_chain": "catalog",
    "language_writing_grammar_progression": "catalog",
    "language_writing_lexis_progression": "catalog",
    "language_writing_curriculum": "selection",
    "language_writing_lesson_planner": "planning",
    "language_writing_generation": "generation",
    "language_writing_runtime": "runtime",
    "language_writing_evaluator": "evaluation",
    "language_writing_explainability": "facts",
    "language_writing_revision": "pedagogy",
    "language_writing_coach": "pedagogy",
    "language_writing_lesson_experience": "experience",
    "language_writing_journey": "journey",
    "language_writing_progression": "progression",
    "language_writing_promotion_test": "progression",
    "language_writing_evaluation_runtime": "evaluation_runtime",
    "language_writing_official_promotion": "progression",
    "language_writing_portfolio": "portfolio",
}

# Packages that must exist with __init__.py + types.py for W0.
REQUIRED_W0_PACKAGES: frozenset[str] = frozenset(PACKAGE_OWNERSHIP.keys())
