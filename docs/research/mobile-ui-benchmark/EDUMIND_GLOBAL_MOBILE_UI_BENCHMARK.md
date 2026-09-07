# EduMind Global Mobile UI Benchmark

Research + design benchmarking only. Android source was not modified.

**Date accessed:** 5 September 2026  
**PDF:** `EDUMIND_GLOBAL_MOBILE_UI_BENCHMARK.pdf`  
**Images:** `images/`  
**Sources:** `sources.md`

## Purpose

Benchmark current mobile UX of Khan Academy, Coursera, Duolingo, and Upwork to inform EduMind **Student Home** — without copying visual identity.

EduMind Home must answer:

1. What should I do now?
2. What needs my attention?
3. What is happening today / this week?
4. What should I continue?
5. How am I progressing?

It must **not** look like a Coursera-style course marketplace.

## Current EduMind Home (read-only)

Existing `StudentHomeScreen` already stacks:

- JourneyHero / المهمة التالية
- اليوم / هذا الأسبوع (planner + routine)
- توصية EduMind
- تابع التعلم
- Progress snapshot + achievements
- لمحة المواد

Student tabs: الرئيسية · روتيني · اللغات · مشاريعي · موادي · حسابي.

This research judges how world-class apps encode the same jobs.

## Versions (iTunes Lookup, 5 Sep 2026)

| App | Version | Store update |
|---|---|---|
| Khan Academy | 8.5.1 | 13 Aug 2026 |
| Coursera | 8.18.1 | 31 Aug 2026 |
| Duolingo | 7.138.0 | 2 Sep 2026 |
| Upwork | 2.12.0 | 26 Aug 2026 |

## Screenshot inventory

| Platform | Official App Store | Official blog | Play HTML extras | Used as production truth |
|---|---:|---:|---:|---|
| Khan Academy | 6 | 0 | 10 (mixed/duplicate) | App Store 01–06 |
| Coursera | 7 | 0 | 10 (mixed) | App Store 01–07, especially 05 |
| Duolingo | 8 | 2022 path + 2026 tabs | 10 (mixed) | App Store + blog Home |
| Upwork | 6 | 0 | 10 (mixed) | App Store 02–06 |

Store creatives are often **marketing-framed** (angled device + slogan) around real UI. Labeled in the PDF.

## Platform notes

### Khan Academy

- Home job = browse subjects, then mastery inside a course.
- Best next-action: Mastery Challenge “Get started”.
- Lesson UX: one problem; video + Up next.
- **Khanmigo chat is not in the native app** (official Help). Activities only in-app v8.0+. Full tutor = mobile web. No fabricated Khanmigo chat screenshot.

### Coursera

- Store sells career marketplace.
- Useful Home analogue: **All Courses / Continue** — percent, module, minutes, Play.
- Learn tab is enrolled programs (official Help). Discovery is a different surface.
- **Avoid** using catalog/certificates as Student Home.

### Duolingo

- Best next-action model: learning **path** + **START**.
- Path documented on official blog (Nov 2022 launch). Still the Home in Feb 2026 core-tabs redesign.
- Streak/XP/leagues are strong; aesthetic is cartoon — borrow principles only.
- App Store 2026 shots emphasize lessons, courses, streak; path Home comes from official blog UI.

### Upwork

- Not education. Use for density, messaging, project status, named AI (Uma) with Insert CTA.
- Do not copy a job feed onto الرئيسية.

## Comparison (short)

See PDF matrix. Headline: Duolingo wins next action; Coursera wins resume anatomy; Khan wins calm hierarchy; Upwork wins professional scanning; **none** own today/week + AI tutor + school routine — that is EduMind’s wedge.

## Recommended Student Home

1. Top bar + greeting  
2. **المهمة التالية** (one primary)  
3. اليوم / هذا الأسبوع  
4. يحتاج انتباهك / توصية EduMind (cyan, one card)  
5. تابع التعلم only if ≠ mission  
6. Progress / XP / streak snapshot  
7. لمحة المواد → full catalog in موادي  

Above the fold: greeting + Next Mission (+ optional first today row). Max two major cards before scroll.

## Compose rules (actionable)

- One `PrimaryButton` per Home.
- `AiMarker` / cyan only on real AI recommendation.
- Amber for streak/XP only.
- Sheets: language, why-this-session, short AI assist.
- Pushed: lesson, quiz, course, chat.
- RTL via layout direction; keep `numeral` helper.
- Do not add a Discover tab onto Home.

## Limitations

- Could not capture live in-app instrumentation (no device farm).
- App Store frames ≠ full-bleed chrome for every screen.
- Duolingo path screenshots from official blog (2022 + 2026), not the 2 Sep 2026 store set.
- Khanmigo native chat UI does not exist to screenshot.
- Play Store scrape included icons and duplicates; deprioritized.
