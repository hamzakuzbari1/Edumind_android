/**
 * Browser/static S7.5 EVI integration checks.
 * Run: node backend/scripts/verify_speaking_s75_evi_browser.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '../..')

function ok(label, passed, detail = '') {
  const mark = passed ? 'PASS' : 'FAIL'
  console.log(`  [${mark}] ${label}${detail ? ` -- ${detail}` : ''}`)
  return passed
}

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8')
}

function main() {
  console.log('Speaking S7.5 Browser Integration Verification\n')
  const results = []

  const composable = read('src/composables/useLiveConversation.js')
  const api = read('src/api/speakingLive.js')
  const shell = read('src/components/language/LanguageSpeakingLiveShell.vue')
  const en = JSON.parse(read('src/locales/en/student.json'))
  const ar = JSON.parse(read('src/locales/ar/student.json'))
  const backendApi = read('backend/app/api/language_speaking_live.py')

  results.push(ok('1 mic via getUserMedia', composable.includes('getUserMedia')))
  results.push(ok('2 audio streams via audio_input', composable.includes('audio_input')))
  results.push(ok('3 assistant playback handler', composable.includes('audio_output')))
  results.push(ok('4 speaking/listening state visible', shell.includes('student.languages.speaking.live.states')))
  results.push(ok('5 interruption handling', composable.includes('user_interruption')))
  results.push(ok('5b tool_call handling', composable.includes("type === 'tool_call'")))
  results.push(ok('5c tool relay endpoint', api.includes('/speaking/live/tool')))
  results.push(ok('6 completed turn upload endpoint', api.includes('/speaking/live/turn')))
  results.push(ok('7 evaluation response handled', composable.includes('student_session_summary') || composable.includes('turnSummaries')))
  results.push(ok('8 no raw provider errors exposed', !shell.includes('Hume API') && composable.includes('errorMessage')))
  results.push(ok('9 no API key in browser code', !composable.includes('HUME_API_KEY') && !api.includes('HUME_API_KEY')))
  results.push(ok('10 i18n keys present en/ar', !!en.languages?.speaking?.live?.title && !!ar.languages?.speaking?.live?.title))

  results.push(ok('token endpoint uses access_token only', backendApi.includes('access_token') && !backendApi.includes('HUME_SECRET_KEY')))
  results.push(ok('WebSocket uses access_token query', composable.includes('access_token')))

  const passed = results.filter(Boolean).length
  const total = results.length
  console.log(`\nSummary: ${passed}/${total} checks passed`)
  if (passed === total) {
    console.log('SPEAKING S7.5 BROWSER STATIC VERIFICATION PASSED.')
    process.exit(0)
  }
  console.log('SPEAKING S7.5 BROWSER STATIC VERIFICATION FAILED.')
  process.exit(1)
}

main()
