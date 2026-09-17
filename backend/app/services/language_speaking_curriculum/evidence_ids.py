"""Canonical evidence dimension identifiers for Speaking skill graph (S1).

These are provider-agnostic codes. Audio frontend and evaluation engines map
provider outputs to these IDs in S4–S7. The graph declares requirements only.
"""

from __future__ import annotations

# Pronunciation / phoneme
PHONEME_ALIGNMENT = "phoneme_alignment"
PRONUNCIATION_CONFIDENCE = "pronunciation_confidence"
ACOUSTIC_SUPPORT = "acoustic_support"
WORD_STRESS_ACCURACY = "word_stress_accuracy"

# Fluency
SPEAKING_RATE = "speaking_rate"
ARTICULATION_RATE = "articulation_rate"
PAUSES = "pauses"
HESITATIONS = "hesitations"
REPETITIONS = "repetitions"
SELF_CORRECTION = "self_correction"

# Prosody
PITCH = "pitch"
STRESS = "stress"
RHYTHM = "rhythm"
INTONATION = "intonation"
ENERGY_VARIATION = "energy_variation"

# Communicative / semantic
SEMANTIC_TASK_RESPONSE = "semantic_task_response"
MEANING_SUCCESS = "meaning_success"
VOCABULARY_FUNCTION = "vocabulary_function"
GRAMMAR_CONTROL = "grammar_control"
TOPIC_DEVELOPMENT = "topic_development"
ORGANIZATION_EVIDENCE = "organization_evidence"

# Interaction
RESPONSE_RELEVANCE = "response_relevance"
TURN_COMPLETION = "turn_completion"
CLARIFICATION_BEHAVIOR = "clarification_behavior"
CONVERSATION_STATE = "conversation_state"

# All known evidence codes (for validator)
ALL_EVIDENCE_CODES: frozenset[str] = frozenset(
    {
        PHONEME_ALIGNMENT,
        PRONUNCIATION_CONFIDENCE,
        ACOUSTIC_SUPPORT,
        WORD_STRESS_ACCURACY,
        SPEAKING_RATE,
        ARTICULATION_RATE,
        PAUSES,
        HESITATIONS,
        REPETITIONS,
        SELF_CORRECTION,
        PITCH,
        STRESS,
        RHYTHM,
        INTONATION,
        ENERGY_VARIATION,
        SEMANTIC_TASK_RESPONSE,
        MEANING_SUCCESS,
        VOCABULARY_FUNCTION,
        GRAMMAR_CONTROL,
        TOPIC_DEVELOPMENT,
        ORGANIZATION_EVIDENCE,
        RESPONSE_RELEVANCE,
        TURN_COMPLETION,
        CLARIFICATION_BEHAVIOR,
        CONVERSATION_STATE,
    }
)
