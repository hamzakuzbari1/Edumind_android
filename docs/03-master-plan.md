# EduSpark Mobile — Master Plan
Web (Vue/FastAPI) → native mobile (React Native + Expo via Rork), with the Projects module added and every existing feature preserved.

---

## 1. The decision that shapes everything else

**You are not rebuilding EduSpark. You are building a second client for it.**

The FastAPI backend — 376 endpoints, 122 tables, JWT auth, the whole AI provider stack — does not get rewritten. It gets hardened for scale and gains ~25 new endpoints for Projects and push notifications. The Vue SPA is replaced by a React Native app.

That framing keeps the migration to roughly 4 months of client work instead of 18 months of full rewrite, and it means the web app can keep running for the English module while mobile catches up.

---

## 1b. Platform strategy — Android first, direct distribution primary

**Tool: Rork Pro (React Native + Expo).** One codebase, both platforms. iOS is not a port — it's a second build target added later, roughly 90–95% shared code.

### Why Android first

1. **Distribution reality.** App Store access in Syria still required a VPN as of mid-2026. Play access is inconsistent but workable — Syria's communications ministry announced VPN-free Play access in January 2026, though community testing through July 2026 found it works on private ISPs (ADSL, MTN 4G) while remaining restricted on Tarasul, the government-linked ISP.
2. **Engineering order.** Android is harder to build *well* — your floor is a 2GB device on Android 10, with weaker RTL support, inconsistent Arabic keyboards, OEM audio quirks, and WebView fragmentation. Build to the harsh floor first and iOS is trivially fine afterward. The reverse order discovers all of it in month five.
3. **Commercial freedom.** See build flavors below.

### Two build flavors — this is the key architectural decision

| Flavor | Channel | Payment | Notes |
|---|---|---|---|
| **`direct`** | APK from your site, distributed via teachers, learning centers, WhatsApp, QR codes | Full local rails; may link directly to the web portal | **Google Play Billing rules only bind apps distributed through Play.** A sideloaded APK has no store tax and no linking restrictions. This is your primary Syrian channel. |
| **`play`** | Google Play Store | Google Play Billing only, no external payment links | For diaspora, Gulf, and anyone with clean Play access. |

Implement as EAS build profiles + `app.config.js` variants, with a `PAYMENT_MODE` flag gating the payment surfaces. Same codebase, two artifacts.

**The `direct` flavor needs an in-app updater.** Sideloaded apps don't auto-update, and a stale client against a moving API is a support nightmare. Ship a version check on launch that hard-blocks below a minimum supported version and offers a download link. Expo Updates handles JS-only changes over the air; native changes need the APK.

### Keeping iOS cheap later

Four rules, followed from day one, make the eventual iOS pass two weeks instead of two months:

- Isolate platform code in `*.ios.tsx` / `*.android.tsx` or `Platform.select` — never inline `if (Platform.OS === 'android')` scattered through components.
- **Never make the hardware back button the only way to go back.** Every screen has a visible back affordance.
- Use `react-native-safe-area-context` everywhere from the start.
- No Android-only libraries. Check iOS support before adding any dependency.
- Run an iOS simulator build via EAS roughly monthly, even though you're not shipping it. Catching drift early is nearly free; catching it late is not.

### Store account registration

Both Play Console and the Apple Developer Program are restricted for Syrian registration — Play Console fails at the payment step with Syria absent from country selection. **Register both through Masar's UAE entity.** Play Console enrollment is fast; start it week 1. Apple can wait until the iOS phase.

---

## 2. Repository separation

Four repos, cleanly split:

```
eduspark-api          ← extracted from Test-2SY backend/. FastAPI + Alembic + workers.
eduspark-mobile       ← new. Rork-generated Expo project, synced via Rork's GitHub integration.
eduspark-portal       ← NEW. Lovable-built payment & account portal. ~13 screens, NOT a clone
                        of the existing web app. This is where money is collected.
eduspark-web          ← what's left of Test-2SY (Vue SPA). Kept running for the English module
                        until mobile Phase 5 ships, then retired. No new features go here.
```

Plus one shared artifact:

```
eduspark-api-client   ← TypeScript client + types, GENERATED from the API's openapi.json.
                        Published to a private npm registry or consumed as a git submodule.
                        Consumed by BOTH eduspark-mobile and eduspark-portal.
                        Neither one ever hand-writes an API call.
```

### On the portal — scope discipline

