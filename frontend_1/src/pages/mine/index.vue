<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import config from "../../config"
import { clearSession, getToken, saveSession } from "../../utils/session.js"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const nickname = ref("未登录")
const balance = ref("0.00")
const phone = ref("登录后查看会员权益")
const loggedIn = ref(false)
const loggingOut = ref(false)
const devBusy = ref(false)
const loginError = ref("")

onShow(() => loadProfile())

async function loadProfile() {
  if (!getToken()) {
    loggedIn.value = false
    nickname.value = "未登录"
    phone.value = "登录后查看会员权益"
    balance.value = "0.00"
    return
  }
  loggedIn.value = true
  try {
    const [profile, wallet] = await Promise.all([
      request("/members/me"),
      request("/wallet/balance"),
    ])
    nickname.value = profile.nickname
    phone.value = profile.phone_masked
    balance.value = formatMoney(wallet.available_cents)
  } catch (error) {
    showError(error)
  }
}

function goLogin() {
  uni.navigateTo({
    url: "/pages/login/index?returnTo=" + encodeURIComponent("/pages/mine/index"),
  })
}

function onProfileTap() {
  if (!loggedIn.value) goLogin()
}

const goHome = () => uni.switchTab({ url: "/pages/home/index" })

async function devLogin() {
  if (devBusy.value) return
  devBusy.value = true
  loginError.value = ""
  try {
    const result = await request("/auth/dev", {
      method: "POST",
      auth: false,
      data: { role: "member" },
    })
    saveSession({ ...result, expires_in: 7 * 24 * 60 * 60, nickname: "温泉旅人", phone_masked: "开发模式" })
    await loadProfile()
  } catch (error) {
    loginError.value = error.message || "开发预览登录失败，请确认后端已启动"
    showError(error)
  } finally {
    devBusy.value = false
  }
}

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await request("/auth/logout", { method: "POST" })
    clearSession()
    loggedIn.value = false
    nickname.value = "未登录"
    phone.value = "登录后查看会员权益"
    balance.value = "0.00"
    uni.showToast({ title: "已退出登录", icon: "none" })
  } catch (error) {
    // On network failure keep the session so logout can actually be retried.
    showError(error)
  } finally { loggingOut.value = false }
}

const goWallet = () => uni.navigateTo({ url: "/pages/wallet/index" })
const goOrders = () => uni.switchTab({ url: "/pages/orders/index" })
const contact = () => uni.showToast({ title: "请前往前台或拨打园区公示电话", icon: "none" })
</script>

<template>
  <view class="page mine-page">
    <view class="mine-background">
      <image class="mine-top-background" src="/static/mine/profile-background.jpg" mode="aspectFill" />
      <view class="mine-top-fade" />
    </view>
    <view class="mine-top">
      <view class="status-space" />
      <view class="profile" @tap="onProfileTap">
        <view class="avatar">蜀</view>
        <view>
          <text>{{ nickname }}</text>
          <text>{{ phone }}</text>
        </view>
        <text>{{ loggedIn ? '›' : '登录' }}</text>
      </view>
    </view>
    <view class="mine-content">
      <view v-if="!loggedIn" class="login-card">
        <text class="login-title">会员登录 / 注册</text>
        <text class="login-desc">首次使用需验证手机号注册会员，已有会员登录原账户。</text>
        <button class="login-button" @tap="goLogin">微信登录 / 注册</button>
        <button class="guest-login-button" @tap="goHome">免登录浏览首页</button>
        <template v-if="config.development">
          <button class="dev-login-button" :disabled="devBusy" :loading="devBusy" @tap="devLogin">开发预览：直接进入</button>
          <text class="dev-hint">仅开发环境使用，登录为后端开发会员，不代表真实微信登录</text>
        </template>
        <text v-if="loginError" class="login-error">{{ loginError }}</text>
      </view>
      <template v-if="loggedIn">
        <view class="balance-card">
        <view>
          <text>储值余额</text>
          <text @tap="goWallet">余额明细　›</text>
        </view>
        <text class="amount">
          <text>¥</text>
          {{ balance }}
        </text>
        <text class="balance-desc">可用于门票、私汤与独立房间点餐</text>
        <button @tap="goWallet">进入储值中心</button>
        <view class="ring ring-one" />
        <view class="ring ring-two" />
      </view>
      <view class="white-card">
        <view class="card-head">
          <text>我的订单</text>
          <text @tap="goOrders">全部订单　›</text>
        </view>
        <view class="order-grid member-order-grid">
          <button @tap="goOrders">
            <text>票</text>
            <text>门票订单</text>
          </button>
          <button @tap="goOrders">
            <text>汤</text>
            <text>私汤预约</text>
          </button>
          <button @tap="goWallet">
            <text>充</text>
            <text>储值记录</text>
          </button>
        </view>
      </view>
      <button :disabled="loggingOut" :loading="loggingOut" @tap="logout">退出登录</button>
      <view class="white-card services">
        <view class="card-head">
          <text>常用服务</text>
        </view>
        <button @tap="goOrders">
          <text class="service-icon">码</text>
          <view>
            <text>票券与预约状态</text>
            <text>每票仅支持一次人工入园核验</text>
          </view>
          <text>›</text>
        </button>
        <button @tap="contact">
          <text class="service-icon">客</text>
          <view>
            <text>联系客服</text>
            <text>异常订单请由前台按权限处理</text>
          </view>
          <text>›</text>
        </button>
      </view>
      </template>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
