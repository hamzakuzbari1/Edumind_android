# Writing W1.1 — Topic Universe Refinement Report

**Phase:** W1 refinement (pre-W2)
**Catalog version:** `1.1.0`
**Status:** Complete — verification green

---

## Summary

Strengthened educational metadata on all **119 nodes** across **40 chains** without changing architecture, implementing AI, or generating lessons.

---

## 1. Future Branching (documented only)

- All chains remain **`ChainTopology.linear`**.
- Added `FutureBranchPoint` type and `documented_future_branches` on chains.
- Flagship example on `travel_airport_journey` at **`check_in`**:
  - Future option A: `travel_business_trip`
  - Future option B: `travel_family_vacation`
- Full design: [`FUTURE_GRAPH_BRANCHING.md`](app/services/language_writing_knowledge_chain/FUTURE_GRAPH_BRANCHING.md)
- Validator rejects multiple `next_node_ids` on linear chains until branching is implemented.

---

## 2. Context Complexity Validation

New module: `complexity_rules.py`

| CEFR | Allowed complexity |
|------|-------------------|
| A1 | 1–2 |
| A2 | 1–3 |
| B1 | 2–4 |
| B2 | 3–5 |
| C1 | 4–5 |
| C2 | 4–5 |

One catalog fix: `services_bank/resolution` complexity raised to 3 for B2.

---

## 3. Grammar Metadata

Every node now has:

- `grammar_focus_primary`
- `grammar_focus_secondary`
- `grammar_focus_review` (auto-filled from prior node's primary on chain build)

---

## 4. Vocabulary Metadata

Every node now has:

- `vocabulary_primary`
- `vocabulary_secondary` (split from seeds or explicit)
- `vocabulary_review` (auto-filled from prior node lemmas)
- `vocabulary_categories`

Legacy `vocabulary_seeds` property returns primary + secondary.

---

## 5. Time Estimation

Every node includes `WritingTimeEstimate`:

- `writing_minutes` — first draft
- `revision_minutes` — coach + rewrite
- `total_minutes` — sum

Derived from CEFR base + complexity + arc (overridable per node).

---

## 6. Expected Output

New enum `ExpectedWritingOutput`:

paragraph · essay · email · report · story · dialogue · review · summary · article · message

Mapped from `genre` at build time; explicit override via `N(..., expected=...)`.

---

## Verification

```bash
cd backend
python scripts/verify_writing_topic_universe.py
```

**28/28 checks passed** (W1.1 refinement suite)

---

## W2

**Not started.** Awaiting explicit go-ahead for goal profiles + coach personalities.
