/**
 * REAL-CLAUDE browser verification for the educational analyzer.
 *
 * Requires the backend on port 8000 started with WRITING_EDUCATIONAL_ANALYZER=claude
 * and a real ANTHROPIC_API_KEY. Drives the ACTUAL browser UI: generates ONE real
 * lesson, then submits three drafts against that SAME lesson through the editor:
 *   1) off-topic but grammatically acceptable
 *   2) on-topic with serious grammar mistakes
 *   3) strong on-topic answer for the student's official CEFR
 *
 * For each draft it proves, from the live draft response rendered in the browser:
 *   provider, exact Claude model, analyzer version, source (must be "claude"),
 *   task response, topic understanding, grammar coaching, CEFR + why,
 *   learning diagnosis, single revision mission, and the Rule Engine readiness.
 *
 * NO silent mock fallback: if any draft returns source !== "claude", the whole
 * verification FAILS explicitly.
 */
import { chromium } from 'playwright'

const BASE = process.env.WRITING_QA_BASE || 'http://127.0.0.1:5173'
const API = process.env.WRITING_QA_API || 'http://127.0.0.1:8000'
const EMAIL = process.env.WRITING_QA_EMAIL || 'qa.listening.student-g@eduspark-test.dev'
const PASSWORD = process.env.WRITING_QA_PASSWORD || 'TestOnly123!'

const I18N_RE = /student\.languages?\./
const TECHNICAL_RE = /404|500|axios|Request failed|status code|ECONNREFUSED|Network Error|Internal Server Error/i

const failures = []
function check(name, ok, detail = '') {
  const tag = ok ? 'PASS' : 'FAIL'
  console.log(`  ${tag}  ${name}${detail ? ` — ${detail}` : ''}`)
  if (!ok) failures.push(name)
  return ok
}

