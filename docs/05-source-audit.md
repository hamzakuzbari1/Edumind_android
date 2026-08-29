# EduMind / EduSpark — Platform Source Audit (English)

Read-only audit of the repository as it exists today. This is what a mobile engineer (e.g. building React Native + Expo in Rork) needs to understand the **real** system — not marketing claims.

---

## What the platform is

**EduSpark Syria (EduMind)** is an Arabic-first (RTL) smart learning platform for Syrian secondary-school students, teachers, and parents. It combines:

1. **Core school platform** — courses, lessons, AI tutor, quizzes, messaging, planner, gamification  
2. **English Language module** — placement exam, reading/listening/writing/speaking, certificates  
3. **Parent portal** — link child, monitor progress, insights, reports  
4. **Teacher portal** — upload lessons, AI processing, quizzes, student monitoring  

**Current web stack:** Vue 3 + Vuetify + Vite  
**Backend:** FastAPI + PostgreSQL + Alembic  
**API base:** `/api` (Swagger at `/docs`)

There is **no React Native app in this repo**. The web app is the reference client.

---

## 1. System architecture

### Frontend (web today)
| Layer | Tech |
|-------|------|
| UI | Vue 3, Vuetify 3, RTL |
| HTTP | axios, Bearer JWT |
| i18n | Arabic + English only (no French bundle despite README mention) |
| PDF preview | pdfjs-dist (teacher uploads) |

Mock mode exists (`VITE_USE_MOCK=true`) — mobile should assume real API mode.

### Backend
| Layer | Tech |
|-------|------|
| API | FastAPI, ~400 routes |
| DB | PostgreSQL 14+ (async SQLAlchemy) |
| Auth | JWT + bcrypt + session table |
| Files | Local `/uploads` static mount |
| Background | In-process asyncio (not Celery) |

### AI stack (when keys are configured)

| Capability | Primary provider |
|------------|------------------|
| Text / JSON (tutor, lessons, quizzes, language) | **Claude Sonnet 5** |
| PDF OCR | Mistral OCR |
| Lesson video transcription | Deepgram Nova |
| Student lesson voice chat (Arabic STT) | Deepgram → Gemini fallback |
| English module STT | OpenAI GPT-4o Transcribe |
| Teacher voice clone / lesson TTS | ElevenLabs |
| English module TTS | Supertonic (local) |
| Live English speaking (“Alex”) | **Hume EVI** (client WebSocket) |
| Lesson RAG | BGE-M3 embeddings + **FAISS** (not pgvector by default) |

All AI keys are optional for server boot — features degrade gracefully.

### Important: what is NOT in the codebase
- Stripe / PayPal  
- Firebase / FCM push  
- SSE / streaming chat (tutor replies are full JSON responses)  
- Backend WebSocket (only Hume from the client)  
- Student “projects” product (brochure/marketing only)

---

## 2. User roles

### Student
**Main navigation:** Journey (courses), Messages, Languages, Subscriptions, Routine, Planner, Achievements, Profile, Settings

| Feature | Status |
|---------|--------|
| Onboarding (grade → subjects → teachers) | ✅ Implemented |
| Course dashboard & lessons | ✅ Needs paid course access |
| AI tutor chat (text + voice) | ✅ Implemented |
| AI lesson quiz | ✅ Implemented |
| Manual course quizzes | ✅ Implemented |
| Subscriptions | ✅ Demo payment only |
| Smart planner | ✅ Implemented |
| Daily routine | ✅ Implemented |
| Achievements / XP | ✅ Implemented |
| English / Languages module | ✅ Large subsystem |
| Messages | ✅ Implemented |
| Assignments (dedicated product) | ⚠️ Partial — homework as lesson type only |
| Projects | ❌ Not implemented |

**Language module gate:** Subscribe → placement exam → skill routes unlock.

---

### Teacher
**Main navigation:** Dashboard, Classes, Messages, Quizzes, Analytics, Profile, Settings