**Do not rebuild the full web app on Lovable.** You already have it: 98 routes, all features, working. Rebuilding it is a *third* full implementation of the same product, and it will consume the months the mobile app needs.

What the web actually has to do is collect money and manage accounts. That is thirteen screens:

| # | Screen |
|---|---|
| W-01 | Landing / value proposition — also your SEO and ad-landing surface |
| W-02 | Pricing & plans |
| W-03 | Register / Login — same session model as the app |
| W-04 | Course catalog & selection |
| W-05 | Checkout — method select (Syriatel Cash, MTN Cash, Sham Cash, voucher, cash-via-teacher, USDT) |
| W-06 | Payment instructions per method, with copyable reference number |
| W-07 | Payment pending / verification status |
| W-08 | Payment success → "now open the app", with APK download link and QR |
| W-09 | Subscription management (active, expiring, renew) |
| W-10 | Redeem voucher |
| W-11 | Parent: link a student |
| W-12 | Account settings |
| W-13 | **Internal payment verification console** — for whoever confirms manual transfers |

W-13 is not optional. Manual payment rails without an ops console means confirming transfers from WhatsApp screenshots, and that breaks at about fifty students.

**One trap:** Lovable defaults to provisioning its own Supabase backend. Do not let it. The portal must call `eduspark-api` through the **same generated TypeScript client** the mobile app uses. Two sources of truth for users and subscriptions is a wound that never heals — put this constraint in Lovable's project knowledge in capital letters.

**One advantage:** the portal shares `01-EduSpark-Design-System.md` with the app. Same palette, same type stack, same Progress Spine motif, same Arabic-first RTL rules. A student who pays on the web and opens the app should feel no seam.

### Extraction steps (do this before touching Rork)

1. `git subtree split -P backend -b api-only` from `Test-2SY`, push to `eduspark-api`.
2. Move root-level backend concerns into it: `Dockerfile`, `docker-compose.yml`, `deploy/`, `.env.example`, `make_pdf.py`, `make_report.py`.
3. **Delete the debris.** All eight `.tmp-*.mjs` files, `.tmp-login-debug.png` (432KB of screenshot in git), and `ai_pipeline_ipynb_txt.ipynb` (178KB notebook). Move the 30+ status reports out of `backend/` into `docs/history/`.
4. **Delete dead code generations** while you have the chance: `language_reading_service.py` (superseded by v2), `language_speaking_legacy_adapter/`, `language_grammar_legacy_bridge/`, grammar `v2`/`v3` frontend components. This alone will cut the service directory meaningfully and make the codebase legible to a new hire or a technical due-diligence reviewer.
5. Reconcile the docs: `SYSTEM_ARCHITECTURE.md` currently claims 47 tables and Alembic head `0007`. Reality is 122 tables and head `0015`. Regenerate the ERD.
6. Add CI — there is currently **no `.github/` directory at all**. Minimum: lint, pytest, Alembic-upgrade-on-empty-DB check, Docker build.

---

## 3. Scalability architecture — your stated top priority

"Thousands of users daily, simultaneous" translates to roughly **3–5k concurrent at peak** (afternoons and evenings, and a brutal spike in the two weeks before البكالوريا). The current single-process setup will not survive that. Here is what changes, in dependency order.

### 3.1 The three things that will break first

| Breaks | Why | Fix |
|---|---|---|
| **The API process** | OCR, Whisper, FAISS embedding, and TTS all run inside the FastAPI event loop. One teacher uploading a 40-minute video stalls every request on that worker. | Extract a worker tier (§3.3). This is the single highest-priority change. |
| **Postgres connections** | asyncpg opens a pool per process. 20 API pods × 20 connections = 400 connections against a default `max_connections` of 100. | PgBouncer in transaction mode in front of Postgres. Non-negotiable before horizontal scaling. |
| **LLM spend and rate limits** | Sonnet 5 on every tutor message, quiz generation, and insight, with no global budget. At 3k concurrent students this is both a cost and a 429 problem. | Model routing + semantic cache + per-tier quotas (§3.6). |

### 3.2 Target topology

