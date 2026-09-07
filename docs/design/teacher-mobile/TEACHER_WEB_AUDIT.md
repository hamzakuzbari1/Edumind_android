# Teacher Web Audit — Test-2SY

**Product authority:** [YassoBases/Test-2SY](https://github.com/YassoBases/Test-2SY)  
**Inspected clone:** current `main` (`5b8ecea` — “Publish the current local app so clones match this machine.”)  
**Date:** 6 September 2026  
**Scope:** Teacher role only. No invented features. No Android implementation.

This audit describes **what the Teacher can do on the live web product**.  
The Student mobile design (approved) is **not** used here as a feature list.

---

## How this audit was done

Inspected, not guessed:

- `src/router/index.js` — every `/teacher/*` route and setup gate
- `src/layouts/TeacherLayout.vue` + `src/config/navigation.js`
- All `src/views/teacher/*.vue` + `TeacherDashboardView.vue`
- Teacher components under `src/components/teacher/`
- Locales: `src/locales/ar|en/teacher.json`, `dashboard.json`, `routes.json`
- Backend routers: `teacher.py`, `teacher_courses.py`, `teacher_setup.py`, `teacher_voice.py`, `teacher_dashboard.py`, `teacher_students.py`, `course_quizzes.py`, `lesson_publish.py`, `messages.py`
- Frontend API modules: `teacher.js`, `teacherCourses.js`, `teacherSetup.js`, `teacherDashboard.js`, `teacherStudents.js`, `manualQuizzes.js`, `parentNotes.js`, `messages.js`, `notifications.js`

---

## Role gate

| Rule | Reality |
|------|---------|
| Auth | JWT session, `role === teacher` |
| Setup | If `teacherSetupComplete` is false, every teacher route except `/teacher/setup` and `/teacher/settings` redirects to setup |
| After setup | Login lands on `/teacher/dashboard` |
| Deprecated | `/teacher/upload` redirects to `/teacher/grades` |

---

## Web navigation (sidebar)

TeacherLayout is a desktop sidebar + header. There are **no bottom tabs**.

| Sidebar item | Path | Arabic | English |
|--------------|------|--------|---------|
| Home | `/teacher/dashboard` | الرئيسية | Home |
| Classes | `/teacher/grades` | الصفوف | Classes |
| Messages | `/teacher/messages` | الرسائل | Messages |
| Quizzes | `/teacher/quizzes` | الكويزات | Quizzes |
| Analytics | `/teacher/analytics` | التحليلات | Analytics |
| Profile | `/teacher/profile` | الملف الشخصي | Profile |
| Settings | `/teacher/settings` | الإعدادات | Settings |

**Implemented but not in the sidebar:** `/teacher/students`, `/teacher/lessons`, lesson preview/edit, quiz builder/results, student profile.

**Header:** hamburger (mobile drawer), page title, language, theme, **notification bell**, shortcut to Classes, profile menu (Profile / Security / Logout).

**Notifications:** header dropdown only. There is **no** `/teacher/notifications` page. Message notifications deep-link to `/teacher/messages?thread=…`.

---

## Feature-by-feature inventory

### 1. Teacher setup

| Field | Value |
|-------|--------|
| **Feature name** | Teacher setup (forced onboarding) |
| **Route** | `/teacher/setup` (`teacher-setup`) — **no TeacherLayout** |
| **Purpose** | Collect the minimum identity + teaching scope before the teacher can work |
| **Entry** | First login, or any teacher route while setup is incomplete |
| **Major actions** | Save profile (name, bio, avatar) · Save teaching (grades + subjects) · Optional create first class (title, price) · Finish setup |
| **Important states** | Incomplete · section saving · error · already complete → dashboard |
| **Related data** | `GET/PUT /teacher/setup/*`, `POST /teacher/setup/complete`, `POST /teacher/setup/courses` |
| **Secondary UI** | Inline cards only. No CV/voice/documents in this wizard |
| **Connects to** | Dashboard after complete. Profile later re-edits the same identity/teaching fields |

**Not in this wizard (despite older mobile inventories):** qualifications, documents, pricing beyond optional first-class price, voice sample. Those live on Profile / coming-soon CV.

---

### 2. Teacher Home (Dashboard)

| Field | Value |
|-------|--------|
| **Feature name** | Teacher Home |
| **Route** | `/teacher/dashboard` |
| **Purpose** | Show what needs action now, then today, then light context |
| **Entry** | Sidebar Home · post-setup landing |
| **Major actions** | Quick actions: Create class, Add lesson, Create quiz, Send message |
| **Action Now (computed, real)** | Unread messages · pending quiz attempts to grade · AI-failed lessons · class with no lessons · draft class · unpublished quizzes · draft lessons |
| **Today / follow-up (computed, real)** | Expiring/expired subscriptions · low completion · inactive students · upcoming quizzes (7 days) |
| **Important states** | Loading cards · error · empty Action Now · empty Today |
| **Related data** | `GET /teacher/dashboard/overview`, `GET /teacher/dashboard/grades`, course detail, manual quizzes, unread message count |
| **Secondary** | Overview KPI strip (explicitly “reference, not tasks”) · My Classes preview · Recent activity |
| **Connects to** | Classes, Quizzes, Messages, Lesson preview/edit |

Web Home is already **mission-shaped**, then it still adds a KPI wall + split classes/activity. Mobile should keep the mission, drop the wall.

---

### 3. Classes (web name: Grades)

| Field | Value |
|-------|--------|
| **Feature name** | Classes |
| **Route** | `/teacher/grades` |
| **Purpose** | List and create the teacher’s courses/classes |
| **Entry** | Sidebar · Home quick action · header Classes button |
| **Major actions** | Create class · filter all/published/draft/grade/subject · open class |
| **Important states** | Loading · no classes · filtered empty · error |
| **Related data** | `GET /teacher/dashboard/grades`, `GET /teacher/courses/form-context`, `POST /teacher/courses/create` |
| **Secondary** | `CreateCourseDialog`: name, description, grade, subject, price, cover, banner, publish toggle |
| **Connects to** | Class Detail |

**Critical naming:** “Grades” on web means **school classes / courses**, **not a gradebook**. There is no gradebook model or API.

---

### 4. Class detail

| Field | Value |
|-------|--------|
| **Feature name** | Class workspace |
| **Route** | `/teacher/grades/:courseId` |
| **Purpose** | Operate one class: content, cohort, publish state |
| **Entry** | Classes list · Home class/task deep links · Analytics |
| **Major actions** | Edit course · Add lesson · Preview / Edit / Reprocess lesson · Manage all students |
| **Important states** | Loading · error · empty lessons · lesson draft / processing / processed / error · published / unpublished class |
| **Related data** | `GET /teacher/dashboard/courses/{id}`, lesson list/detail, course update |
| **Secondary** | `AddLessonDialog`, `EditCourseDialog`, student summary panel (top / lagging / inactive / no-quiz) |
| **Connects to** | Lesson preview/edit · Students list (filtered) · Quizzes for that class |

Web shows **7 KPI cards** on this page. Those numbers exist; they are not the teacher’s next action.

---

### 5. Add lesson

| Field | Value |
|-------|--------|
| **Feature name** | Add lesson |
| **Route** | Dialog on Class Detail (not a standalone route) |
| **Purpose** | Create a lesson with teacher media, then start AI processing |
| **Entry** | Class Detail “Add lesson” · Home “Add lesson” |
| **Major actions** | Enter title/description (optional AI generate per field) · choose source · save/upload |
| **Create sources actually in the UI** | 1. Upload video (MP4/MOV/AVI/MKV/WEBM) · 2. Video link (YouTube/Vimeo/direct) · 3. Upload PDF |
| **Important states** | Empty source · generating title/description · uploading · validation (media required, PDF type/size) |
| **Related data** | `POST /teacher/courses/{id}/lessons`, `/lessons/full`, `/lessons/video`, `/lessons/pdf`, `/teacher/lessons/publish` |
| **Secondary** | `LessonSourcePanel`, `LessonAiProcessingCard` (informational, not live pipeline) |
| **Connects to** | Class Detail reload · AI processing starts automatically for video/PDF |

**Homework:** backend `POST .../lessons/homework` exists and lessons can be typed `homework`. The **create dialog does not offer homework**. Mobile must not invent a new assignment product. Homework lessons, if present, display as a type chip only.

---

### 6. Lesson edit

| Field | Value |
|-------|--------|
| **Feature name** | Edit lesson |
| **Route** | `/teacher/courses/:courseId/lessons/:lessonId/edit` |
| **Purpose** | Change title, description, media, visibility |
| **Entry** | Class lesson row · All Lessons · Home failed-lesson path |
| **Major actions** | Replace/remove video, PDF, audio · toggle visible · save · cancel to preview |
| **Important states** | Loading · load failed · saving · needs reprocessing warning |
| **Related data** | `GET/PATCH .../lessons/{id}`, `POST .../update-content` |
| **Connects to** | Preview after save |

---

### 7. Lesson preview + AI process

| Field | Value |
|-------|--------|
| **Feature name** | Lesson preview / AI status |
| **Route** | `/teacher/courses/:courseId/lessons/:lessonId/preview` |
| **Purpose** | See what students will get, and recover failed AI |
| **Entry** | Class lesson row · Home AI-failed task |
| **Major actions** | Back to class · Edit · Reprocess AI (when PDF exists and status is error/draft/processing) |
| **Important states** | draft · processing · processed · error · visible / hidden · missing media tabs disabled |
| **Related data** | Lesson detail, `POST .../process`, `GET /teacher/lessons/{id}/publish-status` |
| **Secondary** | Tabs: Video / PDF / Audio · info that tutor + quiz appear after processing |
| **Connects to** | Edit · Class Detail |

AI pipeline (backend, real): extract/transcribe → chunks → FAISS → persona → **MCQ lesson quiz** → insights → `processed`.

Lesson statuses: `draft → processing → processed | error`. Students only see **processed** lessons on **paid** courses.

---

### 8. All lessons (orphan)

| Field | Value |
|-------|--------|
| **Feature name** | Cross-class lesson index |
| **Route** | `/teacher/lessons` — **no sidebar link** |
| **Purpose** | Search lessons across all classes |
| **Entry** | Direct URL only |
| **Major actions** | Search · open preview/edit |
| **Important states** | Loading · empty · no search match |
| **Connects to** | Preview / Edit |

Capability is real. Primary nav should not promote an orphan page. Mobile can fold this into Teaching search if needed.

---

### 9. Students list

| Field | Value |
|-------|--------|
| **Feature name** | Students |
| **Route** | `/teacher/students` — **no sidebar link** |
| **Purpose** | Find subscribed students in the teacher’s subjects |
| **Entry** | Class “Manage all students” · Analytics hero |
| **Major actions** | Search (300ms debounce) · filter grade/subject · open profile |
| **Important states** | Loading · empty · filtered empty |
| **Related data** | `GET /teacher/students?q=&grade=&subject_id=` |
| **Data shown** | Name, email, grade, active/expired, last activity, completion, avg quiz % |
| **Connects to** | Student profile |

Web is a **desktop table**. That is a layout, not a feature.

---

### 10. Student profile (teacher view)

| Field | Value |
|-------|--------|
| **Feature name** | Student profile |
| **Route** | `/teacher/students/:studentId` |
| **Purpose** | Understand one student and act |
| **Entry** | Students list · class cohort row |
| **Major actions** | Add/edit/delete **private note** · create/reply/close **parent note** · message linked parents |
| **Important states** | Loading · empty notes · empty planner · no parent linked |
| **Related data** | `GET /teacher/students/{id}`, notes CRUD, parent-notes CRUD, `GET .../planner` (read-only) |
| **Secondary** | KPI cards, insight panel, quiz analytics, activity timeline, planner snapshot |
| **Connects to** | Students list · Messages |

Private notes: **teacher-only, not visible to parents**.  
Parent notes: structured threads (title, category, priority, body) with replies. Categories: academic, attendance, homework, behavior, achievement, warning. Priorities: low / medium / high / urgent. Statuses: new / read / replied / closed.

---

### 11. Manual quizzes

| Field | Value |
|-------|--------|
| **Feature name** | Teacher-authored class quizzes |
| **Routes** | `/teacher/quizzes` · `/teacher/quizzes/:courseId/:quizId/edit` · `.../results` |
| **Purpose** | Create, publish, review, and grade human-authored quizzes |
| **Entry** | Sidebar Quizzes · Home “grade now” / “create quiz” |
| **Major actions** | Create (pick class if several) · edit · publish/unpublish · delete · preview · review attempts · grade essays |
| **Question types** | `multiple_choice` · `true_false` · `short_answer` · `essay` (manual grade) |
| **Settings** | Title, description, optional duration, passing % (default 60), optional future deadline, publish, total points |
| **Fixed rule** | Attempts displayed as **one per student** and **cannot be changed** |
| **Important states** | No classes yet · no quizzes · draft / published · pending review · in-progress attempt (review disabled) · pending essay grading |
| **Related data** | `/teacher/courses/{id}/manual-quizzes*` |
| **Connects to** | Class context · student results · Home pending-attempts task |

**Not a real filter:** Quizzes list shows an “AI” chip with count **hardcoded 0**. Do not design this as a product filter.

**Separate system:** AI lesson MCQs are generated by the lesson processor. They are not the Quiz Builder. Teachers regenerate them via `POST .../quiz/regenerate` (API exists; class-detail `generateQuiz()` is **dead code**, not in the template).

---

### 12. Analytics

| Field | Value |
|-------|--------|
| **Feature name** | Teaching analytics |
| **Route** | `/teacher/analytics` |
| **Purpose** | Cross-class review: who needs attention, weakest quizzes/lessons |
| **Entry** | Sidebar Analytics |
| **Major actions** | Open class · open quiz results · open lesson · open messages |
| **Important states** | Loading · no classes |
| **Related data** | **No `/teacher/analytics` API.** UI composes dashboard overview/grades, manual-quiz analytics, unread messages |
| **Connects to** | Classes, Students, Quizzes, Messages |

Preserve the **information**. Do not copy the desktop chart/table wall.

---

### 13. Messages

| Field | Value |
|-------|--------|
| **Feature name** | Teacher messaging |
| **Route** | `/teacher/messages` — shared `MessagesView` with `role: 'teacher'` |
| **Purpose** | Talk to students and parents |
| **Entry** | Sidebar · Home unread task · Student profile parent contact |
| **Major actions** | Search · new conversation · archive toggle · send text · send attachment · send voice · open thread |
| **Important states** | Empty inbox · loading · unread |
| **Related data** | `/messages/*` plus teacher contacts, conversation create, thread context |
| **Secondary** | `TeacherConversationContextHeader` |
| **Connects to** | Student profile · Notifications bell |

---

### 14. Notifications

| Field | Value |
|-------|--------|
| **Feature name** | Notification bell |
| **Route** | None (header dropdown) |
| **Purpose** | Surface unread events; jump into context |
| **Entry** | Header bell on every TeacherLayout screen |
| **Major actions** | Open item · mark read (shared notification API) |
| **Related data** | `/notifications`, unread count |
| **Connects to** | Messages for `internal_message` |

---

### 15. Profile

| Field | Value |
|-------|--------|
| **Feature name** | Teacher profile |
| **Route** | `/teacher/profile` |
| **Purpose** | Identity, voice, AI phrases, teaching scope |
| **Entry** | Sidebar Profile · header menu |
| **Major actions** | Save/discard name, bio, avatar · record/upload/listen/replace/delete voice samples · edit encouragement phrases · save grades/subjects |
| **Important states** | Saving · voice pending/processing/awaiting_acceptance/ready/failed · max samples |
| **Related data** | `/teacher/setup/profile`, avatar, teaching, ai-profile, `/teacher/voice-*` |
| **Secondary** | Read-only 9-step onboarding explainer (decorative) |
| **Connects to** | Lesson AI voice · student catalog cards |

**Voice clone is real:** upload ≥ sample → transcribe → ElevenLabs clone → preview TTS.

---

### 16. Public CV / portfolio

| Field | Value |
|-------|--------|
| **Feature name** | Teaching page / CV / portfolio |
| **Route** | CV editor is a **Coming soon** block on Profile |
| **Purpose (intended)** | Public teacher page students see |
| **Reality** | `TeacherProfileCvEditor` = coming-soon placeholder. `TeacherPortfolioEditor` exists with locales/API (`/teacher/setup/cv`, portfolio, documents) but is **not mounted**. Students can still read a public profile via `GET /student/courses/{id}/teacher-profile` from whatever CV data exists. |
| **Mobile rule** | Do **not** invent a full CV studio. Show a locked/unavailable Teaching Page row until web ships it. |

---

### 17. Settings

| Field | Value |
|-------|--------|
| **Feature name** | Account security |
| **Route** | `/teacher/settings` (`accountSettings: true` — allowed before setup) |
| **Purpose** | Password / 2FA / trusted devices |
| **Entry** | Sidebar Settings · header Security |
| **Major actions** | Same shared `UserSettingsView` as other roles |
| **Not included** | Teaching prefs, notification prefs as a teacher-specific API |

---

## Exact Teacher feature tree

Built from routes + APIs + mounted UI. **Projects are not here.**

```
Teacher
├── Setup (forced)
│   ├── Identity (name, bio, avatar)
│   ├── Teaching scope (grades, subjects)
│   └── Optional first class
├── Home
│   ├── Action Now
│   ├── Today / follow-up
│   ├── Quick actions
│   └── Light class + activity context
├── Classes
│   ├── Class list + filters
│   ├── Create / edit class
│   ├── Class detail
│   │   ├── Lessons
│   │   │   ├── Add (video file / video link / PDF)
│   │   │   ├── Preview
│   │   │   ├── Edit (video / PDF / audio)
│   │   │   └── AI process / reprocess
│   │   └── Student cohort summary
│   └── All-lessons index (orphan route)
├── Students
│   ├── Students list
│   └── Student profile
│       ├── Private notes (teacher only)
│       ├── Parent notes (threaded)
│       ├── Read-only planner peek
│       └── Message parent
├── Quizzes (manual / teacher-authored)
│   ├── Quiz list
│   ├── Builder + question editor
│   ├── Preview
│   └── Results + essay grading
├── Analytics (composed review)
├── Messages (text / voice / attachment)
├── Notifications (bell only)
├── Profile
│   ├── Identity
│   ├── Voice clone
│   ├── AI phrases
│   ├── Teaching scope
│   └── Teaching page / CV (coming soon)
└── Settings (security + devices)
```

---

## Confirmed non-features (do not design as primary product)

| Claim | Test-2SY reality |
|-------|------------------|
| Teacher Projects | **Does not exist** (no route, view, API, or teacher locale) |
| Gradebook | **Does not exist**. “Grades” = classes |
| Standalone Assignments product | **Does not exist**. Homework is a lesson type/API only; create UI does not expose it |
| Teacher attendance module | **Does not exist**. Attendance is a parent-note category only |
| Teacher planner authoring | **Does not exist**. Read-only student planner peek only |
| Dedicated teacher notifications page | **Does not exist** |
| Quiz “AI” workspace filter | **Fake** (count always 0) |
| Mounted CV / portfolio editor | **Coming soon / unmounted** |
| Changeable quiz attempt count | **Locked to one attempt** |

Older mobile inventories (`TC-14` Grades, `TC-17/18` Projects, full CV wizard) are **not** Test-2SY Teacher features.

---

## Data language teachers actually use

| Web word | Meaning |
|----------|---------|
| Class / Grade / Course | One teaching group (subject + school grade + students) |
| Lesson | Teacher media + optional AI layer |
| Manual quiz | Teacher-authored assessment |
| Lesson quiz | AI MCQ generated from processed media |
| Private note | Teacher-only memory |
| Parent note | Structured message to the parent |
| Published / draft | Visibility of class or quiz |
| Processed | AI pipeline finished; students can use tutor/quiz |

---

## End of audit

This file is the feature authority for Teacher mobile design.  
If a capability is not listed above, it is not a primary Teacher product feature.
