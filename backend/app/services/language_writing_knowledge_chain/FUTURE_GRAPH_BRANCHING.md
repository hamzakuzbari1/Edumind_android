# Future Graph Branching (Architectural Extension)

**Status:** Documented only — **not implemented** in catalog v1.1.
**Current topology:** All 40 knowledge chains are **linear**.

## Current model (v1.1)

Every chain uses `ChainTopology.linear`:

```
Node A → Node B → Node C → … → Terminal Node
```

- Each node has `previous_node_ids` and `next_node_ids` (0 or 1 successor today).
- `future_node_ids` hints at **cross-chain** unlocks (e.g. travel review → hotel chain).
- Progression rules (`progression_rules.py`) follow the single successor.

## Future extension: graph branching

After a shared anchor node, the chain may fork into **parallel narrative paths** that rejoin or terminate independently.

### Example (documented, not live)

```
Airport
   ↓
Check-in  ←── anchor node (branch point)
   ↓
   ├── Business Trip chain      (future: travel_business_trip)
   └── Family Vacation chain  (future: travel_family_vacation)
```

### Architectural hooks (in types, unused in v1.1 data)

| Field | Location | Purpose |
|-------|----------|---------|
| `topology` | `WritingKnowledgeChain` | `linear` today; future `branched` |
| `documented_future_branches` | `WritingKnowledgeChain` | Design-time branch documentation |
| `next_node_ids` (multiple) | `WritingKnowledgeChainNode` | Will hold parallel successors |
| `FutureBranchPoint` | types | Anchor + option chain IDs + labels |

### `FutureBranchPoint` contract

```python
FutureBranchPoint(
    anchor_node_id="check_in",
    branch_label="Trip purpose",
    option_a_chain_id="travel_business_trip",   # not in catalog yet
    option_b_chain_id="travel_family_vacation", # not in catalog yet
    description="Student path depends on trip type (future selection).",
)
```

The flagship `travel_airport_journey` chain includes **one documented branch point** at `check_in` as a reference for future implementation.

## Implementation constraints (when built)

1. **Do not break linear chains** — branching is opt-in per chain.
2. **Selection engine** chooses branch based on goal, prior writing, or student choice.
3. **Progression** tracks completed branch; sibling branch may remain optional enrichment.
4. **Validator** will require symmetric prev/next for all active edges; branch points must have ≥2 `next_node_ids`.

## What is explicitly out of scope now

- No branched edges in catalog data.
- No student branch selection UI.
- No multi-successor progression logic.

Run `verify_writing_topic_universe.py` — includes linear topology and complexity checks.
