<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
import { formatDateTime, formatMoney, parseYuanToCents } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface Entry { id: string; entry_type: string; reference: string; principal_delta: number; gift_delta: number; principal_after: number; gift_after: number; original_entry_id: string | null; created_at: string }
interface Wallet { member_id: string; nickname?: string; phone_masked?: string; principal_cents: number; gift_cents: number; available_cents: number; entries: Entry[] }

const mode = ref<"phone" | "id">("phone")
const query = ref("")
const wallet = ref<Wallet | null>(null)
const loading = ref(false)
const error = ref("")
const refundOrderNo = ref("")
const refundAmountYuan = ref("")
const refundReason = ref("业务方签认的人工退款处理")
const refundNotice = ref("")

async function load() {
  const value = query.value.trim()
  if (!value) return
  loading.value = true; error.value = ""; wallet.value = null
  try {
    wallet.value = mode.value === "phone"
      ? await api.get<Wallet>(`/operations/wallet-by-phone?phone=${encodeURIComponent(value)}`)
      : await api.get<Wallet>(`/operations/wallet/${encodeURIComponent(value)}`)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "账本读取失败"
  } finally { loading.value = false }
}

async function requestRefund() {
  if (!refundOrderNo.value.trim() || !refundReason.value.trim()) return
  const cents = parseYuanToCents(refundAmountYuan.value)
  if (cents === null || cents <= 0) { error.value = "请填写正确的退款金额"; return }
  error.value = ""; refundNotice.value = ""
  try {
    const result = await api.post<{ refund_no: string; status: string; amount_cents: number }>(
      `/operations/orders/${refundOrderNo.value.trim()}/refunds`,
      { reason: refundReason.value, amount_cents: cents },
    )
    refundNotice.value = `${result.refund_no} 已进入 ${result.status}，金额 ${formatMoney(result.amount_cents)}；微信退款仍需渠道确认 SUCCESS。`
    refundOrderNo.value = ""; refundAmountYuan.value = ""
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "退款受理失败" }
}
</script>

<template>
  <PageHeader eyebrow="MEMBER LEDGER" title="会员账本" description="可按手机号查询会员本金、赠送金和追加式流水；人工退款按订单号登记金额与原因。" />
  <section class="panel filter-panel">
    <label>查询方式
      <select v-model="mode"><option value="phone">手机号</option><option value="id">会员 ID</option></select>
    </label>
    <label>{{ mode === "phone" ? "会员手机号" : "会员 ID" }}
      <input v-model="query" :placeholder="mode === 'phone' ? '例如 13800000000' : 'member id'" @keyup.enter="load" />
    </label>
    <button class="button primary compact" @click="load">查询账本</button>
  </section>
  <DataState :loading="loading" :error="error" :empty="!wallet" empty-text="输入手机号查询会员账本" @retry="load">
    <section v-if="wallet" class="metric-grid compact-metrics">
      <article class="metric-card"><span>会员</span><strong class="text-value">{{ wallet.nickname ?? wallet.member_id }}</strong><small>{{ wallet.phone_masked ?? wallet.member_id }}</small></article>
      <article class="metric-card"><span>本金余额</span><strong>{{ formatMoney(wallet.principal_cents) }}</strong><small>消费优先扣减</small></article>
      <article class="metric-card"><span>赠送余额</span><strong>{{ formatMoney(wallet.gift_cents) }}</strong><small>本金不足后扣减</small></article>
      <article class="metric-card"><span>合计可用</span><strong>{{ formatMoney(wallet.available_cents) }}</strong><small>本金 + 赠送</small></article>
    </section>
    <section v-if="wallet" class="panel"><div class="panel-head"><h2>追加式账本流水</h2><span class="muted">原始记录不可覆盖</span></div>
      <div class="table-wrap"><table><thead><tr><th>类型</th><th>业务引用</th><th>本金变动</th><th>赠送变动</th><th>本金余额</th><th>赠送余额</th><th>时间</th></tr></thead>
        <tbody><tr v-for="entry in wallet.entries" :key="entry.id"><td>{{ entry.entry_type }}</td><td class="mono">{{ entry.reference }}</td><td>{{ formatMoney(entry.principal_delta) }}</td><td>{{ formatMoney(entry.gift_delta) }}</td><td>{{ formatMoney(entry.principal_after) }}</td><td>{{ formatMoney(entry.gift_after) }}</td><td>{{ formatDateTime(entry.created_at) }}</td></tr></tbody>
      </table></div>
    </section>
    <section class="panel"><div class="panel-head"><h2>人工退款受理</h2><span>仅财务 / 管理员</span></div>
      <p v-if="refundNotice" class="success-note">{{ refundNotice }}</p>
      <form class="form-stack" @submit.prevent="requestRefund">
        <div class="form-row">
          <label>订单号<input v-model="refundOrderNo" placeholder="已支付订单 order_no" /></label>
          <label>退款金额（元）<input v-model="refundAmountYuan" type="text" inputmode="decimal" placeholder="0.00" /></label>
        </div>
        <label>退款原因<input v-model="refundReason" maxlength="500" /></label>
        <p class="hint">微信订单支持按填写金额退款；余额订单暂只支持原订单全额冲回，部分退款需财务确认规则。押金必须走逐枚归还流程。</p>
        <button class="button secondary" :disabled="!refundOrderNo || !refundAmountYuan || !refundReason">提交人工退款受理</button>
      </form>
    </section>
  </DataState>
</template>
