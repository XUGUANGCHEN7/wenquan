<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api } from "../api"
import type { Exceptions } from "../api/types"
import { formatMoney } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

const data = ref<Exceptions | null>(null)
const loading = ref(true)
const error = ref("")

async function load() {
  loading.value = true; error.value = ""
  try { data.value = await api.get<Exceptions>("/operations/exceptions") }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "异常看板读取失败" }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <PageHeader eyebrow="HUMAN EXCEPTION QUEUE" title="异常看板" description="异常只展示事实与人工处理入口。退款、换房或补偿不得由前端自动判定。" ><button class="button secondary" @click="load">刷新</button></PageHeader>
  <DataState :loading="loading" :error="error" :empty="false" @retry="load">
    <div class="exception-grid">
      <section class="panel"><div class="panel-head"><h2>待处理退款</h2><span>{{ data?.refunds.length ?? 0 }}</span></div><p class="hint">只有微信通知或主动查询确认 SUCCESS 才显示退款成功。</p><div v-for="item in data?.refunds" :key="item.refund_no" class="simple-row"><span class="mono">{{ item.refund_no }}</span><StatusBadge :status="item.status" /><strong>¥{{ formatMoney(item.amount_cents) }}</strong></div></section>
      <section class="panel"><div class="panel-head"><h2>已付款未交付</h2><span>{{ data?.paid_exceptions.length ?? 0 }}</span></div><p class="hint">预约过期、加钟冲突或点餐不可送达的已付款订单，可由财务人工受理退款。</p><div v-for="item in data?.paid_exceptions" :key="item.order_no" class="simple-row"><span class="mono">{{ item.order_no }}</span><StatusBadge :status="item.status" /><strong>¥{{ formatMoney(item.amount_cents) }}</strong></div></section>
      <section class="panel"><div class="panel-head"><h2>发卡结果未知</h2><span>{{ data?.device_unknown.length ?? 0 }}</span></div><p class="hint">先核实实体卡真实权限，不盲目重试或释放柜位。</p><div v-for="item in data?.device_unknown" :key="item.id" class="simple-row"><span class="mono">{{ item.task_no }}</span><small>{{ item.raw_error || "无原始错误" }}</small></div></section>
      <section class="panel"><div class="panel-head"><h2>房间占用冲突</h2><span>{{ data?.room_conflicts.length ?? 0 }}</span></div><p class="hint">按业务方签认的改期/退款流程处理并记录结果。</p><div v-for="item in data?.room_conflicts" :key="item.id" class="simple-row"><span class="mono">{{ item.id }}</span><StatusBadge :status="item.status" /></div></section>
      <section class="panel"><div class="panel-head"><h2>点餐无法送达</h2><span>{{ data?.food_delivery.length ?? 0 }}</span></div><p class="hint">不自动退款、不静默进入商家待接单队列。</p><div v-for="item in data?.food_delivery" :key="item.id" class="simple-row"><span>{{ item.reason }}</span></div></section>
    </div>
  </DataState>
</template>
