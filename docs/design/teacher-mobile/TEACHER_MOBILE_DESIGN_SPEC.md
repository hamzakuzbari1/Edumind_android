# Teacher Mobile Design Spec

**Status:** Design only. Awaiting approval. Do not implement.  
**Feature authority:** `TEACHER_WEB_AUDIT.md` (Test-2SY)  
**IA:** `TEACHER_MOBILE_IA.md`  
**Feel authority:** approved Student mobile (shell, tokens, IMAGE → TEXT → ACTION)

---

## A. Audited feature inventory

See the exact tree in `TEACHER_WEB_AUDIT.md`. Summary of **22** real Teacher capabilities:

1. Forced setup  
2. Home / Action Now  
3. Classes list  
4. Create / edit class  
5. Class detail  
6. Add lesson (video file / video link / PDF)  
7. Lesson preview  
8. Lesson edit (video / PDF / audio)  
9. AI process / reprocess  
10. Cross-class lesson index (orphan on web)  
11. Students list  
12. Student profile  
13. Private notes  
14. Parent notes  
15. Manual quizzes  
16. Quiz results + essay grading  
17. Analytics  
18. Messages (text / voice / attachment)  
19. Notification bell  
20. Profile identity + teaching scope  
21. Voice clone  
22. Settings / security  

**Not designed as product:** Projects, gradebook, assignments product, teacher attendance, teacher planner authoring, mounted CV studio, fake “AI quizzes” filter.

---

## B. Mobile navigation

5 tabs: **الرئيسية · الصفوف · الطلاب · الاختبارات · حسابي**  
Drawer: Messages, Analytics, Profile, Voice, Settings, Logout  
Top bar: hamburger or back · title · notifications  
Details: `TEACHER_MOBILE_IA.md`

---

## I. Design tokens (reuse Student)

| Token | Value | Use |
|-------|--------|-----|
| Primary | `#6366F1` → `#4F46E5` | CTA, selected tab, progress |
| Background | `#F4F7FB` | Screen canvas |
| Surface | `#FFFFFF` | Cards, sheets, top bar |
| Text | `#0C1929` / `#0F172A` | Primary / secondary |
| AI cyan | `#06B6D4` | Hairline + sparkle **only** on AI-authored or AI-processing |
| AI text | `#0E7490` | AI labels |
| Success | `#047857` | Published, processed, graded, ready |
| Danger | `#EF4444` | Failed AI, pending grading, delete |
| Amber | rationed | Attention only when the task is truly urgent (failed AI, pending essays). Not decoration. |
| Radius | ~18dp | Cards, sheets |
| Touch | 48dp min | Every tap target |
| Type | Cairo UI · Tajawal numerals | Western digits by default |
| Shadow | minimal / none | Flat cards |
| Direction | RTL Arabic first · LTR English | Same shell |

**AI contract (same as Student):** cyan marks the machine. A teacher’s own lesson, quiz, or parent note is **human** and never gets a cyan sparkle.

---

## Visual language (major screens)

| Screen | Contextual visual | Not |
|--------|-------------------|-----|
| Home mission | Subject diagram of the class/task in play | Dashboard charts |
| Class | Small classroom / subject board | Stock campus photo |
| Lesson video | Play well + film strip | Generic cloud icon wall |
| Lesson PDF | Document page | File-manager list |
| Lesson audio | Waveform | Microphone toy |
| Quiz | Check / assessment mark | Trophy / gamification |
| Student | Simple progress well | Spreadsheet |
| Analytics | One insight illustration | Chart collage |
| Messages | Person + conversation | Chat-app clone chrome |
| Voice | Calm waveform | Studio mixer |
| AI processing | Small cyan pipeline | Spinner-only void |

---

## J. Teacher journey map

```
Register / Login (shared)
    → Setup: أنا → ماذا أدرّس → صف اختياري → ادخل
        → Home
            → if unread messages     → Messages
            → if essays to grade     → Quiz results
            → if AI failed           → Lesson preview → Reprocess
            → if no lessons          → Class → Add lesson
            → if draft class         → Class → Publish
        → Classes → Class → Add lesson → Processing → Preview → visible
        → Quizzes → Create → Questions → Publish → Results → Grade essay
        → Students → Profile → Note or Message parent
        → Account → Voice / phrases / security
```

Students only see a lesson after it is **processed** and the class is on a **paid** access path. Teacher preview can see drafts.

---

# C–H. Screen-by-screen spec

