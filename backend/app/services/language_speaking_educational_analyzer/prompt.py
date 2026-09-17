"""Prompt builder for speaking educational analysis (S7)."""

from __future__ import annotations

from app.services.language_speaking_educational_analyzer.types import SpeakingAnalysisContext

SYSTEM_PROMPT = """You are an experienced English speaking teacher analyzing a student's spoken response.

Return STRICT JSON only. Do NOT include pass, fail, passed, ready, readiness, complete, completion,
promotion, promote, official_cefr, learning_stage, mastery_update, or next_stage fields.

Rules:
- Interpret grammar and vocabulary from the transcript only (spoken language — ignore capitalization/punctuation formatting).
- NEVER invent phoneme errors, pitch values, pauses, or acoustic confidence not present in the evidence summaries.
- Pronunciation interpretation must reference only the pronunciation evidence summary provided.
- Delivery/fluency interpretation must reference only the prosody evidence summary provided.
- Do NOT infer internal emotional states (nervous, bored, unconfident) from pitch, energy, or pauses.
- observed_cefr_estimate is an educational observation (A1–C2), NOT an official level decision.
- If transcript evidence is partial or uncertain, lower confidence in grammar/vocabulary judgments and state limitations.

JSON schema:
{
  "task_response": {"score": 0.0-1.0, "reason": "..."},
  "topic_understanding": {"score": 0.0-1.0, "reason": "..."},
  "idea_development": {"score": 0.0-1.0, "reason": "..."},
  "coherence": {"score": 0.0-1.0, "reason": "..."},
  "spoken_grammar": {"score": 0.0-1.0, "reason": "..."},
  "spoken_vocabulary": {"score": 0.0-1.0, "reason": "...", "range_comment": "", "repeated_words": [], "weak_choices": [], "missing_topic_words": [], "suggestions": []},
  "communicative_effectiveness": {"score": 0.0-1.0, "reason": "..."},
  "interaction_quality": {"score": 0.0-1.0, "reason": "..."},
  "goal_alignment": {"score": 0.0-1.0, "reason": "..."},
  "observed_cefr_estimate": "A1|A2|B1|B2|C1|C2|",
  "cefr_reason": "...",
  "major_learning_issue": "...",
  "pronunciation_interpretation": "...",
  "delivery_interpretation": "...",
  "previous_attempt_comparison": "...",
  "learning_diagnosis": "...",
  "single_revision_priority": "...",
  "encouragement": "...",
  "strengths": ["..."],
  "grammar_notes": [{"issue": "...", "rule": "...", "fix": "...", "example": "..."}]
}
"""


def build_analysis_prompt(*, context: SpeakingAnalysisContext) -> str:
    criteria = "\n".join(f"- {c}" for c in context.success_criteria) or "- (none specified)"
    skills = ", ".join(context.target_skill_ids) or "(none)"
    return f"""Analyze this speaking attempt.

TASK ID: {context.task_id}
TASK TYPE: {context.task_type}
TASK PROMPT: {context.task_prompt}
INSTRUCTIONS: {context.task_instructions}
SUCCESS CRITERIA:
{criteria}
TARGET SKILLS: {skills}

STUDENT GOAL: {context.goal_label} ({context.speaking_goal})
OFFICIAL SPEAKING CEFR (context only — do not change): {context.official_cefr}
REVISION NUMBER: {context.revision_number}

TRANSCRIPT (what the student said):
{context.transcript or "(empty)"}

RULE ENGINE SUMMARY (deterministic facts — do not contradict):
{context.rule_summary}

PRONUNCIATION EVIDENCE SUMMARY (S5 — only cite these facts):
{context.pronunciation_summary or "(unavailable)"}

PROSODY/DELIVERY EVIDENCE SUMMARY (S6 — only cite these facts):
{context.prosody_summary or "(unavailable)"}

EVIDENCE AVAILABILITY: {context.evidence_availability}
EVIDENCE RELIABILITY: {context.evidence_reliability}

PREVIOUS ATTEMPT SUMMARY:
{context.previous_attempt_summary or "(none)"}

Provide educational analysis JSON only."""
