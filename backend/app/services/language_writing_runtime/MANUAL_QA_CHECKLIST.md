# Writing W6 Manual QA Checklist

Use after deploying the writing runtime with Claude configured (`ANTHROPIC_API_KEY` set).

## Prerequisites

- [ ] Backend running with `WRITING_MODEL_PROVIDER=claude` (or `mock` for offline structural QA)
- [ ] Student account with language learning access
- [ ] Official writing CEFR available in `language_progression` (or pass `official_cefr` in request)

## Generate three goal profiles

Run for each goal (API or script):

```bash
cd backend
python scripts/manual_qa_writing_w6.py --goal travel
python scripts/manual_qa_writing_w6.py --goal ielts
python scripts/manual_qa_writing_w6.py --goal business
```

Or POST `/api/student/languages/writing/generate` with body `{"goal": "travel"}` (etc.).

| Goal | Default chain | Default node |
|------|---------------|--------------|
| Travel | `travel_airport_journey` | `complaint_email` |
| IELTS | `education_university_path` | `course_interest` |
| Business | `business_email_flow` | `meeting_request` |

## Per-lesson confirmation

For each generated lesson, verify **no educational drift from blueprint**:

- [ ] **Mission matches Blueprint** — `writing_context` / prompt reflects `narrative_why` and node task
- [ ] **Grammar matches Blueprint** — primary grammar target appears in lesson metadata
- [ ] **Vocabulary matches Blueprint** — primary lemmas referenced in lesson metadata
- [ ] **Expected Output matches Blueprint** — `expected_output` equals blueprint `expected_writing_output`
- [ ] **Success Criteria matches Blueprint** — checklist aligns with `success_criteria_labels`
- [ ] **Blueprint hash preserved** — `body_json.writing_blueprint.blueprint_hash` unchanged from planner
- [ ] **Generation audit present** — `body_json.writing_generation` includes version, model, provider, duration, validation, repair, generation_hash

## Error handling smoke tests

- [ ] Invalid JSON from provider → structured error, no raw Anthropic traceback in API response
- [ ] Missing API key with `claude` provider → `provider_unavailable` structured error
- [ ] Generation gate after repeated failures → `generation_gate_closed` with retryable flag

## Out of scope (W6)

- [ ] Do **not** test evaluator / grading / revision / portfolio / progression / promotion

## Sign-off

| Goal | Generated | Blueprint aligned | Auditor |
|------|-----------|-------------------|---------|
| Travel | | | |
| IELTS | | | |
| Business | | | |
