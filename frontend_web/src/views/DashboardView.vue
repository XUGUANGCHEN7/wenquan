<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { api } from "../api"
import { useAuthStore } from "../stores/auth"
import type { Exceptions, RoomBoardItem } from "../api/types"
import { statusText } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"

const auth = useAuthStore()
const loading = ref(true)
const error = ref("")
const exceptions = ref<Exceptions | null>(null)
const rooms = ref<RoomBoardItem[]>([])
const status = ref<Record<string, string>>({})
const canViewExceptions = computed(() => auth.role !== "merchant")
const canViewRooms = computed(() => auth.role === "frontdesk" || auth.role === "admin")
const exceptionCount = computed(() => exceptions.value
  ? Object.values(exceptions.value).reduce((total, list) => total + list.length, 0) : 0)
const occupied = computed(() => rooms.value.filter((room) => ["ACTIVE", "IN_USE", "PENDING_CLEANING", "CLEANING"].includes(room.status)).length)

async function load() {
  loading.value = true
  error.value = ""
  try {
    status.value = await api.get<Record<string, string>>("/operations/status")
    const requests: Promise<unknown>[] = []
    if (canViewExceptions.value) requests.push(api.get<Exceptions>("/operations/exceptions").then((data) => { exceptions.value = data }))
    if (canViewRooms.value) requests.push(api.get<RoomBoardItem[]>("/operations/rooms/board").then((data) => { rooms.value = data }))
    await Promise.all(requests)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "加载失败"
  } finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="DAILY OPERATIONS" title="运营总览" description="以服务端状态为主，优先处理资金、设备未知与房间占用冲突。" />
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
    <section class="metric-grid">
      <article class="metric-card"><span>待处理异常</span><strong>{{ exceptionCount }}</strong><small>{{ canViewExceptions ? "退款、设备、冲突与送达" : "商家账号仅处理出餐队列" }}</small></article>
      <article class="metric-card"><span>占用中私汤房</span><strong>{{ canViewRooms ? occupied : "—" }}</strong><small>使用、待清洁与清洁中</small></article>
      <article class="metric-card"><span>支付模式</span><strong class="text-value">{{ status.payment_mode ?? "—" }}</strong><small>正式环境需替换支付适配器</small></article>
      <article class="metric-card"><span>设备模式</span><strong class="text-value">{{ status.device_mode ?? "—" }}</strong><small>真实 SDK/NFC 尚未联调</small></article>
    </section>
    <div class="dashboard-grid">
      <section class="panel"><div class="panel-head"><h2>今日工作提示</h2></div>
        <ol class="task-list">
          <li><span>01</span><div><strong>前台人工核验票券</strong><p>每张票只允许一次入园；闸机与自动重进不在本期范围。</p></div></li>
          <li><span>02</span><div><strong>分房前重查实际使用与清洁</strong><p>晚到可能撞上下一笔预约，冲突时不得覆盖或静默顺延。</p></div></li>
          <li><span>03</span><div><strong>设备结果未知时停止重试</strong><p>核实实体卡真实权限后再补偿，不自动释放柜位。</p></div></li>
        </ol>
      </section>
      <section class="panel"><div class="panel-head"><h2>异常分类</h2><RouterLink class="link-button" :to="canViewExceptions ? '/exceptions' : '/dining'">进入处理 →</RouterLink></div>
        <div v-if="canViewExceptions && exceptions" class="exception-summary">
          <RouterLink to="/exceptions"><span>待处理退款</span><strong>{{ exceptions.refunds.length }}</strong></RouterLink>
          <RouterLink to="/exceptions"><span>发卡结果未知</span><strong>{{ exceptions.device_unknown.length }}</strong></RouterLink>
          <RouterLink to="/exceptions"><span>房间占用冲突</span><strong>{{ exceptions.room_conflicts.length }}</strong></RouterLink>
          <RouterLink to="/exceptions"><span>点餐无法送达</span><strong>{{ exceptions.food_delivery.length }}</strong></RouterLink>
        </div>
        <p v-else class="muted">商家账号请从“商家出餐”进入已付款且可送达订单队列。</p>
      </section>
      <section v-if="canViewRooms" class="panel wide"><div class="panel-head"><h2>私汤房即时状态</h2><RouterLink class="link-button" to="/rooms">房态工作台 →</RouterLink></div>
        <div class="room-strip"><div v-for="room in rooms" :key="room.id" class="room-chip" :data-status="room.status"><strong>{{ room.number }}</strong><span>{{ statusText(room.status) }}</span></div></div>
      </section>
    </div>
  </DataState>
</template>
