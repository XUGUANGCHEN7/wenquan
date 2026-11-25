<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { request, loginMember, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const loggedIn = ref(false)
const balance = ref("0.00")
const loading = ref(false)

onShow(() => {
  loggedIn.value = Boolean(uni.getStorageSync("dining_member_token"))
  if (loggedIn.value) loadBalance()
})

async function loadBalance() {
  loading.value = true
  try {
    const wallet = await request("/wallet/balance")
    balance.value = formatMoney(wallet.available_cents)
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

async function login() {
  loading.value = true
  try {
    await loginMember()
    loggedIn.value = true
    await loadBalance()
    uni.showToast({ title: "开发会员已明确绑定", icon: "none" })
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

function logout() {
  uni.removeStorageSync("dining_member_token")
  loggedIn.value = false
  balance.value = "0.00"
}
</script>

<template>
  <view class="page dining-member">
    <view class="member-card">
      <text class="eyebrow">ONE MEMBER, ONE LEDGER</text>
      <text class="page-title">{{ loggedIn ? "已连接业务会员" : "访客点餐" }}</text>
      <text class="member-desc">任何扫码者都可浏览并使用本人微信支付。只有明确登录并验证会员归属后，才能查看或扣减共享余额。</text>
      <view v-if="loggedIn" class="member-balance"><text>统一可用余额</text><text>¥{{ balance }}</text></view>
      <button v-if="!loggedIn" class="primary" :loading="loading" @tap="login">明确登录并绑定会员</button>
      <button v-else class="logout" @tap="logout">退出会员，继续访客点餐</button>
    </view>
    <view class="identity-note">
      <text>身份与房间码相互独立</text>
      <text>房间码只定位送餐房号，不授予会员权限。两个小程序的 OpenID 不同，正式环境需通过安全授权流程绑定到同一个 member_id，不会静默合并或重复开卡。</text>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
