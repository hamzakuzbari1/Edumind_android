# EduSpark Mobile — Screen Inventory
**117 app screens across 5 roles, plus 13 web portal screens.** Each entry is a self-contained brief. Design them in the phase order given — do not design ahead of the phase you're building.

**Platform:** Android first (React Native + Expo via Rork), two build flavors — `direct` (APK) and `play` (Google Play). iOS is added later from the same codebase; design nothing that would block it. The web portal screens (W-01 to W-13) are specified in the Master Plan §2 and built in Lovable against the same design system.

Legend: **P0** = ship in v1 · **P1** = v1.1 · **P2** = v1.2

---

## Navigation shells

Each role gets its own bottom tab bar. Five tabs maximum — anything else lives one level deeper.

| Role | Tabs |
|---|---|
| **Student** | الرئيسية Home · موادي Courses · مشاريعي Projects · الإنجليزية English · حسابي Me |
| **Teacher** | لوحتي Dashboard · موادي Courses · طلابي Students · مشاريع Projects · حسابي Me |
| **Parent** | الرئيسية Home · التقدم Progress · التقارير Reports · الرسائل Messages · حسابي Me |

Messages and Notifications are reachable from the TopBar on every root screen (badge counts), not from a tab.

---

# PHASE 0 — Foundation & Auth (14 screens) · P0

### A-01 · Splash & Language Gate
First launch only. Logo + the two language choices as large equal cards (العربية / English), no default pre-selected. Selecting sets locale + direction and warms the app. Subsequent launches: logo + silent token refresh, ~600ms max.
**States:** first-run · returning · token-refresh-failed → A-04.

### A-02 · Value Carousel
3 slides, swipeable, skippable. Slide 1: an AI tutor that knows your curriculum. Slide 2: a study plan built around your exams. Slide 3: real projects you build with your hands. Type-led, one illustration-free hero per slide using the Progress Spine motif.

### A-03 · Role Select
Three large cards: طالب / معلّم / وليّ أمر. Each with one line explaining what that account does. This is a fork, not a form — no other elements.

### A-04 · Login
Email + password, "remember me", forgot-password link, link to register. Inline validation, single error region. Must handle: wrong credentials, unverified email → A-08, 2FA required → A-09, account locked, offline.

### A-05 · Register — Student
Name, email, password + strength meter, password confirm, terms. Goes to A-08 then student onboarding.

### A-06 · Register — Parent
Same fields + a note that they'll link their child next. Goes to A-08 then PR-01.

### A-07 · Register — Teacher
Same fields + subject and grade intent. Goes to A-08 then TC-01.

### A-08 · Verify Email
"We sent a code to {email}" + 6-cell OTP + resend with visible cooldown timer + change-email escape hatch.
**States:** idle · verifying · wrong code (attempts remaining) · expired · cooldown · success.

### A-09 · Two-Factor Verify
6-cell OTP, resend with cooldown and a resend cap, "trust this device". Distinct visual identity from A-08 so users don't confuse the two.

### A-10 · Forgot Password
Email input → confirmation state with a clear "check spam" hint.

### A-11 · Reset Password
New password + confirm + strength meter. Reached by deep link. Handle expired-link state gracefully with a re-request action.

### A-12 · Certificate Verification (public)
Deep-linked, no auth. Shows: holder name, certificate title, CEFR level or project name, issue date, issuing teacher, verified/invalid badge. Designed to be screenshotted and shared — this is a marketing surface.

### A-13 · Locale Switch Transition
The 1-second branded reload when direction flips. Logo + spine sweeping from one edge to the other. Small screen, high polish — it's the moment the bilingual promise is proven.

### A-14 · Global States Kit
Not a screen — a sheet of every shared state: offline banner, no-results empty, error with retry, skeleton loaders for list/card/detail, permission-denied, session-expired, update-required, maintenance. Design these once, together, so they're consistent.

---

# PHASE 1 — Student Core (26 screens) · P0

### SO-01 · Onboarding: Grade
Large grade cards (الصف العاشر / الحادي عشر / البكالوريا + branch). Progress spine at 1/4.

### SO-02 · Onboarding: Subjects
Multi-select subject chips with icons, grouped by track. Minimum-one validation. Spine at 2/4.

### SO-03 · Onboarding: Teachers
Per chosen subject, a horizontal carousel of teacher cards (photo, name, experience, rating, price, a 20s intro-voice play button). Selecting one per subject. Spine at 3/4.