```
                     Cloudflare (CDN, WAF, rate limit)
                                │
                        Load balancer
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   API pods (N)            API pods (N)            API pods (N)     ← stateless, autoscaled on RPS
        └───────────────────────┼───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              PgBouncer                   Redis
                    │            (cache · rate limit · locks · queue broker · pub-sub)
        ┌───────────┴───────────┐           │
   Postgres primary      Read replicas      │
   (writes)              (analytics,        │
                          parent reports)   │
                                            │
                            ┌───────────────┴───────────────┐
                     Worker pool: ai-heavy          Worker pool: ai-light
                     (OCR, Whisper, embeddings,     (quiz gen, insights,
                      TTS, video) — GPU-optional     tutor async, notifications)
                                    │
                        S3 / Cloudflare R2 + CDN  ← all media, all TTS audio, all lesson PDFs
```

### 3.3 Worker tier — do this first

You already have the table. `ai_job_service.py` literally says *"workers process ai_jobs rows (no heavy work in HTTP handlers)"* — and there are no workers. Build them.

- **ARQ** (asyncio-native, Redis-backed) is the right fit given the codebase is fully async. Celery would force sync/async bridging everywhere.
- Two queues with separate autoscaling: `ai-heavy` (OCR, Whisper, video transcription, embedding, TTS — long, memory-hungry, few) and `ai-light` (quiz generation, insights, tutor completions, notifications — short, many).
- Every job: idempotency key, max retries with exponential backoff, dead-letter queue, visible status in `ai_jobs` so TC-06 (Lesson Processing Status) can show real state.
- API handlers enqueue and return `202` + a job id. The mobile app polls or receives a push when done.

### 3.4 Database

- **PgBouncer, transaction pooling.** Set `statement_cache_size=0` on asyncpg or prepared statements will break under it.
- **Read replicas** for the parent reporting surface, teacher analytics, and all rollup reads. Route with an explicit session factory, not magic.
- **Partition the firehose tables** by month: `student_activity_events`, `student_engagement_events`, `conversation_messages`, `language_activity_log`, `language_ai_usage`. These grow fastest and are almost always queried by recent time window.
- **Index audit.** You already have `audit_parent_sql_counts.py` and `audit_parent_backend_perf.py` in scripts — good instinct. Run them under load and fix N+1s before launch, not after.
- **Keep the rollup pattern.** `course_analytics`, `teacher_analytics`, `student_analytics`, `student_grade_reports` are already pre-aggregated. Move their refresh into the worker tier on a schedule instead of inline hooks.
- **Cursor pagination everywhere.** Several list endpoints currently return unbounded sets. Under 3k concurrent that's a memory event.

### 3.5 Caching (Redis)

| Layer | TTL | What |
|---|---|---|
| Catalog cache | 1h | Subjects, courses, teacher profiles, curriculum trees — read constantly, change rarely |
| Session cache | token TTL | Avoid a DB hit per request for session validation |
| Response cache | 5–15m | Dashboard aggregates, achievement definitions, language curriculum |
| Rate limits | rolling | Per-user, per-endpoint, per-tier |
| Distributed locks | short | Prevents duplicate expensive AI jobs for the same lesson |
| Semantic cache | 7d | Embedding-keyed cache of tutor answers — students in the same class ask the same question |

You already have `language_cache.py` and `language_lesson_audio_cache` — generalize that pattern app-wide.

### 3.6 AI cost and concurrency control

At 3k concurrent students, unrestrained Sonnet 5 is the budget. Four controls:

1. **Model routing.** Haiku for classification, intent detection, short feedback, hint tiering, and message titling. Sonnet for lesson generation, curriculum authoring, and substantive tutoring. This alone is typically a 60–70% reduction.
2. **Semantic cache** on tutor Q&A keyed by lesson id + question embedding. Within one class, hit rates are high.
3. **Content banks over generation.** You already do this in the language module (`language_placement_question_bank`, listening bank, reading bank, `grammar_canonical_lessons`). Extend it: generate once at authoring time, serve from the bank at runtime. Never generate what you can pre-generate.
4. **Per-tier quotas with graceful degradation.** `language_rate_limit_service` and the AI usage tables exist — make them global. When a student hits their tutor quota, degrade to cached/bank content with a clear message, never a hard error.

### 3.7 Media

Everything currently writes to local disk under `UPLOAD_DIR`, mounted as static from the API. This does not survive multiple pods.

- Switch `media_storage_service` to its already-implemented **S3/R2** backend. R2 is the better pick — no egress fees, which matters when you're serving lesson videos and TTS audio to thousands of students.
- Serve through the CDN with signed URLs. The API should never proxy media bytes.
- Cache TTS aggressively — the same lesson narration is served to every student in the class.

### 3.8 Real-time & push

