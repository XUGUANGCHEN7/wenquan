<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import config from "../../config"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const nickname = ref("温泉旅人")
const balance = ref("0.00")

onShow(() => loadProfile())

async function loadProfile() {
  try {
    const [profile, wallet] = await Promise.all([
      request(`/members/${config.memberId}/profile`),
      request("/wallet/balance"),
    ])
    nickname.value = profile.nickname
    balance.value = formatMoney(wallet.available_cents)
  } catch (error) {
    showError(error)
  }
}

const goWallet = () => uni.navigateTo({ url: "/pages/wallet/index" })
const goOrders = () => uni.switchTab({ url: "/pages/orders/index" })
const contact = () => uni.showToast({ title: "请前往前台或拨打园区公示电话", icon: "none" })
</script>

<template>
  <view class="page mine-page">
    <view class="mine-top">
      <view class="status-space" />
      <view class="profile">
        <view class="avatar">蜀</view>
        <view>
          <text>{{ nickname }}</text>
          <text>统一业务会员 · 两个小程序一份账本</text>
        </view>
        <text>›</text>
      </view>
    </view>
    <view class="mine-content">
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
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
