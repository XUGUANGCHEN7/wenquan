<script setup>
import { ref } from "vue"
import { onShow, onHide } from "@dcloudio/uni-app"
import config from "../../config"
import MemberEntryGrid from "../../components/MemberEntryGrid.vue"
import { getToken, saveSession } from "../../utils/session.js"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const loggedIn = ref(false)
const profile = ref(null)
const balance = ref(null)
const loading = ref(false)
const profileError = ref("")
const balanceError = ref("")
const devBusy = ref(false)
const loginError = ref("")
let generation = 0
const orderEntries = [
  { key: "TICKET", label: "门票订单", icon: "file" },
  { key: "PRIVATE", label: "私汤预约", icon: "time-line" },
  { key: "RECHARGE", label: "储值记录", icon: "history" },
  { key: "REFUND", label: "退款记录", icon: "history" },
]
const serviceEntries = [
  { key: "profile", label: "个人信息", icon: "user" },
  { key: "security", label: "账户安全", icon: "lock" },
  { key: "contact", label: "联系客服", icon: "phone" },
  { key: "notice", label: "预约须知", icon: "question-circle" },
  { key: "about", label: "关于我们", icon: "info-circle" },
]
onShow(loadProfile)
onHide(() => { generation++ })
async function loadProfile() {
  const version = ++generation
  const token = getToken()
  loggedIn.value = !!token
  profile.value = null
  balance.value = null
  profileError.value = ""
  balanceError.value = ""
  loading.value = false
  if (!token) return
  loading.value = true
  const results = await Promise.allSettled([request("/members/me"), request("/wallet/balance")])
  if (version !== generation) return
  if (token !== getToken()) { loggedIn.value = false; loading.value = false; return }
  const [member, wallet] = results
  if (member.status === "fulfilled") profile.value = member.value
  else profileError.value = member.reason.message || "会员信息加载失败"
  if (wallet.status === "fulfilled" && Number.isInteger(wallet.value.available_cents)) balance.value = formatMoney(wallet.value.available_cents)
  else balanceError.value = wallet.status === "rejected" ? wallet.reason.message : "余额数据暂不可用"
  loading.value = false
}
function goLogin(target = "/pages/mine/index") {
  uni.navigateTo({ url: "/pages/login/index?returnTo=" + encodeURIComponent(target) })
}
function goOrders(filter = "ALL") {
  uni.setStorageSync("member_order_filter", filter)
  if (!getToken()) { goLogin("/pages/orders/index"); return }
  uni.switchTab({ url: "/pages/orders/index" })
}
function goWallet(entries = false) {
  const url = entries ? "/pages/wallet/transactions" : "/pages/wallet/index"
  if (!getToken()) { goLogin(url); return }
  uni.navigateTo({ url })
}
function goService(key) {
  const url = "/pages/member-service/index?section=" + key
  if (["profile", "security"].includes(key) && !getToken()) { goLogin(url); return }
  uni.navigateTo({ url })
}
async function devLogin() {
  if (devBusy.value) return
  devBusy.value = true
  loginError.value = ""
  try {
    const result = await request("/auth/dev", { method: "POST", auth: false, data: { role: "member" } })
    saveSession({ ...result, expires_in: 7 * 24 * 60 * 60, nickname: "温泉旅人", phone_masked: "开发模式" })
    await loadProfile()
  } catch (error) { loginError.value = error.message || "开发预览登录失败"; showError(error) }
  finally { devBusy.value = false }
}
</script>
<template>
  <view class="page mine-page">
    <view class="member-header">
      <image class="member-header-bg" src="/static/mine/member-header.jpg" mode="aspectFill" />
      <view class="member-header-shade" />
      <text class="member-brand">♨ 蜀南温泉</text>
      <view class="member-profile" @tap="loggedIn ? goService('profile') : goLogin()">
        <image class="member-avatar" :src="profile?.avatar_url || '/static/mine/default-avatar.png'" mode="aspectFill" />
        <view class="member-profile-copy">
          <view class="member-name-row"><text class="member-name">{{ loggedIn ? loading ? '正在读取会员信息…' : profile?.nickname || '会员' : '欢迎来到蜀南温泉' }}</text><text v-if="loggedIn" class="member-badge">会员</text></view>
          <text class="member-welcome">{{ loggedIn ? '欢迎回来，畅享蜀南温泉服务' : '登录后享受会员服务' }}</text>
        </view>
        <text class="profile-arrow">›</text>
      </view>
    </view>
    <view class="mine-content">
      <view v-if="loggedIn" class="member-balance-card">
        <image class="balance-background" src="/static/mine/member-balance.jpg" mode="aspectFill" />
        <view class="balance-content">
          <view class="balance-heading"><text>会员余额</text><button class="balance-details" @tap="goWallet(true)">余额明细 ›</button></view>
          <text class="balance-amount"><text>¥</text>{{ loading ? '加载中…' : balance ?? '—' }}</text>
          <text class="balance-description">可用于门票、私汤预约</text>
          <text v-if="balanceError || profileError" class="member-error">{{ balanceError || profileError }}</text>
          <button v-if="balanceError || profileError" class="retry-link" @tap="loadProfile">重新加载</button>
          <view class="balance-actions"><button class="voucher-button" @tap="goOrders('VOUCHERS')">我的卡券</button><button class="recharge-button" @tap="goWallet(false)">立即储值</button></view>
        </view>
      </view>
      <view v-else class="member-login-card">
        <text class="login-title">开启你的温泉会员之旅</text><text class="login-description">登录后查看会员余额、订单与票券</text>
        <button class="recharge-button" @tap="goLogin()">微信快捷登录</button>
        <template v-if="config.development"><button class="dev-login-button" :loading="devBusy" :disabled="devBusy" @tap="devLogin">开发预览：直接进入</button><text class="dev-hint">仅开发环境使用</text></template>
        <text v-if="loginError" class="member-error">{{ loginError }}</text>
      </view>
      <view class="member-white-card">
        <view class="member-card-head"><text>我的订单</text><button @tap="goOrders('ALL')">全部订单 ›</button></view>
        <MemberEntryGrid :items="orderEntries" @select="goOrders" />
      </view>
      <view class="member-white-card">
        <view class="member-card-head"><text>常用服务</text></view>
        <MemberEntryGrid :items="serviceEntries" :columns="5" @select="goService" />
      </view>
    </view>
  </view>
</template>
<style>
@import "./style.css";
</style>