IDs are new Teacher-mobile IDs (`TM-`). They are **not** the old `TC-*` inventory (that inventory included Projects / gradebook).

Legend for every screen:

1 Name · 2 Purpose · 3 Entry · 4 Top bar · 5 Vertical hierarchy · 6 Visual · 7 Primary CTA · 8 Secondary · 9 Data · 10 Empty · 11 Loading · 12 Error · 13 Interactions · 14 After action · 15 Web source

---

## TM-00 Setup — Identity

1. **إعداد المعلم · ١ / ٣**  
2. Collect name, bio, avatar so the teacher exists as a person.  
3. First teacher login, or any tab while setup incomplete.  
4. Back hidden. Title: إعداد المعلم. No hamburger. Settings gear allowed (web already lets settings through).  
5. Progress 1/3 → greeting line → avatar well → name → bio → Save.  
6. Calm portrait well (initials if no photo).  
7. حفظ  
8. Skip photo. Open Settings.  
9. Full name, bio, avatar.  
10. — (first-run, fields empty is normal)  
11. Skeleton of the card.  
12. Inline error + retry.  
13. Avatar opens system picker.  
14. Teaching scope.  
15. `/teacher/setup` profile card · `PUT /teacher/setup/profile` · `POST /teacher/setup/avatar`

```
┌────────────────────────────┐
│          إعداد المعلم      │
│              ١ / ٣         │
│                            │
│     [ portrait well ]      │
│     أضف صورة               │
│                            │
│ الاسم                      │
│ [ ........................]│
│ نبذة قصيرة                 │
│ [ ........................]│
│                            │
│        [ حفظ ]             │
└────────────────────────────┘
```

---

## TM-01 Setup — Teaching scope

1. **ماذا أدرّس · ٢ / ٣**  
2. Bind the teacher to school grades + subjects.  
3. After identity save.  
4. Back to identity.  
5. Progress 2/3 → question → grade chips → subject chips (loaded per grade) → Save.  
6. Subject diagram, not a form wall.  
7. حفظ  
8. Back.  
9. Selected grade levels, subject IDs.  
10. No subjects for grade → “اختر صفّاً أولاً”.  
11. Chip skeletons.  
12. Retry load subjects.  
13. Multi-select chips, 48dp.  
14. Optional first class.  
15. Setup teaching step · `PUT /teacher/setup/teaching` · `GET /teacher/setup/subjects`

```
┌────────────────────────────┐
│ ←            ٢ / ٣         │
│ ماذا أدرّس؟                │
│ [ subject visual ]         │
│ الصفوف                     │
│ [عاشر] [حادي عشر] [بكالوريا]│
│ المواد                     │
│ [رياضيات] [فيزياء] …        │
│        [ حفظ ]             │
└────────────────────────────┘
```

---

## TM-02 Setup — Optional first class

1. **أول صف · ٣ / ٣**  
2. Optional first course so Home is not empty.  
3. After teaching save.  
4. Back.  
5. Progress 3/3 → “يمكنك إنشاء صف الآن أو لاحقاً” → title → price → Add or Skip.  
6. Small classroom visual.  
7. إنشاء الصف **or** تخطي  
8. —  
9. Title, price (web setup course fields only). Cover/banner wait until Create Class after setup.  
10. Skip is a valid empty.  
11. Saving.  
12. Error toast.  
13. Skip must not block Finish.  
14. Setup complete.  
15. Optional course on setup · `POST /teacher/setup/courses`

---

## TM-03 Setup complete

1. **جاهز للتعليم**  
2. Confirm setup and enter Home.  
3. After TM-02.  
4. No back to unfinished mandatory steps if already completed server-side.  
5. Check visual → one sentence → Enter.  
6. Success well (green, not amber celebration).  
7. ادخل إلى EduMind  
8. —  
9. —  
10. —  
11. Completing…  
12. Retry complete.  
13. Single tap.  
14. Home.  
15. `POST /teacher/setup/complete`

---

## TM-10 Home

1. **الرئيسية**  
2. Answer: *what needs my attention now?*  
3. Tab Home. Post-setup landing.  
4. ☰ · EduMind · 🔔  
5. **Exact hierarchy:**  
   1. Greeting: صباح الخير أستاذ {name}  
   2. One-line status (“جاهز نكمّل؟” / “في شغلة مستعجلة”)  
   3. **أهم شيء الآن** — one dominant card only (first Action Now item)  
   4. **اليوم** — up to 3 follow-up rows  
   5. Optional compact class row **or** one cyan AI card only if a lesson AI-failed  
   6. Stop. No KPI grid. No activity wall. No four equal quick-action buttons.  
