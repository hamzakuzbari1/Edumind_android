# EduSpark Mobile — Design System v1.0
**Paste this file at the top of every Claude Design prompt and into Rork's project knowledge.**

---

## 1. Design brief

**Product:** EduSpark — an Arabic-first AI learning app for Syrian secondary students, their teachers, and their parents.
**Primary audience:** students aged 14–18, on low-end Android (Android 9+, 2–4GB RAM, 720×1600), often on unreliable power and mobile data.
**Secondary audiences:** teachers (30–55, tablet + phone), parents (35–60, low tech-confidence, need clarity over density).
**The app's single job:** make a student open it every day and finish one more thing than they would have alone.

**Anti-brief — what this must NOT look like:**
- Not another blue/indigo edtech dashboard.
- Not a children's app. These are teenagers preparing for the البكالوريا. Playful, not babyish.
- Not a translated Western app with Arabic bolted on. Arabic is the design language; English is the translation.
- No cream-and-serif "premium editorial" look, no near-black-with-acid-green, no stock 3D illustrations.

---

## 2. Signature element — the Progress Spine (المسار)

Every learning surface in the app carries a single continuous vertical rail along the **leading edge** of the screen (right edge in Arabic, left edge in English). Lessons, milestones, and project stages sit on it as **beads**.

- Completed beads: filled Zaytoun, connected by a solid rail.
- Current bead: larger, Barq ring, gently pulsing (respects `prefers-reduced-motion`).
- Locked beads: hollow, hairline rail.

The spine is not decoration — it is the app's information architecture made visible. It is the same object on a course page, a language learning path, and a project milestone board. **It is the one thing users should be able to describe when asked what the app looks like.**

Rule: only one spine per screen. Screens without sequence (settings, messages, profile) have no spine.

---

## 3. Color

Named tokens. Use the names, never raw hex, in prompts and code.

### Core
| Token | Light | Dark | Use |
|---|---|---|---|
| `basalt` | `#101416` | `#101416` | Primary text (light), app background (dark) |
| `zaytoun` | `#146B58` | `#3FA98F` | Primary actions, progress fill, active nav |
| `zaytoun-soft` | `#E4F0EB` | `#16302A` | Primary-tinted surfaces, selected rows |
| `barq` | `#E0A42B` | `#F0B740` | XP, streaks, achievements, celebration only |
| `jouri` | `#B23A5B` | `#D9607F` | AI-generated content marker, tutor identity |
| `hajar-50` | `#F5F7F4` | `#171C1E` | App background (light), card (dark) |
| `hajar-100` | `#E8ECE7` | `#1F2528` | Subtle fill, skeletons |
| `hajar-300` | `#CBD2C9` | `#2C3438` | Borders, dividers |
| `surface` | `#FFFFFF` | `#171C1E` | Cards, sheets |
| `text-muted` | `#5C6763` | `#94A19C` | Secondary text |

### Semantic
| Token | Light | Dark |
|---|---|---|
| `success` | `#1F8A4C` | `#3FBF74` |
| `warning` | `#C97A0E` | `#EDA23A` |
| `danger` | `#C33A3A` | `#EB6A6A` |
| `info` | `#2C6E8F` | `#5AA6C7` |

### Rules
- **Barq is rationed.** It appears on XP gains, streak counters, achievement unlocks, and certificates. Never as a general button color. If Barq is on more than 10% of a screen, remove some.
- **Jouri marks the machine.** Anything Claude generated — a tutor reply, an AI hint, a generated quiz, an AI project review — carries a Jouri hairline or dot. Human-authored content (a teacher's lesson, a parent's note) never does. This is a trust contract with parents, not a style choice.
- **Dark mode is not optional.** Students study at night, often on battery. Dark is a first-class theme, designed alongside light, not derived from it.
- Never use color alone to carry state. Pair with icon or label.

---

## 4. Typography

**UI face — the system stack.** On Android: **Noto Sans Arabic** and **Roboto**, both OS-provided. On iOS later: **SF Arabic** and **SF Pro**. Rationale: zero bundle size on a device floor where every megabyte matters, native text rendering, and free font-scaling support. Declare it as a platform-resolved token (`--font-ui`), never as a named family in a component.

