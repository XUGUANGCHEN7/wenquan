import test from 'node:test'
import assert from 'node:assert/strict'
import { getToken, saveSession, clearSession, safeReturnTo, guardPage, resumeAfterLogin } from '../src/utils/session.js'
import { request } from '../src/utils/api.js'

const store = new Map()
let sent = []
let navigations = []
globalThis.getCurrentPages = () => [{ route: 'pages/orders/index', options: {} }]
globalThis.uni = {
  getStorageSync: key => store.get(key),
  setStorageSync: (key, value) => store.set(key, value),
  removeStorageSync: key => store.delete(key),
  reLaunch: options => navigations.push(['reLaunch', options.url]),
  switchTab: options => navigations.push(['switchTab', options.url]),
  request: options => { sent.push(options); options.success({ statusCode: 200, data: {} }) },
}

function reset() { store.clear(); sent = []; navigations = []; clearSession() }
const session = token => ({ access_token: token, expires_in: 600, member_id: 'member-real', nickname: '小泉' })

test('unsigned protected requests do not fall back to the shared demo member', async () => {
  reset()
  await assert.rejects(request('/wallet/balance'), error => error.code === 'AUTH_REQUIRED')
  assert.equal(sent.length, 0)
  assert.match(navigations[0][1], /^\/pages\/login\/index/)
})

test('authenticated requests use the actual session and a 401 removes it', async () => {
  reset()
  saveSession(session('real-session-token'))
  await request('/wallet/balance')
  assert.equal(sent[0].header.Authorization, 'Bearer real-session-token')
  uni.request = options => options.success({ statusCode: 401, data: { code: 'AUTH_INVALID' } })
  await assert.rejects(request('/wallet/balance'), error => error.code === 'AUTH_INVALID')
  assert.equal(getToken(), '')
  assert.match(navigations[0][1], /login/)
})

test('a late 401 from an old session does not discard a newly logged-in session', async () => {
  reset()
  saveSession(session('old-session'))
  let complete
  uni.request = options => { complete = options.success }
  const pending = request('/wallet/balance')
  saveSession(session('new-session'))
  complete({ statusCode: 401, data: { code: 'AUTH_INVALID' } })
  await assert.rejects(pending)
  assert.equal(getToken(), 'new-session')
})

test('expired or legacy demo credentials cannot unlock member pages', () => {
  reset()
  store.set('member_token', 'dev-member')
  assert.equal(getToken(), '')
  saveSession(session('expired'))
  store.set('member_expires_at', Date.now() - 1)
  assert.equal(guardPage('/pages/tickets/index'), false)
  assert.equal(getToken(), '')
  assert.equal(guardPage('/pages/login/index'), true)
  assert.equal(guardPage('/pages/account-info/index'), true)
  assert.equal(guardPage('/pages/home/index'), true)
  assert.equal(guardPage('/pages/mine/index'), true)
})

test('explicit development preview session is opt-in and can be cleared', () => {
  reset()
  saveSession({ ...session('dev-member'), mode: 'development' })
  assert.equal(getToken(), 'dev-member')
  clearSession()
  assert.equal(getToken(), '')
})

test('return navigation permits only known member pages and handles tabs', () => {
  reset()
  assert.equal(safeReturnTo('https://evil.example'), '/pages/home/index')
  assert.equal(safeReturnTo('/pages/unknown/index'), '/pages/home/index')
  assert.equal(safeReturnTo('/pages/tickets/index?source=share'), '/pages/tickets/index?source=share')
  assert.equal(safeReturnTo('/pages/orders/detail?id=ord-real'), '/pages/orders/detail?id=ord-real')
  resumeAfterLogin('/pages/orders/index?from=share')
  assert.deepEqual(navigations.pop(), ['switchTab', '/pages/orders/index'])
  resumeAfterLogin('/pages/private-room/index?day=1')
  assert.deepEqual(navigations.pop(), ['reLaunch', '/pages/private-room/index?day=1'])
})

test('the App show event cannot redirect before a deep-linked page is initialized', async () => {
  reset()
  const { memberPageGuard } = await import('../src/utils/session.js')
  globalThis.getCurrentPages = () => []
  assert.equal(typeof memberPageGuard, 'function')
  memberPageGuard.call({ $mpType: 'app' })
  assert.equal(navigations.length, 0)
  globalThis.getCurrentPages = () => [{ route: 'pages/private-room/index', options: { day: '2' } }]
  memberPageGuard.call({ $mpType: 'page' })
  assert.match(navigations[0][1], /returnTo=%2Fpages%2Fprivate-room%2Findex%3Fday%3D2/)
})