### SO-04 · Onboarding: Personalize
Learning-profile questions: study hours available, strongest/weakest subjects, exam dates, preferred study time. Conversational one-question-per-screen paging, not a wall of form. Spine at 4/4.

### SO-05 · Onboarding Complete
Celebration + a summary card of what was chosen + one primary action into the dashboard.

### ST-01 · Student Home
The most important screen in the app. Sections in order: (1) greeting + streak flame + XP level bar, (2) **Continue** card — the single next thing to do, large, unmissable, (3) today's plan strip from the planner, (4) subject grid with per-subject progress rings, (5) active project card, (6) English level card. Pull-to-refresh. Offline-tolerant with cached content.

### ST-02 · Course Detail
Course header (subject, teacher, progress %) + **Progress Spine** of lessons as beads. Each row: lesson title, duration, media-type icons, status. Locked lessons show why. Sticky "Continue" bar.

### ST-03 · Lesson Player
Single shell handling PDF, video, and teacher-voice audio. Content area + floating actions: ask-tutor, take-quiz, mark-complete, download-for-offline. PDF: page thumbnails, pinch-zoom, page memory. Video: scrubber, speed, captions. Audio: waveform + transcript follow.
**States:** loading · downloading · offline-available · processing (teacher still uploading).

### ST-04 · AI Tutor Chat
Full-height chat grounded in the current lesson. Jouri-marked AI bubbles. Suggested-question chips on empty. Message actions: copy, regenerate, "explain simpler", "give me an example". A context pill at the top showing which lesson is loaded, tappable to change. Markdown + KaTeX math rendering.

### ST-05 · AI Tutor Voice Mode
Press-and-hold to speak with a live waveform, release to send. Shows the transcript as it resolves, then the reply with a play button in the teacher's cloned voice. Big central control, minimal chrome — usable one-handed while reading a textbook.

### ST-06 · Quiz Runner
One question per screen. Progress spine horizontal at top. Types: multiple choice, true/false, gap fill, short answer. Immediate or deferred feedback per quiz config. Timer optional. Bail-out saves progress.

### ST-07 · Quiz Results
Score dial + per-question breakdown with explanations + XP earned + two actions: "Review wrong answers" and "Practice these again" (triggers the remedial quiz).

### ST-08 · Remedial Quiz
Visually distinct from ST-06 — framed as practice, not assessment. No score pressure, hints available.

### ST-09 · Manual Quiz Runner
Teacher-authored quiz. Same shell as ST-06 but with a teacher-attribution header (no Jouri marking — a human wrote this).

### ST-10 · Planner
Week view with day columns, session blocks colored by subject, completion checkboxes. Today highlighted. Tap a block for detail sheet. FAB: "Regenerate my week".

### ST-11 · Planner AI Chat
Conversational adjustment: "I have football Tuesday, move my chemistry". Shows the proposed change as a diff card the student accepts or rejects before it's applied.

### ST-12 · Routine Builder (conversational)
The multi-turn setup: wake time, school hours, commitments, energy patterns. Chat-shaped with quick-reply chips, not a form.

### ST-13 · Routine Week View
The confirmed weekly routine. Slot actions: complete, miss, undo. Weekly renewal prompt. Distinct from the Planner — routine is habit structure, planner is study content.

### ST-14 · Exam Schedule Capture
Camera-first: photograph the school exam schedule → OCR → an editable list of extracted exams with dates → confirm → feeds the planner. Show OCR confidence and make correction effortless.

### ST-15 · Achievements
XP level with the next-level bar, streak calendar heatmap, achievement grid (earned / locked with unlock criteria visible). Locked achievements are motivation, so show them.

### ST-16 · Subscriptions
Active course subscriptions with expiry dates and renew actions, plus available courses to add. Clear "expires in N days" warnings.

> **Payment on Android — read before designing ST-17 to ST-21.**
> The app ships in **two flavors** and the payment surfaces differ between them. Design both.
> **`direct`** (APK, primary Syrian channel): no store rules apply. Full local rails, and the app may link straight to the portal checkout.
> **`play`** (Google Play): Google Play Billing only. All external payment links must be absent from this build.
> One `PAYMENT_MODE` flag switches between them. Design each screen in both variants where they differ.

### ST-17 · Course Paywall Sheet
Bottom sheet: what's included, duration, teacher, price. Two variants —
**`direct`:** primary action opens the portal checkout in a browser tab, with a secondary "I have a voucher code" action.
**`play`:** primary action opens the native Google Play purchase sheet with Play-Billing-supplied localized pricing plus a restore-purchases action. No portal link, no mention of other methods.

