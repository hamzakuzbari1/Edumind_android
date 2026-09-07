# EduMind Student Mobile — Visual Design Prototype

Design-only. No Android / Compose / backend code was changed.

Open the interactive prototype: [`prototype/index.html`](prototype/index.html)

---

## 1. Design rationale

EduMind Home answers **three questions in 1–2 seconds**, visually:

1. What should I do now? → **ابدأ من هون** (the only dominant card)
2. What do I have today? → **open 3-item timeline**
3. What should I review? → **خلينا نراجع هاد**

Rule: the image explains, the text names, the button continues.

Progress is one compact row. No subject catalog on Home.

The product story on every screen is: *see the state → one next action*.

Identity is EduMind, not a clone:

| Token | Use |
|---|---|
| Indigo `#6366F1` | Primary CTA, active nav, course progress |
| Cyan `#0E7490` | **AI-authored content only** (hairline + sparkle). Trust contract from `Color.kt` |
| Amber `#B45309` | XP, streak, badges — rationed |
| Success `#047857` | Completed / correct |
| Science `#0369A1` | Physics / biology identity — **not cyan** |
| Language `#7C3AED` | Language skill identity |

Arabic UI is first-class: RTL, Cairo, Eastern-Arabic digits, LTR isolation for formulas and English labels.

---

## 2. Final Student Home design

Hierarchy, top → bottom:

```
App bar (menu · EduMind · bell)
صباح الخير، رنا / جاهزة نكمّل؟
ابدأ من هون          ← only dominant card
Today — open timeline, 3 items + عرض يومي
خلينا نراجع هاد      ← one guidance card
Compact progress row (تقدمك · أيام · XP · اختبار)
موادي →
Bottom nav
```

Above the fold: greeting + ابدأ من هون + the start of Today.

---

## 3. Interactive prototype

File: `docs/design/student-frontend-v2/prototype/index.html`

How to use:

- Click **Next Mission** → Lesson
- **EduMind لاحظ** → Review / Quiz
- **Today → Planner**
- **Continue Learning** → Course
- Lesson → **AI Tutor** or **Quiz**
- Quiz (4 questions, tap an answer) → Result
- Bottom nav → Home / Routine / Language / Projects / Courses / Account
- Left rail lists all 13 screens
- `←` back · `R` replay motion

---

## 4. All designed screens

Every screen is captured full-length (no cropping) in `screens/`, and collected
page-by-page in `EDUMIND_STUDENT_FRONTEND_V2_SCREENS.pdf`.

| # | Screen | File |
|---|---|---|
| 1 | Student Home | `screens/01-student-home.png` |
| 2 | My Courses | `screens/02-my-courses.png` |
| 3 | Course Detail | `screens/03-course-detail.png` |
| 4 | Lesson | `screens/04-lesson.png` |
| 5 | AI Tutor | `screens/05-ai-tutor.png` |
| 6 | Quiz | `screens/06-quiz.png` |
| 7 | Quiz Results | `screens/07-quiz-result.png` |
| 8 | Planner | `screens/08-planner.png` |
| 9 | Routine | `screens/09-routine.png` |
| 10 | Language Home | `screens/10-language-home.png` |
| 11 | Projects | `screens/11-projects.png` |
| 12 | Achievements | `screens/12-achievements.png` |
| 13 | Account | `screens/13-account.png` |

Drawer is visually polished only. Nav architecture is unchanged.

Interaction coverage was verified by driving the prototype in headless Chrome:
hero → lesson, inline practice feedback, lesson → quiz, four quiz answers →
result ring, all six bottom-nav destinations, drawer open/close, and the tutor
quick-reply chips — 22 checks, no console errors.

---

## 5. Visual asset strategy

No stock photos. Every image is a **vector illustration that carries meaning**.

