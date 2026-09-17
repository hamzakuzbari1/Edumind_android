import { chromium, request as playwrightRequest } from 'playwright'

const BASE = process.env.LISTENING_QA_BASE || 'http://localhost:5174'
const API = process.env.LISTENING_QA_API || 'http://127.0.0.1:8000'
const PASSWORD = 'TestOnly123!'

const PERSONAS = [
  ['A', 'qa.listening.student-a@eduspark-test.dev'],
  ['B', 'qa.listening.student-b@eduspark-test.dev'],
  ['C', 'qa.listening.student-c@eduspark-test.dev'],
  ['D', 'qa.listening.student-d@eduspark-test.dev'],
  ['E', 'qa.listening.student-e@eduspark-test.dev'],
  ['F', 'qa.listening.student-f@eduspark-test.dev'],
  ['G', 'qa.listening.student-g@eduspark-test.dev'],
]

const TECHNICAL_RE = /404|500|axios|HTTP|Request failed|status code|ECONNREF|Network Error/i
const I18N_RE = /student\.languages?\./

async function login(email) {
  const ctx = await playwrightRequest.newContext({ baseURL: API })
  const res = await ctx.post('/api/auth/login', { data: { email, password: PASSWORD } })
  if (!res.ok()) throw new Error(`login ${email}: ${res.status()}`)
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

async function verifyPersona(browser, key, email) {
  const failures = []
  const session = await login(email)
  const context = await browser.newContext({ locale: 'en-US' })
  await context.addInitScript((s) => {
    localStorage.setItem('eduspark_session', JSON.stringify(s))
    localStorage.setItem('eduspark-locale', 'en')
  }, session)
  const page = await context.newPage()
  const api404 = []

  page.on('response', (res) => {
    const url = res.url()
    if (url.includes('/api/student/languages/listening/next') && res.status() === 404) {
      api404.push(url)
    }
  })

  await page.goto(`${BASE}/student/languages/listening`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.waitForTimeout(1500)

  const bodyText = await page.locator('body').innerText()
  if (I18N_RE.test(bodyText)) failures.push('raw i18n keys visible')
  if (TECHNICAL_RE.test(bodyText)) failures.push(`technical text visible: ${bodyText.slice(0, 120)}`)

  // Journey tab
  await page.getByRole('tab', { name: /journey/i }).click()
  await page.waitForTimeout(800)

  // Practice tab + start
  await page.getByRole('tab', { name: /practice/i }).click()
  await page.waitForTimeout(800)

  const startBtn = page.getByRole('button', { name: /start listening|continue your lesson/i }).first()
  if (await startBtn.isVisible()) {
    await startBtn.click()
    await page.waitForTimeout(10000)
  }

  const afterText = await page.locator('body').innerText()
  if (TECHNICAL_RE.test(afterText)) failures.push('technical text after practice start')
  if (api404.length) failures.push(`listening/next returned 404 (${api404.length}x)`)

  const hasLessonOrFriendly =
    (await page.locator('.result-card, [class*="mission"], .acquisition-card').count()) > 0 ||
    /Preparing your lesson|Almost ready|Unable to prepare|Continue your lesson|Adaptive listening/i.test(afterText)
  if (!hasLessonOrFriendly) failures.push('no lesson UI or friendly acquisition card')

  // Promotion tab smoke
  await page.getByRole('tab', { name: /promotion/i }).click()
  await page.waitForTimeout(1500)
  const promoText = await page.locator('body').innerText()
  if (I18N_RE.test(promoText)) failures.push('i18n keys on promotion tab')

  await context.close()
  return failures
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  const allFailures = []
  for (const [key, email] of PERSONAS) {
    console.log(`\n=== Persona ${key} (${email}) ===`)
    try {
      const fails = await verifyPersona(browser, key, email)
      if (fails.length) {
        allFailures.push(`${key}: ${fails.join('; ')}`)
        console.log('FAIL', fails)
      } else {
        console.log('PASS')
      }
    } catch (e) {
      allFailures.push(`${key}: ${e.message}`)
      console.log('FAIL', e.message)
    }
  }
  await browser.close()
  if (allFailures.length) {
    console.log('\n=== SUMMARY: FAIL ===')
    allFailures.forEach((f) => console.log(f))
    process.exit(1)
  }
  console.log('\n=== SUMMARY: PASS ===')
}

main()