### ST-18 · Payment Method Select (`direct` only)
Syriatel Cash, MTN Cash, Sham Cash, voucher code, cash via teacher or center, USDT. Each with a one-line "how this works" and an expected verification time. This may be an in-app screen or a portal handoff — decide once and keep it consistent.

### ST-19 · Payment Pending
Manual rails don't confirm instantly. Show what was submitted, the reference number, expected verification window, and a clear "we'll notify you" with push enabled. Give the student something to do while waiting — a free lesson, the placement test.

### ST-20 · Purchase Success
Works identically in both flavors, because entitlements are the same object regardless of rail. Immediate access, celebration, direct action into the first lesson.

### ST-21 · Voucher Redeem
Single code field + camera scan for printed cards. Permitted in both flavors. **This is the most important payment screen in the app** — a teacher sells a scratch card for cash, the student types twelve characters, access unlocks. No gateway, no bank, no connectivity at the point of sale. Make it fast, forgiving of case and spacing, and reachable from both the paywall and Settings.

### ST-22 · Update Required (`direct` only)
Sideloaded APKs don't auto-update. When the client falls below the minimum supported version, this screen hard-blocks with a download link and a QR code. Unglamorous and essential.

### ST-22 · Student Profile
Avatar, name, grade, school, level, linked parents (with revoke), quick stats. Edit in a sheet, not a separate screen.

### ST-23 · Settings — Account
Name, email (change flow), password change, avatar, delete account.

### ST-24 · Settings — Security
2FA enable/disable, active sessions list with device + last-seen + revoke each / revoke all.

### ST-25 · Settings — Language & Display
Language, numeral system, theme (light/dark/system), text size, Hijri dates toggle.

### ST-26 · Settings — Notifications
Granular toggles grouped by category, quiet hours.

---

# PHASE 2 — Projects (12 screens) · P0 — the new module

### PJ-01 · Projects Hub
Two sections: **My projects** (in-progress cards with milestone progress) and **Discover** (catalog filtered by subject, difficulty, duration, solo/team, physical/digital). Each catalog card shows the end deliverable as the hook — "you'll build a working water-level alarm", not "learn about circuits".

### PJ-02 · Project Detail
Hero: what you'll build. Then: skills gained, materials needed (with a checklist you can tick before starting), estimated time, difficulty, milestone preview via the Progress Spine, sample of what others built. Primary action: "Start project" or "Join a team".

### PJ-03 · Milestone Board
The Progress Spine as the whole screen. Each bead is a milestone with its tasks nested. Current milestone expanded, others collapsed. Shows what's blocking progress.

### PJ-04 · Task Detail
Instructions (rich text, images, video), a "what good looks like" example, hints available at cost, and the submit action. Long-form content, so paginated with a persistent bottom action bar.

### PJ-05 · Submission Composer
Multi-modal capture: camera photo, video record, file upload, link, or written reflection — whichever the task requires. Draft-saved locally, uploads when connected. Show upload progress and allow background upload.

### PJ-06 · AI Review & Rubric
The submission alongside rubric rows, each scored with a short reason. Jouri-marked. Strengths first, then one specific improvement, then "resubmit" or "continue". Never a bare grade.

### PJ-07 · Peer Review
Review another student's submission against the same rubric. Anonymized. Guardrails: minimum comment length, tone check before send.

### PJ-08 · Team Workspace
For team projects: members with roles, shared task assignment, team chat thread, shared deliverable. Reuses the messaging thread component.

### PJ-09 · Reflection Log
Voice-first: record a 60-second reflection after each milestone. Transcribed and kept in the portfolio. Low friction is the entire point — one big record button.

### PJ-10 · Project Portfolio
The student's showcase: completed projects as cards with hero image, date, skills, and a share action. Designed to be shown to a parent or a university — treat it as a public artifact.

### PJ-11 · Project Certificate
Issued on completion. Same verification system as language certificates. Shareable image export.

### PJ-12 · Materials & Safety Sheet
For physical projects: required materials with local-sourcing notes, cost estimate, and safety guidance where relevant. Must be readable offline.

---

# PHASE 3 — Teacher (18 screens) · P1

### TC-01 · Teacher Setup Wizard
Multi-step: identity → subjects & grades → qualifications → experience → documents → pricing → voice sample. Spine-tracked, resumable, each step saveable.

### TC-02 · Teacher Dashboard
Today's number that matters (active students, lessons awaiting processing, ungraded submissions, unread messages) then a work queue, not a chart wall. Charts live in TC-15.