| Context | Drawing |
|---|---|
| Physics / Next Mission | Rotating disc + ω |
| Mathematics | Parabola + roots + Δ |
| Biology | Cell (membrane / nucleus) |
| Language | Conversation bubbles |
| Listening | Waveform |
| Reading | Article page |
| Writing | Pen + ruled lines |
| Vocabulary | Word-specific: handshake / leaf / bulb |
| Lesson example | One revolution in 4 seconds (matches the worked example) |
| Language journey | RTL path: done → current → locked |
| Projects | Layered boards + milestone flag |
| Achievements | Badge tiles (flame, shield, medal, crown, target) |
| Teacher | Initial avatar, not a photo |
| AI | Cyan sparkle + cyan hairline — never on human-authored cards |

Placeholders are production-intent: the same SVGs can ship as Compose `ImageVector` / raw resources.

---

## 6. Animation / motion strategy

Motion explains state. It never entertains.

| Motion | Where | Intent |
|---|---|---|
| Staggered rise (52ms) | Every screen enter | Hierarchy appears in reading order |
| Progress bars / rings scale in | Home, Course, Result | Value is already in the markup (static-truthful); motion only reveals it |
| Next Mission CTA 1.5px breathe | Home, Language hero | One obvious next action |
| Timeline line draws top → bottom | Today, Routine, Course journey, Project milestones | Sequence, not a list |
| Quiz option: green settle / red shake | Quiz, lesson practice | Instant feedback |
| Incorrect → formula card | Quiz + Tutor | Transition from error to explanation |
| AI sparkle (slow 3.4s) | AI cards only | Machine-authored marker |
| Sheet / drawer slide | Drawer | Standard mobile chrome |
| Confetti (5 dots, once) | Quiz result | Quiet celebration |
| XP / score count-up | Progress, Result | Reward without bounce |

Forbidden: infinite bounce, giant glow, rainbow motion, looping hero animation.

---

## 7. What was borrowed conceptually

**Khan Academy**
- Calm hierarchy and whitespace
- Lesson as concept → example → practice, not a wall of text
- Locked / unlocked journey nodes

**Coursera**
- Continue Learning anatomy: cover + progress + duration + next step
- Course progress as ring + lesson count + last score
- One current-lesson spotlight above the full journey

**Duolingo**
- One obvious next action (hero CTA)
- Visual progress (path, rings, streak week)
- Low decision fatigue (Home does not open a catalogue)
- Quiz = one question at a time

**Upwork**
- Compact status cards (Planner blocks, Account rows)
- Scannable metadata (time · status · conflict)
- Professional density — not childish gamification

---

## 8. What was intentionally NOT copied

| Not copied | Why |
|---|---|
| Duolingo green mascot / cartoon world | EduMind stays professional; amber is rationed |
| Duolingo hearts / lives | Learning system, not a game over |
| Coursera marketplace grid on Home | Home is a mission board |
| Khan Academy left-rail web IA | Bottom nav stays as specified |
| Upwork job-feed chrome | Not a freelance marketplace |
| Generic chatbot on Home | AI is one recommendation + a contextual Tutor |
| Stock photography | Subject drawings only |
| Cyan on science cards | Cyan = AI trust contract |

---

## 9. Files created

```
docs/design/student-frontend-v2/
  prototype/index.html                        ← interactive prototype (single file)
  DESIGN.md                                   ← this document
  screens/01…13-*.png                         ← full-length screen captures
  EDUMIND_STUDENT_FRONTEND_V2_SCREENS.pdf     ← 14-page review sheet (cover + 13 screens)
```

Android source was not modified. The prototype is one self-contained HTML file:
no build step, no dependencies, no network calls except the optional Cairo web
font fallback. Every illustration is inline SVG, so each one can ship later as a
Compose `ImageVector` or a vector drawable without redrawing it.

---

## 10. Screens to review first

Review in this order — each one locks architecture for the screens after it:

1. **Student Home** — if the hero / today / attention / AI split is wrong, everything else waits
2. **Lesson** — visual learning blocks (this is the product)
3. **AI Tutor** — rich cards, not a generic chat
4. **Quiz → Result** — one question, then one next action
5. **Course Detail** — journey, not a row list
6. Language / Planner / Projects — after the core loop is approved