6. Mission visual matches the task (inbox / quiz / failed lesson / empty class).  
7. The mission button (افتح الرسائل / صحّح الآن / أعد المعالجة / أضف درساً / انشر الصف).  
8. Today rows. Drawer. Bell.  
9. Only computed Action Now + Today items from the web Home logic.  
10. No urgent + no today → “كل شيء مرتّب” + one quiet CTA: إنشاء صف or إضافة درس.  
11. Skeleton: greeting + one tall card + 3 rows.  
12. Error + retry. Offline banner (Student pattern).  
13. Pull to refresh. Mission is the only large tap.  
14. Deep-link to the owning screen. Back returns to Home with the same phase of the day (list re-fetched).  
15. `/teacher/dashboard` Action Now + Today. Overview KPIs and activity **intentionally omitted** on mobile.

```
┌────────────────────────────┐
│ ☰        EduMind        🔔 │
│                            │
│ صباح الخير أستاذ سامر      │
│ في شغلة مستعجلة            │
│                            │
│ [ assessment visual ]      │
│ أهم شيء الآن               │
│ ٣ إجابات تحتاج تصحيحاً     │
│ [ صحّح الآن ]              │
│                            │
│ اليوم                      │
│ ○ اشتراك ينتهي — ١٢ أ       │
│ ● طالبان بلا نشاط          │
│                            │
└────────────────────────────┘
     الرئيسية الصفوف الطلاب
     الاختبارات حسابي
```

Priority order (same as web computation, first item becomes the mission):

1. Unread messages  
2. Pending quiz grading  
3. AI-failed lesson  
4. Class with zero lessons  
5. Draft class  
6. Unpublished quizzes / draft lessons  

Today rows: expiring access, low completion, inactive students, upcoming quiz.

---

## TM-20 Classes list

1. **الصفوف**  
2. What am I teaching?  
3. Tab Classes. Home empty CTA.  
4. ☰ · الصفوف · 🔔  
5. Subject visual header (small) → filter chips → class cards. FAB: صف جديد.  
6. Per card: subject diagram + class name.  
7. Open class. FAB create.  
8. Filters: الكل / منشور / مسودة / صف دراسي / مادة.  
9. Subject, school grade, publish state, student count, lesson count, quiz count.  
10. “ما في صفوف بعد” + classroom visual + أنشئ أول صف.  
11. Card skeletons.  
12. Retry.  
13. Card tap. Filter chips.  
14. Class detail, or Create Class.  
15. `/teacher/grades`

```
┌────────────────────────────┐
│ ☰         الصفوف        🔔 │
│ [الكل] [منشور] [مسودة]     │
│ ┌────────────────────────┐ │
│ │ [math visual]  منشور   │ │
│ │ رياضيات · الصف العاشر  │ │
│ │ ٢٤ طالباً · ٨ دروس     │ │
│ └────────────────────────┘ │
│                      [ + ] │
└────────────────────────────┘
```

---

## TM-21 Create / edit class

1. **صف جديد / تعديل الصف**  
2. Create or edit one course.  
3. FAB · Class Detail edit.  
4. ← title.  
5. Steps: Basic (name, description) → Teaching (grade, subject, price) → Appearance (cover, banner) → Publish toggle → Save.  
6. Classroom / cover visual on appearance step.  
7. إنشاء / حفظ  
8. Back step (does not wipe).  
9. Web CreateCourseDialog / EditCourseDialog fields only.  
10. —  
11. Saving.  
12. Validation + API error.  
13. Progressive steps, not one giant form.  
14. Class detail.  
15. `POST /teacher/courses/create` · `PUT /teacher/courses/{id}`

---

## TM-22 Class detail

1. **تفاصيل الصف**  
2. Operate one class.  
3. Classes list · Home class tasks.  
4. ← class name · overflow (edit class).  
5. Cover/visual → name · subject · grade · published chip → **one** completion line (not 7 KPIs) → **الدروس** list → **الطلاب** compact cohort (3 groups max: يحتاجون متابعة / متقدمون / بلا نشاط) → link كل الطلاب.  
6. Course visual / cover.  
7. أضف درساً  
8. Edit class · lesson overflow (preview, edit, reprocess if eligible).  
9. Lessons with type + status. Cohort names. One completion percent.  
10. No lessons → document/video empty + أضف أول درس.  
11. Header + list skeletons.  
12. Retry.  
13. Lesson tap → preview. Cohort tap → Students filtered.  
14. Add lesson / Preview / Students.  
15. `/teacher/grades/:courseId` — KPIs collapsed to one line.

