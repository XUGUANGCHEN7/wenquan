<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api } from "../api"
import type { RoomBoardItem } from "../api/types"
import { formatDateTime, statusText } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

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
  <PageHeader eyebrow="ROOM STATE & ASSIGNMENT" title="私汤房态与分房" description="预约不指定房号；实际使用从前台分房起算。未完成清洁不得再次分房。" />
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
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
