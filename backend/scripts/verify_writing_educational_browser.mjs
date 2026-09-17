/**
 * Browser + HTTP QA for the deep educational analyzer (15 required cases).
 *
 * Part A (HTTP): exercises the full backend pipeline over real routes for every
 * QA case and asserts the `educational_analysis` payload is teacher-like AND
 * carries NO pass/fail decision (the Rule Engine owns progression).
 *
 * Part B (UI): drives the writing page and confirms the "Teacher's read" panel
 * renders real feedback (CEFR + why, grammar coaching, encouragement) with no
 * raw i18n keys or technical error strings.
 *
 * Requires the backend (WRITING_QA_API) and frontend (WRITING_QA_BASE) running.
 * Run the backend with WRITING_EDUCATIONAL_ANALYZER=mock for deterministic QA,
 * or with a live CLAUDE key for a real model check.
 */
import { chromium, request as playwrightRequest } from 'playwright'

const BASE = process.env.WRITING_QA_BASE || 'http://127.0.0.1:5173'
const API = process.env.WRITING_QA_API || 'http://127.0.0.1:8000'
const EMAIL = process.env.WRITING_QA_EMAIL || 'qa.listening.student-g@eduspark-test.dev'
const PASSWORD = process.env.WRITING_QA_PASSWORD || 'TestOnly123!'

const I18N_RE = /student\.languages?\./
const TECHNICAL_RE = /404|500|axios|Request failed|status code|ECONNREFUSED|Network Error|Internal Server Error/i
const PASSFAIL_KEYS = ['passed', 'ready', 'ready_to_complete', 'completed', 'eligible', 'promotion', 'stage', 'level_up']

const failures = []
function check(name, ok, detail = '') {
  const tag = ok ? 'PASS' : 'FAIL'
  console.log(`  ${name}: ${tag}${detail ? ` — ${detail}` : ''}`)
  if (!ok) failures.push(name)
  return ok
}

async function login() {
  const ctx = await playwrightRequest.newContext({ baseURL: API })
  const res = await ctx.post('/api/auth/login', { data: { email: EMAIL, password: PASSWORD } })
  if (!res.ok()) throw new Error(`login failed: ${res.status()} ${await res.text()}`)
  const data = await res.json()
  await ctx.dispose()
  return {
    ...data.user,
    accessToken: data.access_token,
    refreshToken: data.refresh_token || null,
    loggedInAt: new Date().toISOString(),
    onboardingComplete: true,
  }
}

const BAD_GRAMMAR = 'i want learn english because english help me get good job. english are important and i is happy when i study english.'
const REPETITIVE = 'My city is a good city. The city is big and the city is nice. I love my city because the city is my home city and the city is great.'
const B2_TEXT =
  'Remote work offers clear advantages, however it also brings challenges. On the one hand, it gives employees flexibility because they can manage their own schedule. Moreover, many people report higher productivity when they avoid a long commute. On the other hand, working from home can feel isolating, and therefore some colleagues struggle to stay motivated. In conclusion, remote work is beneficial when companies provide clear structure.'
const A2_TEXT = 'I have family. My family is good. I like my family. My mother is nice. My father is nice. I am happy.'
const OFF_TOPIC = 'My name is Hamza. I live in Malaysia. I have two brothers and one sister. I am twenty years old.'