- Replace polling notification checks with **Expo Push → FCM/APNs**. Add a `device_tokens` table (user, token, platform, locale, last_seen).
- The live speaking conversation (Hume EVI / OpenAI Realtime) is the only true WebSocket surface. Isolate it on its own service with its own scaling policy and a hard concurrent-session budget — you already have `speaking_live_leases` and `speaking_live_daily_usage`, which is exactly the right idea.

### 3.9 The scalability feature nobody counts: offline-first

**A student working offline generates zero server load.** Designing the mobile app offline-first is simultaneously the right UX for Syrian connectivity and the cheapest capacity you will ever buy.

- `expo-sqlite` local store, seeded on login, synced on connect.
- Cache: lessons, PDFs, course structure, vocabulary bank, project instructions, quiz questions.
- Queue outbound: quiz submissions, progress events, project submissions, reflection recordings.
- Sync protocol: last-write-wins on server timestamps for progress; append-only for events; explicit conflict UI only for project submissions.
- **Design this before you build screens.** Retrofitting offline into a finished app is a rewrite.

### 3.10 Observability & deployment

- OpenTelemetry traces, Sentry for both API and mobile, structured JSON logs with request/user/job correlation ids.
- Dashboards on: p95 latency per endpoint, worker queue depth, LLM spend per hour per feature, DB connection saturation, cache hit rate, push delivery rate.
- Rolling deploys; every migration backward-compatible (expand → migrate → contract), because mobile clients update on the user's schedule and you will always be serving N-2 versions.
- **Regional placement:** host in Frankfurt or Istanbul. Latency from Syria to either is materially better than to US-East, and the difference is felt on every tutor message.
- Load-test to 5k concurrent with k6 before the pilot. Test the spike shape, not the average.

---

## 4. Localization architecture

Arabic and English at launch, third language with zero code changes.

- **`i18next` + `react-i18next` + `expo-localization`.** Namespaced bundles mirroring the existing web locale files (`auth`, `common`, `dashboard`, `student`, `teacher`, `parent`, `messages`, `errors`, `validation`, `routes`, `settings`) plus new `projects` and `language`.
- **Direction:** `I18nManager.forceRTL()` requires a reload. Resolve locale at splash (A-01) before the tree mounts; on in-app switch, persist then `Expo.reloadAsync()` behind the A-13 transition screen.
- **ICU plurals, always.** Arabic has six plural categories. Any `count === 1 ? a : b` in the codebase is a defect.
- **No string concatenation, ever.** Full sentences with placeholders only.
- **Server-side localization:** the API must honor `Accept-Language`. AI-generated content (tutor replies, insights, feedback, project reviews) is generated *in* the requested locale and cached per-locale. The `app/core/` AI locale module already establishes Arabic-first prompting — extend it to a locale parameter rather than a constant.
- **Content vs. interface.** Interface strings are translated. Curriculum content is authored per-locale and stored per-locale — never machine-translated at runtime.
- **Adding a language later** = drop in a locale bundle, add a direction flag, add the AI locale prompt, add the font subset if the script needs one. No component touches that.

---

## 5. New backend work required

Everything else stays. This is the delta.

**Projects module (~22 endpoints, 6 tables):**
`projects`, `project_milestones`, `project_tasks`, `project_submissions`, `project_reviews`, `project_teams`. Endpoints for catalog, enroll, milestone progress, submit, AI review, peer review, teacher review queue, portfolio, certificate issue.

**Architectural recommendation before you write it:** you already have a mastery engine — `language_knowledge_components`, `language_component_mastery`, `language_skill_level_state`, `grammar_evidence_ledger`, promotion gates, and `language_learner_model_service`. That machinery (evidence → mastery → gated progression) is exactly what Projects needs, and exactly what the coding module will need in v2. **Generalize `language_*` into a domain-agnostic `skill_*` core first**, then English, Projects, and Coding all become tracks over one engine. If you skip this you will build the same progression logic three times, and the learner-model work will have three homes instead of one.

**Mobile support (~8 endpoints):**
Device token register/unregister, push send, a `/sync/bootstrap` snapshot endpoint for offline seeding, a `/sync/push` batch endpoint for queued events, and cursor pagination added to every list endpoint.

**Payments (~14 endpoints) — two rails, one entitlement model:**

The backend must treat *entitlement* and *payment source* as separate concepts. One `entitlements` table answers "does this student have access to this course right now", and several payment providers write into it.

