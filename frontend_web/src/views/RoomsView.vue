<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, toRefs } from "vue"
import { useRoute } from "vue-router"
import { createPrivateVerification } from "./privateVerification"
import type { TicketOrderLookup } from "./ticketVerification"
import { api } from "../api"
import type { RoomBoardItem } from "../api/types"
import { formatDateTime, statusText } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

interface VerifyPrivateResult { room_number: string; room_use_id: string; status: string; actual_end_at: string | null; already_verified: boolean }

const rooms = ref<RoomBoardItem[]>([])
const loading = ref(true)
const error = ref("")
const notice = ref("")
const bookingId = ref("")
const actualStart = ref(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))
const assignReason = ref("游客到店，前台重新检查完整使用与清洁区间")
const blockRoom = ref("")
const blockStart = ref("")
const blockEnd = ref("")
const blockReason = ref("设备维护或人工占用")
const route = useRoute()
const verification = createPrivateVerification({ lookup: code => api.get<TicketOrderLookup>(`/operations/orders/${encodeURIComponent(code)}`),
  verify: payload => api.post<VerifyPrivateResult>("/operations/rooms/verify-code", payload) }, requestId)
const { code: verifyCode, reason: verifyReason, busy: verifyBusy, error: verifyError, notice: verifyNotice, result: verifyResult } = toRefs(verification.state)
onBeforeUnmount(verification.dispose)
onMounted(() => { if (typeof route.query.code === "string") { verifyCode.value = route.query.code; verification.lookup() } })

function requestId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function verifyPrivate() {
  await verification.confirm()
  if (verifyResult.value) await load()
}

async function load() {
  loading.value = true
  error.value = ""
  try { rooms.value = await api.get<RoomBoardItem[]>("/operations/rooms/board") }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "房态读取失败" }
  finally { loading.value = false }
}

async function assign() {
  if (!bookingId.value) return
  error.value = ""; notice.value = ""
  try {
    const result = await api.post<{ room_number: string; room_use_id: string }>(`/operations/rooms/bookings/${bookingId.value.trim()}/assign`, {
      actual_start: new Date(actualStart.value).toISOString(), reason: assignReason.value,
    })
    notice.value = `已分房 ${result.room_number}，使用记录 ${result.room_use_id}`
    bookingId.value = ""
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "分房失败" }
}

async function useAction(room: RoomBoardItem, action: string) {
  if (!room.room_use_id) return
  try {
    if (action === "finish") await api.post(`/operations/rooms/uses/${room.room_use_id}/finish`, { reason: "前台确认使用结束" })
    if (action === "start") await api.post(`/operations/rooms/uses/${room.room_use_id}/cleaning/start`)
    if (action === "complete") await api.post(`/operations/rooms/uses/${room.room_use_id}/cleaning/complete`)
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "操作失败" }
}

async function createBlock() {
  try {
    await api.post("/operations/rooms/blocks", {
      room_id: blockRoom.value, start_at: new Date(blockStart.value).toISOString(),
      end_at: new Date(blockEnd.value).toISOString(), kind: "MANUAL", reason: blockReason.value,
    })
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "占用登记失败" }
}
</script>

