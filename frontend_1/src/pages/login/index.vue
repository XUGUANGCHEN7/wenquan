<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import config from '../../config'
import { request } from '../../utils/api.js'
import { clearSession, getToken, saveSession, resumeAfterLogin, safeReturnTo } from '../../utils/session.js'

const nickname = ref('')
const consent = ref(false)
const busy = ref(false)
const error = ref('')
const registrationToken = ref('')
let returnTo = '/pages/home/index'

onLoad(async options => {
  let target = options.returnTo || ''
  try { target = decodeURIComponent(target) } catch { target = '' }
  returnTo = safeReturnTo(target)
  if (!getToken()) return
  busy.value = true
  try {
    await request('/members/me')
    resumeAfterLogin(returnTo)
  } catch (reason) {
    // Keep credentials after a network outage; explicit retry can recover the account.
    error.value = reason.message
  } finally { busy.value = false }
})

function complete(result) {
  saveSession(result)
  registrationToken.value = ''
  resumeAfterLogin(returnTo)
}

async function login() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  registrationToken.value = ''
  try {
    const loginResult = await new Promise((resolve, reject) => uni.login({ provider: 'weixin', success: resolve, fail: reject }))
    if (!loginResult.code) throw new Error('未取得微信登录凭证，请重试')
    const result = await request('/auth/wechat/login', { method: 'POST', auth: false, data: { code: loginResult.code } })
    if (result.status === 'AUTHENTICATED') complete(result)
    else if (result.status === 'REGISTER_REQUIRED') registrationToken.value = result.registration_token
    else throw new Error('登录状态异常，请重新登录')
  } catch (reason) {
    error.value = reason.message || '微信登录失败，请重新尝试'
  } finally { busy.value = false }
}

async function register(event) {
  if (busy.value) return
  if (!consent.value) { error.value = '请先阅读并同意手机号使用说明'; return }
  const phoneCode = event.detail?.code
  if (!phoneCode) { error.value = '尚未授权手机号，请重新授权后完成注册'; return }
  if (!registrationToken.value) { error.value = '注册凭证已失效，请重新微信登录'; return }
  busy.value = true
  error.value = ''
  try {
    const result = await request('/auth/wechat/register', {
      method: 'POST', auth: false,
      data: { registration_token: registrationToken.value, phone_code: phoneCode, nickname: nickname.value.trim(), consent: true },
    })
    complete(result)
  } catch (reason) {
    error.value = reason.message || '注册未完成，请重新微信登录后再授权'
    // Both WeChat codes are one-use. A fresh login also recovers a committed registration after a lost response.
    registrationToken.value = ''
  } finally { busy.value = false }
}

async function devLogin() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await request('/auth/dev', { method: 'POST', auth: false, data: { role: 'member' } })
    complete({ ...result, expires_in: 7 * 24 * 60 * 60, nickname: '温泉旅人', phone_masked: '开发模式' })
  } catch (reason) {
    error.value = reason.message || '开发登录不可用，请确认后端已启动'
  } finally { busy.value = false }
}

const updateNickname = event => { nickname.value = event.detail.value }
const showInfo = () => uni.navigateTo({ url: '/pages/account-info/index' })
const goHome = () => uni.switchTab({ url: '/pages/home/index' })
</script>

