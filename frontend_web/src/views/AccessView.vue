<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { api } from "../api"
import type { AccessOverview } from "../api/types"
import { formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

const data = ref<AccessOverview | null>(null)
const loading = ref(true)
const error = ref("")
const notice = ref("")
const depositId = ref("")
const cardId = ref("")
const bindingId = ref("")
const returnReason = ref("实物手牌已回收并核对该次发放记录")
const cleanLockerId = ref("")
const paidDeposits = computed(() => data.value?.deposits.filter((item) => item.status === "PAID") ?? [])
const boundCards = computed(() => data.value?.bindings.filter((item) => item.status === "BOUND") ?? [])

async function load() {
  loading.value = true; error.value = ""
  try { data.value = await api.get<AccessOverview>("/operations/access/overview") }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "读取失败" }
  finally { loading.value = false }
}

async function issue() {
  notice.value = ""
  try {
    const result = await api.post<{ binding_id: string; task: { task_no: string } }>("/operations/cards/issue", { deposit_id: depositId.value, card_id: cardId.value })
    notice.value = `已预占柜位并创建写卡任务 ${result.task.task_no}；设备成功前不视为正式绑定。`
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "发卡失败" }
}

async function returnCard() {
  try {
    const result = await api.post<{ refund_no: string; clear_task: { task_no: string } }>(`/operations/cards/${bindingId.value}/return`, { reason: returnReason.value })
    notice.value = `已登记归还，独立退款单 ${result.refund_no}；清卡任务 ${result.clear_task.task_no} 与退款不相互阻塞。`
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "归还失败" }
}

async function lockerCleaned() {
  try {
    await api.post(`/operations/lockers/${cleanLockerId.value}/cleaned`, { reason: "柜位已清理，可重新分配" })
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "释放柜位失败" }
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="PHYSICAL ACCESS CONTROL" title="手牌 · 柜位 · 逐枚押金" description="每位游客独立票券、押金和手牌。写卡结果未知时不自动释放或重试。" />
  <p v-if="notice" class="success-note">{{ notice }}</p>
  <DataState :loading="loading" :error="error" :empty="!data" @retry="load">
    <section v-if="data" class="metric-grid compact-metrics">
      <article class="metric-card"><span>可用手牌</span><strong>{{ data.cards.filter((c) => c.status === 'AVAILABLE').length }}</strong><small>共 {{ data.cards.length }} 枚</small></article>
      <article class="metric-card"><span>空闲柜位</span><strong>{{ data.lockers.filter((l) => l.status === 'FREE').length }}</strong><small>共 {{ data.lockers.length }} 个</small></article>
      <article class="metric-card"><span>已付押金</span><strong>{{ paidDeposits.length }}</strong><small>逐枚独立退款责任</small></article>
      <article class="metric-card"><span>未知设备任务</span><strong>{{ data.device_tasks.filter((t) => t.status === 'UNKNOWN').length }}</strong><small>需核实实体卡</small></article>
    </section>
    <div class="two-column form-panels">
      <section class="panel"><div class="panel-head"><h2>发牌并写卡</h2></div>
        <form class="form-stack" @submit.prevent="issue">
          <label>已付押金<select v-model="depositId"><option value="">选择押金</option><option v-for="deposit in paidDeposits" :key="deposit.id" :value="deposit.id">{{ deposit.id }} · ¥{{ formatMoney(deposit.amount_cents) }}</option></select></label>
          <label>可用实体手牌<select v-model="cardId"><option value="">选择手牌</option><option v-for="card in data?.cards.filter(c => c.status === 'AVAILABLE')" :key="card.id" :value="card.id">{{ card.id }} · {{ card.physical_uid }}</option></select></label>
          <button class="button primary" :disabled="!depositId || !cardId">预占柜位并创建写卡任务</button>
        </form>
      </section>
      <section class="panel"><div class="panel-head"><h2>归还与独立退款</h2></div>
        <form class="form-stack" @submit.prevent="returnCard">
          <label>已绑定手牌<select v-model="bindingId"><option value="">选择绑定</option><option v-for="binding in boundCards" :key="binding.id" :value="binding.id">{{ binding.id }} · {{ binding.card_id }}</option></select></label>
          <label>归还核对原因<textarea v-model="returnReason" rows="3" /></label>
          <button class="button secondary" :disabled="!bindingId">登记实物归还</button>
        </form>
      </section>
    </div>
    <section class="panel"><div class="panel-head"><h2>柜位与设备任务</h2></div>
      <div class="split-lists">
        <div class="simple-list"><div v-for="locker in data?.lockers" :key="locker.id" class="simple-row"><span>{{ locker.number }} 号柜</span><StatusBadge :status="locker.status" /><button v-if="locker.status === 'CLEANING'" class="mini-button" @click="cleanLockerId = locker.id; lockerCleaned()">清洁完成并释放</button></div></div>
        <div class="simple-list"><div v-for="task in data?.device_tasks.slice(0, 15)" :key="task.id" class="simple-row"><span>{{ task.task_type }}</span><StatusBadge :status="task.status" /><small>{{ task.raw_error || task.task_no }}</small></div></div>
      </div>
    </section>
  </DataState>
</template>
