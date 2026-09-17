# Speaking Skill Dependency Graph (S1)

## Why the graph exists

Legacy Speaking scores symptoms (fluency %, word pronunciation list) without tracing **which underlying skill** caused a breakdown. The Skill Dependency Graph is the canonical educational map that lets future systems answer:

- "What prerequisite skill caused this speaking problem?"
- "What is the highest-value next skill to practice?"

S1 defines the catalog and trace utilities only. No student mastery, no selection logic, no audio.

## Owner

**`language_speaking_curriculum`** owns all prerequisite relationships. Other packages (diagnostic, knowledge model, lesson planner) **read** the graph; they must not redefine edges.

## Node model (`SpeakingSkillNode`)

| Field | Future consumer |
|-------|-----------------|
| `skill_id` | S2 mastery keys, all persistence references |
| `skill_type` | S8 filtering, S9 blueprint targeting |
| `cefr_min` / `cefr_max` | S8–S9 level-aware selection |
| `prerequisite_skill_ids` | S8 diagnostic trace-back |
| `next_skill_ids` | S9 forward curriculum path |
| `related_skill_ids` | S8 cross-links (non-directional) |
| `mastery_requirements` | S2 Student Knowledge Model gates |
| `evidence_requirements` | S7 Evaluation Engine dimension mapping |
| `goal_relevance` | S8 goal-weighted diagnostic |
| `diagnostic_tags` / `remediation_tags` | S8 trace, S12 coach hints |
| `recommended_activity_types` | S9–S10 lesson shapes |
| `spaced_repetition_profile` | S2 retention scheduling |
| `transfer_targets` | S8 remediation routing |

Stable IDs use `category:slug` (e.g. `phoneme:theta`, `task:debate`). Labels may change; IDs must not.

## Skill types (S0 enum — not redesigned)

| S0 `SpeakingSkillType` | S1 concept |
|------------------------|------------|
| `phoneme` | Speech primitive |
| `pronunciation_pattern` | Pattern / contrast |
| `word` | Word realization |
| `phrase` | Phrase pattern |
| `grammar_structure` | Grammar-for-speaking |
| `vocabulary_function` | Vocabulary function |
| `speaking_function` | Communicative function |
| `fluency_skill` | Fluency control |
| `prosody_skill` | Prosody / intonation |
| `interaction_skill` | Interaction |
| `conversation_skill` | Conversation |
| `task_skill` | Extended task |

Skill type and graph depth are independent — a `task_skill` may depend on phoneme, fluency, and function nodes.

## Prerequisite DAG rules

- **Prerequisite edges are directed** (A → B means B requires A). The prerequisite subgraph must be acyclic.
- **`next_skill_ids` must be symmetric** with prerequisites (if B lists A as prereq, A lists B as next).
- **Related skills** are advisory cross-links; they do not create prerequisite edges and are not cycle-checked.
- **Roots** (`is_root=True` or empty prerequisites) are entry points for trace forward walks.

## Mastery requirements (catalog only)

`SkillMasteryRequirement` declares evidence counts, stability sessions, thresholds, and flags (e.g. `task_response_required`). **S2 evaluates**; Claude/runtime must never invent requirements.

## Evidence requirements

`SkillEvidenceRequirement` lists canonical evidence codes from `evidence_ids.py` (e.g. `phoneme_alignment`, `speaking_rate`). Providers map outputs in S4–S7; the graph only declares which dimensions can support each skill.

## Goal relevance

Uses canonical `SpeakingGoal` from S0 (`general_english`, `travel`, `ielts`, `business`, `academic`, `job_interview`, `daily_communication`). Each node declares `goal_relevance` for S8 goal-weighted prioritization — not copied from Writing goal profiles.

## Versioning

- `SPEAKING_SKILL_GRAPH_VERSION` — catalog content version
- `SPEAKING_SKILL_SCHEMA_VERSION` — node contract version

Persisted student mastery (S2+) must reference stable `skill_id` values. Graph version bumps require migration notes when nodes are renamed or removed.

## Graph examples

### 1. Opinion and reasoning (pronunciation → task)

```
phoneme:theta → pattern:th_substitution → word:think → phrase:i_think
  → function:express_opinion → function:support_opinion → skill:explain_reasoning → task:debate
```

### 2. Questions → clarification → interaction

```
prosody:question_intonation → phrase:yes_no_questions → phrase:polite_questions
  → function:clarification_request → interaction:interactive_conversation
```

### 3. Past tense → extended narrative

```
grammar:past_tense_control → phrase:past_event_sentence → skill:sequence_events
  → skill:tell_story → task:extended_narrative
```

### 4. IELTS extended (multi-family prerequisites)

`task:ielts_extended_response` requires Part 2 cue-card skill, explain-reasoning function, support-opinion function, IELTS fluency under time pressure, and spoken organization — spanning function, fluency, and task families.

## Trace utilities (`SpeakingSkillGraphTrace`)

- `get_skill`, `get_direct_prerequisites`, `get_prerequisites` / `get_ancestors`
- `get_next_skills`, `get_descendants`
- `find_dependency_path(from, to)`
- `find_root_prerequisite_candidates(skill_id)`
- `relationship_between([skills])`

Student-specific next-skill selection is **S8** (`language_speaking_diagnostic`).

## What S1 does NOT do

- Student mastery storage or scoring (S2)
- Audio processing or provider calls (S3+)
- Evaluation or pass/fail (S7)
- Diagnostic next-skill selection (S8)
- Lesson generation (S10)
- Progression / promotion (S15–S18)
- Frontend changes
- Legacy runtime hotfixes

## Verification

```bash
python scripts/verify_speaking_s1_skill_graph.py
python scripts/verify_speaking_s0_architecture.py
```
