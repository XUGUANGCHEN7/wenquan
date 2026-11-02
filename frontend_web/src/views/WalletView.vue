<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
import { formatDateTime, formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

interface Entry { id: string; entry_type: string; reference: string; principal_delta: number; gift_delta: number; principal_after: number; gift_after: number; original_entry_id: string | null; created_at: string }
interface Wallet { member_id: string; principal_cents: number; gift_cents: number; available_cents: number; entries: Entry[] }

const memberId = ref("member-demo")
const wallet = ref<Wallet | null>(null)
const loading = ref(false)
const error = ref("")
const refundOrderNo = ref("")
const refundReason = ref("业务方签认的人工退款处理")
const refundNotice = ref("")

async function requestRefund() {
  if (!refundOrderNo.value || !refundReason.value) return
  refundNotice.value = ""
  try {
    const result = await api.post<{ refund_no: string; status: string }>(
      `/operations/orders/${refundOrderNo.value.trim()}/refunds`, { reason: refundReason.value })
    refundNotice.value = `${result.refund_no} 已进入 ${result.status}；微信退款仍需渠道确认 SUCCESS。`
    refundOrderNo.value = ""
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "退款受理失败" }
}

async function load() {
  if (!memberId.value) return
  loading.value = true; error.value = ""
  try { wallet.value = await api.get<Wallet>(`/operations/wallet/${encodeURIComponent(memberId.value.trim())}`) }
  catch (cause) { wallet.value = null; error.value = cause instanceof Error ? cause.message : "账本读取失败" }
  finally { loading.value = false }
}
</script>

<template>
  <PageHeader eyebrow="PRINCIPAL & GIFT LEDGER" title="会员账本" description="商家与财务可分别查看本金、赠送金及追加式流水。游客端只看到合计可用余额。" />
  <section class="panel filter-panel"><label>会员 ID<input v-model="memberId" @keyup.enter="load" /></label><button class="button primary compact" @click="load">查询账本</button></section>
  <DataState :loading="loading" :error="error" :empty="!wallet" empty-text="输入会员 ID 查询统一储值账本" @retry="load">
    <section v-if="wallet" class="metric-grid compact-metrics">
      <article class="metric-card"><span>本金余额</span><strong>{{ formatMoney(wallet.principal_cents) }}</strong><small>消费优先扣减</small></article>
      <article class="metric-card"><span>赠送余额</span><strong>{{ formatMoney(wallet.gift_cents) }}</strong><small>本金不足后扣减</small></article>
      <article class="metric-card"><span>合计可用</span><strong>{{ formatMoney(wallet.available_cents) }}</strong><small>{{ wallet.member_id }}</small></article>
    </section>
    <section v-if="wallet" class="panel"><div class="panel-head"><h2>追加式账本流水</h2><span class="muted">原始记录不可覆盖</span></div>
      <div class="table-wrap"><table><thead><tr><th>类型</th><th>业务引用</th><th>本金变动</th><th>赠送变动</th><th>本金余额</th><th>赠送余额</th><th>时间</th></tr></thead>
        <tbody><tr v-for="entry in wallet.entries" :key="entry.id"><td>{{ entry.entry_type }}</td><td class="mono">{{ entry.reference }}</td><td>{{ formatMoney(entry.principal_delta) }}</td><td>{{ formatMoney(entry.gift_delta) }}</td><td>{{ formatMoney(entry.principal_after) }}</td><td>{{ formatMoney(entry.gift_after) }}</td><td>{{ formatDateTime(entry.created_at) }}</td></tr></tbody>
      </table></div>
    </section>
    <section class="panel"><div class="panel-head"><h2>人工退款受理</h2><span>仅财务 / 管理员</span></div>
      <p v-if="refundNotice" class="success-note">{{ refundNotice }}</p>
      <form class="form-stack" @submit.prevent="requestRefund">
        <div class="form-row"><label>订单号<input v-model="refundOrderNo" placeholder="已支付订单 order_no" /></label><label>处理原因<input v-model="refundReason" /></label></div>
        <p class="hint">余额支付会立即按原本金/赠送来源冲回；微信支付只登记受理，必须由渠道查询确认成功。押金必须从逐枚归还流程退款。</p>
        <button class="button secondary" :disabled="!refundOrderNo || !refundReason">提交人工退款受理</button>
      </form>
    </section>
  </DataState>
</template>