**Display face — IBM Plex Sans Arabic**, bundled, used *only* for brand moments: splash, onboarding carousel headlines, certificates, celebration overlays, empty-state headlines. Roughly 5% of the app's text. This gives EduSpark a typographic signature without paying font weight on every screen. Ship the Arabic and Latin subsets only, variable weight.

**Utility face: IBM Plex Mono** — scores, timers, codes, IDs, and (later) code exercises. Never for prose.

> Practical rule for design and code: if the text is part of the *interface*, it's the system face. If it's part of the *brand*, it's Plex. Never mix them in the same block.

### Scale
| Role | Size / Line-height (AR) | Line-height (EN) | Weight |
|---|---|---|---|
| `display` | 32 / 48 | 32 / 42 | 700 |
| `title-lg` | 24 / 38 | 24 / 32 | 600 |
| `title` | 20 / 32 | 20 / 28 | 600 |
| `body-lg` | 17 / 30 | 17 / 26 | 400 |
| `body` | 15 / 27 | 15 / 23 | 400 |
| `caption` | 13 / 22 | 13 / 18 | 500 |
| `mono` | 15 / 20 | 15 / 20 | 500 |

**Critical:** Arabic needs ~1.6–1.8× line-height where Latin needs 1.35–1.45. Do not use one line-height token for both scripts — the type ramp must switch with the locale. Arabic diacritics and descenders clip otherwise.

**Type-led, not illustration-led.** This app has almost no illustration. The Arabic script itself is the texture: large confident headings, generous leading, restrained weight contrast. This keeps the bundle small and the app fast, and it looks more serious than clip-art — which matters when a parent is deciding whether to pay.

---

## 5. Layout & shape

- **Grid:** 4pt base. Screen gutter 20pt. Card padding 16pt. Section gap 24pt.
- **Radius:** `sm` 12 · `md` 18 · `lg` 26 · `pill` 999. Cards use `md`, sheets use `lg` on top corners only, buttons use `pill`.
- **Elevation:** two levels only, expressed as **tint + hairline**, not shadow. Cheap Android renders soft shadows badly and it costs GPU. Level 1 = `surface` on `hajar-50` + 1px `hajar-300`. Level 2 (sheets, modals) = `surface` + a 1px border and a 6% scrim behind.
- **Touch targets:** 48×48 minimum, always. Students use this on the bus.
- **Bottom-sheet first.** Prefer sheets over full-screen pushes for anything under ~half a screen of content (filters, hints, quick actions). Reachability matters on 6.7" phones.

---

## 5b. Platform conventions — Android first, iOS-safe

The app ships Android first and adds iOS later from the same codebase. Design to Android now, but never in a way that blocks iOS.

- **Bottom tab bar** per role, 5 tabs max, sitting above the gesture bar. Top bar carries title, back, and up to two actions.
- **Hardware back button** must be handled on every screen — but **never as the only way back**. Every screen also has a visible back affordance, because iOS has no hardware back.
- **Bottom sheets** for anything under half a screen: paywall, hints, filters, quick actions, submission composer. Reachability matters on 6.7" phones and sheets are cheap to render.
- **Edge-swipe back must flip in RTL** — in Arabic the gesture starts from the *right* edge. This is the most commonly broken thing in Arabic mobile apps, and Android gets it wrong more often than iOS.
- **Safe areas via `react-native-safe-area-context` from day one**, not `StatusBar.currentHeight`. Notches, punch-holes, and gesture bars vary wildly across OEMs.
- **Ripple feedback** on touchables (Android convention). Use `Pressable` with platform-appropriate feedback so iOS gets opacity instead later.
- **Font scaling** honored to the accessibility sizes. Arabic at 200% is the hardest layout case in the app — test it early.
- **Dark mode follows the system** by default, with a manual override in Settings.

### The device floor

Design and test against a **$100–150 Android phone: 2–3GB RAM, Android 11–12, 720×1600**. Not an emulator, not a flagship. Concrete consequences:

- No soft shadows — tint and hairline borders only (already in §5).
- No blur effects, no continuous animation, no parallax.
- Images served pre-sized from the CDN; never a full-resolution asset scaled down on device.
- Lists virtualized with fixed item heights wherever possible.
- Keep the bundled font set minimal — this is why the UI face is the system font.