```
┌────────────────────────────┐
│ ←   رياضيات · العاشر       │
│ [ cover / subject visual ] │
│ منشور · ٢٤ طالباً · ٦٨٪    │
│                            │
│ الدروس                     │
│ ○ المشتقة   فيديو  جاهز    │
│ ○ السلسلة   PDF   يعالج    │
│ ○ الواجب    ملف   مسودة    │
│                            │
│ الطلاب · يحتاجون متابعة    │
│ ريم — بلا اختبار           │
│ كل الطلاب ←                │
│                            │
│      [ أضف درساً ]         │
└────────────────────────────┘
```

---

## TM-23 Add lesson

1. **درس جديد**  
2. Add teacher media to a class.  
3. Class Detail CTA · Home “add lesson”.  
4. ← درس جديد. Steps 1/3.  
5. **Step 1 Basic:** title, description, optional Generate (cyan, AI).  
   **Step 2 Teacher content:** source picker — فيديو / رابط فيديو / ملف PDF. Upload well.  
   **Step 3 Review:** summary + “EduMind سيجهّز المعلّم الذكي والاختبار بعد الرفع” (cyan, informational). Save.  
6. Source-specific visual (film / link / document).  
7. حفظ الدرس  
8. Back step.  
9. Title, description, one source.  
10. Empty well: “اسحب الملف أو اختره”.  
11. Upload progress.  
12. Type/size validation. Failed upload.  
13. One source at a time (web panel).  
14. Processing screen, then Class Detail.  
15. `AddLessonDialog` + `LessonSourcePanel`. No homework create path.

Upload states: empty · uploading · processing · ready · failed.

---

## TM-24 Lesson processing

1. **تجهيز الدرس**  
2. Show the AI pipeline so the teacher is not stuck.  
3. After save, or open a processing/error lesson.  
4. ← lesson title.  
5. Lesson visual → status sentence → steps: استخراج → تقسيم → فهرسة → اختبار ذكي → رؤية. Each step waiting / done / failed.  
6. Small cyan pipeline (AI).  
7. If failed: أعد المحاولة. If ready: معاينة.  
8. Back to class (does not cancel server job).  
9. `publish-status` / lesson status.  
10. —  
11. Steps animate once, no ambient loop.  
12. Failed step named + retry.  
13. Poll status.  
14. Preview.  
15. Process + publish-status APIs. Web preview banners, made into a dedicated mobile surface.

---

## TM-25 Lesson preview

1. **معاينة الدرس**  
2. See student-facing media + visibility.  
3. Class row · processing done · Home failed-lesson (then retry).  
4. ← title · Edit.  
5. Type + status chips · visibility · media well (video / PDF / audio) · note that tutor/quiz appear after processed.  
6. Same media language as Student: Video / File / Audio.  
7. If error: أعد المعالجة. Else none (Edit is secondary).  
8. Edit.  
9. Content type, status, visibility, completion % if any.  
10. Missing media: disabled well + أضف من التعديل.  
11. Media skeleton.  
12. Load error.  
13. Switch source if multiple assets (segmented control, not nested tabs).  
14. Edit or Class.  
15. `/teacher/courses/.../preview`

---

## TM-26 Lesson edit

1. **تعديل الدرس**  
2. Change info, media, visibility.  
3. Preview Edit · class overflow.  
4. ← تعديل.  
5. Title · description · media cards (video / PDF / audio) replace/remove · visible toggle · Save.  
6. Same media cards as Student lesson materials, in teacher-manage mode.  
7. حفظ  
8. Cancel → preview.  
9. Existing assets.  
10. Must keep at least one of video/PDF/audio (web rule).  
11. Saving.  
12. Error + needs-reprocessing toast.  
13. Replace opens picker.  
14. Preview.  
15. `TeacherLessonEditView`

---

## TM-30 Students list

1. **الطلاب**  
2. Who needs me?  
3. Tab Students · Class “كل الطلاب” · Analytics.  
4. ☰ · الطلاب · 🔔  
5. Search → filter chips → student cards.  
6. Identity well (initials) + thin progress.  
7. Open student.  
8. Filters: grade, subject, status.  
9. Name, grade, active/expired, last activity, completion, quiz average.  
10. “ما في طلاب مشتركين بعد” + explain they appear after course access.  
11. Row skeletons.  
12. Retry.  
13. Search debounce 300ms (web).  
14. Student profile.  
15. `/teacher/students` — **cards, not a table**.

