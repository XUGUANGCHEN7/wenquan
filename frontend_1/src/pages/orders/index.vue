<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const typeNames = { TICKET: "公共浴池门票", PRIVATE: "私汤预约", RECHARGE: "会员储值" }
const statusNames = { PENDING: "待支付", PAID: "已支付", EXCEPTION: "人工处理中", REFUNDED: "已退款" }
const loading = ref(true)
const orders = ref([])
const expanded = ref("")
const detail = ref(null)

onShow(() => loadOrders())

async function loadOrders() {
  loading.value = true
  try {
    const records = await request("/orders")
    orders.value = records.map((order) => ({
      ...order,
      typeName: typeNames[order.order_type] || order.order_type,
      statusName: statusNames[order.status] || order.status,
      amount: formatMoney(order.amount_cents),
    }))
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

async function toggle(order) {
  if (expanded.value === order.order_no) {
    expanded.value = ""
    detail.value = null
    return
  }
  expanded.value = order.order_no
  detail.value = null
  try {
    let record = null
    if (order.order_type === "TICKET") record = await request(`/tickets/orders/${order.order_no}`)
    if (order.order_type === "PRIVATE") record = await request(`/rooms/bookings/${order.business_id}`)
    detail.value = record
  } catch (error) {
    showError(error)
  }
}

function goHome() {
  uni.switchTab({ url: "/pages/home/index" })
}
</script>

<template>
  <view class="page orders-page">
    <view class="orders-heading">
      <text>MY JOURNEYS</text>
      <text>我的订单</text>
    </view>
    <view v-if="loading" class="empty">正在读取订单…</view>
    <view v-else-if="orders.length === 0" class="empty">
      <text>还没有订单</text><button @tap="goHome">去挑选一池好汤</button>
    </view>
    <view v-for="item in orders" :key="item.order_no" class="order-card">
      <button class="order-summary" @tap="toggle(item)">
        <view>
          <text>{{ item.typeName }}</text>
          <text :class="'status ' + item.status">{{ item.statusName }}</text>
        </view>
        <text class="order-no">{{ item.order_no }}</text>
        <view class="order-amount">
          <text>实付 / 应付</text>
          <text>¥{{ item.amount }}</text>
        </view>
      </button>
      <view v-if="expanded === item.order_no" class="order-detail">
        <template v-if="item.order_type === 'TICKET' && detail">
          <text>入园日期 {{ detail.visit_date }}</text>
          <view v-for="ticket in detail.tickets" :key="ticket.ticket_no" class="ticket-line">
            <text>{{ ticket.category === "ADULT" ? "成人票" : "儿童票" }} · {{ ticket.status === "USED" ? "已入园" : "待核验" }}</text>
            <text>{{ ticket.ticket_no }}</text>
          </view>
          <text v-if="detail.tickets.length === 0">支付完成后逐人生成票券</text>
        </template>
        <template v-if="item.order_type === 'PRIVATE' && detail">
          <text>预约日期 {{ detail.visit_date }}</text>
          <text>场次 {{ detail.start_at }} — {{ detail.end_at }}</text>
          <text>{{ detail.room_number ? "已分房 " + detail.room_number + " 号" : "到店后由前台分房，预约时未指定房号" }}</text>
        </template>
        <text v-if="!detail && item.order_type !== 'RECHARGE'">正在读取详情…</text>
        <text v-if="item.order_type === 'RECHARGE'">储值结果以服务端账本和支付状态为准</text>
      </view>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
