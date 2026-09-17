# AI Writing Coach Architecture (W2.1 — FROZEN)

**Status:** FROZEN — future phases must reuse this architecture; no redesign permitted.

Design-only. No generation, runtime, frontend, or storage.

## Mission

The Writing Coach is an **AI teacher**, not an evaluator. Educational facts and teaching voice are strictly separated.

## End-to-end flow (frozen)

```
Student
  ↓ submit draft
Writing Evaluator              ← computes rubric facts
  ↓
Writing Facts                  ← explainability assembles bundle
  ↓
Learning Narrative Builder     ← shared language_learning_narrative
  ↓
Coach Mission Layer            ← today's mission / focus / goal / criteria / outcomes
  ↓
Lesson Experience              ← mission card + composer
  ↓
Writing Coach                  ← personality + memory + adaptive tone → revision plan
  ↓
Revision Plan                  ← student-facing teaching output
  ↓
Student
```

## 1. Goal Profiles (complete educational profiles)

**Owner:** `language_writing_curriculum/goal_profiles.py`
**Version:** `GOAL_PROFILE_VERSION = "2.1.0"`

Each of 8 `WritingGoal` profiles defines:

| Field | Purpose |
|-------|---------|
| `preferred_task_types` | Task selection bias |
| `preferred_genres` | Genre selection bias |
| `preferred_mission_style` | How missions are framed |
| `preferred_writing_outputs` | ExpectedWritingOutput set |
| `preferred_vocabulary_categories` | LexisCategory priorities |
| `preferred_grammar_priorities` | Grammar focus order |
| `preferred_coach_tone` | Default communication tone |
| `preferred_revision_style` | How coach guides revision |
| `preferred_promotion_style` | WPA / promotion framing |
| + coach defaults, feedback style, WPA key, topic/chain prefs |

## 2. Coach Personalities

**Owner:** `language_writing_coach/personalities.py`

Seven personalities. **Fixed per session goal** — does not change with adaptive tone.

## 3. Adaptive Coach Tone

**Owner:** `language_writing_coach/adaptive_tone.py`

Personality stays fixed. Tone adapts for:

- Student frustration
- Recent improvement
- Repeated failures
- Long inactivity
- High confidence

**Invariant:** Educational content (priority issue, outcomes, success criteria) never changes — only communication style.

## 4. Coach Memory

**Owner:** `language_writing_coach/memory_design.py`

Tracks (architecture only):

- Repeated mistakes / strengths
- Grammar & vocabulary habits
- Grammar trend / vocabulary trend
- Writing speed trend
- Revision behaviour
- Favorite / avoided topics
- Confidence trend
- Learning momentum
- Student preferences

## 5. Coach Mission Layer

**Owner:** `language_writing_coach/mission_layer.py`

Every lesson begins with:

1. Today's Mission
2. Today's Focus
3. Today's Goal
4. Success Criteria
5. Expected Learning Outcomes

Mission text is assembled **after** narrative builder. Does not generate lesson content.

## 6. Revision Plan

**Owner:** `language_writing_coach/types.py` → `WritingRevisionPlan`

Encouragement · Main issue · Priority · Example · Revision mission · Ready to complete · Next lesson recommendation

## 7. Feedback layers

See `FEEDBACK_LAYERS.md`.

## 8. Freeze policy

- W2.1 architecture is **frozen** as of this document.
- W3+ may **implement** against these contracts.
- W3+ may **extend** memory signals or add personalities via enum + catalog pattern.
- W3+ must **not redesign** evaluator/coach separation, pipeline order, or mission layer placement.

## Verification

```bash
python scripts/verify_writing_w2_coach_architecture.py
```