<template>
  <view class="login-page">
    <view class="brand">泉</view>
    <text class="eyebrow">蜀南温泉</text>
    <text class="title">欢迎开启温泉之旅</text>
    <text class="description">首次使用须验证手机号注册会员，已有会员登录原账户。</text>
    <view class="login-card">
      <template v-if="registrationToken">
        <text class="label">昵称（选填）</text>
        <input type="nickname" :value="nickname" maxlength="80" placeholder="可选择微信昵称，或稍后填写" @input="updateNickname" @blur="updateNickname" />
        <text class="hint">未填写时使用“会员＋手机号后四位”</text>
        <view class="consent">
          <checkbox-group @change="consent = $event.detail.value.includes('agree')">
            <label><checkbox value="agree" :checked="consent" color="#246B61" />我已阅读并同意</label>
          </checkbox-group>
          <text class="link" @tap="showInfo">《手机号使用说明》</text>
        </view>
        <button v-if="consent" class="primary" open-type="getPhoneNumber" :disabled="busy" :loading="busy" @getphonenumber="register">授权手机号并注册</button>
        <button v-else class="primary" @tap="error = '请先阅读并同意手机号使用说明'">授权手机号并注册</button>
        <button class="secondary" :disabled="busy" @tap="login">重新微信登录</button>
      </template>
      <template v-else>
        <button class="primary" :disabled="busy" :loading="busy" @tap="login">微信登录 / 注册</button>
        <text class="hint">无需设置密码；手机号仅在首次注册或补全资料时授权。</text>
        <text class="link info-link" @tap="showInfo">查看手机号使用说明</text>
      </template>
      <text v-if="error" class="error">{{ error }}</text>
      <button class="guest-button" @tap="goHome">免登录进入首页</button>
      <text class="guest-hint">可先浏览；购票、预约、订单和储值需要登录后使用</text>
      <template v-if="config.development">
        <button class="dev-button" :disabled="busy" :loading="busy" @tap="devLogin">开发预览：直接进入</button>
        <text class="dev-hint">仅开发环境使用，登录为后端开发会员，不代表真实微信登录</text>
      </template>
    </view>
  </view>
</template>

<style scoped>
.login-page { min-height:100vh; box-sizing:border-box; padding:100rpx 44rpx 60rpx; background:#f8f6f1; color:#243d34; }
.brand { width:108rpx; height:108rpx; line-height:108rpx; text-align:center; background:#246b61; color:#fffdf9; border-radius:32rpx; font-size:64rpx; font-family:serif; margin-bottom:32rpx; }
.eyebrow,.title,.description,.label,.hint,.error { display:block; }
.eyebrow { font-size:26rpx; letter-spacing:6rpx; color:#56766c; }
.title { font-size:44rpx; line-height:1.6; margin-top:18rpx; font-weight:600; }
.description { font-size:27rpx; line-height:1.8; margin-top:18rpx; color:#5f7069; }
.login-card { margin-top:48rpx; padding:36rpx 30rpx; background:#fffdf9; border:1rpx solid #e6e9e1; border-radius:28rpx; }
.label { font-size:28rpx; margin-bottom:16rpx; }
input { height:88rpx; background:#f3f5ef; border-radius:14rpx; padding:0 20rpx; font-size:27rpx; }
.hint { margin-top:16rpx; font-size:24rpx; line-height:1.8; color:#5f7069; }
.consent { margin:30rpx 0; display:flex; flex-wrap:wrap; align-items:center; font-size:24rpx; line-height:2; }
checkbox { transform:scale(.8); }
.link { color:#246b61; text-decoration:underline; font-size:25rpx; }
.info-link { display:block; margin-top:22rpx; }
.primary { margin-top:20rpx; background:#246b61; color:#fff; font-size:29rpx; border-radius:18rpx; }
.secondary { margin-top:20rpx; color:#246b61; background:transparent; font-size:25rpx; }
.error { margin-top:26rpx; color:#a33e2e; font-size:26rpx; line-height:1.7; overflow-wrap:anywhere; }
.guest-button { margin-top:24rpx; height:82rpx; display:flex; align-items:center; justify-content:center; border:1rpx solid #b9d2ca; border-radius:16rpx; color:#246b61; background:#fffdf9; font-size:26rpx; }
.guest-hint { display:block; margin-top:12rpx; color:#74817b; font-size:22rpx; line-height:1.6; text-align:center; }
.dev-button { margin-top:26rpx; color:#8a6a3c; background:#f4ead9; font-size:24rpx; border-radius:14rpx; }
.dev-hint { display:block; margin-top:12rpx; color:#8a6a3c; font-size:21rpx; line-height:1.6; text-align:center; }
</style>
