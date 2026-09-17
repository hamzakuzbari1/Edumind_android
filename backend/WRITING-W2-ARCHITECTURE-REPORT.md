# Writing W2.1 — AI Writing Coach Architecture Report (FROZEN)

**Phase:** W2 final refinement + freeze
**Architecture version:** `2.1.0-frozen`
**Goal profile version:** `2.1.0`
**Status:** Complete — verification green
**Topic Universe:** Frozen at catalog v1.2.0 (unchanged)

---

## Executive Summary

W2.1 completes and **freezes** the AI Writing Coach architecture. Future phases must reuse these contracts — no redesign permitted. No generation, runtime, frontend, or storage was implemented.

---

## Frozen Pipeline

```
Student → Evaluator → Facts → Narrative → Coach Mission → Lesson Experience
                ↓ (on draft submit)
         Coach (+ adaptive tone + memory) → Revision Plan → Student
```

---

## 1. Goal Profile Enrichment

Every `WritingGoalProfile` now defines:

| Field | Description |
|-------|-------------|
| `preferred_mission_style` | How missions are framed |
| `preferred_writing_outputs` | ExpectedWritingOutput set |
| `preferred_vocabulary_categories` | LexisCategory priorities |
| `preferred_grammar_priorities` | Grammar focus order |
| `preferred_coach_tone` | Default communication tone |
| `preferred_revision_style` | Revision guidance style |
| `preferred_promotion_style` | WPA / promotion framing |
| + task types, genres, coach defaults, WPA key |

**Module:** `language_writing_curriculum/goal_profiles.py`

---

## 2. Coach Memory Expansion

**Module:** `language_writing_coach/memory_design.py`

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

---

## 3. Adaptive Coach Tone

**Module:** `language_writing_coach/adaptive_tone.py`

Personality **fixed**. Tone adapts for frustration, improvement, repeated failures, inactivity, high confidence.

**Invariant:** Educational content never changes — only communication style.

---

## 4. Coach Mission Layer

**Module:** `language_writing_coach/mission_layer.py`

Placed **after** Learning Narrative Builder. Every lesson opens with:

1. Today's Mission
2. Today's Focus
3. Today's Goal
4. Success Criteria
5. Expected Learning Outcomes

Does not generate lesson content.

---

## 5. Freeze Policy

- Coach architecture is **frozen** at W2.1
- W3+ may implement and extend signals
- W3+ must **not** redesign evaluator/coach separation or pipeline order
- Documented in `COACH_ARCHITECTURE.md`

---

## Files Added/Updated

| File | Change |
|------|--------|
| `language_writing/enums.py` | MissionStyle, RevisionStyle, CoachTone |
| `language_writing_curriculum/types.py` | Complete goal profile fields |
| `language_writing_curriculum/goal_profiles.py` | Enriched 8 profiles |
| `language_writing_coach/memory_design.py` | Expanded memory signals |
| `language_writing_coach/adaptive_tone.py` | **New** |
| `language_writing_coach/mission_layer.py` | **New** |
| `language_writing_coach/COACH_ARCHITECTURE.md` | W2.1 + freeze |
| `language_writing_coach/FEEDBACK_LAYERS.md` | Mission layer added |
| `language_writing_bundles.py` | `WritingCoachMissionOut` |
| `verify_writing_w2_coach_architecture.py` | W2.1 checks |

---

## Verification

```bash
cd backend
python scripts/verify_writing_w2_coach_architecture.py
```

---

## Not Started

- W3 and beyond — awaiting explicit approval
- No lesson generation, AI runtime, frontend, or memory storage
