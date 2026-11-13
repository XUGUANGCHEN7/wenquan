<script setup lang="ts">
import { onMounted, ref } from "vue"
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
const verifyCode = ref("")
const verifyReason = ref("私汤订单前台核验并分房")
const verifyBusy = ref(false)
const verifyError = ref("")
const verifyNotice = ref("")
const verifyResult = ref<VerifyPrivateResult | null>(null)

function requestId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function verifyPrivate() {
  const code = verifyCode.value.trim()
  if (!code || verifyBusy.value) return
  verifyBusy.value = true
  verifyError.value = ""
  verifyNotice.value = ""
  verifyResult.value = null
  try {
    const result = await api.post<VerifyPrivateResult>("/operations/rooms/verify-code", {
      code, request_id: requestId(), reason: verifyReason.value,
    })
    verifyResult.value = result
    verifyNotice.value = result?.already_verified ? "该私汤订单已完成核验" : "核验成功，已记录使用开始时间"
    verifyCode.value = ""
    await load()
  } catch (cause) {
    verifyError.value = cause instanceof Error ? cause.message : "私汤核验失败"
  } finally { verifyBusy.value = false }
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
      <form class="form-stack" @submit.prevent="verifyPrivate">
        <label>私汤订单二维码 / 订单号 / 预约 ID
          <input v-model="verifyCode" autocomplete="off" placeholder="扫码枪扫描，或输入订单编号" />
        </label>
        <label>核验原因 / 记录<input v-model="verifyReason" maxlength="500" /></label>
        <p class="hint">核验会按预约完整使用区间与清洁区间重新检查可用房，不会覆盖下一笔预约；冲突时交由前台人工处理。</p>
        <p v-if="verifyError" class="form-error">{{ verifyError }}</p>
        <p v-if="verifyNotice" class="success-note">{{ verifyNotice }}</p>
        <button class="button primary" :disabled="verifyBusy || !verifyCode.trim()">{{ verifyBusy ? "正在核验…" : "核验并分房" }}</button>
      </form>
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