### TC-03 · Courses List
Per grade/subject cards with student count, lesson count, publish status.

### TC-04 · Course Detail
Lesson list with status (draft / processing / published), reorder by drag, add-lesson FAB.

### TC-05 · Lesson Upload
Pick PDF or video, title, order, and options (generate quiz, generate voice narration, index for tutor). Upload with resumable progress — teachers are on the same bad connections.

### TC-06 · Lesson Processing Status
Live pipeline view: extract → chunk → index → quiz → narrate, each with state and any error. This screen prevents support tickets; make the failure states actionable.

### TC-07 · Lesson Editor
Edit extracted text, chunk boundaries, generated quiz questions, and the AI-generated insights before publishing. Teacher approval before students see AI output is a trust requirement.

### TC-08 · Lesson Preview
Exactly what the student will see. No editing chrome.

### TC-09 · Voice Profile
Record or upload voice samples, quality feedback per sample, regenerate, preview a narrated paragraph, enable/disable cloned narration. Handle consent explicitly.

### TC-10 · Quiz Builder
Add/edit questions, types, correct answers, explanations, ordering, point values. Bulk-import from an AI-generated set with per-question accept/reject.

### TC-11 · Quiz Results
Class-level distribution + per-student results + per-question difficulty analysis showing which question the class failed.

### TC-12 · Students List
Searchable, filterable by course/grade/status. Row shows name, course, progress, last-active, flags.

### TC-13 · Student Profile (teacher view)
Progress, quiz history, attendance, activity timeline, private teacher notes, note-to-parent action, message action.

### TC-14 · Grades
Gradebook per course. Enter/adjust grades, publish to students and parents.

### TC-15 · Teacher Analytics
Engagement over time, completion funnels, at-risk student list. Charts here, and only here.

### TC-16 · Teacher Profile / CV Editor
Public-facing profile: bio, qualifications, experience, documents, "why study with me" points, intro voice clip. This is what students see in SO-03 — show a live preview.

### TC-17 · Project Authoring
Create a project: title, deliverable, milestones, tasks, rubric, materials, team size, media. Rubric builder is the hard part — make weights and criteria visually obvious.

### TC-18 · Project Review Queue
Submissions awaiting teacher review with the AI's pre-review already attached, so the teacher confirms or overrides rather than starting cold.

---

# PHASE 4 — Parent (14 screens) · P1

Design principle for this entire section: **parents get answers, not dashboards.** Every screen leads with one sentence in plain Arabic, then the evidence.

### PR-01 · Link Student
Enter the student's link code, or scan it. Shows what the parent will and will not be able to see — transparency is a feature.

### PR-02 · Parent Home
Child selector (if multiple) + a plain-language status line ("رهف تدرس بانتظام هذا الأسبوع") + this week's headline numbers + anything needing attention.

### PR-03 · Executive Summary
The weekly AI narrative: what happened, what's improving, what's slipping, one recommended action. Jouri-marked. This is the screen parents will actually read.

### PR-04 · Performance
Per-subject grades and trends over time. Comparison against the student's own past, never against other students.

### PR-05 · Attendance
Weekly/monthly view of study sessions and lesson engagement, with a clear definition of what "attendance" means in an app context.

### PR-06 · Lessons Progress
Per-course lesson completion list.

### PR-07 · Lesson Detail (parent view)
What the lesson covered, whether it was completed, quiz result. No tutor chat contents — that's the student's private space, and saying so builds trust.

### PR-08 · Planner Visibility
The child's study plan and adherence, read-only.

### PR-09 · Academic Intelligence
Deeper AI analysis: strengths, weak knowledge components, predicted risk areas. Jouri-marked, with confidence framing.

### PR-10 · Reports
Historical report list + generate-new + **PDF export** (Arabic RTL, shareable to WhatsApp).

### PR-11 · Subjects & Teachers
Which teachers the child studies with, their profiles, and a message action.

### PR-12 · Notes & Replies
Teacher notes about the child, threaded replies, read/acknowledge states.

### PR-13 · Parent Notifications
Notification list + granular settings for what triggers an alert.

### PR-14 · Parent Projects View
The child's project portfolio — the most emotionally persuasive screen for a paying parent. Photos of what their kid actually built.

---

# PHASE 5 — English Language Module (26 screens) · P2

The largest module. Port it after everything else is stable.