Then STOP. Implementation starts only after design approval.

---

## Home refinement (this pass)

Only Student Home changed. Other screens are unchanged.

### Before → After

| Before | After |
|---|---|
| 7 competing sections of similar weight | 3 jobs: Do now / Know now / See progress |
| Next Mission was a text card with a watermark drawing | Illustration is its own visual well; title + one CTA follow |
| Today sat inside a dashboard card + color legend | Open timeline: time, title, icon. 3 items. رابط «عرض المخطط» |
| Needs Attention **and** EduMind recommendation | One cyan card: المشكلة → السبب → الإجراء |
| Continue Learning repeated a full course card | Biology only, as a small “تابع أيضاً” row — Physics is already the mission |
| Progress was a 3-block analytics card | One tappable row: مستوى ٤ · ٧ أيام · ٣٤٠ XP · ٨٢٪ |
| Subjects were 3 course-like tiles | 3 thin percent rows + عرض موادي |

### Removed
- Today card chrome, duration chips, color legend
- Separate «يحتاج متابعة» card
- Separate «EduMind يقترح» card + full-width button
- Teacher name and extra chips on the hero
- Week-dot strip, quiz sparkline, XP leftover copy
- Subject snapshot tiles
- Infinite CTA pulse on Home

### Merged
Needs Attention + Smart Recommendation → **EduMind لاحظ**
Visual: parabola + down-trend spark + «٣ أخطاء» + «مراجعة سريعة · ١٠ دقائق»

### Visually dominant
**Next Mission.** Nothing else above the fold competes with it.

### Motion (Home only)
- Hero enters with a short scale/rise (once)
- CTA fades in after the hero, no loop
- Today items stagger in along the line
- Guidance card eases from a cyan wash to white
- Progress bar / ring / XP count still animate to value
- Press scale on tappable cards — unchanged

### Prototype path
`docs/design/student-frontend-v2/prototype/index.html`

---

## Student screens refinement (Home frozen)

Student Home was **not modified**. Greeting → ابدأ من هون → اليوم → خلينا نراجع هاد → compact progress → bottom nav remain exactly as approved.

The other 12 screens were refined to the same rule: **image explains, text names, action continues**.

| Screen | Before | After |
|---|---|---|
| My Courses | LMS cards: long titles, status chips, next-lesson metadata | Visual + name + teacher + progress + one CTA. Locked = visual + مقفلة + اشترك |
| Course Detail | Teacher card + 3-stat ring + current lesson + journey + AI note | Cover → name/teacher → one bar → **كمّل من هون** hero → visual journey |
| Lesson | Mini-PDF: concept + formula + example + video + practice + help | One idea per step: مفهوم → مثال → جرب → تحقق → التالي. `٢ / ٥` |
| AI Tutor | Short paragraph + diagram + tags | ليش؟ → diagram → one sentence → formula → 3 chips |
| Quiz | Strong; long formula feedback | Same one-question structure. Correct = green. Wrong = correct choice + one-line reason → التالي |
| Results | Score + 3 topic bars + XP + two extra buttons | Score → 3 صحيحة / 1 خطأ → أصعب نقطة → راجعها ١٠ دقائق |
| Planner | Full week chart + 4 dated blocks + conflict + AI | Compact week → **اليوم** timeline → غداً secondary → one AI card |
| Routine | Approved structure | Spacing, current-task pulse once, CTAs: ابدأ / أكمل / تم |
| Language | Journey + hero + 4 analytic skill tiles + vocab + grammar | Mission hero + 4 skill shortcuts + A2 → B1. Stop. |
| Projects | Status/team/dates competing with cover | Solar cover → title → progress → current milestone → journey → compact others |
| Achievements | Next badge was a small row | Large next-badge art, 6/10, progress. Level + streak kept |
| Account | Identity + 3 dashboard numbers + Plus promo | Clear identity header + grouped rows. Not a dashboard |

Nav unchanged: الرئيسية / روتيني / اللغات / مشاريعي / موادي / حسابي.
