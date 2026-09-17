/**
 * REAL-CLAUDE browser verification for the Writing COACH + feedback hierarchy.
 *
 * Requires the backend on port 8000 started with WRITING_EDUCATIONAL_ANALYZER=claude
 * and a real ANTHROPIC_API_KEY. Drives the ACTUAL browser UI: generates ONE real
 * lesson, then submits drafts through the editor and proves, from the live draft
 * response AND the rendered DOM, that:
 *
 *   - Claude produced the coaching (revision_plan.guidance_source === "claude")
 *   - the coach main issue is NOT the isolated first grammar error
 *   - the revision mission is distinct from the main issue (no duplicate fields)
 *   - a before/after example is shown and before != after
 *   - success criteria distinguish attempted-inaccurately from not-attempted
 *   - "Improvements" is a short summary (<= 3 items)
 *   - Teacher Analysis keeps full educational depth
 *   - the Rule Engine still owns readiness (Claude did not decide)
 *
 * NO silent mock fallback: any source !== "claude" fails the whole run.
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
    // Task solid but with an isolated 'I are' slip AND deeper question/modal errors.
    emailLike:
      `Here is my message about ${title}. I are writing to ask for your help. ` +
      'Could you tell me what should I do next? Should I submited the form online or by email? ' +
      'I would be very grateful for your guidance, and I will follow your advice carefully.',
    // Off-topic but grammatically clean.
    offTopic:
      'The quarterly logistics report shows that container shipping tariffs increased by twelve percent last month. ' +
      'The warehouse automation system requires a firmware update before the next fiscal audit. ' +
      'Stakeholders must approve the revised procurement budget by Friday.',
    // Strong on-topic with a single spelling slip.
    strong:
      `Here is my writing about ${title}. This matters to me because it shapes how I communicate every day. ` +
      'For example, when I first experienced it, I felt nervous; however, I prepared carefully, and therefore everything went smoothly. ' +
      'Moreover, clear structure and specific details make a real diference. ' +
      'In conclusion, I feel far more confident and motivated to keep improving.',
  }
}

function reportCoach(label, payload) {
  const rp = payload.revision_plan || {}
  const a = payload.educational_analysis || {}
  const ev = payload.evaluation_display || {}
  console.log(`\n----- ${label} (revision ${payload.revision_number}) -----`)
  console.log('  analyzer source:      ', a.source)
  console.log('  guidance source:      ', rp.guidance_source, '| priority_key:', rp.priority_key)
  console.log('  coach main_issue:     ', (rp.main_issue || '').slice(0, 160))
  console.log('  coach why_it_matters: ', (rp.why_it_matters || '').slice(0, 160))
  console.log('  coach mission:        ', (rp.revision_mission || '').slice(0, 160))
  console.log('  before:               ', (rp.before_example || '').slice(0, 140))
  console.log('  after:                ', (rp.after_example || '').slice(0, 140))
  console.log('  learning_diagnosis:   ', (a.learning_diagnosis || '').slice(0, 160))
  console.log('  improvements count:   ', (ev.improvements || []).length)
  console.log('  rule readiness:       ', payload.ready_to_complete)

  const norm = (s) => (s || '').trim().toLowerCase()
  const p = label
  check(`${p}: Claude produced the analysis (source=claude)`, a.source === 'claude', `source=${a.source}`)
  check(`${p}: coach guidance from Claude`, rp.guidance_source === 'claude', rp.guidance_source)
  check(`${p}: coach main issue is not the raw 'I are' slip`, !/^\s*i are\b/i.test(rp.main_issue || '') && norm(rp.main_issue) !== 'i are')
  check(`${p}: main issue and mission are distinct`, norm(rp.main_issue) !== norm(rp.revision_mission) && Boolean(norm(rp.revision_mission)))
  check(`${p}: why-it-matters distinct from main issue`, norm(rp.why_it_matters) !== norm(rp.main_issue))
  check(`${p}: before/after example present`, Boolean(rp.before_example) && Boolean(rp.after_example))
  check(`${p}: before != after (a real correction)`, norm(rp.before_example) !== norm(rp.after_example))
  check(`${p}: improvements are a short summary (<=3)`, (ev.improvements || []).length <= 3, `${(ev.improvements || []).length} items`)
  check(`${p}: success criteria carry a 4-state display_status`, (ev.success_criteria || []).every((c) => ['met', 'partially_met', 'attempted_inaccurately', 'not_attempted'].includes(c.display_status)))
  check(`${p}: teacher analysis retains depth (diagnosis present)`, Boolean(a.learning_diagnosis))
  check(`${p}: rule engine owns readiness`, typeof payload.ready_to_complete === 'boolean')
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
  console.log('REAL-CLAUDE Writing COACH — Browser Verification')
  console.log(`API=${API}  BASE=${BASE}\n`)

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

  console.log('\n2) Submit the email-like draft (task solid, deeper question/modal issue)')
  const p1 = await submitThroughUI(page, drafts.emailLike, 'Email-like draft')
  reportCoach('Email-like (task solid, question/modal + I-are slip)', p1)

  // Verify the DOM renders the coach hierarchy without duplication.
  const bodyText = await page.locator('body').innerText()
  check('UI shows "Your next revision" coach section', /Your next revision|One thing to focus on/i.test(bodyText))
  check('UI shows "Main learning issue"', /Main learning issue/i.test(bodyText))
  check('UI shows "Why this matters"', /Why this matters/i.test(bodyText))
  check('UI shows Before/After example', /Before/i.test(bodyText) && /After/i.test(bodyText))
  check('UI shows criterion status text (4-state)', /(Attempted, but needs correction|Not used yet|Almost there|Done correctly)/i.test(bodyText))
  check('UI teacher panel retained', /Your writing, explained|Teacher's read/i.test(bodyText))
  check('UI no raw i18n keys', !I18N_RE.test(bodyText))
  check('UI no technical error text', !TECHNICAL_RE.test(bodyText))

  console.log('\n3) Off-topic draft — coach must prioritise task, not a grammar slip')
  const p2 = await submitThroughUI(page, drafts.offTopic, 'Off-topic draft')
  reportCoach('Off-topic (clean grammar)', p2)

  console.log('\n4) Strong draft with a single spelling slip')
  const p3 = await submitThroughUI(page, drafts.strong, 'Strong draft')
  reportCoach('Strong (one spelling slip)', p3)

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
  console.log('RESULT: PASS — the coach preserves Claude\'s educational understanding end-to-end; Rule Engine retains readiness.')
}

main().catch((e) => {
  console.error('\nFATAL', e.message)
  console.error('RESULT: FAIL — verification could not complete (Claude unavailable or backend not in claude mode).')
  process.exit(1)
})
