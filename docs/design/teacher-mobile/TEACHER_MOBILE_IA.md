# Teacher Mobile Information Architecture

**Depends on:** `TEACHER_WEB_AUDIT.md`  
**Visual family:** approved Student mobile (same shell, not the same tabs)  
**Phase:** Design only. No implementation.

---

## Translation rule

Test-2SY Teacher sidebar is a **desktop information dump**.

Mobile cannot copy seven equal destinations.

We group by the teacher’s daily questions:

| Question | Primary home |
|----------|----------------|
| What needs my attention now? | Home |
| What am I teaching? | Classes |
| What do my students need? | Students |
| What assessment needs action? | Quizzes |
| Who am I in this product? | Account |

Messages and Analytics stay real. They are **secondary destinations** because:

- Messages already interrupt Home when unread, and the bell already deep-links threads
- Analytics is a review surface, not a create surface
- Student mobile already keeps Messages out of the tab bar

---

## Layers

### PRIMARY — bottom navigation (5)

Same chrome language as Student: 5 destinations, 48dp targets, one selected color, RTL labels.

| Tab | Arabic | English | Web source | Why it is primary |
|-----|--------|---------|------------|-------------------|
| Home | الرئيسية | Home | `/teacher/dashboard` | Landing after setup. Holds Action Now. |
| Classes | الصفوف | Classes | `/teacher/grades` + class/lesson child routes | Core teaching work. |
| Students | الطلاب | Students | `/teacher/students` (hidden on web sidebar, but real) | Web hid this; teachers still live here from class + analytics. Promote it. |
| Quizzes | الاختبارات | Quizzes | `/teacher/quizzes` + builder/results | Daily grade/create loop. Label matches Student (`الاختبارات`), not web `الكويزات`. |
| Account | حسابي | Account | `/teacher/profile` + `/teacher/settings` | Same Account-hub philosophy as Student. |

**Not a tab:** Messages, Analytics, Voice, Settings, All Lessons, CV.

**Do not add:** Projects, Gradebook, Planner, Attendance. They are not Teacher web features.

---

### SECONDARY — hamburger drawer

Same Student top-bar pattern: **☰ + EduMind / screen title + 🔔**

Drawer is the complete map:

| Row | Arabic | Opens | Web source |
|-----|--------|-------|------------|
| Home | الرئيسية | Home tab | dashboard |
| Classes | الصفوف | Classes tab | grades |
| Students | الطلاب | Students tab | students |
| Quizzes | الاختبارات | Quizzes tab | quizzes |
| Messages | الرسائل | Messages list | `/teacher/messages` |
| Analytics | التحليلات | Analytics | `/teacher/analytics` |
| Profile | الملف الشخصي | Account → identity | `/teacher/profile` |
| Voice | الصوت | Voice profile | Profile voice section |
| Settings | الإعدادات | Security settings | `/teacher/settings` |
| Logout | تسجيل الخروج | Confirm sheet | header menu |

Footer tip (optional, cyan only if truly AI): short voice-recording tip already used in web sidebar promo.

---

### TERTIARY — sheets, steps, screen actions

| Interaction | Pattern | Replaces on web |
|-------------|---------|-----------------|
| Create class | Step sheet / short flow | `CreateCourseDialog` |
| Edit class | Same flow, prefilled | `EditCourseDialog` |
| Add lesson | Step flow (info → source → review) | `AddLessonDialog` |
| Filters | Chip row or filter sheet | Desktop filter bar |
| Private note | Bottom sheet | Dialog |
| Parent note | Thread screen + compose sheet | Nested profile panels |
| New message | Contact sheet → thread | Split inbox compose |
| Notifications | Bell → bottom sheet | Header dropdown |
| Quiz question editor | Full screen | Teleport overlay |
| Quiz preview | Full screen or large sheet | `TeacherQuizPreviewDialog` |
| Essay grading | Attempt screen, not a modal-on-modal | Results overlay |
| Publish / delete | Confirm sheet | Confirm dialog |
| Voice record | In-place recorder on Voice screen | Profile section widget |

Avoid: desktop tables, nested tabs, modal-on-modal, long horizontal tab bars.

---

## Top bar

Follow Student exactly.

| Element | Rule |
|---------|------|
| Leading | Hamburger on root tabs. Back on pushed screens. Never both. |
| Center | `EduMind` on Home. Screen name on other roots (`الصفوف`, `الطلاب`, `الاختبارات`, `حسابي`). Contextual title on pushed screens. |
| Trailing | **Notifications bell only.** Badge = unread count. |
| Not in the top bar | Messages icon, Classes shortcut, theme, language (language stays in Account / existing app locale switch). |

Why no permanent Messages icon: audited Teacher flow already surfaces unread messages as Home’s first Action Now item, and the bell already routes `internal_message` into the thread.

---

## Proposed graph

```
Auth (shared, already designed)
 └── Teacher Setup (forced) ──► Teacher shell

Teacher shell
├── Tab Home
│   └── deep links into Classes / Students / Quizzes / Messages / Lesson preview
├── Tab Classes
│   ├── Class Detail
│   │   ├── Add Lesson (steps)
│   │   │   └── Processing
│   │   ├── Lesson Preview
│   │   │   └── Lesson Edit
│   │   └── Students (filtered)
│   └── Create / Edit Class (steps)
├── Tab Students
│   └── Student Profile
│       ├── Private note sheet
│       ├── Parent note thread
│       └── Messages thread
├── Tab Quizzes
│   ├── Quiz Settings
│   ├── Questions
│   │   └── Question editor
│   ├── Preview
│   └── Results
│       └── Attempt / essay grade
└── Tab Account
    ├── Identity
    ├── Voice
    ├── AI phrases
    ├── Teaching page (locked / coming soon)
    └── Settings

Drawer / bell
├── Messages list → thread → new conversation
├── Analytics
└── Notifications sheet → contextual destination
```

---

## Setup vs shell

| If | Then |
|----|------|
| `teacherSetupComplete == false` | Full-screen setup only. No tabs. Settings still reachable (web already allows this). |
| Setup finished | Tabs appear. Setup is not a tab. |

---

## Why this is not the old TC inventory

`docs/02-screen-inventory.md` Teacher tabs were:

`لوحة · موادي · طلابي · مشاريع · حسابي`

That tree is **wrong for Test-2SY**:

- “موادي” is Student language. Teacher works in **classes**, not a student course catalog.
- **Projects do not exist** for Teacher.
- **Quizzes** are a first-class web destination and a Home Action Now item. They must not be buried.
- **Students** exist but were hidden in the web sidebar; mobile promotes them.

Existing Android Teacher tabs (`Dashboard / Courses / Students / Projects / Me`) must be **redesigned after approval**, not treated as the approved IA.

---

## Destination ownership

| Capability | Owner | Also reachable from |
|------------|-------|---------------------|
| Next action | Home | — |
| Create class / lesson | Classes | Home quick/empty |
| Create / grade quiz | Quizzes | Home Action Now |
| Student follow-up | Students | Class cohort, Analytics, Home inactive-student task |
| Talk to a parent/student | Messages | Home, Student profile, bell |
| Review across classes | Analytics | Drawer, Home only if no urgent task |
| Voice / AI phrases | Account | Drawer |
| Security | Account | Drawer (and before setup) |