---

## 6. Bilingual & RTL rules — non-negotiable

1. **Never use `left`/`right`.** Only `start`/`end` (`marginStart`, `paddingEnd`, `textAlign: 'start'`). Any hardcoded direction is a bug.
2. **Mirror directional icons** (arrows, chevrons, back, send, next). Do **not** mirror: clocks, media play/pause, checkmarks, logos, phone, camera.
3. **Numerals:** Western digits (0–9) are the **default in both locales** — they keep scores, timers, grades, and future code consistent, and Syrian students read them fluently. Arabic-Indic digits (٠–٩) are a user setting, not a default.
4. **Dates:** Gregorian default; Hijri as a togglable secondary line for parents.
5. **Mixed-direction text is normal.** "درس Python الأول" must render correctly. Wrap Latin runs in an isolating span; never concatenate translated strings — use full ICU messages with placeholders.
6. **Arabic plurals have six forms.** Every count string must use ICU `plural` with `zero/one/two/few/many/other`. A `count === 1 ? x : y` ternary is a bug.
7. **Text expansion:** English runs ~20% longer than Arabic in buttons. Design Arabic first, then verify no English label wraps.
8. **Locale is chosen before login** and can be changed in Settings. Switching RTL⇄LTR requires an app reload — design that moment as an intentional, branded 1-second transition, not a crash.
9. **Adding a third language must require zero code changes** — only a new locale bundle and a direction flag. No language names in component logic, ever.

---

## 7. Component inventory

Build these once; every screen composes from them.

**Navigation:** RoleTabBar (5 tabs max), TopBar (title + leading back + up to 2 trailing actions), SegmentedControl, SheetHandle
**Surfaces:** Card, ListRow, SectionHeader, EmptyState, ErrorState, OfflineBanner, SkeletonBlock
**Progress:** **ProgressSpine**, SpineBead, ProgressRing, StreakFlame, XPChip, LevelBar, CEFRBadge
**Input:** TextField (RTL-aware), PasswordField, OTPInput (6-cell), SearchField, Chip, ChipGroup, Stepper, DatePicker, FileDropRow
**Actions:** PrimaryButton, SecondaryButton, GhostButton, IconButton, FAB, DestructiveButton
**AI:** AiMessageBubble (Jouri-marked), UserMessageBubble, TypingIndicator, VoiceRecordButton (press-and-hold, waveform), AudioPlayer, HintTier (locked/unlockable tiers), AiDisclosureFooter
**Assessment:** QuestionCard, ChoiceOption, GapFillInput, AudioQuestion, ScoreDial, ResultBreakdown, RubricRow
**Media:** LessonPlayer (PDF / video / audio in one shell), CameraCaptureSheet, ImageGrid
**Feedback:** Toast, ConfirmDialog, CelebrationOverlay (confetti — level-up & certificates only), PaywallSheet

---

## 8. Motion

Restrained by default. Three sanctioned moments:

1. **Spine fill** — on lesson/milestone completion the rail fills from the previous bead to the current one (400ms, ease-out), then the bead pops (150ms).
2. **XP flight** — the XP chip animates from the completion point to the tab-bar profile icon (300ms).
3. **Celebration** — confetti + Barq wash, reserved for level-up, promotion pass, and certificate issue. Nowhere else.

Everything else: 150–200ms opacity/transform crossfades. Honor reduced-motion by replacing all three with instant state changes. No parallax, no ambient loops — they cost battery.

---

## 9. Voice & copy

- Arabic is **Modern Standard, warm and direct** — not formal-bureaucratic, not slangy. Teachers and parents read the same strings students do.
- Buttons name the outcome: «ابدأ الدرس» / "Start lesson", not «إرسال» / "Submit".
- The same action keeps the same word from button → toast → history.
- Errors say what happened and what to do. No apologies, no "oops".
- Empty states are invitations with one action, never a shrug.
- The AI tutor speaks as a tutor, never claims to be human, and never gives a final answer where a hint would teach more.

---

## 10. Accessibility floor

Contrast 4.5:1 body / 3:1 large. Every interactive element labeled for TalkBack in the active locale. Dynamic type up to 200% without clipping. All state changes announced. Full keyboard/switch traversal on tablet.
