import { chromium, request as playwrightRequest } from 'playwright'

const BASE = process.env.WRITING_QA_BASE || 'http://127.0.0.1:5173'
const API = process.env.WRITING_QA_API || 'http://127.0.0.1:8000'
const EMAIL = process.env.WRITING_QA_EMAIL || 'qa.listening.student-g@eduspark-test.dev'
const PASSWORD = 'TestOnly123!'

const I18N_RE = /student\.languages?\./
const TECHNICAL_RE = /404|500|axios|HTTP|Request failed|status code|ECONNREF|Network Error|Internal Server Error/i

function extractVocabWords(bodyText) {
  const words = []
  const re = /Include vocabulary:\s*([^\n]+)/gi
  let m
  while ((m = re.exec(bodyText))) {
    m[1].split(/[,;]/).forEach((w) => {
      const t = w.trim().toLowerCase()
      if (t) words.push(t)
    })
  }
  return words
}

function buildDraft(minWords, bodyText = '') {
  const lower = bodyText.toLowerCase()
  const vocab = extractVocabWords(bodyText).join(' ')
  let draft
  if (lower.includes('housekeeping') || lower.includes('available')) {
    draft =
      'Dear hotel manager, Could you please send housekeeping to my room? I would like extra towels because they are not available in the bathroom. ' +
      'Would you please check if room service is available tonight? I must ask politely for housekeeping support and available supplies. Please could you help with this request.'
  } else if (lower.includes('noise') || lower.includes('broken') || lower.includes('maintenance') || lower.includes('room problem')) {
    draft =
      'Dear hotel staff, I am writing because there is a broken air conditioner in my room and there are loud noise problems from the hallway. ' +
      'The maintenance team is not fixing the issue and guests are complaining. I am staying in room 204 and the heating is not working properly. ' +
      'There is broken furniture near the window and there are maintenance delays every day. Please send maintenance to repair the broken unit and reduce the noise.'
  } else if (lower.includes('complain') || lower.includes('refund') || lower.includes('delay')) {
    draft =
      'Dear Customer Service, I am writing to complain about my delayed flight because the boarding was late. ' +
      'I missed my connection and I would like a refund and an apology for this delay. ' +
      'The announcement was unclear and I felt the staff did not help enough. Please respond soon. Regards, Sam.'
  } else if (lower.includes('past simple')) {
    draft =
      'Dear hotel team, I wanted to say thank you for your helpful service during my stay. I appreciated the clean room and the staff helped me when I checked in yesterday. ' +
      'I traveled last week and stayed at your hotel because my friends recommended it. The reception team answered my questions and I felt welcomed throughout the visit. appreciate helpful'
  } else {
    draft =
      'When I arrived at the hotel, there is a friendly reception desk and there are many brochures on the counter. ' +
      'At the reception, the staff checked my reservation and gave me the key to my room. ' +
      'My room was clean and there is a beautiful view from the window. ' +
      'There are several restaurants near the hotel. ' +
      'In conclusion, there are many reasons I would recommend this accommodation because the reception and room were excellent. reception room'
  }
  if (vocab) draft += ` ${vocab}`
  if (lower.includes('modal')) draft += ' could would please must may might '
  if (lower.includes('polite')) draft += ' please could you would you kindly '
  while (draft.split(/\s+/).filter(Boolean).length < Math.max(minWords, 60)) {
    draft += ' Please review this travel writing paragraph carefully.'
  }
  return draft.trim()
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

  console.log('1. Journey tab')
  await page.goto(`${BASE}/student/languages/writing`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.waitForTimeout(1000)
  let bodyText = await page.locator('body').innerText()
  if (I18N_RE.test(bodyText)) failures.push('raw i18n keys on journey')
  if (TECHNICAL_RE.test(bodyText)) failures.push(`technical text on journey: ${bodyText.slice(0, 120)}`)
  if (!/Writing journey|writingJourney|Official level|B1/i.test(bodyText)) failures.push('journey hero not visible')

  await page.getByRole('tab', { name: /journey/i }).click()
  await page.waitForTimeout(500)
  const goalBtn = page.locator('button, [role="button"]').filter({ hasText: /travel|ielts|business|general/i }).first()
  if (await goalBtn.isVisible()) await goalBtn.click()

  console.log('2. Practice + Generate')
  await page.getByRole('tab', { name: /practice/i }).click()
  await page.waitForTimeout(800)
  const generateBtn = page.getByRole('button', { name: /generate lesson/i })
  await generateBtn.waitFor({ state: 'visible', timeout: 30000 })
  await generateBtn.click()
  await page.waitForTimeout(4000)
  bodyText = await page.locator('body').innerText()
  if (!bodyText.includes('Submit draft') && !bodyText.includes('Submit revision')) {
    failures.push('mission/editor not shown after generate')
  }
  const genCall = apiCalls.find((c) => c.url.includes('/writing/generate'))
  if (!genCall || genCall.status !== 200) failures.push(`generate API status ${genCall?.status ?? 'missing'}`)

  const textarea = page.locator('textarea').first()
  await textarea.waitFor({ state: 'visible', timeout: 15000 })

  console.log('3. Bad draft must fail with explanation')
  await textarea.fill('My name are Hamza')
  await page.getByRole('button', { name: /submit draft/i }).click()
  await page.waitForTimeout(3000)
  bodyText = await page.locator('body').innerText()
  const badDraftCall = apiCalls.filter((c) => c.url.includes('/draft') && c.method === 'POST').pop()
  if (!badDraftCall || badDraftCall.status !== 200) failures.push(`bad draft API status ${badDraftCall?.status ?? 'missing'}`)
  if (/Complete lesson/i.test(bodyText)) failures.push('Complete button visible for bad draft')
  if (!/subject-verb|Subject-verb|name is|Grammar|needs_work|Improve|agreement/i.test(bodyText)) {
    failures.push(`bad draft missing grammar explanation: ${bodyText.slice(0, 400)}`)
  }

  console.log('4. Good draft + Evaluation')
  const counterMatch = bodyText.match(/(\d+)\s*\/\s*(\d+)|min[^\d]*(\d+)/i)
  const minWords = counterMatch ? parseInt(counterMatch[1] || counterMatch[3] || '60', 10) : 60
  const draft = buildDraft(minWords, bodyText)
  await textarea.fill(draft)
  await page.getByRole('button', { name: /submit revision|submit draft/i }).click()
  await page.waitForTimeout(3000)
  bodyText = await page.locator('body').innerText()
  if (!/Writing dimensions|dimensions|Grammar|Vocabulary|Success criteria|Coach|Revision/i.test(bodyText)) {
    failures.push('evaluation/coach panel not visible after good submit')
  }
  const draftCall = apiCalls.filter((c) => c.url.includes('/draft') && c.method === 'POST').pop()
  if (!draftCall || draftCall.status !== 200) failures.push(`draft API status ${draftCall?.status ?? 'missing'}`)

  console.log('5. Revision')
  await textarea.fill(`${draft}\n\nTherefore, I revised my paragraph to improve organization and vocabulary throughout the text.`)
  await page.getByRole('button', { name: /submit revision/i }).click()
  await page.waitForTimeout(3000)
  bodyText = await page.locator('body').innerText()
  if (!/revision|Revision/i.test(bodyText)) failures.push('revision turn not reflected in UI')

  console.log('6. Completion')
  let completed = false
  for (let attempt = 0; attempt < 3 && !completed; attempt++) {
    bodyText = await page.locator('body').innerText()
    let draft = buildDraft(minWords, bodyText)
    await textarea.fill(draft)
    const submitLabel = (await page.getByRole('button', { name: /submit revision/i }).isVisible().catch(() => false))
      ? /submit revision/i
      : /submit draft/i
    await page.getByRole('button', { name: submitLabel }).click()
    await page.waitForTimeout(3500)
    const completeBtn = page.getByRole('button', { name: /complete lesson/i })
    if (await completeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await completeBtn.click()
      await page.waitForTimeout(3500)
      bodyText = await page.locator('body').innerText()
      if (/New writing|Lesson complete|lessons completed|progress/i.test(bodyText)) {
        completed = true
        break
      }
    }
    if (attempt < 2) {
      await page.getByRole('button', { name: /generate lesson/i }).click().catch(() => {})
      await page.waitForTimeout(3500)
      bodyText = await page.locator('body').innerText()
      minWords = 60
      await textarea.waitFor({ state: 'visible', timeout: 15000 })
    }
  }
  if (!completed) failures.push('Could not complete lesson after retries (criteria or API)')

  console.log('7. Journey refresh')
  await page.getByRole('tab', { name: /journey/i }).click()
  await page.waitForTimeout(2000)
  const journeyCall = apiCalls.filter((c) => c.url.includes('/writing/journey')).pop()
  if (!journeyCall || journeyCall.status !== 200) failures.push(`journey refresh API ${journeyCall?.status ?? 'missing'}`)
  bodyText = await page.locator('body').innerText()
  if (I18N_RE.test(bodyText)) failures.push('i18n keys after journey refresh')

  await browser.close()

  console.log('\n=== API trace ===')
  apiCalls.forEach((c) => console.log(c.method, c.status, c.url.replace(API, '')))

  if (failures.length) {
    console.log('\n=== FAIL ===')
    failures.forEach((f) => console.log('-', f))
    process.exit(1)
  }
  console.log('\n=== PASS === Writing browser E2E complete')
}

main().catch((e) => {
  console.error('FATAL', e.message)
  process.exit(1)
})