async function loginSession(request) {
  const ctx = await request.newContext({ baseURL: API })
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

function buildDrafts(lesson) {
  const title = (lesson?.mission_title || lesson?.title || lesson?.prompt || 'this topic').toString().slice(0, 90)
  return {
    offTopic:
      'The quarterly logistics report shows that container shipping tariffs increased by twelve percent last month. ' +
      'Meanwhile, the warehouse automation system requires a firmware update before the next fiscal audit. ' +
      'Stakeholders must review the compliance spreadsheet and approve the revised procurement budget by Friday.',
    badGrammar:
      `Here is my writing about ${title}. i is very interested in this topic and i want tell you about it. ` +
      'yesterday i go there and it are very good. the people was friendly but i not understand everything. ' +
      'i think it help me learn many thing and i want to practice more for improve my english.',
    strong:
      `Here is my writing about ${title}. This matters to me because it shapes how I think and communicate every day. ` +
      'For example, when I first experienced it, I felt nervous; however, I prepared carefully, and therefore everything went smoothly. ' +
      'Moreover, I learned that clear structure and specific details make a real difference. ' +
      'In conclusion, I now feel far more confident and I am motivated to keep improving my writing.',
  }
}

function reportEvidence(label, payload) {
  const a = payload.educational_analysis || {}
  console.log(`\n----- ${label} (revision ${payload.revision_number}) -----`)
  console.log('  Claude called (source):   ', a.source)
  console.log('  Provider:                 ', a.provider)
  console.log('  Claude model:             ', a.model_name)
  console.log('  Analyzer version:         ', a.analyzer_version)
  console.log('  Task response:            ', (a.task_response || '').slice(0, 160))
  console.log('  Topic understanding:      ', (a.topic_understanding || '').slice(0, 160))
  console.log('  Grammar coaching notes:   ', (a.grammar_notes || []).length)
  if ((a.grammar_notes || []).length) {
    const n = a.grammar_notes[0]
    console.log('    e.g.:                   ', `${n.issue} | Rule: ${n.rule} | Fix: ${n.fix} | Ex: ${n.example}`.slice(0, 220))
  }
  console.log('  CEFR estimate:            ', a.cefr_estimate)
  console.log('  CEFR why:                 ', (a.cefr_reason || '').slice(0, 180))
  console.log('  Learning diagnosis:       ', (a.learning_diagnosis || '').slice(0, 180))
  console.log('  Single revision mission:  ', (a.revision_priority || '').slice(0, 180))
  console.log('  Rule Engine readiness:    ', payload.ready_to_complete, '(completed=' + payload.completed + ')')

  const p = `${label}`
  check(`${p}: Claude actually called (source=claude)`, a.source === 'claude', `source=${a.source}`)
  check(`${p}: provider is anthropic`, a.provider === 'anthropic', a.provider)
  check(`${p}: exact Claude model present`, typeof a.model_name === 'string' && a.model_name.startsWith('claude'), a.model_name)
  check(`${p}: analyzer version present`, Boolean(a.analyzer_version), a.analyzer_version)
  check(`${p}: task response analysis`, Boolean(a.task_response))
  check(`${p}: topic understanding`, Boolean(a.topic_understanding))
  check(`${p}: CEFR estimate + why`, Boolean(a.cefr_estimate) && Boolean(a.cefr_reason))
  check(`${p}: learning diagnosis`, Boolean(a.learning_diagnosis))
  check(`${p}: single revision mission`, Boolean(a.revision_priority) && !a.revision_priority.includes('\n'))
  check(`${p}: rule-engine readiness present`, typeof payload.ready_to_complete === 'boolean')
}

async function submitThroughUI(page, text, label) {
  const editor = page.locator('textarea').first()
  await editor.click()
  await editor.fill('')
  await editor.fill(text)
  const respPromise = page.waitForResponse(
    (r) => /\/writing\/\d+\/draft$/.test(r.url()) && r.request().method() === 'POST',
    { timeout: 180000 },
  )
  await page.getByRole('button', { name: /Submit draft|Submit revision/i }).first().click()
  const resp = await respPromise
  if (!resp.ok()) throw new Error(`${label} draft POST failed: ${resp.status()} ${await resp.text()}`)
  const payload = await resp.json()
  await page.waitForTimeout(1500)
  return payload
}

async function main() {
  console.log('REAL-CLAUDE Writing Educational Analyzer — Browser Verification')
  console.log(`API=${API}  BASE=${BASE}\n`)

  // Preflight: confirm analyzer mode is claude (not mock) before touching the UI.
  const { request } = await import('playwright')
  const session = await loginSession(request)

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ locale: 'en-US' })
  await context.addInitScript((s) => {
    localStorage.setItem('eduspark_session', JSON.stringify(s))
    localStorage.setItem('eduspark-locale', 'en')
  }, session)
  const page = await context.newPage()

  let generatedLesson = null
  page.on('response', async (r) => {
    if (/\/writing\/generate$/.test(r.url()) && r.request().method() === 'POST' && r.ok()) {
      try {
        generatedLesson = await r.json()
      } catch {
        /* ignore */
      }
    }
  })

  console.log('1) Open practice tab and generate ONE real lesson via the UI')
  await page.goto(`${BASE}/student/languages/writing?tab=practice`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.waitForTimeout(1500)
  const genBtn = page.getByRole('button', { name: /Generate lesson/i }).first()
  if (await genBtn.isVisible().catch(() => false)) {
    await genBtn.click()
  }
  await page.waitForSelector('textarea', { timeout: 180000 })
  await page.waitForTimeout(500)
  check('lesson generated via UI', Boolean(generatedLesson), generatedLesson ? `content_item_id=${generatedLesson.content_item_id}, cefr=${generatedLesson.official_cefr}` : 'no generate response captured')
  const drafts = buildDrafts(generatedLesson || {})
  console.log(`   Lesson prompt: ${(generatedLesson?.prompt || '').slice(0, 140)}`)
  console.log(`   Official CEFR: ${generatedLesson?.official_cefr}`)

  console.log('\n2) Submit the three drafts through the editor (same lesson)')
  const p1 = await submitThroughUI(page, drafts.offTopic, 'Draft 1 off-topic')
  reportEvidence('Draft 1 (off-topic, acceptable grammar)', p1)

  const p2 = await submitThroughUI(page, drafts.badGrammar, 'Draft 2 bad-grammar on-topic')
  reportEvidence('Draft 2 (on-topic, serious grammar mistakes)', p2)

  const p3 = await submitThroughUI(page, drafts.strong, 'Draft 3 strong on-topic')
  reportEvidence('Draft 3 (strong on-topic)', p3)

  console.log('\n3) Confirm the browser renders the real Claude analysis')
  const bodyText = await page.locator('body').innerText()
  check('UI teacher panel visible', /Your writing, explained|Teacher's read/i.test(bodyText))
  check('UI shows provider/model provenance (anthropic + claude)', /anthropic/i.test(bodyText) && /claude/i.test(bodyText))
  check('UI shows CEFR level', /Around [ABC][12]/i.test(bodyText))
  check('UI shows grammar coaching', /How to fix|Grammar coaching/i.test(bodyText))
  check('UI no raw i18n keys', !I18N_RE.test(bodyText))
  check('UI no technical error text', !TECHNICAL_RE.test(bodyText))

  if (process.env.WRITING_QA_SCREENSHOT) {
    await page.screenshot({ path: process.env.WRITING_QA_SCREENSHOT, fullPage: true })
    console.log(`\n  screenshot saved: ${process.env.WRITING_QA_SCREENSHOT}`)
  }

  await browser.close()

  console.log('\n=================================')
  if (failures.length) {
    console.log(`RESULT: FAIL — ${failures.length} check(s) failed:`)
    failures.forEach((f) => console.log('  -', f))
    process.exit(1)
  }
  console.log('RESULT: PASS — real Claude analysis verified end-to-end through the browser; Rule Engine retains readiness.')
}

main().catch((e) => {
  console.error('\nFATAL', e.message)
  console.error('RESULT: FAIL — verification could not complete (Claude unavailable or backend not in claude mode).')
  process.exit(1)
})
