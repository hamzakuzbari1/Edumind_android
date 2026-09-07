# EduMind Mobile — Approved Design → Screen Map

This folder (`docs/design/mobile-approved/`) is the **frozen, approved visual
authority** for Android implementation. `index.html` is a byte-identical copy
of the published Claude Design canvas at the time of freeze (44 static phone
mockups across 7 pages, indigo/cyan/amber design system, Arabic-first RTL).

**Authority hierarchy going forward:**
1. **This folder** — visual authority (how it looks)
2. **Test-2SY** (`github.com/YassoBases/Test-2SY`) — functional/UX behavior reference (how it works)
3. **Existing Android app** — implementation/reuse foundation (shared components, tokens, architecture)

Screen IDs below are the canonical ones from `docs/02-screen-inventory.md`
(130-screen inventory). Do not invent new IDs when implementing — reuse these.

**Coverage note:** this first design pass covers 44 of the 130 inventoried
screens — the highest-priority representative screen per feature area, plus
extra states/flow-steps on the most complex ones (Lesson+AI Tutor, Quiz,
Planner, Routine, Placement Exam). It is not full 1:1 coverage of every
inventoried screen; screens not listed below should be extrapolated from the
same design system (tokens, components, patterns) shown here, per the Part 1
migration plan, not designed from scratch.

---

## Auth & Onboarding

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `Main.dc.html` | **A-03** · Role Select | Front-door mockup; the 3 role cards (Student/Teacher/Parent) match A-03 exactly |
| `Login.dc.html` | **A-04** · Login | |
| `OtpVerify.dc.html` | **A-09** · Two-Factor Verify | 6-cell OTP + resend cooldown. Shares its OTP-cell component with **A-08** · Verify Email, which the inventory notes should get its *own* distinct visual identity — not designed separately here |
| `OnboardingGrade.dc.html` | **SO-01** · Onboarding: Grade | |
| `OnboardingPersonalize.dc.html` | **SO-04** · Onboarding: Personalize | Android's actual step order (Grade→Subjects→Teachers→Personalize→Complete) differs from Test-2SY's web order — flagged in the Part 1 audit, not resolved here |
| `OnboardingComplete.dc.html` | **SO-05** · Onboarding Complete | |