| Feature | Status |
|---------|--------|
| Setup wizard (forced until complete) | ✅ Implemented |
| Course & lesson management | ✅ Implemented |
| PDF/video/homework upload | ✅ Implemented |
| AI lesson processing (OCR, RAG, quiz, persona) | ✅ Implemented |
| AI teaching style / persona | ✅ Implemented |
| Voice sample & clone | ✅ Implemented |
| Manual quiz builder | ✅ Implemented |
| Student monitoring & notes | ✅ Implemented |
| Analytics | ✅ Implemented |
| Public CV page | ⚠️ “Coming soon” placeholder |
| Legacy standalone upload page | ❌ Deprecated |

---

### Parent
**Main navigation:** Dashboard, performance, attendance, lessons, subjects/teachers, planner, notifications, insights, reports, messages, settings

| Feature | Status |
|---------|--------|
| Link child via code | ✅ Implemented |
| Monitor dashboard, lessons, attendance | ✅ Implemented |
| Planner / routine visibility | ✅ Implemented |
| “AI insights” | ✅ Implemented — **rule-based, not LLM** |
| Report export (CSV/XLSX/PDF) | ✅ Implemented |
| Messaging teachers | ✅ Implemented |
| Parent notes from teachers | ✅ Implemented |

Parent uses **their own account** + linked students (`?student_id=` on APIs). They do **not** log in as the student.

---

### Admin
**Minimal:** Settings page only in UI.  
Backend has `GET /api/admin/audit-logs` (requires admin role assignment in DB).  
**No admin console** for users, content, or audit logs in the frontend.

---

## 3. Authentication

| Topic | Reality |
|-------|---------|
| Register | `teacher \| student \| parent` only |
| Login | Returns JWT access + refresh token + session id |
| Token storage (web) | localStorage `eduspark_session` |
| Refresh endpoint | ❌ **Does not exist** — re-login on 401 |
| Email verification | ✅ API exists, ❌ **not required to login** |
| Password reset | ✅ Implemented (needs email config) |
| 2FA | ✅ Email OTP; TOTP returns 501 |
| Logout | ✅ Revokes session server-side |

**Important mismatch:** Backend `/auth/me` often hardcodes `onboarding_complete=true`, `needs_payment=false`. Payment/onboarding gates exist in the web router but are **bypassed** after refresh. Language subscription gating is **real and separate**.

---

## 4. Feature map — AI features

### Core platform AI

| Feature | Trigger | Backend | Functional? |
|---------|---------|---------|---------------|
| **Lesson processing** | Teacher processes uploaded PDF/video | OCR → chunks → FAISS → persona → quiz | ✅ |
| **AI tutor (RAG)** | Student asks in lesson chat | Retrieve chunks + Claude reply | ✅ No streaming |
| **Voice chat in lesson** | Student sends audio | Deepgram STT → same chat pipeline | ✅ |
| **Lesson quiz generation** | At process + regenerate | Claude/Ollama | ✅ |
| **Teacher voice clone** | Teacher uploads ≥60s sample | Whisper → persona → ElevenLabs | ✅ Needs TTS keys |
| **Smart planner generate** | Student opens planner | Rule-based optimizer | ✅ Not LLM |
| **Planner chat** | Free-text message | Regex + optional Claude augment | ✅ Reply is template text |
| **Routine AI chat** | Student chats about schedule | Claude | ✅ |
| **Parent insights** | Parent opens insights | Rule-based aggregation | ✅ Not LLM |

### English / Language module AI

| Feature | Status | Notes |
|---------|--------|-------|
| Placement exam (4 skills) | ✅ | Speaking/listening/writing + MCQ |
| Speaking conversation turns | ✅ | STT + Claude + TTS |
| Speaking journey + lesson runtime + discussion | ✅ | Complex state machines |
| Talk with Alex (Hume EVI) | ✅ | Backend mints token; **client connects to Hume WS** |
| Writing generate + evaluate | ✅ | Claude hybrid evaluator |
| Listening next lesson | ✅ | Claude + cached TTS |
| Reading v2 | ⚠️ | Default is **local mock**, AI opt-in via server flag |
| Vocabulary challenge | ✅ | Claude |
| Vocabulary “generate-ai” | ⚠️ | **Misnamed** — serves word bank, no LLM |
| Grammar module + lesson chat | ⚠️ | Off unless server flags enabled |
| English Journey UI | ⚠️ | Journey graph works; some UI calls **missing backend routes** |

