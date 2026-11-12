<script setup>
import { ref } from "vue"
import { onShow } from "@dcloudio/uni-app"
import { request, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const statusNames = {
  NOT_READY: "待支付",
  QUEUED: "等待商家接单",
  ACCEPTED: "商家已接单",
  PREPARING: "制作中",
  DELIVERED: "已送达",
  EXCEPTION: "前台人工处理中",
}
const loading = ref(true)
const orders = ref([])

onShow(() => loadOrders())

async function loadOrders() {
  loading.value = true
  try {
    let orderNos = uni.getStorageSync("dining_order_nos") || []
    if (uni.getStorageSync("dining_member_token")) {
      const memberOrders = await request("/orders")
      orderNos = [...new Set([
        ...orderNos,
        ...memberOrders.filter((item) => item.order_type === "FOOD").map((item) => item.order_no),
      ])]
    }
    const records = await Promise.all(orderNos.map(async (orderNo) => {
      try {
        return await request(`/dining/orders/${orderNo}`)
      } catch (error) {
        return null
      }
    }))
    orders.value = records.filter(Boolean).map((order) => ({
      ...order,
      amount: formatMoney(order.amount_cents),
      statusName: statusNames[order.fulfillment_status] || order.fulfillment_status,
      items: order.items.map((line) => ({ ...line, price: formatMoney(line.unit_price_cents) })),
      roomNumber: order.room_number || order.room_id.replace("room-", ""),
    }))
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <view class="page dining-orders">
    <view class="orders-title"><text class="eyebrow">DINING JOURNEY</text><text class="page-title">点餐订单</text></view>
    <view v-if="loading" class="empty">正在读取订单…</view>
    <view v-else-if="orders.length === 0" class="empty">暂无本机可查的点餐订单；会员登录后可查询账号订单。</view>
    <view v-for="order in orders" :key="order.order_no" class="dining-order-card">
      <view class="order-top">
        <text>送至 {{ order.roomNumber }} 号私汤房</text>
        <text class="fulfillment" :class="order.fulfillment_status">{{ order.statusName }}</text>
      </view>
      <view v-for="line in order.items" :key="line.name_snapshot" class="order-line">
        <text>{{ line.name_snapshot }} × {{ line.quantity }}</text><text>¥{{ line.price }}</text>
      </view>
      <view class="order-total"><text>合计</text><text>¥{{ order.amount }}</text></view>
      <text class="order-no">{{ order.order_no }}</text>
      <view v-if="order.fulfillment_status === 'EXCEPTION'" class="exception-note">{{ order.exception_reason }}。订单未自动退款，请由前台按权限处理。</view>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