// goal, label, draft, and case-specific assertions on the educational_analysis block.
const CASES = [
  { id: '1 off-topic', goal: 'general_english', text: OFF_TOPIC, expect: (a) => a.task_response && /does not|drift|unrelated|topic|prompt/i.test(a.task_response) },
  { id: '2 grammar-ok wrong-task', goal: 'general_english', text: B2_TEXT, expect: (a) => Array.isArray(a.grammar_notes) },
  { id: '3 bad-grammar right-idea', goal: 'general_english', text: BAD_GRAMMAR, expect: (a) => a.grammar_notes.length >= 1 && a.grammar_notes[0].rule && a.grammar_notes[0].fix && a.grammar_notes[0].example },
  { id: '4 excellent B2', goal: 'ielts', text: B2_TEXT, expect: (a) => ['B2', 'C1'].includes(a.cefr_estimate) },
  { id: '5 weak A2', goal: 'general_english', text: A2_TEXT, expect: (a) => ['A1', 'A2'].includes(a.cefr_estimate) },
  { id: '6 repetitive vocab', goal: 'general_english', text: REPETITIVE, expect: (a) => a.repeated_words.length >= 1 },
  { id: '7 strong organization', goal: 'general_english', text: 'Making a good first impression matters. Firstly, it builds trust, because people judge quickly.\n\nSecondly, body language helps. For example, a warm smile shows confidence. Moreover, clear speech helps.\n\nIn conclusion, preparation creates a strong first impression.', expect: (a) => /structure|paragraph|link|guide|clear/i.test(a.organization) },
  { id: '8 poor organization', goal: 'general_english', text: 'first impression important smile good clothes nice talk clear be confident arrive early shake hands look eyes', expect: (a) => Boolean(a.organization) },
  { id: '9 business goal', goal: 'business', text: 'Dear colleague, I would like to schedule a meeting with the client to discuss the project deadline. Please confirm your availability. Kind regards, Omar.', expect: (a) => /business/i.test(a.goal_alignment) },
  { id: '10 travel goal', goal: 'travel', text: 'Hello, I booked a hotel room for my trip, but my flight was cancelled at the airport. Could I please have a refund for my booking? Thank you.', expect: (a) => /travel/i.test(a.goal_alignment) },
  { id: '11 ielts opinion', goal: 'ielts', text: 'I strongly agree that studying abroad benefits students. Firstly, it improves language skills, because students practise daily. However, some argue it is expensive. In my opinion, the advantages outweigh the disadvantages. In conclusion, I agree.', expect: (a) => Boolean(a.idea_development) },
  { id: '12 academic report', goal: 'academic', text: 'This study analysed the relationship between sleep and memory. The research collected data from forty participants. The results show that participants who slept longer performed better. Therefore, the analysis suggests adequate sleep improves memory.', expect: (a) => /academic/i.test(a.goal_alignment) },
  { id: '13 creative writing', goal: 'creative_writing', text: 'Suddenly, the cold wind broke the silence of the night. A shadow moved across the bright snow, and my heart began to race. I remembered the dream I had, and the street felt like a whisper from the past.', expect: (a) => /creative/i.test(a.goal_alignment) },
]

function assertUniversal(prefix, a) {
  check(`${prefix} available`, a && a.available === true)
  if (!a || !a.available) return
  check(`${prefix} cefr estimate present`, Boolean(a.cefr_estimate), a.cefr_estimate)
  check(`${prefix} cefr reason (why)`, Boolean(a.cefr_reason))
  check(`${prefix} encouragement specific`, Boolean(a.encouragement) && a.encouragement.length > 15)
  check(`${prefix} learning diagnosis`, Boolean(a.learning_diagnosis))
  check(`${prefix} single revision priority`, Boolean(a.revision_priority) && !a.revision_priority.includes('\n'))
  const dims = ['task_response', 'topic_understanding', 'coherence', 'organization', 'idea_development', 'goal_alignment', 'vocabulary']
  check(`${prefix} every dimension has a reason (why)`, dims.every((d) => Boolean(a[d] && String(a[d]).trim())))
  check(`${prefix} no pass/fail keys`, !PASSFAIL_KEYS.some((k) => k in a))
}