### LN-01 · Languages Hub
Current CEFR level, skill radar (reading/listening/speaking/writing/grammar/vocabulary), daily mission card, streak, continue action.
### LN-02 · Subscribe / Paywall — module-specific pricing sheet.
### LN-03 · Placement Intro — what the test covers, how long, why it matters.
### LN-04 · Placement Runner — sectioned test (reading, listening, writing, speaking) with per-section intro and a persistent progress spine.
### LN-05 · Placement Result — CEFR level reveal with per-skill breakdown and the path it unlocks.
### LN-06 · Placement History — past attempts and level trajectory.
### LN-07 · Curriculum / Learning Path — the Progress Spine at full scale: stages, units, lessons, gates.
### LN-08 · Lessons List — within a unit.
### LN-09 · Lesson Runtime — mixed-activity lesson shell (present → practice → produce).
### LN-10 · Reading — passage + comprehension questions, inline word-tap to dictionary.
### LN-11 · Listening — audio player with segment replay, transcript reveal, gap-fill and comprehension items.
### LN-12 · Speaking Practice — prompt, record, waveform, then pronunciation + fluency + prosody feedback with per-word scoring.
### LN-13 · Speaking Live Conversation — real-time voice conversation with the AI partner. Full-screen, minimal chrome, connection-state visible, graceful degradation to turn-based when the connection is poor.
### LN-14 · Speaking Discussion — structured topic debate with scaffolding.
### LN-15 · Writing — task prompt, composer with word count, submit for evaluation.
### LN-16 · Writing Feedback — annotated text with inline corrections by category, rubric scores, revision action.
### LN-17 · Writing Portfolio — past pieces and improvement over time.
### LN-18 · Grammar Hub — topics by mastery state.
### LN-19 · Grammar Lesson — explanation → guided practice → free practice.
### LN-20 · Grammar Lesson Chat — ask-about-this-rule tutor, scoped to the topic.
### LN-21 · Grammar Review — spaced review of weak topics.
### LN-22 · Vocabulary — word bank, SRS review session, per-word detail with image, audio, example, and mastery state.
### LN-23 · Dictionary — search, definitions, AR translation, audio, save-to-bank.
### LN-24 · Promotion Test — the gate to the next CEFR level. Higher-stakes visual treatment than a normal quiz.
### LN-25 · Progress & Insights — skill trajectories, error patterns, time invested.
### LN-26 · Language Certificates — earned certificates, share and verify.

---

# PHASE 6 — Cross-cutting (6 screens) · P0

### X-01 · Messages List — threads with participant avatars, last message, unread badge, search.
### X-02 · Conversation Thread — messages, attachments, read receipts, in-thread search, participant sheet.
### X-03 · New Conversation — contact picker scoped by role permissions.
### X-04 · Notifications Center — grouped by type and day, mark-read, deep links into the relevant screen.
### X-05 · Global Search — across lessons, courses, projects, vocabulary. Recent + suggested on empty.
### X-06 · Offline Library — everything downloaded for offline use, with storage used and per-item remove. Critical in Syria; give it a permanent home in the Me tab.

---

# PHASE 7 — Coding module (deferred to v2)

Not designed now. When you get there the screens are roughly: Coding Hub, Track Detail, Exercise Runner (Parsons / fill-blank / free-write), Mobile Code Editor with a snippet keyboard row, Run Output console, Test Results, Hint Tiers, and Coding Project Bridge. **Design decision to make before any of it:** code execution should run on-device — Pyodide in a WebView for Python, Hermes for JavaScript — so exercises work offline and cost nothing per run.

---

## Screen count by phase

| Phase | Screens | Surface | Priority |
|---|---|---|---|
| 0 · Foundation & Auth | 14 | App | P0 |
| 1 · Student Core | 27 | App | P0 |
| 2 · Projects | 12 | App | P0 |
| 3 · Teacher | 18 | App | P1 |
| 4 · Parent | 14 | App | P1 |
| 5 · Language | 26 | App | P2 |
| 6 · Cross-cutting | 6 | App | P0 |
| W · Payment portal | 13 | Web (Lovable) | **P0 — gates revenue** |
| **Total** | **130** | | |

**v1 launch scope = Phases 0, 1, 2, 6 (59 app screens) + all 13 portal screens.**

The portal is P0 alongside the app, not after it. The app can be beautiful and still earn nothing if there's no way to pay. Build both tracks in parallel — they share the design system and the generated API client, so the marginal cost of the portal is much lower than its screen count suggests.

Phases 3–5 follow at roughly one per month. The iOS parity pass slots in around week 26, after Phase 4.
