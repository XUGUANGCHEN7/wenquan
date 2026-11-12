<script setup>
import { computed, ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import config from "../../config"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const balance = ref("0.00")
const plans = ref([])
const entries = ref([])
const selected = ref(0)
const loading = ref(true)
const submitting = ref(false)
const selectedPlan = computed(() => plans.value[selected.value] || null)

onShow(() => loadWallet())

async function loadWallet() {
  loading.value = true
  try {
    const [wallet, plansData, entriesData] = await Promise.all([
      request("/wallet/balance"),
      request("/catalog/recharge-activities", { auth: false }),
      request("/wallet/entries"),
    ])
    balance.value = formatMoney(wallet.available_cents)
    plans.value = plansData.map((plan) => ({
      ...plan,
      amount: formatMoney(plan.principal_cents),
      gift: formatMoney(plan.gift_cents),
    }))
    entries.value = entriesData.map((entry) => ({
      ...entry,
      delta: formatMoney(entry.delta_cents),
      after: formatMoney(entry.balance_after_cents),
    }))
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

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
      <text>当前储值余额</text>
      <text class="balance">
        <text>¥</text>
        {{ balance }}
      </text>
      <text>与独立点餐小程序共用同一会员账本</text>
      <view class="ring one" />
      <view class="ring two" />
    </view>
    <view class="section-head wallet-head">
      <view>
        <text class="en">RECHARGE BONUS</text>
        <text class="title">选择储值金额</text>
      </view>
    </view>
    <view class="plans">
      <button v-for="(item, index) in plans" :key="item.id" :class="{ active: selected === index }" @tap="selectPlan(index)">
        <text class="popular">{{ item.name }}</text>
        <text>储值</text>
        <text>¥{{ item.amount }}</text>
        <text>赠送 ¥{{ item.gift }}</text>
      </button>
    </view>
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
          <text>服务端确认</text>
          <text>消费先扣本金，再扣赠送金；余额不由客户端修改</text>
        </view>
      </view>
      <view>
        <text>03</text>
        <view>
          <text>不支持提现</text>
          <text>一期不实现储值余额自动退还或提现</text>
        </view>
      </view>
    </view>
    <view class="entries">
      <text class="entries-title">最近账本记录</text>
      <view v-for="item in entries" :key="item.reference" class="entry-line">
        <text>{{ item.entry_type }} · {{ item.reference }}</text>
        <text>{{ item.delta }} · 余 {{ item.after }}</text>
      </view>
      <view v-if="!loading && entries.length === 0" class="entry-empty">暂无储值或消费记录</view>
    </view>
    <view class="agreement">当前为开发 Mock 支付，正式环境需配置微信支付商户能力。</view>
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
