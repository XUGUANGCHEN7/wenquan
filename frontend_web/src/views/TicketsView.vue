<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
import { useAuthStore } from "../stores/auth"
import { formatDateTime, formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"

interface TicketItem { ticket_no: string; category: string; price_cents: number; status: string }
interface OrderLookup {
  order_no: string; order_type: string; status: string; amount_cents: number
  payment_method: string | null; created_at: string; paid_at: string | null
  member: { nickname: string; phone_masked: string } | null; tickets?: TicketItem[]
}
interface VerificationResult {
  admission_id: string; ticket_no: string; order_no: string | null
  remaining_tickets: number; admitted_at: string
}

const auth = useAuthStore()
const code = ref("")
const reason = ref("前台人工核对票券与身份")
const busy = ref(false)
const lookupBusy = ref(false)
const error = ref("")
const notice = ref("")
const order = ref<OrderLookup | null>(null)
const results = ref<Array<{ code: string; message: string; time: string }>>([])

function normalizeCode(raw: string) {
  const text = raw.trim()
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>
    const value = parsed.order_no ?? parsed.orderNo ?? parsed.ticket_no ?? parsed.ticketNo
    if (typeof value === "string" && value.trim()) return value.trim()
  } catch { /* scanner may send plain text */ }
  try {
    const url = new URL(text)
    const value = url.searchParams.get("order_no") ?? url.searchParams.get("orderNo") ?? url.searchParams.get("ticket_no")
    if (value) return value
  } catch { /* not a URL */ }
  return text
}

function requestId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function lookup() {
  const value = normalizeCode(code.value)
  if (!value || lookupBusy.value) return
  lookupBusy.value = true
  error.value = ""
  order.value = null
  try {
    order.value = await api.get<OrderLookup>(`/operations/orders/${encodeURIComponent(value)}`)
    if (order.value.order_type !== "TICKET") error.value = "该订单不是公共浴池票券订单"
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "订单查询失败"
  } finally { lookupBusy.value = false }
}

async function admit() {
  const value = normalizeCode(code.value)
  if (!value || busy.value) return
  busy.value = true
  error.value = ""
  notice.value = ""
  try {
    const result = await api.post<VerificationResult>("/operations/tickets/admit-code", {
      code: value, request_id: requestId(), reason: reason.value,
    })
    notice.value = `核验成功：票券 ${result.ticket_no}，订单剩余未核验 ${result.remaining_tickets} 张`
    results.value.unshift({
      code: value, message: `票券 ${result.ticket_no} 已入园；剩余 ${result.remaining_tickets} 张`,
      time: new Date().toLocaleTimeString("zh-CN"),
    })
    if (order.value?.order_no === result.order_no) await lookup()
    else code.value = ""
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "核验失败"
  } finally { busy.value = false }
}
</script>

<template>
  <PageHeader eyebrow="MANUAL ADMISSION" title="票券核验"
    description="使用小白盒扫描购票订单二维码，或输入订单编号/票券编号；每张票只允许一次人工入园。" />
  <div class="two-column">
    <section class="panel">
      <div class="panel-head"><h2>扫描或输入</h2><span class="operator-tag">{{ auth.role }}</span></div>
      <form class="form-stack" @submit.prevent="admit">
        <label>订单二维码 / 订单号 / 票券号
          <input v-model="code" autocomplete="off" autofocus placeholder="扫码枪扫描，或手动输入订单编号" @keyup.enter="lookup" />
        </label>
        <label>核验原因 / 记录<textarea v-model="reason" rows="3" maxlength="500" /></label>
        <p class="hint">二维码弹窗异常时使用备用方案：直接输入订单编号。扫描订单会依次核验该订单中尚未使用的票券。</p>
        <p v-if="error" class="form-error">{{ error }}</p>
        <p v-if="notice" class="success-note">{{ notice }}</p>
        <div class="button-row">
          <button type="button" class="button secondary" :disabled="lookupBusy || !code.trim()" @click="lookup">{{ lookupBusy ? "查询中…" : "查询订单" }}</button>
          <button class="button primary" :disabled="busy || !code.trim()">{{ busy ? "正在核验…" : "确认核验入园" }}</button>
        </div>
      </form>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>订单数据</h2><span class="muted">数据库记录</span></div>
      <div v-if="!order" class="data-state">扫描或输入订单后显示订单与票券状态</div>
      <template v-else>
        <div class="order-meta">
          <span>订单号 <strong class="mono">{{ order.order_no }}</strong></span>
          <span>状态 <strong>{{ order.status }}</strong></span>
          <span>金额 <strong>{{ formatMoney(order.amount_cents) }}</strong></span>
          <span>支付 <strong>{{ order.payment_method ?? "—" }}</strong></span>
        </div>
        <p class="muted">会员：{{ order.member?.nickname ?? order.order_no }} · {{ order.member?.phone_masked ?? "" }}</p>
        <p class="muted">创建 {{ formatDateTime(order.created_at) }} · 支付 {{ formatDateTime(order.paid_at) }}</p>
        <div class="table-wrap"><table><thead><tr><th>票券号</th><th>类型</th><th>价格</th><th>状态</th></tr></thead>
          <tbody><tr v-for="ticket in order.tickets ?? []" :key="ticket.ticket_no"><td class="mono">{{ ticket.ticket_no }}</td><td>{{ ticket.category }}</td><td>{{ formatMoney(ticket.price_cents) }}</td><td>{{ ticket.status }}</td></tr></tbody>
        </table></div>
      </template>
    </section>
    <section class="panel wide">
      <div class="panel-head"><h2>本次核验记录</h2><span class="muted">仅显示当前页面</span></div>
      <div v-if="results.length === 0" class="data-state">等待核验票券</div>
      <div v-for="item in results" :key="`${item.code}-${item.time}`" class="result-row">
        <span class="result-dot success" /><div><strong>{{ item.code }}</strong><p>{{ item.message }}</p></div><time>{{ item.time }}</time>
      </div>
    </section>
  </div>
</template>
