const protectedPages = new Set([
  '/pages/home/index', '/pages/tickets/index', '/pages/private-room/index',
  '/pages/orders/index', '/pages/mine/index', '/pages/wallet/index',
  '/pages/orders/detail', '/pages/wallet/transactions',
  '/pages/member-service/index',
])
const guestPages = new Set(['/pages/home/index', '/pages/mine/index', '/pages/login/index', '/pages/account-info/index', '/pages/member-service/index'])
const tabs = new Set(['/pages/home/index', '/pages/orders/index', '/pages/mine/index'])
let redirecting = false

export function clearSession() {
  for (const key of ['member_token', 'member_expires_at', 'member_profile', 'dev_preview']) uni.removeStorageSync(key)
  redirecting = false
}

export function getToken() {
  const token = uni.getStorageSync('member_token')
  const expires = Number(uni.getStorageSync('member_expires_at'))
  const devPreview = uni.getStorageSync('dev_preview') === true
  if (!token || (token === 'dev-member' && !devPreview) || !Number.isFinite(expires) || expires <= Date.now()) {
    if (token) clearSession()
    return ''
  }
  return token
}

export function saveSession(result) {
  const devPreview = result.mode === 'development'
  uni.setStorageSync('member_token', result.access_token)
  uni.setStorageSync('member_expires_at', Date.now() + result.expires_in * 1000)
  uni.setStorageSync('member_profile', {
    member_id: result.member_id, nickname: result.nickname, phone_masked: result.phone_masked,
  })
  uni.setStorageSync('dev_preview', devPreview)
  redirecting = false
}

export function safeReturnTo(value) {
  if (typeof value !== 'string' || value.length > 1600 || !protectedPages.has(value.split('?')[0])) {
    return '/pages/home/index'
  }
  return value
}

export function currentPage() {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  const page = pages[pages.length - 1]
  if (!page?.route) return '/pages/home/index'
  const query = Object.entries(page.options || {}).map(([key, value]) =>
    `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join('&')
  return '/' + page.route + (query ? '?' + query : '')
}

export function redirectToLogin(target = currentPage()) {
  if (currentPage().split('?')[0] === '/pages/login/index' || redirecting) return
  redirecting = true
  uni.reLaunch({
    url: '/pages/login/index?returnTo=' + encodeURIComponent(safeReturnTo(target)),
    fail() { redirecting = false },
  })
}

export function guardPage(path = currentPage()) {
  const route = path.split('?')[0]
  if (guestPages.has(route)) {
    redirecting = false
    return true
  }
  if (getToken()) return true
  redirectToLogin(path)
  return false
}

export function memberPageGuard() {
  // Global mixins receive App hooks too. Only a Page has its final route/context.
  if (this.$mpType === 'page') guardPage()
}

export function resumeAfterLogin(target) {
  redirecting = false
  const url = safeReturnTo(target)
  if (tabs.has(url.split('?')[0])) uni.switchTab({ url: url.split('?')[0] })
  else uni.reLaunch({ url })
}
