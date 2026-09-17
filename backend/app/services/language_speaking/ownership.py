"""Speaking package ownership registry (S0) — used by architecture verification."""

from __future__ import annotations

# Exactly one owner per responsibility. Keys are package directory names under app/services/.
PACKAGE_OWNERSHIP: dict[str, str] = {
    "language_speaking_audio_session": "Live/recorded session lifecycle and processing state (no scoring)",
    "language_speaking_audio_frontend": "Provider orchestration → canonical SpeakingSpeechEvidence",
    "language_speaking_providers": "Provider ABCs: transcription, embedding, phoneme, acoustic, speech output, educational analyzer",
    "language_speaking_evaluator": "Rule engine + SpeakingEvaluationEngineResult — owns pass/fail/readiness gates",
    "language_speaking_educational_analyzer": "LLM educational facts (JSON only) — never pass/fail/promotion",
    "language_speaking_pronunciation": "Phoneme/word/phrase/utterance pronunciation facts",
    "language_speaking_fluency": "Rate, pause, hesitation, filler, self-correction facts",
    "language_speaking_prosody": "Pitch, stress, rhythm, intonation facts (language learning only)",
    "language_speaking_live_conversation": "Provider-neutral live conversation contracts, turn/session/event facts, turn audio accumulator",
    "language_speaking_curriculum": "Skill dependency graph catalog and node metadata (S1+)",
    "language_speaking_knowledge_model": "Per-skill mastery, confidence, evidence, retention risk",
    "language_speaking_diagnostic": "Next-skill selection from graph + mastery gaps",
    "language_speaking_lesson_planner": "SpeakingLessonBlueprint — deterministic targets (no LLM)",
    "language_speaking_generation": "Lesson/conversation content generation pipeline",
    "language_speaking_interruption": "Interrupt/wait/micro-drill policy engine",
    "language_speaking_coach": "Canonical educational priority + render-only coach guidance",
    "language_speaking_evaluation_runtime": "Turn pipeline orchestration (evaluator + coach + S7→S2 knowledge bridge + persistence)",
    "language_speaking_explainability": "Student/teacher display mapping from canonical facts",
    "language_speaking_lesson_experience": "Student lesson bundle assembly",
    "language_speaking_journey": "JourneyBundle assembly for speaking",
    "language_speaking_live_budget": "Talk with Alex daily live budget + lease accounting (cost control, not educational authority)",
    "language_speaking_progression": "Post-turn progression runtime + JSONB mutation",
    "language_speaking_learning_stage": "Speaking learning stage engine (Stage 1–3)",
    "language_speaking_transition_gate": "Stage transition gate (pronunciation, fluency, task, stability, etc.)",
    "language_speaking_promotion_readiness": "Promotion readiness scoring (never promotes CEFR)",
    "language_speaking_promotion_stability": "Rolling readiness history / stability",
    "language_speaking_promotion_test": "SPA task bundles and sessions",
    "language_speaking_official_promotion": "Official speaking CEFR promotion (sole writer of official_speaking_cefr)",
    "language_speaking_legacy_adapter": "Freeze-wrap legacy flat services → canonical types (only legacy import path)",
}

SHARED_INFRASTRUCTURE: frozenset[str] = frozenset(
    {
        "language_speaking",  # enums + core types only
        "language_progression_service",
        "language_learner_memory_service",
        "language_learning_facts",
        "language_learning_narrative",
        "language_learning_goal",
        "language_level_utils",
    }
)

# Packages that may import legacy flat modules (language_conversation_service, etc.).
LEGACY_IMPORT_GATEWAY: frozenset[str] = frozenset({"language_speaking_legacy_adapter"})