### Config flags that exist but are mostly inactive
- `LANG_AI_TUTOR_ENABLED`, `LANG_AI_TEACHER_ENABLED`, `LANG_ADAPTIVE_INTELLIGENCE_ENABLED` — default **false**
- Web frontend still calls `/student/tutor/*`, `/student/teacher/*`, `/student/adaptive/insights` — **these routes do not exist on the backend**

---

## 5. Backend API map (mobile-relevant)

**Base:** `{HOST}/api`  
**Auth header:** `Authorization: Bearer {access_token}`  
**Locale:** `Accept-Language: ar|en`

### Auth — `/auth`
Register, login, logout, `/me`, password reset, email verify, 2FA, sessions, change password/email

### Student core
| Domain | Key paths |
|--------|-----------|
| Dashboard / courses | `/student/dashboard`, `/student/courses/{id}` |
| Lessons + tutor | `/student/lesson/{id}`, `/student/chat`, `/student/chat/voice` |
| Progress / quiz | `/student/lessons/{id}/progress`, `/student/quiz/*` |
| Subscriptions | `/student/subscriptions/*`, `/student/payments/demo-checkout` |
| Planner | `/student/planner/*` |
| Routine | `/student/routine/*` |
| Gamification | `/student/gamification` |
| Manual quizzes | `/student/manual-quizzes/*` |
| Onboarding | `/student/onboarding/*`, `/catalog/*` |

### Language module — `/student/languages/*`
Access, subscribe, hub, curriculum, reading-v2, listening, writing, speaking, vocabulary, dictionary, progress, certificates, journey, exam, grammar (if enabled), speaking live/journey/discussion/runtime

### Teacher — `/teacher/*`
Setup, dashboard, courses, lesson multipart uploads, process, voice sample, manual quizzes, students, notes

### Parent — `/parent/*`
Link student, dashboard, insights, lessons, attendance, planner, reports export, notifications, notes, messaging

### Shared
Messages (`/messages/*`), notifications, attendance, `GET /ai/jobs/{id}`, public certificate verify, `/health`

### Deprecated (410 Gone)
- `POST /student/lessons/{id}/complete` — completion is automatic via progress  
- Legacy placement mutations — use `/student/languages/exam`  
- `POST /teacher/upload/voice` — use `/teacher/voice-sample`

---

## 6. Important data models

```
User (student | teacher | parent)
├── StudentProfile — grade, onboarding, parent_link_code
├── TeacherProfile — bio, AI style, setup_completed_at, voice samples
└── ParentStudentLink — parent ↔ student

Subject → Course → Lesson
├── LessonAsset (video, pdf, homework, audio...)
├── ContentChunk (RAG text)
├── ChatMessage (tutor history)
└── QuizQuestion (AI lesson quiz)

StudentCourseAccess — paid access per course
Payment / PaymentItem — course or language product

CourseQuiz — teacher manual quizzes (separate from lesson quiz)

LanguageProduct → LanguageSubscription → LanguageStudentProfile
LanguageExamSession — placement state
LanguageContentItem — skill content
+ per-skill progress tables

PlannerProfile, RoutineProfile, StudentXp, Notifications, ConversationThread...
```

Lesson statuses: `draft → processing → processed | error`  
Students only see **processed** lessons for **paid** courses.

---

## 7. Verified user flows

### Teacher uploads lesson → student uses AI tutor
1. Teacher completes setup  
2. Creates lesson (PDF and/or video) via multipart upload  
3. Triggers `POST .../lessons/{id}/process`  
4. Backend: OCR/transcribe → chunk → FAISS index → persona + quiz + insights  
5. Student subscribes to course (demo checkout marks access paid)  
6. Student opens lesson, chats via `POST /student/chat` (RAG + Claude)  
7. Optional voice chat, quiz submit, progress updates  

