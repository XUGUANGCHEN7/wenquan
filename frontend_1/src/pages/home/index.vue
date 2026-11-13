<script setup>
import { computed, ref } from "vue"
import { onHide, onShow, onUnload } from "@dcloudio/uni-app"
import HomeHero from "../../components/HomeHero.vue"
import JourneyCard from "../../components/JourneyCard.vue"
import MemberGuideCard from "../../components/MemberGuideCard.vue"
import { getToken } from "../../utils/session.js"
import { request } from "../../utils/api.js"
import { businessPresentation } from "../../utils/business-hours.js"
import { formatMoney } from "../../utils/money"

const businessConfig = ref(null)
const business = computed(() => businessPresentation(businessConfig.value))
let businessTimer
let businessVersion = 0

function stopBusinessRefresh() {
  businessVersion += 1
  clearTimeout(businessTimer)
}

async function refreshBusiness(version) {
  let delay = 60
  try {
    const data = await request("/catalog/business-hours", { auth: false })
    if (version !== businessVersion) return
    businessConfig.value = data
    delay = data.refresh_after_seconds || 60
  } catch {
    if (version !== businessVersion) return
    businessConfig.value = null
  }
  businessTimer = setTimeout(() => refreshBusiness(version), Math.max(1, Math.min(60, delay)) * 1000)
}

onShow(() => {
  stopBusinessRefresh()
  businessConfig.value = null
  refreshBusiness(businessVersion)
})
onHide(stopBusinessRefresh)
onUnload(stopBusinessRefresh)

const memberProfile = ref(null)
const walletBalance = ref("")
const walletStatus = ref("guest")
let memberVersion = 0
const balanceDisplay = computed(() => {
  if (!memberProfile.value) return "登录后查看余额"
  if (walletStatus.value === "loading") return "加载中…"
  if (walletStatus.value === "error") return "余额读取失败"
  return `¥${walletBalance.value}`
})
const isBalanceMessage = computed(() => !memberProfile.value || walletStatus.value !== "ready")

async function refreshMember() {
  const version = ++memberVersion
  if (!getToken()) {
    memberProfile.value = null
    walletBalance.value = ""
    walletStatus.value = "guest"
    return
  }
  const stored = uni.getStorageSync("member_profile") || {}
  memberProfile.value = {
    nickname: stored.nickname || "会员",
  }
  walletStatus.value = "loading"
  try {
    const wallet = await request("/wallet/balance")
    if (version !== memberVersion) return
    if (!Number.isInteger(wallet?.available_cents) || wallet.available_cents < 0) {
      throw new Error("invalid wallet balance")
    }
    walletBalance.value = formatMoney(wallet.available_cents)
    walletStatus.value = "ready"
  } catch {
    if (version !== memberVersion) return
    // Keep a readable error state; never present a failed request as ¥0.00.
    walletStatus.value = "error"
  }
}

function goMemberAction() {
  if (memberProfile.value) {
    goMine()
    return
  }
  uni.navigateTo({
    url: "/pages/login/index?returnTo=" + encodeURIComponent("/pages/home/index"),
  })
}

onShow(refreshMember)
refreshMember()

const heroSlides = [
  { image: "/static/home-carousel/home-01.jpg" },
  { image: "/static/home-carousel/home-02.jpg" },
  { image: "/static/home-carousel/home-03.jpg" },
  { image: "/static/home-carousel/home-04.jpg" },
]

const goTickets = () => uni.navigateTo({ url: "/pages/tickets/index" })
const goPrivateRoom = () => uni.navigateTo({ url: "/pages/private-room/index" })
const goWallet = () => uni.navigateTo({ url: "/pages/wallet/index" })
const goMine = () => uni.switchTab({ url: "/pages/mine/index" })

function goRecharge() {
  if (!memberProfile.value) {
    uni.navigateTo({
      url: "/pages/login/index?returnTo=" + encodeURIComponent("/pages/home/index"),
    })
    return
  }
  goWallet()
}
</script>

<template>
  <view class="page home">
    <HomeHero :slides="heroSlides" />

    <view class="home-content">
      <view class="welcome">
        <view class="business-status" :class="{ 'is-open': business.isOpen }">
          <view class="business-dot" />
          <text>{{ business.label }}</text>
        </view>
        <view class="welcome-hours">
          <view class="business-clock" />
          <text>{{ business.hours }}</text>
        </view>
      </view>

      <MemberGuideCard :profile="memberProfile" @action="goMemberAction" />

      <view class="journey-grid">
        <JourneyCard
          image="/static/journey/tickets.jpg"
          title="购买门票"
          description="温泉畅享，即买即用"
          @select="goTickets"
        />
        <view class="journey-divider" />
        <JourneyCard
          image="/static/journey/private-room.jpg"
          title="预约私汤房"
          description="独立汤池，静享时光"
          @select="goPrivateRoom"
        />
      </view>

      <view class="member-card">
        <view class="wallet-head">
          <view class="wallet-label">
            <view class="wallet-icon">
              <view class="wallet-line" />
              <view class="wallet-dot" />
            </view>
            <text>我的会员余额</text>
          </view>
          <view class="wallet-scope">
            <text class="scope-symbol">♨</text>
            <text>温泉 · 点餐通用</text>
          </view>
        </view>

        <text class="wallet-caption">当前可用余额</text>
        <text class="wallet-balance" :class="{ 'is-message': isBalanceMessage }">{{ balanceDisplay }}</text>
        <text v-if="!memberProfile" class="wallet-guest-hint">登录 / 开通会员后，余额两小程序通用</text>

        <view class="wallet-footer">
          <view class="wallet-usage">
            <view class="usage-mark">
              <view class="usage-fork" />
              <view class="usage-knife" />
            </view>
            <text>温泉消费 · 餐饮点单</text>
          </view>
          <button
            class="recharge-button"
            hover-class="recharge-button--pressed"
            @tap="goRecharge"
          >
            立即充值
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