# Legacy flat modules — frozen; no new features. S0 documents boundary only.
LEGACY_FLAT_MODULES: frozenset[str] = frozenset(
    {
        "language_speaking_service",
        "language_speaking_feedback_service",
        "language_speaking_coach_service",
        "language_speaking_evolution_service",
        "language_conversation_service",
        "language_conversation_ai_service",
        "language_conversation_correction",
        "language_conversation_scenario_service",
        "language_conversation_tts_task",
        "language_shadowing_service",
        "language_pronunciation_service",
        "language_transcription_service",
        "language_reply_tts_service",
        "speaking_coach_service",
        "speaking_coach_prompts",
    }
)

# Provider SDK names that must NOT appear outside audio_frontend / providers / legacy_adapter.
FORBIDDEN_PROVIDER_SDK_IMPORTS: frozenset[str] = frozenset(
    {
        "whisperx",
        "faster_whisper",
        "speechbrain",
        "opensmile",
        "parselmouth",
        "praat",
        "transformers",  # WavLM/HuBERT path — gated until S3+
        "livekit",
        "elevenlabs",
    }
)

ALLOWED_PACKAGE_DEPENDENCIES: dict[str, frozenset[str]] = {
    "language_speaking_audio_session": frozenset(),
    "language_speaking_live_budget": frozenset(),
    "language_speaking_providers": frozenset(),
    "language_speaking_audio_frontend": frozenset({"language_speaking_providers"}),
    "language_speaking_pronunciation": frozenset({"language_speaking_evaluator"}),
    "language_speaking_fluency": frozenset({"language_speaking_evaluator"}),
    "language_speaking_prosody": frozenset({"language_speaking_evaluator"}),
    "language_speaking_educational_analyzer": frozenset(),
    "language_speaking_live_conversation": frozenset(),
    "language_speaking_evaluator": frozenset(
        {
            "language_speaking_educational_analyzer",
            "language_speaking_pronunciation",
            "language_speaking_fluency",
            "language_speaking_prosody",
        }
    ),
    "language_speaking_curriculum": frozenset(),
    "language_speaking_knowledge_model": frozenset({"language_speaking_curriculum"}),
    "language_speaking_diagnostic": frozenset(
        {"language_speaking_curriculum", "language_speaking_knowledge_model"}
    ),
    "language_speaking_lesson_planner": frozenset(
        {"language_speaking_curriculum", "language_speaking_diagnostic", "language_speaking_knowledge_model"}
    ),
    "language_speaking_generation": frozenset({"language_speaking_lesson_planner"}),
    "language_speaking_interruption": frozenset({"language_speaking_evaluator", "language_speaking_lesson_planner"}),
    "language_speaking_coach": frozenset(
        {
            "language_speaking_evaluator",
            "language_speaking_diagnostic",
            "language_speaking_educational_analyzer",
            "language_speaking_curriculum",
            "language_speaking_knowledge_model",
            "language_speaking_lesson_planner",
        }
    ),
    "language_speaking_explainability": frozenset({"language_speaking_evaluator"}),
    "language_speaking_evaluation_runtime": frozenset(
        {
            "language_speaking_audio_session",
            "language_speaking_audio_frontend",
            "language_speaking_evaluator",
            "language_speaking_coach",
            "language_speaking_explainability",
            "language_speaking_progression",
            "language_speaking_legacy_adapter",
            "language_speaking_pronunciation",
            "language_speaking_prosody",
            "language_speaking_live_conversation",
            "language_speaking_curriculum",
            "language_speaking_knowledge_model",
        }
    ),
    "language_speaking_lesson_experience": frozenset(
        {
            "language_speaking_explainability",
            "language_speaking_coach",
            "language_speaking_generation",
            "language_speaking_lesson_planner",
        }
    ),
    "language_speaking_journey": frozenset(
        {
            "language_speaking_explainability",
            "language_speaking_progression",
            "language_speaking_promotion_test",
            "language_speaking_curriculum",
            "language_speaking_lesson_planner",
            "language_speaking_diagnostic",
            "language_speaking_knowledge_model",
            "language_speaking_live_budget",
        }
    ),
    "language_speaking_progression": frozenset(
        {
            "language_speaking_evaluator",
            "language_speaking_learning_stage",
            "language_speaking_promotion_readiness",
            "language_speaking_promotion_stability",
            "language_speaking_knowledge_model",
        }
    ),
    "language_speaking_learning_stage": frozenset(
        {
            "language_speaking_knowledge_model",
            "language_speaking_curriculum",
            "language_speaking_diagnostic",
            "language_speaking_lesson_planner",
            "language_speaking_transition_gate",
        }
    ),
    "language_speaking_transition_gate": frozenset({"language_speaking_learning_stage"}),
    "language_speaking_promotion_readiness": frozenset(
        {
            "language_speaking_learning_stage",
            "language_speaking_knowledge_model",
        }
    ),
    "language_speaking_promotion_stability": frozenset(
        {
            "language_speaking_promotion_readiness",
            "language_speaking_knowledge_model",
        }
    ),
    "language_speaking_promotion_test": frozenset(
        {
            "language_speaking_curriculum",
            "language_speaking_generation",
        }
    ),
    "language_speaking_official_promotion": frozenset(
        {"language_speaking_promotion_test", "language_speaking_progression"}
    ),
    "language_speaking_legacy_adapter": frozenset(
        {
            "language_speaking_audio_frontend",
            "language_speaking_evaluator",
        }
    ),
}