## Student Core

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `StudentHome.dc.html` | **ST-01** · Student Home | |
| `CourseDetail.dc.html` | **ST-02** · Course Detail | Unlocked state, Progress Spine of lessons |
| `CourseDetailLocked.dc.html` | **ST-02** · Course Detail | Locked/paywall state — entry point into **ST-16**/**ST-17** |
| `LessonPlayer.dc.html` | **ST-03** · Lesson Player | Video-media state shown; PDF/audio states not separately mocked |
| `TutorChat.dc.html` | **ST-04** · AI Tutor Chat | Includes math rendering, concept chips, typing indicator |
| `QuizRunner.dc.html` | **ST-06** · Quiz Runner | In-progress state, MCQ selected |
| `QuizResults.dc.html` | **ST-07** · Quiz Results | |
| `Achievements.dc.html` | **ST-15** · Achievements | |
| `LearningPreferences.dc.html` | *New — proposed* | Extends **ST-22** · Student Profile with an AI-adaptation preference screen (goal/explanation-length/interests). Not a numbered screen in the current inventory; proposed during the Test-2SY web-audit phase since Test-2SY's `StudentProfileView` is a preference surface with no Android equivalent |

## Planner, Routine, Payments, Projects

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `Planner.dc.html` | **ST-10** · Planner | |
| `PlannerSessionSheet.dc.html` | **ST-10** · Planner | The "tap a block for detail sheet" state named explicitly in ST-10's own inventory entry |
| `RoutineBuilder.dc.html` | **ST-12** · Routine Builder (conversational) | Shows the activities-picker step of the multi-turn setup |
| `RoutineWeek.dc.html` | **ST-13** · Routine Week View | Accordion-by-day, today expanded, complete/miss/undo actions |
| `PaymentMethod.dc.html` | **ST-18** · Payment Method Select | `direct`-flavor variant only (`play`-flavor Google Play Billing sheet not mocked) |
| `PurchaseSuccess.dc.html` | **ST-20** · Purchase Success | |
| `ProjectsHub.dc.html` | **PJ-01** · Projects Hub | My Projects tab shown; Discover/Portfolio tabs not separately mocked |

## Teacher

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `TeacherDashboard.dc.html` | **TC-02** · Teacher Dashboard | |
| `LessonUpload.dc.html` | **TC-05** · Lesson Upload | AI-processing state shown also represents **TC-06** · Lesson Processing Status |
| `QuizBuilder.dc.html` | **TC-10** · Quiz Builder | Single-question editor state |
| `TeacherStudents.dc.html` | **TC-12** · Students List | Card-list treatment, not the dense desktop table Test-2SY uses |
| `TeacherStudentProfile.dc.html` | **TC-13** · Student Profile (teacher view) | AI-insight card pattern for the "private teacher notes" surface |

## Parent — module is currently 0% built on Android; all screens below are new

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `ParentHome.dc.html` | **PR-02** · Parent Home | AI-insight teaser card also represents **PR-03** · Executive Summary |
| `ParentLinkStudent.dc.html` | **PR-01** · Link Student | Text-code entry, matching the code-based linking Test-2SY actually uses (no QR scan) |
| `ParentProgress.dc.html` | **PR-04** · Performance | AI analysis card also represents **PR-09** · Academic Intelligence |
| `ParentReports.dc.html` | **PR-10** · Reports | Export sheet shows PDF only (Test-2SY's CSV/Excel export deliberately cut for mobile, per the Part-2 mobile-design phase) |

Not yet designed: **PR-05** Attendance, **PR-06/07** Lessons, **PR-08** Planner Visibility, **PR-11** Subjects & Teachers, **PR-12** Notes & Replies, **PR-13** Parent Notifications (see shared `Notifications.dc.html` pattern below), **PR-14** Parent Projects View.

## Language Hub — module is currently 0% built on Android; all screens below are new

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `LanguageHub.dc.html` | **LN-01** · Languages Hub | |
| `PlacementExam.dc.html` | **LN-04** · Placement Runner | Speaking section, recording state |
| `Curriculum.dc.html` | **LN-07** · Curriculum / Learning Path | CEFR stage-path-map pattern |
| `Reading.dc.html` | **LN-10** · Reading | |
| `Listening.dc.html` | **LN-11** · Listening | |
| `Speaking.dc.html` | **LN-14** · Speaking Discussion | Guided conversational exchange with inline corrections; also the closest reference for **LN-12** Speaking Practice and **LN-13** Live Conversation, which were not mocked as separate screens |
| `Vocabulary.dc.html` | **LN-22** · Vocabulary | Flashcard + SM-2 grading state |

Not yet designed: **LN-02** Subscribe/Paywall (reuse **ST-17** Course Paywall Sheet pattern, per the Part-2 mobile-design recommendation), **LN-03** Placement Intro, **LN-05/06** Placement Result/History, **LN-08/09** Lessons List/Runtime, **LN-15/16/17** Writing, **LN-20/21** Grammar Chat/Review, **LN-23** Dictionary, **LN-24** Promotion Test, **LN-26** Certificates.

## Grammar, Messaging, Notifications

| Design file | Screen ID | Feature / Notes |
|---|---|---|
| `GrammarJourney.dc.html` | **LN-18** · Grammar Hub | CEFR stage-map pattern shared with LN-07 |
| `GrammarLesson.dc.html` | **LN-19** · Grammar Lesson | Fill-in-the-blank practice state |
| `MessagesList.dc.html` | **X-01** · Messages List | |
| `MessagesThread.dc.html` | **X-02** · Conversation Thread | Includes a voice-message bubble |
| `Notifications.dc.html` | **X-04** · Notifications Center | New screen — Android currently has only a TopBar badge (see `RoleShell.kt`'s own "Phase 6" placeholder comment) |
| `LanguageProgress.dc.html` | **LN-25** · Progress & Insights | AI-coach card + recurring-mistakes pattern |

---

## Screens NOT designed in this pass (for later batches)

Everything in Phase 0 beyond A-03/A-04/A-09 (A-01, A-02, A-05–A-08, A-10–A-14),
most of Phase 2 Projects (PJ-02–PJ-12), most of Phase 3 Teacher (TC-01,
TC-03/04, TC-06–TC-09, TC-11, TC-14–TC-18), most of Phase 4 Parent (listed
above), most of Phase 5 Language (listed above), and X-03/X-05/X-06 from
Phase 6. These should extrapolate from the shared design system established
in the 44 screens here, not be designed as a separate visual language.
