<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api } from "../api"
import type { FoodOrder } from "../api/types"
import { formatMoney, formatDateTime } from "../utils/format"
import PageHeader from "../components/PageHeader.vue"
import DataState from "../components/DataState.vue"
import StatusBadge from "../components/StatusBadge.vue"

const orders = ref<FoodOrder[]>([])
const loading = ref(true)
const error = ref("")
const reason = ref("商家按标准流程接单并更新状态")
const next: Record<string, string> = { QUEUED: "ACCEPTED", ACCEPTED: "PREPARING", PREPARING: "DELIVERED" }
const actionText: Record<string, string> = { QUEUED: "接单", ACCEPTED: "开始制作", PREPARING: "确认送达" }

async function load() {
  loading.value = true; error.value = ""
  try { orders.value = await api.get<FoodOrder[]>("/operations/dining/orders") }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "队列读取失败" }
  finally { loading.value = false }
}

async function advance(order: FoodOrder) {
  const target = next[order.fulfillment_status]
  if (!target) return
  try {
    await api.post(`/operations/dining/orders/${order.id}/transition`, { status: target, reason: reason.value })
    await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : "状态更新失败" }
}

onMounted(load)
</script>

<template>
  <PageHeader eyebrow="PAID & DELIVERABLE ONLY" title="商家出餐队列" description="只有支付确认且原 room_use_id 仍可送达的订单才进入队列；异常订单不会静默出现在待接单中。" />
  <section class="panel filter-panel"><label>操作记录原因<input v-model="reason" /></label><button class="button secondary" @click="load">刷新队列</button></section>
  <DataState :loading="loading" :error="error" :empty="orders.length === 0" empty-text="当前没有待处理或已完成的点餐订单" @retry="load">
    <div class="card-list">
      <article v-for="order in orders" :key="order.id" class="order-card">
        <div class="order-card-head"><div><span class="room-label">{{ order.room_number }} 号房</span><strong>{{ order.order_no }}</strong></div><StatusBadge :status="order.fulfillment_status" /></div>
        <div class="line-items"><span v-for="line in order.items" :key="line.name_snapshot">{{ line.name_snapshot }} × {{ line.quantity }}<small>{{ formatMoney(line.unit_price_cents) }}</small></span></div>
        <div class="order-meta"><span>合计 ¥{{ formatMoney(order.amount_cents) }}</span><span>下单 {{ formatDateTime(order.created_at) }}</span><span>送达 {{ formatDateTime(order.delivered_at) }}</span></div>
        <button v-if="next[order.fulfillment_status]" class="button primary compact" @click="advance(order)">{{ actionText[order.fulfillment_status] }}</button>
      </article>
    </div>
  </DataState>
</template>