ARCHITECTURE_LAYERS: tuple[str, ...] = (
    "session",  # audio_session
    "providers",  # providers
    "audio",  # audio_frontend
    "analysis",  # pronunciation, fluency, prosody, educational_analyzer
    "evaluation",  # evaluator
    "curriculum",  # curriculum, knowledge_model, diagnostic
    "planning",  # lesson_planner
    "generation",  # generation
    "policy",  # interruption
    "pedagogy",  # coach
    "facts",  # explainability
    "evaluation_runtime",  # evaluation_runtime
    "experience",  # lesson_experience
    "journey",  # journey
    "progression",  # progression, learning_stage, promotion_*
    "legacy",  # legacy_adapter
)

PACKAGE_LAYER: dict[str, str] = {
    "language_speaking_audio_session": "session",
    "language_speaking_live_budget": "session",
    "language_speaking_providers": "providers",
    "language_speaking_audio_frontend": "audio",
    "language_speaking_pronunciation": "analysis",
    "language_speaking_fluency": "analysis",
    "language_speaking_prosody": "analysis",
    "language_speaking_educational_analyzer": "analysis",
    "language_speaking_live_conversation": "analysis",
    "language_speaking_evaluator": "evaluation",
    "language_speaking_curriculum": "curriculum",
    "language_speaking_knowledge_model": "curriculum",
    "language_speaking_diagnostic": "curriculum",
    "language_speaking_lesson_planner": "planning",
    "language_speaking_generation": "generation",
    "language_speaking_interruption": "policy",
    "language_speaking_coach": "pedagogy",
    "language_speaking_explainability": "facts",
    "language_speaking_evaluation_runtime": "evaluation_runtime",
    "language_speaking_lesson_experience": "experience",
    "language_speaking_journey": "journey",
    "language_speaking_progression": "progression",
    "language_speaking_learning_stage": "progression",
    "language_speaking_transition_gate": "progression",
    "language_speaking_promotion_readiness": "progression",
    "language_speaking_promotion_stability": "progression",
    "language_speaking_promotion_test": "progression",
    "language_speaking_official_promotion": "progression",
    "language_speaking_legacy_adapter": "legacy",
}

REQUIRED_S0_PACKAGES: frozenset[str] = frozenset(PACKAGE_OWNERSHIP.keys())

# New speaking packages must not import legacy flat modules directly.
FORBIDDEN_LEGACY_IMPORTS_IN: frozenset[str] = REQUIRED_S0_PACKAGES - LEGACY_IMPORT_GATEWAY
