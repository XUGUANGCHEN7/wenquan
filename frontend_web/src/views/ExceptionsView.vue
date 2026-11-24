<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { useAuthStore } from "../stores/auth"
import { api } from "../api"
import type { Exceptions } from "../api/types"
import { formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

const data = ref<Exceptions | null>(null)
const loading = ref(true)
const error = ref("")
interface RefundApplication { order_no: string; order_type: string; amount_cents: number; status: string; reason: string; review_reason: string; refund_no: string | null; refund_status: string | null }
const auth = useAuthStore()
const canReview = computed(() => auth.role === "finance" || auth.role === "admin")
const applications = ref<RefundApplication[]>([])
const reviewNotes = ref<Record<string, string>>({})
const reviewingOrder = ref("")
const notice = ref("")

async function reviewApplication(item: RefundApplication, approve: boolean) {
  const reason = (reviewNotes.value[item.order_no] || "").trim()
  if (!reason) { error.value = "请填写审核意见"; return }
  if (reviewingOrder.value) return
  reviewingOrder.value = item.order_no
  error.value = ""; notice.value = ""
  try {
    await api.post(`/operations/refund-applications/${encodeURIComponent(item.order_no)}/review`, { approve, reason })
    notice.value = approve ? "审核通过，已进入退款处理；到账以退款结果为准" : "申请已拒绝，未使用票券可继续核验"
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "审核失败" }
  finally { reviewingOrder.value = "" }
}

async function load() {
  loading.value = true; error.value = ""
  try {
    const [exceptions, requests] = await Promise.all([
      api.get<Exceptions>("/operations/exceptions"),
      canReview.value ? api.get<RefundApplication[]>("/operations/refund-applications") : Promise.resolve([]),
    ])
    data.value = exceptions; applications.value = requests
  }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "异常看板读取失败" }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <PageHeader eyebrow="HUMAN EXCEPTION QUEUE" title="异常看板" description="异常只展示事实与人工处理入口。退款、换房或补偿不得由前端自动判定。" ><button class="button secondary" @click="load">刷新</button></PageHeader>
  <p v-if="notice" class="success-note">{{ notice }}</p>
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
    <div class="exception-grid">
      <section v-if="canReview" class="panel">
        <div class="panel-head"><h2>会员退款申请审核</h2><span>{{ applications.filter(item => item.status === 'PENDING').length }} 笔待审核</span></div>
        <p class="hint">仅公共票、私汤未使用订单可整单申请。审核期间暂停核销；通过审核不等于微信已到账。</p>
        <p v-if="applications.length === 0" class="hint">暂无会员退款申请</p>
        <div v-for="item in applications" :key="item.order_no" class="refund-application">
          <div class="simple-row"><strong class="mono">{{ item.order_no }}</strong><span>{{ { PENDING: '待审核', APPROVED: '已通过', REJECTED: '已拒绝' }[item.status] || item.status }}</span><strong>¥{{ formatMoney(item.amount_cents) }}</strong></div>
          <p>{{ item.order_type === 'TICKET' ? '公共票' : '私汤' }} · 申请原因：{{ item.reason }}</p>
          <p v-if="item.review_reason" class="hint">审核意见：{{ item.review_reason }}</p>
          <p v-if="item.refund_no" class="hint">退款单 {{ item.refund_no }} · {{ item.refund_status }}</p>
          <template v-if="item.status === 'PENDING'">
            <label>审核意见<textarea v-model="reviewNotes[item.order_no]" rows="2" maxlength="500" placeholder="请填写通过或拒绝的原因" /></label>
            <div class="button-row"><button class="button secondary" :disabled="!!reviewingOrder" @click="reviewApplication(item, false)">拒绝申请</button><button class="button primary" :disabled="!!reviewingOrder" @click="reviewApplication(item, true)">审核通过并退款</button></div>
          </template>
        </div>
      </section>
      <section class="panel"><div class="panel-head"><h2>待处理退款</h2><span>{{ data?.refunds.length ?? 0 }}</span></div><p class="hint">只有微信通知或主动查询确认 SUCCESS 才显示退款成功。</p><div v-for="item in data?.refunds" :key="item.refund_no" class="simple-row"><span class="mono">{{ item.refund_no }}</span><StatusBadge :status="item.status" /><strong>¥{{ formatMoney(item.amount_cents) }}</strong></div></section>
      <section class="panel"><div class="panel-head"><h2>已付款未交付</h2><span>{{ data?.paid_exceptions.length ?? 0 }}</span></div><p class="hint">预约过期、加钟冲突或点餐不可送达的已付款订单，可由财务人工受理退款。</p><div v-for="item in data?.paid_exceptions" :key="item.order_no" class="simple-row"><span class="mono">{{ item.order_no }}</span><StatusBadge :status="item.status" /><strong>¥{{ formatMoney(item.amount_cents) }}</strong></div></section>
      <section class="panel"><div class="panel-head"><h2>发卡结果未知</h2><span>{{ data?.device_unknown.length ?? 0 }}</span></div><p class="hint">先核实实体卡真实权限，不盲目重试或释放柜位。</p><div v-for="item in data?.device_unknown" :key="item.id" class="simple-row"><span class="mono">{{ item.task_no }}</span><small>{{ item.raw_error || "无原始错误" }}</small></div></section>
      <section class="panel"><div class="panel-head"><h2>房间占用冲突</h2><span>{{ data?.room_conflicts.length ?? 0 }}</span></div><p class="hint">按业务方签认的改期/退款流程处理并记录结果。</p><div v-for="item in data?.room_conflicts" :key="item.id" class="simple-row"><span class="mono">{{ item.id }}</span><StatusBadge :status="item.status" /></div></section>
      <section class="panel"><div class="panel-head"><h2>点餐无法送达</h2><span>{{ data?.food_delivery.length ?? 0 }}</span></div><p class="hint">不自动退款、不静默进入商家待接单队列。</p><div v-for="item in data?.food_delivery" :key="item.id" class="simple-row"><span>{{ item.reason }}</span></div></section>
    </div>
  </DataState>
</template>

<style scoped>
.refund-application { padding: 18px 0; border-top: 1px solid var(--line, #e8e1d4); overflow-wrap: anywhere; }
.refund-application p { margin: 10px 0; }
.refund-application textarea { display: block; width: 100%; margin: 8px 0 12px; }
</style>
