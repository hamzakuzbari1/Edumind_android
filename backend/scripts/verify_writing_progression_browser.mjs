import { chromium, request as playwrightRequest } from 'playwright'

const BASE = process.env.WRITING_QA_BASE || 'http://127.0.0.1:5173'
const API = process.env.WRITING_QA_API || 'http://127.0.0.1:8000'
const EMAIL = process.env.WRITING_QA_EMAIL || 'qa.listening.student-g@eduspark-test.dev'
const PASSWORD = 'TestOnly123!'

const I18N_RE = /student\.languages?\./
const TECHNICAL_RE = /404|500|axios|HTTP|Request failed|status code|ECONNREFUSED|Network Error|Internal Server Error/i

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

async function main() {
  const failures = []
  const apiCalls = []
  const session = await login()
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ locale: 'en-US' })
  await context.addInitScript((s) => {
    localStorage.setItem('eduspark_session', JSON.stringify(s))
    localStorage.setItem('eduspark-locale', 'en')
  }, session)
  const page = await context.newPage()

  page.on('response', (res) => {
    const url = res.url()
    if (url.includes('/api/student/languages/writing')) {
      apiCalls.push({ url, status: res.status(), method: res.request().method() })
    }
  })

  console.log('1. Journey tab — progression fields')
  await page.goto(`${BASE}/student/languages/writing`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.waitForTimeout(1500)
  let bodyText = await page.locator('body').innerText()
  if (I18N_RE.test(bodyText)) failures.push('raw i18n keys on journey')
  if (TECHNICAL_RE.test(bodyText)) failures.push(`technical text on journey: ${bodyText.slice(0, 120)}`)
  if (!/Writing journey|Official level|Learning stage|Readiness/i.test(bodyText)) {
    failures.push('journey hero missing stage/readiness fields')
  }

  const journeyCall = apiCalls.find((c) => c.url.includes('/writing/journey'))
  if (!journeyCall || journeyCall.status !== 200) failures.push(`journey API status ${journeyCall?.status ?? 'missing'}`)

  console.log('2. Promotion tab')
  await page.getByRole('tab', { name: /promotion/i }).click()
  await page.waitForTimeout(2000)
  bodyText = await page.locator('body').innerText()
  if (I18N_RE.test(bodyText)) failures.push('raw i18n keys on promotion tab')
  if (!/Promotion|readiness|Blockers|WPA|Official CEFR/i.test(bodyText)) {
    failures.push('promotion tab content not visible')
  }

  const statusCall = apiCalls.find((c) => c.url.includes('/writing/promotion-test/status'))
  if (!statusCall || statusCall.status !== 200) {
    failures.push(`promotion status API ${statusCall?.status ?? 'missing'}`)
  }

  console.log('3. API journey payload check')
  const req = await playwrightRequest.newContext({
    baseURL: API,
    extraHTTPHeaders: { Authorization: `Bearer ${session.accessToken}` },
  })
  const journeyRes = await req.get('/api/student/languages/writing/journey')
  if (!journeyRes.ok()) failures.push(`direct journey API ${journeyRes.status()}`)
  else {
    const journey = await journeyRes.json()
    for (const field of [
      'learning_stage',
      'readiness_score',
      'readiness_band',
      'primary_blockers',
      'estimated_lessons_remaining',
      'promotion_target',
      'can_start_wpa',
    ]) {
      if (!(field in journey)) failures.push(`journey missing field ${field}`)
    }
  }

  const promoRes = await req.get('/api/student/languages/writing/promotion-test/status')
  if (!promoRes.ok()) failures.push(`direct promotion status API ${promoRes.status()}`)
  else {
    const promo = await promoRes.json()
    if (!promo.eligibility || !promo.readiness) failures.push('promotion status missing eligibility/readiness')
  }
  await req.dispose()

  await browser.close()

  console.log('\n=== API trace ===')
  apiCalls.forEach((c) => console.log(c.method, c.status, c.url.replace(API, '')))

  if (failures.length) {
    console.log('\n=== FAIL ===')
    failures.forEach((f) => console.log('-', f))
    process.exit(1)
  }
  console.log('\n=== PASS === Writing progression browser verification complete')
}

main().catch((e) => {
  console.error('FATAL', e.message)
  process.exit(1)
})