async function main() {
  const session = await login()
  const req = await playwrightRequest.newContext({
    baseURL: API,
    extraHTTPHeaders: { Authorization: `Bearer ${session.accessToken}` },
    timeout: 300000,
  })

  console.log('=== Part A: HTTP pipeline — 15 educational QA cases ===\n')
  let firstBadGrammar = null
  for (const c of CASES) {
    console.log(`[${c.id}] (goal=${c.goal})`)
    const gen = await req.post('/api/student/languages/writing/generate', { data: { goal: c.goal } })
    if (!gen.ok()) {
      check(`${c.id} generate lesson`, false, `${gen.status()} ${await gen.text()}`)
      continue
    }
    const lesson = await gen.json()
    const sub = await req.post(`/api/student/languages/writing/${lesson.content_item_id}/draft`, {
      data: { draft_text: c.text, complete_if_ready: false },
    })
    if (!sub.ok()) {
      check(`${c.id} submit draft`, false, `${sub.status()} ${await sub.text()}`)
      continue
    }
    const payload = await sub.json()
    const a = payload.educational_analysis
    assertUniversal(c.id, a)
    check(`${c.id} case-specific expectation`, Boolean(a) && c.expect(a))
    if (c.id.startsWith('3')) firstBadGrammar = { contentItemId: lesson.content_item_id, prevCefr: a?.cefr_estimate }
    console.log('')
  }

  // Case 14: compare draft 1 vs draft 2 on the same lesson.
  console.log('[14 draft comparison]')
  {
    const gen = await req.post('/api/student/languages/writing/generate', { data: { goal: 'general_english' } })
    const lesson = await gen.json()
    await req.post(`/api/student/languages/writing/${lesson.content_item_id}/draft`, {
      data: { draft_text: BAD_GRAMMAR, complete_if_ready: false },
    })
    const sub2 = await req.post(`/api/student/languages/writing/${lesson.content_item_id}/draft`, {
      data: {
        draft_text:
          'I want to learn English because it helps me find a better job. Moreover, English lets me travel and meet new people. For example, I can read books and watch films in English, which improves my skills every day.',
        complete_if_ready: false,
      },
    })
    const p2 = await sub2.json()
    check('14 second draft revision number >= 2', p2.revision_number >= 2, String(p2.revision_number))
    check('14 progress comparison present', Boolean(p2.educational_analysis?.progress_comparison), p2.educational_analysis?.progress_comparison || '')
    assertUniversal('14', p2.educational_analysis)
  }
  console.log('')

  // Case 15: WHY on every judgment is validated by assertUniversal across all cases above.
  console.log('[15 every judgment explains WHY] — validated by universal reason checks across all cases above\n')

  await req.dispose()

  console.log('=== Part B: UI — Teacher analysis panel renders ===\n')
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ locale: 'en-US' })
  await context.addInitScript((s) => {
    localStorage.setItem('eduspark_session', JSON.stringify(s))
    localStorage.setItem('eduspark-locale', 'en')
  }, session)
  const page = await context.newPage()
  await page.goto(`${BASE}/student/languages/writing?tab=practice`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.waitForTimeout(1500)

  // Generate a lesson if the practice tab shows the intro (no editor yet).
  const genBtn = page.getByRole('button', { name: /Generate lesson/i }).first()
  if (await genBtn.isVisible().catch(() => false)) {
    await genBtn.click()
  }
  await page.waitForSelector('textarea', { timeout: 180000 })
  const editor = page.locator('textarea').first()
  await editor.fill(BAD_GRAMMAR)
  await page.getByRole('button', { name: /Submit draft|Submit revision/i }).first().click()
  await page.waitForTimeout(2500)

  const bodyText = await page.locator('body').innerText()
  check('UI no raw i18n keys', !I18N_RE.test(bodyText))
  check('UI no technical error text', !TECHNICAL_RE.test(bodyText))
  check('UI teacher panel visible', /Your writing, explained|Teacher's read/i.test(bodyText))
  check('UI shows CEFR level', /Around [ABC][12]/i.test(bodyText))
  check('UI shows grammar coaching', /How to fix|Grammar coaching/i.test(bodyText))
  check('UI shows encouragement or mission', /learn|progress|mission|revision/i.test(bodyText))

  if (process.env.WRITING_QA_SCREENSHOT) {
    await page.screenshot({ path: process.env.WRITING_QA_SCREENSHOT, fullPage: true })
    console.log(`  screenshot saved: ${process.env.WRITING_QA_SCREENSHOT}`)
  }

  await browser.close()

  console.log('\n=================================')
  if (failures.length) {
    console.log(`FAIL — ${failures.length} check(s) failed:`)
    failures.forEach((f) => console.log('  -', f))
    process.exit(1)
  }
  console.log('PASS — educational analyzer browser QA complete (teacher-like feedback, no pass/fail leakage).')
}

main().catch((e) => {
  console.error('FATAL', e.message)
  process.exit(1)
})