| Rail | Surface | Notes |
|---|---|---|
| **Local rails** | `eduspark-portal` (web) — and linkable from the **`direct`** APK | Syriatel Cash, MTN Cash, Sham Cash, cash-via-teacher, USDT. Manual verification with an ops console (W-13). This is the primary revenue path. |
| **Voucher codes** | Portal + both app flavors | Prepaid cards sold through teachers and learning centers. The most operationally robust rail in a cash economy — no gateway, no reconciliation, works offline. |
| **Google Play Billing** | **`play`** flavor only | Required by policy for anything sold inside a Play-distributed app. 15–30% to Google. Diaspora and Gulf only. |
| **Apple IAP (StoreKit 2)** | iOS, later phase | Deferred until the iOS build. Same entitlement model. |

The app reads **entitlements** and does not care how they were granted. A student who paid by Syriatel Cash on the portal logs into the app and simply has access.

**The flavor flag matters legally, not just cosmetically.** In the `direct` APK you may link straight to the portal checkout — no store rules apply to software you distribute yourself. In the `play` build those links must be absent and purchase must go through Play Billing. One `PAYMENT_MODE` constant, checked at every payment surface, keeps you compliant in one build and unrestricted in the other.

**Prioritize vouchers.** They are unglamorous and they will carry more revenue than anything else: a teacher sells a scratch card for cash, the student types twelve characters, access unlocks. No gateway, no bank, no reconciliation, no connectivity required at the moment of sale. Build this rail first.

This is a longer path than it looks and it gates all revenue. Assign it in week 1.

---

## 6. Rork workflow

**What Rork actually is:** Rork Pro generates React Native + Expo projects and, on paid plans, exports them to GitHub with two-way sync. What you download is an ordinary Expo project — `app/`, `package.json`, `npx expo start`. So Rork writes your first implementation; you own and maintain the repo.

**Therefore:**

1. **Paid plan and GitHub sync on day one.** Never work without an exported repo.
2. **Feed it the generated API client, not descriptions.** Export `openapi.json` from FastAPI, run `openapi-typescript-codegen`, and put the generated types in the repo before generating screens. Otherwise Rork invents endpoint shapes and you spend weeks debugging fiction.
3. **Rork builds the shell and the screens. Claude Code owns the hard parts** — offline sync, RTL edge cases, audio recording, the live conversation WebSocket, push. Don't ask Rork for those.
4. **One vertical slice first.** Login → Home → Course → Lesson → Tutor chat, working against the real API. Prove the contract end to end before generating 50 screens on assumptions.
5. **Expect to leave Rork around 60% completion.** That is the tool working correctly, not failing.

### Project knowledge to load into Rork

Create a single context file Rork sees on every prompt, containing:
- The design system file (`01-EduSpark-Design-System.md`) in full.
- The RTL rules as hard constraints.
- The tech stack: Expo SDK + expo-router, React Native Paper, i18next, TanStack Query, expo-secure-store, expo-sqlite, Zustand for local UI state.
- "All API calls use the generated client in `src/api/generated`. Never write `fetch` directly. Never invent an endpoint."
- "All strings come from i18next. No literal user-facing text in components."

---

## 7. Prompting workflow — Claude Design → Rork

**Per screen, three steps:**

**Step 1 — Claude Design.** Paste the design system file, then the screen brief from the inventory, then:

> Design screen `ST-02 · Course Detail` for EduSpark Mobile.
> Constraints: 390×844 mobile viewport, **Arabic RTL as the primary artboard**, dark mode as a second artboard. Use only the tokens in the design system above. Include the Progress Spine on the leading edge. Show these states: loaded, loading skeleton, empty (no lessons yet), offline.
> Do not invent new colors, radii, or fonts.

**Step 2 — Export the design** as an image plus the token/spacing notes.

**Step 3 — Rork prompt.** Attach the image and write:

> Build screen `ST-02 CourseDetail` at `app/(student)/course/[id].tsx` matching the attached design exactly.
> Data: `getCourse(courseId)` and `getCourseLessons(courseId)` from `src/api/generated`. Types are in `src/api/generated/types`.
> Behaviour: tapping a lesson row navigates to `/lesson/[id]`. Locked lessons open the paywall sheet instead. Pull-to-refresh refetches. Sticky bottom bar continues to the first incomplete lesson.
> States: skeleton while loading, `EmptyState` when the lesson list is empty, `OfflineBanner` plus cached data when offline.
> All strings from `t('student:course.*')` — add the keys to both `ar` and `en` bundles.
> RTL: use `start`/`end` only. The spine sits on the leading edge.
> Reuse existing components from `src/components/` — do not create new ones if an equivalent exists.

