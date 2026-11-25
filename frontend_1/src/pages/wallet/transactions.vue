<script setup>
import { ref } from "vue"
import { onShow, onHide } from "@dcloudio/uni-app"
import { request } from "../../utils/api"
import { getToken, redirectToLogin } from "../../utils/session.js"
import { formatMoney } from "../../utils/money"
const entries = ref([])
const loading = ref(false)
const error = ref("")
const guest = ref(false)
const labels = { RECHARGE: "会员储值", CONSUME: "余额消费", REVERSAL: "消费退回", REFUND: "退款入账" }
let generation = 0
onShow(loadEntries)
onHide(() => { generation++ })
function goLogin() { redirectToLogin("/pages/wallet/transactions") }
async function loadEntries() {
  const version = ++generation
  const token = getToken()
  entries.value = []
  error.value = ""
  guest.value = !token
  loading.value = false
  if (!token) return
  loading.value = true
  try {
    const records = await request("/wallet/entries")
    if (version !== generation || token !== getToken()) return
    if (!Array.isArray(records)) throw new Error("交易记录格式异常，请重试")
    entries.value = records.map(item => ({ ...item,
      label: labels[item.entry_type] || item.entry_type,
      delta: `${item.delta_cents > 0 ? "+" : ""}${formatMoney(item.delta_cents)}`,
      after: formatMoney(item.balance_after_cents),
      time: formatTime(item.created_at),
    }))
  } catch (reason) {
    if (version !== generation) return
    if (!getToken()) guest.value = true
    else error.value = reason.message || "交易记录读取失败"
  } finally { if (version === generation) loading.value = false }
}
function formatTime(value) {
  if (!value) return ""
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : value + "Z")
  if (Number.isNaN(date.getTime())) return ""
  return new Date(date.getTime() + 8 * 3600000).toISOString().slice(0, 19).replace("T", " ")
}
</script>
<template>
  <view class="transactions-page">
    <view v-if="guest" class="transaction-state"><text>登录后查看交易明细</text><button @tap="goLogin">前往登录</button></view>
    <view v-else-if="loading" class="transaction-state">正在读取交易记录…</view>
    <view v-else-if="error" class="transaction-state"><text>{{ error }}</text><button @tap="loadEntries">重新加载</button></view>
    <view v-else-if="!entries.length" class="transaction-state">暂无储值或消费记录</view>
    <template v-else>
      <text class="transactions-tip">最近交易记录（最多100条）</text>
      <view v-for="(item, index) in entries" :key="item.reference + '-' + item.entry_type + '-' + index" class="transaction-card">
        <view class="transaction-heading"><text>{{ item.label }}</text><text :class="{ 'is-income': item.delta_cents > 0 }">{{ item.delta }}</text></view>
        <text v-if="item.time" class="transaction-meta">{{ item.time }}</text>
        <text class="transaction-reference">流水关联号：{{ item.reference }}</text>
        <text class="transaction-after">交易后余额 ¥{{ item.after }}</text>
      </view>
    </template>
  </view>
</template>
<style scoped>
.transactions-page { box-sizing: border-box; min-height: 100vh; padding: 28rpx 28rpx calc(36rpx + env(safe-area-inset-bottom)); background: #f8f6f1; color: #263f38; }
.transactions-tip { display: block; margin: 8rpx 0 24rpx; color: #89938d; font-size: 23rpx; }
.transaction-card { margin-bottom: 20rpx; padding: 28rpx; border: 1rpx solid #eee7db; border-radius: 24rpx; background: #fff; }
.transaction-heading { display: flex; justify-content: space-between; gap: 20rpx; font-size: 28rpx; font-weight: 600; }
.transaction-heading text:last-child { max-width: 58%; overflow-wrap: anywhere; }
.transaction-heading .is-income { color: #246b61; }
.transaction-meta,.transaction-reference,.transaction-after { display: block; margin-top: 16rpx; color: #89938d; font-size: 22rpx; line-height: 1.6; overflow-wrap: anywhere; }
.transaction-after { color: #537366; }
.transaction-state { padding: 70rpx 24rpx; text-align: center; color: #89938d; font-size: 26rpx; line-height: 1.8; }
.transaction-state button { margin-top: 28rpx; background: #246b61; color: #fff; border-radius: 22rpx; font-size: 26rpx; }
</style>
