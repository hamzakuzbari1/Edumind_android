# Rork Project Knowledge — EduSpark Mobile
**Paste this into Rork's project knowledge / custom instructions once. It governs every prompt afterward.**
**Also paste the full contents of `01-EduSpark-Design-System.md` below it.**

---

## What this app is

EduSpark is an Arabic-first AI learning app for Syrian secondary students, their teachers, and their parents. It has an AI tutor grounded in the student's own curriculum, a study planner, gamified progress, hands-on projects, parent monitoring, and an English-learning module.

**Target device:** a $100–150 Android phone — 2–3GB RAM, Android 11–12, 720×1600, on unreliable mobile data and unreliable electricity. Every performance decision is made for that device, not for a flagship.

---

## Stack — do not substitute

| Concern | Choice |
|---|---|
| Framework | React Native + Expo (managed) |
| Routing | **expo-router** (file-based) |
| Server state | **TanStack Query** — never `useEffect` + `fetch` |
| Local UI state | **Zustand** — small stores, no global god-store |
| API | **Generated client only** (see below) |
| i18n | **i18next + react-i18next + expo-localization** |
| Secure storage | **expo-secure-store** for tokens |
| Local database | **expo-sqlite** for the offline layer |
| Forms | **react-hook-form + zod** |
| Icons | **lucide-react-native** |
| Safe areas | **react-native-safe-area-context** |
| Media | expo-image, expo-av / expo-audio, expo-camera, expo-file-system |

**Never add a dependency without checking iOS support.** iOS is a later build target from this same codebase.

---

## Hard rules

These are not preferences. A screen that violates any of them is wrong and needs rework.

### 1. API — generated client only
All API calls go through `src/api/generated`, which is produced from the backend's `openapi.json`. Types live in `src/api/generated/types`.

- **Never write `fetch` or `axios` directly.**
- **Never invent an endpoint, a field name, or a response shape.** If a prompt names an endpoint you can't find in the generated client, stop and say so rather than guessing.
- Wrap every call in a TanStack Query hook in `src/hooks/queries/`.

### 2. Strings — i18next only
- **No literal user-facing text in any component.** Ever.
- Every string added to **both** `src/locales/ar/*.json` and `src/locales/en/*.json` in the same change.
- Namespaces: `common`, `auth`, `student`, `teacher`, `parent`, `projects`, `language`, `messages`, `errors`, `validation`, `settings`.
- **Counts use ICU plurals with all six Arabic forms** (`zero`, `one`, `two`, `few`, `many`, `other`). A `count === 1 ? a : b` ternary is a bug.
- **Never concatenate translated fragments.** Full sentences with placeholders only.

### 3. RTL — logical properties only
- **`left` and `right` are forbidden** in styles. Use `start` / `end`: `marginStart`, `paddingEnd`, `textAlign: 'start'`, `borderStartWidth`.
- Mirror directional icons (arrows, chevrons, back, send, next). Do **not** mirror clocks, play/pause, checkmarks, camera, phone, logos.
- Arabic is the primary layout. Design and verify Arabic first, then check that English labels don't wrap.
- Arabic needs ~1.6–1.8× line-height where Latin needs ~1.4. Use the locale-aware type tokens, never one shared line-height.

### 4. Design tokens only
- All colors, spacing, radii, and type come from `src/theme/tokens.ts`.
- **No raw hex values, no magic numbers, no inline font sizes** in components.
- Every screen supports **light and dark**. Dark is designed, not derived.

### 5. Navigation
- **Handle the Android hardware back button on every screen — but never make it the only way back.** Every screen also has a visible back affordance, because iOS has no hardware back button.
- Bottom sheets for anything under half a screen.
- Use `react-native-safe-area-context`, never `StatusBar.currentHeight`.

### 6. Performance floor
- No soft shadows — tint + hairline borders only.
- No blur, no parallax, no continuous animation.
- All lists virtualized (`FlashList` or `FlatList` with `getItemLayout`).
- Images pre-sized from the CDN; never scale a full-resolution asset on device.
- Respect reduced-motion.

### 7. Every screen ships four states
Loading (skeleton), loaded, empty, and error — plus an offline variant where the screen has cached data. No screen is done with only the happy path.

### 8. Platform code is isolated
Use `Platform.select` or `Component.ios.tsx` / `Component.android.tsx`. **No scattered `if (Platform.OS === 'android')` inside component bodies.**

### 9. Payment flavors
The app builds in two flavors, switched by a `PAYMENT_MODE` constant:
- **`direct`** (APK, primary Syrian channel): local payment rails, may link out to the web portal checkout.
- **`play`** (Google Play): Google Play Billing only. **All external payment links must be absent from this build** — including any text that mentions another way to pay.

Every payment surface must check this flag. Getting it wrong is a Play policy violation.

### 10. Reuse before creating
Check `src/components/` before creating anything. If an equivalent component exists, use it and extend it rather than making a near-duplicate. The app has one `Card`, one `ListRow`, one `PrimaryButton`.

---

## Project structure

```
app/                          expo-router routes
  (auth)/                     login, register, verify, 2fa, reset
  (student)/                  student tabs + nested routes
  (teacher)/                  teacher tabs
  (parent)/                   parent tabs
  _layout.tsx                 root: locale bootstrap, theme, query client
src/
  api/generated/              GENERATED — never edit by hand
  components/
    ui/                       Card, ListRow, PrimaryButton, EmptyState, ...
    progress/                 ProgressSpine, SpineBead, XPChip, StreakFlame
    ai/                       AiMessageBubble, VoiceRecordButton, HintTier
    assessment/               QuestionCard, ChoiceOption, ScoreDial
  hooks/queries/              TanStack Query hooks, one file per domain
  stores/                     Zustand stores
  theme/                      tokens.ts, light.ts, dark.ts, typography.ts
  locales/ar/  locales/en/    i18next bundles
  lib/                        offline sync, secure storage, formatters
```

---

## The Progress Spine

The app's signature element: a continuous vertical rail on the **leading edge** (right in Arabic, left in English) of every learning screen, with lessons, milestones, and project stages as beads.

- Completed beads: filled `zaytoun`, solid rail between them.
- Current bead: larger, `barq` ring, gentle pulse (disabled under reduced-motion).
- Locked beads: hollow, hairline rail.

It is the same component on a course page, a language learning path, and a project milestone board. **One spine per screen maximum.** Screens without sequence (settings, messages, profile) have no spine.

---

## Screen prompt template

Every screen prompt I give you will follow this shape. If any part is missing, ask for it rather than guessing.

```
Build screen <ID · Name> at <exact file path>.

Data:      <exact functions from src/api/generated>
Behaviour: <navigation targets, actions, side effects>
States:    <loading / empty / error / offline specifics>
Strings:   t('<namespace>:<prefix>.*') — add keys to both ar and en
Layout:    <reference to the attached design image>
Reuse:     <named existing components>
```

---

## What you build, and what you don't

**You build:** screens, navigation, forms, lists, component composition, wiring to the generated query hooks, theming, translation scaffolding.

**You do not build** (these are handled separately in Claude Code — do not attempt them, and say so if asked):
- The offline sync engine and SQLite schema
- Audio recording and the live-conversation WebSocket
- Push notification registration and handling
- The in-app updater
- Payment flavor logic beyond reading the flag
- Anything touching native modules

If a prompt asks for one of these, build the UI and stub the logic behind a clearly named interface.