**The rule that makes this work:** every prompt names the file path, the exact API functions, the states, the translation namespace, and the components to reuse. Vague prompts produce generic output — that is the single most reported failure mode with AI app builders.

---

## 8. Timeline

| Weeks | Track A — Backend | Track B — Android app (Rork) | Track C — Portal (Lovable) |
|---|---|---|---|
| 1–2 | Repo split, cleanup, CI, PgBouncer, Redis | Design system, Rork setup, API client codegen, nav shell, i18n + RTL foundation | Play Console enrollment (UAE entity), portal scaffold, W-01/W-02/W-03 |
| 3–5 | Worker tier (ARQ), R2 media, cursor pagination | Phase 0 auth (14 screens) + vertical slice: login → home → course → lesson → tutor | Entitlements-aware checkout, W-04 to W-08 |
| 6–9 | Entitlements model, voucher rail, Projects + `skill_*` generalization, push infra, sync endpoints | Phase 1 student core (26 screens), offline layer, build flavors | W-09 to W-12, **W-13 ops console** |
| 10–12 | Local rails integration, read replicas, partitioning | Phase 2 Projects (12) + Phase 6 cross-cutting (6) | Portal live, first real payments taken |
| 13–14 | Load test to 5k concurrent, observability | Hardening, low-end device sweep, in-app updater, RTL + Dynamic Type pass | Voucher printing & teacher distribution kit |
| **15** | **Android v1 launch — 58 screens, `direct` APK + `play` build** | | |
| 16–20 | — | Phase 3 Teacher (18) | — |
| 21–25 | — | Phase 4 Parent (14) | — |
| 26–28 | — | **iOS parity pass** — Apple enrollment, StoreKit, platform fixes, App Review. Two weeks of work if the four iOS rules were followed; two months if not. | — |
| 29–37 | — | Phase 5 Language (26) | — |
| 38+ | Code execution infra | Phase 7 Coding | — |

**Note on the iOS slot:** it sits at week 26 deliberately, not week 15. Adding iOS is cheap *once the Android app is stable* and expensive while it's still moving. Resist pulling it earlier unless a Gulf or diaspora opportunity justifies it.

---

## 9. Where to start — this week

**Day 1 — two things in parallel.**
(a) Start Google Play Console enrollment under the UAE entity. Syria isn't selectable and payment fails from there, so this must run through Masar's UAE registration.
(b) Split the repo: `git subtree split` the backend, delete the debris, push `eduspark-api`.

**Day 2:** Stand up the API somewhere real (Frankfurt or Istanbul), behind PgBouncer, with Redis attached. Export `openapi.json`.

**Day 3:** Generate the TypeScript client. Commit it to `eduspark-api-client`. This one artifact is what makes every later Rork *and* Lovable prompt reliable — both consume it, neither writes API calls by hand.

**Day 4:** Take `01-EduSpark-Design-System.md` into Claude Design and produce three screens: **A-04 Login**, **ST-01 Student Home**, **ST-02 Course Detail** — each in Arabic RTL, light and dark. These three establish the entire visual language for all three surfaces. Iterate until you love them, because everything else inherits from them.

**Day 5:** Open Rork, load the project knowledge file, and build exactly one screen: **A-04 Login**, wired to the real `/auth/login`. Install the APK on a **cheap physical Android device** — not an emulator, not your own flagship — and log in against your live API.

**Buy the test device before day 5.** Something around $100–150, 2–3GB RAM, Android 11 or 12. This is the device your product actually runs on, and every performance decision for the next six months should be validated against it. A flagship will lie to you for months.

The moment a real login succeeds from a real cheap device against your real backend, the migration is de-risked and everything after it is repetition.

---

## 10. The three risks I'd watch

1. **Scope.** You have 116 screens and one team. The temptation will be to port the English module early because it's the most impressive. Resist it — it's 26 screens and the hardest audio work in the app. Ship student core + projects first; that's the product a parent pays for.
2. **The progression engine.** If Projects ships with its own bespoke mastery logic, you will have three incompatible progression systems by the time coding arrives. Generalize `language_*` → `skill_*` in weeks 6–9 or accept the debt permanently.
3. **Payments.** It's the least interesting item on this plan and the only one that stops revenue. It has no technical dependency on anything else, which means it will keep getting deferred. Assign it to someone in week 1.