```
┌────────────────────────────┐
│ ☰         الطلاب        🔔 │
│ [ بحث ]                    │
│ ريم الحلبي        نشط      │
│ العاشر · آخر نشاط أمس      │
│ ████░░  ٦٨٪   اختبار ٧٢٪   │
└────────────────────────────┘
```

---

## TM-31 Student profile

1. **ملف الطالب**  
2. Who this is, what needs attention, what I can do.  
3. Students list · class cohort.  
4. ← name.  
5. Identity → **احتياج واحد** (derived: expired / inactive / no quiz / low completion) → progress line → quiz line → activity (3 events) → Private notes preview → Parent notes preview → read-only planner peek if present.  
6. Progress visual, not a 5-KPI dashboard.  
7. Contextual: راسل الأهل **or** أضف ملاحظة.  
8. All notes, planner expand.  
9. Profile payload scoped to this teacher’s subjects.  
10. Sections empty independently.  
11. Skeleton blocks.  
12. Retry.  
13. Message creates/opens conversation (web).  
14. Note sheet / parent thread / Messages.  
15. `/teacher/students/:id` — KPI wall flattened.

---

## TM-32 Private note sheet

1. **ملاحظة خاصة**  
2. Teacher-only memory.  
3. Student profile.  
4. Sheet handle. Title ملاحظة خاصة.  
5. Warning: “لا يراها الأهل” → text field → Save.  
6. None (sheet).  
7. حفظ  
8. Delete if editing.  
9. Note body.  
10. Empty composer.  
11. Saving.  
12. Error.  
13. Edit/delete existing from list.  
14. Back to profile.  
15. `/teacher/students/{id}/notes`

---

## TM-33 Parent note thread

1. **ملاحظة للأهل**  
2. Structured parent communication.  
3. Student profile.  
4. ← title.  
5. Status/priority/category chips → body → replies → composer.  
6. Communication visual only on empty.  
7. إرسال / إغلاق المحادثة.  
8. Edit own note.  
9. Category, priority, status, replies.  
10. “ابدأ ملاحظة للأهل”.  
11. Thread skeleton.  
12. Retry.  
13. Close is explicit (web close endpoint).  
14. Profile.  
15. parent-notes API. Categories/priorities exactly as web.

---

## TM-40 Quizzes list

1. **الاختبارات**  
2. What assessment needs action?  
3. Tab Quizzes · Home grade-now.  
4. ☰ · الاختبارات · 🔔  
5. If pending grading exists, a slim banner first → grouped by class → quiz cards. FAB: اختبار جديد.  
6. Assessment visual on empty.  
7. Open quiz (edit if draft, results if published with attempts). FAB create.  
8. Filters: الكل / منشور / مسودة / يحتاج مراجعة. **No AI filter.**  
9. Title, class, published, attempts, average, pending grading.  
10. No classes → اذهب إلى الصفوف. No quizzes → أنشئ اختباراً.  
11. Card skeletons.  
12. Retry.  
13. Overflow: edit, results, delete (confirm). Create asks for class if several (sheet).  
14. Builder or Results.  
15. `/teacher/quizzes` minus fake AI chip.

---

## TM-41 Quiz settings

1. **إعداد الاختبار**  
2. Configure one manual quiz.  
3. Create · card edit.  
4. ← إعداد الاختبار.  
5. Title · description · duration (optional/unlimited) · passing % · **attempts: fixed line “محاولة واحدة لكل طالب”** (not a control) · optional deadline · publish toggle · Save.  
6. Assessment mark.  
7. حفظ ومتابعة للأسئلة  
8. Preview (after questions exist).  
9. Web settings fields only.  
10. —  
11. Saving.  
12. Validation (future deadline).  
13. New quiz (`quizId=new`) stays on settings until first save, then questions unlock (web).  
14. Questions.  
15. `TeacherQuizSettingsCard`

---

## TM-42 Questions + TM-43 Question editor

1. **الأسئلة / سؤال**  
2. Author questions.  
3. After settings save.  
4. ← الأسئلة. Editor is a pushed screen.  
5. List of question cards + أضف سؤالاً. Editor: type (locked when editing existing) · prompt · options/answer · points · explanation · Save.  
6. Check visual.  
7. حفظ السؤال  
8. Delete question. Preview quiz.  
9. Types: اختيار من متعدد · صح/خطأ · إجابة قصيرة · مقالي.  
10. “أضف أول سؤال”.  
11. Saving.  
12. Error.  
13. One question per editor screen (mobile).  
14. Back to list.  
15. Question CRUD APIs.

