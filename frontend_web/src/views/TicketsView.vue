<script setup lang="ts">
import { computed, onBeforeUnmount } from "vue"
import { api } from "../api"
import { useAuthStore } from "../stores/auth"
import { formatDateTime, formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import { createTicketVerification, type BatchResult, type TicketOrderLookup } from "./ticketVerification"

const auth = useAuthStore()
const model = createTicketVerification({
  lookup: code => api.get<TicketOrderLookup>(`/operations/orders/${encodeURIComponent(code)}`),
  admit: payload => api.post<BatchResult>("/operations/tickets/admit-batch", payload),
}, () => typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)
const { state, eligibleTickets, selectedTickets, canSubmit } = model
const allSelected = computed(() => eligibleTickets.value.length > 0 && selectedTickets.value.length === eligibleTickets.value.length)
const selectedAmount = computed(() => selectedTickets.value.reduce((sum, ticket) => sum + ticket.price_cents, 0))
const canOperate = computed(() => auth.role === "frontdesk" || auth.role === "admin")
onBeforeUnmount(model.dispose)
function statusLabel(status: string) { return ({ UNUSED: "待使用", USED: "已核销", VOID: "已失效", REFUNDED: "已退款" } as Record<string, string>)[status] || status }
</script>

<template>
  <PageHeader eyebrow="TICKET ADMISSION" title="票券核验" description="输入票券号或订单号，查询所属订单；核对并勾选本订单票券后，统一确认核销。" />
  <div class="two-column">
    <section class="panel">
      <div class="panel-head"><h2>第一步 · 查询订单</h2><span class="operator-tag">{{ auth.role }}</span></div>
      <form class="form-stack" @submit.prevent="model.lookup">
        <label>票券号 / 订单号 / 扫码内容
          <input v-model="state.code" :disabled="state.busy || state.lookupBusy" autocomplete="off" autofocus placeholder="输入票券号，或用扫码枪扫描" />
        </label>
        <label>核验原因 / 记录<textarea v-model="state.reason" :disabled="state.busy" rows="3" maxlength="500" /></label>
        <p class="hint">查询本身不会核销。每次只处理当前订单，不关联核销该会员的其他订单。</p>
        <p v-if="state.error" class="form-error">{{ state.error }}</p>
        <p v-if="state.notice" class="success-note">{{ state.notice }}</p>
        <button class="button secondary" :disabled="state.busy || state.lookupBusy || !state.code.trim()">{{ state.lookupBusy ? "查询中…" : "查询所属订单" }}</button>
      </form>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>第二步 · 勾选并核销</h2><span class="muted">{{ eligibleTickets.length }} 张可选</span></div>
      <div v-if="!state.order" class="data-state">输入任意票券号，可查询该票券所属订单及订单内全部票券</div>
      <template v-else>
        <div class="order-meta">
          <span>订单号 <strong class="mono">{{ state.order.order_no }}</strong></span>
          <span>支付状态 <strong>{{ state.order.status }}</strong></span>
          <span>订单金额 <strong>¥{{ formatMoney(state.order.amount_cents) }}</strong></span>
          <span>支付方式 <strong>{{ state.order.payment_method ?? "—" }}</strong></span>
        </div>
        <p class="muted">会员：{{ state.order.member?.nickname ?? "—" }} · {{ state.order.member?.phone_masked ?? "" }}</p>
        <p v-if="state.order.visit_date" class="muted">入园日期 {{ state.order.visit_date }}</p>
        <p v-if="state.order.day_type" class="muted">{{ state.order.day_type === 'HOLIDAY' ? '节假日票：周六、周日及后台配置节假日' : '工作日票：非节假日的周一至周五' }} · 有效期至 {{ formatDateTime(state.order.valid_until) }}</p>
        <p v-if="state.order.admission_error" class="form-error">{{ state.order.admission_error.message }}</p>
        <p class="muted">创建 {{ formatDateTime(state.order.created_at) }} · 支付 {{ formatDateTime(state.order.paid_at) }}</p>
        <p v-if="state.order.refund_application?.status === 'PENDING'" class="form-error">退款审核中，当前订单禁止勾选核销。</p>
        <RouterLink v-if="state.order.order_type === 'PRIVATE' && canOperate" class="button secondary" :to="{ path: '/rooms', query: { code: state.order.order_no } }">查看私汤票券并确认核验</RouterLink>
        <template v-if="state.order.order_type === 'TICKET'">
          <div class="table-wrap"><table>
            <thead><tr><th><input type="checkbox" aria-label="全选可核销票券" :checked="allSelected" :indeterminate="selectedTickets.length > 0 && !allSelected" :disabled="!canOperate || state.busy || eligibleTickets.length === 0" @change="model.selectAll(($event.target as HTMLInputElement).checked)" /></th><th>票券号</th><th>类型</th><th>价格</th><th>状态</th></tr></thead>
            <tbody><tr v-for="ticket in state.order.tickets ?? []" :key="ticket.ticket_no">
              <td><input v-model="state.selected" type="checkbox" :value="ticket.ticket_no" :aria-label="'选择票券 ' + ticket.ticket_no" :disabled="!canOperate || state.busy || !ticket.can_admit || ticket.status !== 'UNUSED' || state.order.status !== 'PAID' || state.order.refund_application?.status === 'PENDING'" /></td>
              <td class="mono">{{ ticket.ticket_no }}</td><td>{{ ticket.category === 'ADULT' ? '成人票' : ticket.category === 'CHILD' ? '儿童票' : ticket.category }}</td><td>¥{{ formatMoney(ticket.price_cents) }}</td><td>{{ statusLabel(ticket.status) }}</td>
            </tr></tbody>
          </table></div>
          <div class="batch-summary">
            <strong>已选 {{ selectedTickets.length }} 张 · 票面金额 ¥{{ formatMoney(selectedAmount) }}</strong>
            <p class="hint">只核销已勾选票券。任意一张状态不符，整批不核销；已核销票券不能再次选择。</p>
            <p v-if="!canOperate" class="hint">当前账号仅可查询，前台或管理员账号才可核销。</p>
            <button class="button primary" :disabled="!canOperate || !canSubmit" @click="model.admit">{{ state.busy ? "正在统一核销…" : `确认核销已选 ${selectedTickets.length} 张` }}</button>
          </div>
        </template>
      </template>
    </section>

    <section class="panel wide">
      <div class="panel-head"><h2>本次核验记录</h2><span class="muted">仅显示当前页面</span></div>
      <div v-if="state.results.length === 0" class="data-state">等待确认核销票券</div>
      <div v-for="(item, index) in state.results" :key="index" class="result-row">
        <span class="result-dot success" /><div><strong class="mono">{{ item.order_no }}</strong><p>核销成功 {{ item.admitted_count }} 张，剩余 {{ item.remaining_tickets }} 张</p><p class="muted mono">{{ item.admissions.map(admission => admission.ticket_no).join('、') }}</p></div><time>{{ formatDateTime(item.admitted_at) }}</time>
      </div>
    </section>
  </div>
</template>

<style scoped>
.batch-summary { padding-top: 20px; }
.batch-summary .button { margin-top: 8px; }
input[type="checkbox"] { width: 18px; height: 18px; padding: 0; accent-color: #246b61; cursor: pointer; }
input[type="checkbox"]:disabled { cursor: not-allowed; }
.order-meta, .result-row { overflow-wrap: anywhere; }
</style>