### English module
1. `GET /student/languages/access`  
2. Subscribe (`POST /student/languages/subscribe`)  
3. Placement exam (`/student/languages/exam/*`)  
4. Skills unlock (reading, listening, writing, speaking, vocabulary, grammar if enabled)  
5. Live Alex: token from backend → WebSocket to Hume → heartbeat/turn/end back to API  

### Parent monitoring
1. Student shares link code  
2. Parent `POST /parent/link`  
3. All monitor APIs use `?student_id={id}`  

---

## 8. Mobile reuse map

| Feature | Backend | Ready / Partial / Missing |
|---------|---------|---------------------------|
| Auth (login/register/logout/2FA) | ✅ | **READY** (no refresh) |
| Student courses + lessons + text tutor | ✅ | **READY** |
| Lesson voice chat | ✅ | **PARTIAL** (native audio + multipart) |
| Manual quizzes, messages, planner, routine | ✅ | **READY** / **PARTIAL** (attachments) |
| Course/language subscribe | Demo only | **PARTIAL** |
| Language module (all skills) | ✅ | **PARTIAL** (audio, Hume WS, complex state) |
| Teacher upload + process | ✅ | **PARTIAL** (large files) |
| Parent portal | ✅ | **READY** |
| Push notifications | In-app only | **MISSING** |
| Token refresh | ❌ | **MISSING** |
| Student projects | ❌ | **MISSING** |
| Admin console | Minimal API | **MISSING UI** |

---

## 9. Frontend–backend contract risks (critical for mobile)

1. **No `/auth/refresh`** — handle 401 with re-login  
2. **Dead API calls in web frontend** — do not build mobile against `/student/tutor/*`, `/student/teacher/*`, `/student/adaptive/insights`  
3. **No streaming chat** — show loading spinner 5–30+ seconds  
4. **Hume live speaking** — React Native must do WebSocket + audio to Hume, not to your backend  
5. **Media URLs** — often relative `/uploads/...`; prefix with API host  
6. **Multipart everywhere** for voice/files  
7. **Demo payments only** — no real gateway  
8. **Parent “AI insights”** — heuristic cards, not generative AI  
9. **Projects feature** — does not exist; ignore brochure  
10. **Onboarding/payment flags** — backend may say “complete” even when product wants gates  

---

## 10. Final summary

### A. Reuse immediately
REST API at `/api`, auth, student/teacher/parent core flows, lesson tutor (text), quizzes, messages, planner, routine, gamification, language module structure, static media at `/uploads`.

### B. Needs backend work before mobile
Refresh token endpoint, real payments, push notifications (FCM/APNs), fix or implement dead tutor/teacher/adaptive routes, resumable uploads for large teacher files, optionally restore real onboarding/payment flags.

### C. Do NOT rebuild in Rork
Lesson AI pipeline (OCR, RAG, FAISS, quiz gen), language exam scoring, speaking evaluation engines, subscription ledger, grammar/speaking state machines, Hume token/budget logic, database schema.

### D. Design correctly
- **Four experiences in one app:** student, teacher, parent, (+ minimal admin)  
- **Arabic-first RTL**  
- **Three products:** Arabic courses + English module + parent monitoring  
- **English module:** subscribe → placement → skills; live speaking = Hume WS  
- **No projects feature**  
- **AI tutor is not streaming**  
- **Parent selects child**, does not impersonate  

### E. Recommended integration order
1. Auth shell  
2. Student dashboard + lessons + text chat + quiz  
3. Onboarding + demo subscribe  
4. Teacher classes + upload + process poll  
5. Parent link + dashboard  
6. Messages + notifications  
7. Planner + routine  
8. Language module (one skill at a time)  
9. Advanced speaking + Hume live  
10. Voice uploads everywhere  

---

The full detailed version with endpoint lists, env var names, and file references is in **`EDUMIND_MOBILE_SOURCE_AUDIT.md`** at the repo root (1024 lines). This message is the English executive report you asked for in the chat.