---

## TM-44 Quiz preview

1. **معاينة الاختبار**  
2. See the student-facing quiz without embedding the live student runner.  
3. Builder preview.  
4. ← معاينة.  
5. Title · one question at a time, read-only.  
6. Same family as Student Quiz, **teacher-attribution, no cyan**.  
7. إغلاق  
8. Next/prev question.  
9. Question text + choices.  
10. No questions → back to add.  
11. —  
12. —  
13. Not scored.  
14. Builder.  
15. `TeacherQuizPreviewDialog`

---

## TM-45 Quiz results

1. **نتائج الاختبار**  
2. Class result + who needs grading.  
3. Quiz card · Home grade-now.  
4. ← نتائج. Edit in overflow.  
5. One insight sentence → 3 numbers max (attempts, average, pending essays) → student rows.  
6. Assessment / progress visual.  
7. Open first pending essay if any, else none.  
8. Edit quiz.  
9. Web results + insights (below passing, in progress, low completion).  
10. “ما في محاولات بعد”.  
11. Skeleton.  
12. Retry.  
13. Row tap → attempt. In-progress rows not reviewable (web).  
14. Attempt screen.  
15. `/teacher/quizzes/.../results`

---

## TM-46 Attempt / essay grade

1. **محاولة الطالب**  
2. Review answers; grade essays.  
3. Results row.  
4. ← student name.  
5. Score summary → per-question answers → if essay pending: points + feedback + Save.  
6. None.  
7. حفظ التصحيح (when needed).  
8. Back.  
9. Attempt detail.  
10. —  
11. Saving grade.  
12. Error.  
13. Single screen, no modal-on-modal.  
14. Results (updated).  
15. attempt detail + grade endpoint.

---

## TM-50 Messages list

1. **الرسائل**  
2. Inbox.  
3. Drawer · Home mission · Student CTA · bell.  
4. ← الرسائل · compose.  
5. Search → conversation rows (name, last line, time, unread).  
6. Person visual on empty.  
7. Open thread. Compose.  
8. Archived toggle (web).  
9. Teacher conversations.  
10. “ابدأ محادثة مع طالب أو ولي أمر”.  
11. Row skeletons.  
12. Retry.  
13. Same product language as Student messages.  
14. Thread / new conversation.  
15. `/teacher/messages`

---

## TM-51 Thread

1. **المحادثة**  
2. Talk.  
3. List · notification · student profile.  
4. ← name.  
5. Optional teacher context header (student/class) → bubbles → composer (text / attach / voice).  
6. Context, not decoration.  
7. Send.  
8. Attach, hold-to-talk if web voice send exists (it does).  
9. Messages + attachments.  
10. Empty thread composer.  
11. Sending.  
12. Failed send retry.  
13. No nested chat settings.  
14. Stays in thread.  
15. Shared messages view + teacher context header.

---

## TM-52 New conversation

1. **محادثة جديدة**  
2. Pick a contact the teacher is allowed to message.  
3. Compose.  
4. ←  
5. Search contacts → rows.  
6. —  
7. Select contact.  
8. Cancel.  
9. `GET /messages/contacts`  
10. No contacts.  
11. Loading.  
12. Error.  
13. Creates conversation then opens thread (web).  
14. Thread.  
15. Teacher conversation create.

---

## TM-53 Notifications sheet

1. **الإشعارات**  
2. Catch up, then jump.  
3. Bell.  
4. Sheet.  
5. Unread first → rows with time.  
6. —  
7. Open item.  
8. Mark read.  
9. `/notifications`  
10. “ما في إشعارات”.  
11. Skeleton.  
12. Retry.  
13. `internal_message` → thread. Other types → owning Teacher screen if mapped.  
14. Destination.  
15. Header bell. Same sheet pattern as Student.

---

## TM-60 Analytics

