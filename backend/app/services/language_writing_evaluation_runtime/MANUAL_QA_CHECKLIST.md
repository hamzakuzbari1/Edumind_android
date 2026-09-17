# Writing W7 Manual QA Checklist (Browser)

Use with W6-generated lessons and the W7 draft evaluation endpoint.

## Prerequisites

- [ ] Backend running; student logged in
- [ ] Generate lessons for **Travel**, **IELTS**, and **Business** via `POST /api/student/languages/writing/generate`
- [ ] Note each `content_item_id`

## API flow per goal

1. **Generate** — `POST /writing/generate` with `{"goal": "travel"|"ielts"|"business"}`
2. **Write** — compose draft in UI (or prepare text offline)
3. **Evaluate** — `POST /writing/{content_item_id}/draft` with `{"draft_text": "..."}`
4. **Revise** — edit draft; submit again to same endpoint
5. **Complete** — submit strong draft or set `"complete_if_ready": true` when coach marks ready

## Per-goal verification

| Check | Travel | IELTS | Business |
|-------|--------|-------|----------|
| Draft evaluates without error | | | |
| `revision_plan.encouragement` present | | | |
| `revision_plan.main_issue` present | | | |
| `revision_plan.ready_to_complete` boolean | | | |
| Second draft shows `comparison` object | | | |
| `comparison.improved` / `unchanged` / `regressed` populated | | | |
| Completion only when blueprint criteria met | | | |

## Separation checks (mandatory)

- [ ] **Evaluator never writes coaching** — `writing_evaluation_facts` has no `encouragement`, `main_issue`, or `revision_mission`
- [ ] **Coach never computes scores** — `writing_coach_plan` has no dimension scores or `overall_readiness` numbers
- [ ] **Completion depends on blueprint** — `writing_completion.reason` references criteria/word limits, not revision count

## Persistence checks

- [ ] `body_json.writing_blueprint.blueprint_hash` unchanged after evaluation
- [ ] `body_json.writing_generation.generation_hash` unchanged
- [ ] `body_json.writing_revision_session.drafts` grows each submit
- [ ] `body_json.writing_revision_session.evaluation_facts_history` retains turns

## Out of scope (W7)

- [ ] Do **not** test portfolio, progression, promotion, or analytics

## Sign-off

| Goal | Write → Evaluate → Revise → Complete | Reviewer |
|------|----------------------------------------|----------|
| Travel | | |
| IELTS | | |
| Business | | |