<template>
  <PageHeader eyebrow="PRIVATE ONSEN VERIFICATION" title="私汤核验与房态" description="扫描购票订单二维码或输入订单编号完成私汤核验；未支付、已使用或冲突订单不会被强行分房。" />
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
    <section class="panel verify-panel">
      <div class="panel-head"><h2>私汤订单核验</h2><span class="muted">小白盒扫码 / 备用订单号</span></div>
      <form class="form-stack" @submit.prevent="verification.lookup">
        <label>私汤订单二维码 / 订单号 / 票券号
          <input v-model="verifyCode" :disabled="verifyBusy || verification.state.lookupBusy" autocomplete="off" placeholder="聚焦后用扫码枪扫描，回车查询订单" />
        </label>
        <label>核验原因 / 记录<input v-model="verifyReason" maxlength="500" /></label>
        <p class="hint">核验会按预约完整使用区间与清洁区间重新检查可用房，不会覆盖下一笔预约；冲突时交由前台人工处理。</p>
        <p v-if="verifyError" class="form-error">{{ verifyError }}</p>
        <p v-if="verifyNotice" class="success-note">{{ verifyNotice }}</p>
        <button class="button secondary" :disabled="verifyBusy || verification.state.lookupBusy || !verifyCode.trim()">{{ verification.state.lookupBusy ? "查询中…" : "查询所属订单" }}</button>
      </form>
      <div v-if="verification.state.order" class="verify-result">
        <strong class="mono">订单 {{ verification.state.order.order_no }}</strong>
        <span>订单金额 ¥{{ (verification.state.order.amount_cents / 100).toFixed(2) }} · {{ verification.state.order.status }}</span>
        <span>会员 {{ verification.state.order.member?.nickname ?? '—' }} · {{ verification.state.order.member?.phone_masked ?? '' }}</span>
        <template v-if="verification.state.order.private_booking">
          <span>预约日期 {{ verification.state.order.private_booking.visit_date }}</span>
          <span>预约时间 {{ formatDateTime(verification.state.order.private_booking.start_at) }} — {{ formatDateTime(verification.state.order.private_booking.end_at) }}</span>
          <span class="mono">票券 {{ verification.state.order.private_booking.ticket_no ?? '未签发' }}</span>
          <span>票券状态 {{ verification.state.order.private_booking.voucher_status === 'UNUSED' ? '待使用' : verification.state.order.private_booking.voucher_status === 'USED' ? '已核销' : '不可核销' }}</span>
          <p v-if="verification.state.order.refund_application?.status === 'PENDING'" class="form-error">退款审核中，暂停核销</p>
          <label><input v-model="verification.state.selected" type="checkbox" :disabled="!verification.eligible.value || verifyBusy" /> 核对并勾选本订单私汤票券</label>
          <button type="button" class="button primary" :disabled="!verification.canConfirm.value" @click="verifyPrivate">{{ verifyBusy ? '核验中…' : '确认核销并分房' }}</button>
        </template>
      </div>
      <div v-if="verifyResult" class="verify-result">
        <strong>{{ verifyResult.room_number }} 号房</strong>
        <span>状态 {{ verifyResult.status }}</span>
        <span>预计结束 {{ formatDateTime(verifyResult.actual_end_at) }}</span>
        <span class="mono">{{ verifyResult.room_use_id }}</span>
      </div>
    </section>
    <div class="room-board">
      <article v-for="room in rooms" :key="room.id" class="room-tile" :data-status="room.status">
        <div class="room-tile-head"><strong>{{ room.number }}</strong><StatusBadge :status="room.status" /></div>
        <p>结束 {{ formatDateTime(room.actual_end_at) }}</p><p>清洁至 {{ formatDateTime(room.cleaning_end_at) }}</p>
        <div class="tile-actions">
          <button v-if="room.status === 'ACTIVE' || room.status === 'IN_USE'" class="mini-button" @click="useAction(room, 'finish')">结束使用</button>
          <button v-if="room.status === 'PENDING_CLEANING'" class="mini-button" @click="useAction(room, 'start')">开始清洁</button>
          <button v-if="room.status === 'CLEANING'" class="mini-button" @click="useAction(room, 'complete')">清洁完成</button>
        </div>
      </article>
    </div>
    <p v-if="notice" class="success-note">{{ notice }}</p>
    <div class="two-column form-panels">
      <section class="panel"><div class="panel-head"><h2>到店分房</h2></div>
        <form class="form-stack" @submit.prevent="assign">
          <label>预约 ID<input v-model="bookingId" placeholder="booking id（用户端不显示房号）" /></label>
          <label>实际开始时间<input v-model="actualStart" type="datetime-local" /></label>
          <label>处理原因<textarea v-model="assignReason" rows="3" /></label>
          <button class="button primary" :disabled="!bookingId">重新检查并分房</button>
        </form>
      </section>
      <section class="panel"><div class="panel-head"><h2>维护 / 人工占用</h2></div>
        <form class="form-stack" @submit.prevent="createBlock">
          <label>房间<select v-model="blockRoom"><option v-for="room in rooms" :key="room.id" :value="room.id">{{ room.number }} 号房</option></select></label>
          <div class="form-row"><label>开始<input v-model="blockStart" type="datetime-local" /></label><label>结束<input v-model="blockEnd" type="datetime-local" /></label></div>
          <label>原因<textarea v-model="blockReason" rows="3" /></label>
          <button class="button secondary" :disabled="!blockRoom || !blockStart || !blockEnd">登记占用区间</button>
        </form>
      </section>
    </div>
  </DataState>
</template>