1. **التحليلات**  
2. What should I review across classes?  
3. Drawer.  
4. ← التحليلات.  
5. **One insight card** (worst class or weakest quiz — sentence + meaning + CTA) → Needs attention list (max 5) → optional compact class ranking (top 3) → stop.  
6. Cyan only if the insight is AI-authored. Most of this rollup is **not** LLM; keep it human/indigo.  
7. CTA on the insight (افتح الصف / افتح النتائج).  
8. Students / Classes links.  
9. Composed dashboard + quiz analytics data.  
10. No classes → أنشئ صفّاً.  
11. Skeleton.  
12. Retry.  
13. Charts are optional and secondary; never first.  
14. Class / Results / Lesson preview / Messages.  
15. `/teacher/analytics` without the table wall.

```
┌────────────────────────────┐
│ ←         التحليلات        │
│ [ simple progress visual ] │
│ الفيزياء تحتاج تثبيتاً     │
│ إكمال الدروس ٤١٪           │
│ [ افتح الصف ]              │
│                            │
│ يحتاج انتباهاً             │
│ ○ اختبار المشتقة — ٨ بانتظار│
│ ○ صف عاشر — اشتراكان ينتهيان│
└────────────────────────────┘
```

---

## TM-70 Account hub

1. **حسابي**  
2. Identity + destinations + logout. No dashboard.  
3. Tab Account.  
4. ☰ · حسابي · 🔔  
5. Identity card (avatar, name, subjects line) → groups:  
   - التعليم: الملف · الصوت · عبارات EduMind · صفحة التدريس (قريباً)  
   - الحساب: الإعدادات  
   - تسجيل الخروج  
6. Portrait, not a stats ring.  
7. None (hub).  
8. Each row.  
9. Profile snapshot.  
10. —  
11. Identity skeleton.  
12. Retry.  
13. Same Account-hub philosophy as Student.  
14. Child screens.  
15. Profile + Settings, grouped.

```
┌────────────────────────────┐
│ ☰         حسابي         🔔 │
│ [avatar] سامر الخطيب       │
│ رياضيات · فيزياء           │
│ الملف الشخصي            ← │
│ الصوت                   ← │
│ عبارات EduMind          ← │
│ صفحة التدريس    قريباً     │
│ الإعدادات               ← │
│ تسجيل الخروج               │
└────────────────────────────┘
```

---

## TM-71 Identity editor

1. **الملف الشخصي**  
2. Edit name, bio, avatar, grades/subjects.  
3. Account · drawer.  
4. ← الملف.  
5. Avatar · name · bio · grade/subject chips · Save / Discard.  
6. Portrait.  
7. حفظ  
8. Discard reloads (web).  
9. Setup profile + teaching fields.  
10. —  
11. Saving.  
12. Error.  
13. Avatar auto-upload on pick (web).  
14. Account.  
15. Profile basic + teaching sections.

---

## TM-72 Voice

1. **الصوت**  
2. Record the voice EduMind clones for lesson TTS.  
3. Account · drawer.  
4. ← الصوت.  
5. Why this matters (one sentence) → sample cards (status) → Record / Upload → Preview phrase.  
6. Waveform. Cyan only while **processing** (machine). Ready samples are success, not cyan.  
7. سجّل عيّنة  
8. Listen, replace, delete, regenerate failed, preview TTS.  
9. Voice profile samples.  
10. “سجّل دقيقة واحدة على الأقل” (web quality rule — show the real constraint from voice constants, do not invent a new duration).  
11. Processing status.  
12. Failed + أعد التوليد.  
13. Consent line before upload (web has voice consent language — keep it).  
14. Stay on Voice.  
15. `/teacher/voice-*` · Profile voice section.

States: empty · pending · processing · awaiting_acceptance · ready · failed.

---

## TM-73 AI phrases

1. **عبارات EduMind**  
2. Set the teacher’s AI encouragement style.  
3. Account.  
4. ←  
5. Short explainer (cyan) → phrase chips/fields from web AI profile options → Save.  
6. Small cyan sparkle — this **is** AI identity.  
7. حفظ  
8. —  
9. `GET/PUT /teacher/setup/ai-profile`  
10. Defaults shown.  
11. Saving.  
12. Error.  
13. Do not add a free-form “persona studio” beyond web fields.  
14. Account.  
15. `TeacherAiProfileSection`

---

## TM-74 Teaching page (locked)

1. **صفحة التدريس**  
2. Honest unavailable state.  
3. Account row.  
4. ←  
5. Visual → “هذه الصفحة قيد التجهيز على الويب” → Back.  
6. Document visual, muted.  
7. حسناً  
8. —  
9. None.  
10. This screen **is** the empty/locked state.  
11. —  
12. —  
13. No fake editor.  
14. Account.  
15. Coming-soon CV on Profile. Portfolio unmounted.

