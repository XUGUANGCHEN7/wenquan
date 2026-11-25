<script setup>
import { computed, ref } from "vue"
import { onLoad, onShow } from "@dcloudio/uni-app"
import config from "../../config"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const balance = ref("0.00")
const plans = ref([])
const selected = ref(0)
const loading = ref(true)
const submitting = ref(false)
const selectedPlan = computed(() => plans.value[selected.value] || null)
let focusEntries = false
onLoad(options => {
  focusEntries = options.section === "entries"
  if (focusEntries) uni.redirectTo({ url: "/pages/wallet/transactions" })
})

onShow(() => { if (!focusEntries) return loadWallet() })

async function loadWallet() {
  loading.value = true
  try {
    const [wallet, plansData] = await Promise.all([
      request("/wallet/balance"),
      request("/catalog/recharge-activities", { auth: false }),
    ])
    balance.value = formatMoney(wallet.available_cents)
    plans.value = plansData.map((plan) => ({
      ...plan,
      amount: formatMoney(plan.principal_cents),
      gift: formatMoney(plan.gift_cents),
    }))
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

function goTransactions() { uni.navigateTo({ url: "/pages/wallet/transactions" }) }

function selectPlan(index) {
  selected.value = index
}

async function recharge() {
  const plan = selectedPlan.value
  if (!plan || submitting.value) return
  if (!config.development) {
    uni.showToast({ title: "正式微信支付适配器尚未配置", icon: "none" })
    return
  }
  submitting.value = true
  try {
    const result = await request("/wallet/recharges", { method: "POST", data: { activity_id: plan.id } })
    await request(`/payments/${result.payment_no}/mock-confirm`, { method: "POST" })
    await loadWallet()
    uni.showModal({
      title: "开发 Mock 储值完成",
      content: `服务端账本已确认储值 ¥${plan.amount}，赠送 ¥${plan.gift}；未发生真实微信扣款。`,
      showCancel: false,
    })
  } catch (error) {
    showError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="page wallet-page">
    <view class="wallet-card">
      <image class="wallet-card-background" src="/static/wallet/balance-background.jpg" mode="aspectFill" />
      <text class="wallet-card-title">当前储值余额</text>
      <text class="balance">
        <text>¥</text>
        {{ balance }}
      </text>
      <button class="transactions-link" @tap="goTransactions">交易明细</button>
    </view>
    <view class="section-head wallet-head">
      <view>
        <text class="title">选择储值金额</text>
      </view>
    </view>
    <view class="plans">
      <button v-for="(item, index) in plans" :key="item.id" :class="{ active: selected === index }" @tap="selectPlan(index)">
        <view class="plan-copy"><text class="plan-name">{{ item.name }}</text><text class="plan-caption">会员储值</text></view>
        <view class="plan-value"><text class="plan-amount">¥{{ item.amount }}</text><text class="plan-gift">赠送 ¥{{ item.gift }}</text></view>
        <view class="plan-check" />
      </button>
    </view>
    <!--
    <view class="benefits">
      <text class="benefit-title">账本说明</text>
      <view>
        <text>01</text>
        <view>
          <text>全场通用</text>
          <text>门票、私汤和独立房间点餐均可使用</text>
        </view>
      </view>
      <view>
        <text>02</text>
        <view>
          <text>不支持提现</text>
          <text>一期不实现储值余额自动退还或提现</text>
        </view>
      </view>
    </view>

    <view class="agreement">当前为开发 Mock 支付，正式环境需配置微信支付商户能力。</view>
-->
    <button
      class="recharge"
      :loading="submitting"
      :disabled="!plans.length || submitting"
      @tap="recharge"
    >
      立即储值 ¥{{ selectedPlan ? selectedPlan.amount : "0.00" }}
    </button>
  </view>
</template>

<style>
@import "./style.css";
</style>