---

## TM-75 Settings

1. **الإعدادات**  
2. Security and devices.  
3. Account · drawer · setup gear.  
4. ← الإعدادات.  
5. Same grouped security rows as Student/shared settings.  
6. —  
7. Row actions.  
8. —  
9. Shared user settings.  
10. —  
11. —  
12. —  
13. No teacher-only preference invention.  
14. Stay / logout from Account.  
15. `/teacher/settings`

---

# F. Web → mobile adaptations

| Web | Mobile | Why |
|-----|--------|-----|
| 7 sidebar items | 5 tabs + drawer | Same as Student shell; quiz/students promoted; messages/analytics demoted from permanent chrome |
| Home KPI wall + activity split | Mission + Today only | Web already computes Action Now; KPIs are labeled non-actionable |
| Class detail 7 KPI cards | One completion line | Next action is Add lesson / open student, not a dashboard |
| Desktop student table | Identity cards | Tables fail on a phone |
| Add lesson dialog | 3-step flow | Giant upload dialog is unusable on mobile |
| Processing as banners on preview | Dedicated processing screen | Teachers on bad networks need a pipeline they can leave and reopen |
| Quiz builder one long page | Settings → questions → editor screen | Web already uses a full-screen question overlay |
| Results overlay grading | Pushed attempt screen | No modal-on-modal |
| Analytics tables/charts first | Insight → meaning → CTA | Preserve data, change hierarchy |
| Messages split pane | List → thread | Native pattern, same actions |
| Bell dropdown | Notifications sheet | Same as Student |
| Profile = one scrolling desktop page | Account hub + child screens | Same as Student Account |
| Orphan `/teacher/lessons` | Search inside Classes / Class | Do not add a sixth tab |
| `الكويزات` | `الاختبارات` | Student product language |
| `Grades` | `الصفوف` | Avoid gradebook confusion |
| Homework API without create UI | Display type only | Do not invent Assignments |
| Coming-soon CV | Locked row | Do not invent a studio |
| Fake AI quiz filter | Omitted | Not a feature |
| Header Classes shortcut | Classes tab | Duplicate chrome removed |
| Projects in old Android Teacher IA | Omitted | Not in Test-2SY |

---

# K. Intentionally different on mobile

1. **Students are a tab** even though web hid them. The data and routes are real; hiding them was a desktop IA mistake.  
2. **Quizzes labeled الاختبارات** to stay in the Student product family. Capability unchanged.  
3. **Messages not a tab.** Capability unchanged; Home + drawer + bell cover the audited urgency.  
4. **No Projects / Gradebook screens.** Older `TC-17/18` and `TC-14` are rejected.  
5. **Homework create is not added.** API-only type remains display-only until web expose it.  
6. **Existing Android Teacher app is not the design source.** It currently includes Projects and a Courses tab naming. After approval it must follow this spec.

---

# L. Unresolved product decisions

1. **Homework create:** Backend can create homework lessons; web create UI cannot. Confirm we keep display-only.  
2. **Lesson AI quiz regenerate:** API exists; web class page does not expose it. Mobile should wait until web surfaces it, unless product explicitly wants the API button.  
3. **Voice minimum duration:** Use the exact constant in `src/constants/teacherVoice.js` at implementation time; do not invent a new number in UI copy until then.  
4. **Public Teaching Page:** Ship locked state until Test-2SY mounts CV/portfolio.  
5. **Notification types besides messages:** Map each `type` to a Teacher screen during implementation from the notifications API — do not invent extra notification products.  
6. **Existing Android Teacher routes** (`teacher/projects`, gradebook, review queue): retire or hide after this design is approved. Out of scope for this phase.  
7. **English LTR tab labels:** Home / Classes / Students / Quizzes / Account. Confirm Quizzes vs Tests wording in EN (`الاختبارات` = Tests on Student). Recommend **Quizzes** only if we must distinguish from student lesson tests; otherwise **Tests** for family consistency. **Decision needed.**

---

## Global states (every important screen)

| State | Treatment |
|-------|-----------|
| Empty | Contextual visual + what this is + one next action |
| Loading | Skeleton of the real hierarchy (not a spinner wall) |
| Error | Sentence + Retry |
| Success | Toast / brief banner, then the updated screen |
| Locked | Teaching Page only |
| Offline | Student offline banner |

---

## Implementation freeze

Do not write Compose, routes, repositories, or mocks from this document until the design is approved.

Approved Student screens stay frozen. Parent is not started.
