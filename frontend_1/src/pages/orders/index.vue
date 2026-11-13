<script setup>
import { computed } from "vue"
import { onHide, onShow, onUnload } from "@dcloudio/uni-app"
import { request } from "../../utils/api.js"
import { getToken, redirectToLogin } from "../../utils/session.js"
import { categories, createOrdersModel, presentOrder } from "./model.js"

const model = createOrdersModel({ request, getToken })
const { state } = model
const cards = computed(() => model.visibleOrders.value.map(order => ({
  ...presentOrder(order, state.details[order.order_no]?.data),
  detail: state.details[order.order_no],
})))
onShow(model.load)
onHide(model.invalidate)
onUnload(model.invalidate)

function selectCategory(value) {
  state.category = value
  state.expanded = ""
}
function goHome() { uni.switchTab({ url: "/pages/home/index" }) }
function goLogin() { redirectToLogin("/pages/orders/index") }
function ticketStatus(status) {
  return { UNUSED: "待核验", USED: "已入园", REFUNDED: "已退款", INVALID: "已失效" }[status] || status
}
function slotTime(value) { return value ? String(value).replace("T", " ").slice(0, 16) : "待确认" }
</script>

<template>
  <view class="page orders-page">
    <view class="orders-heading">
      <text class="orders-eyebrow">MY JOURNEYS</text>
      <text class="orders-title sn-serif">我的订单</text>
      <view class="orders-heading-line" />
      <view class="orders-steam steam-one" />
      <view class="orders-steam steam-two" />
    </view>

    <view class="orders-tabs">
      <button
        v-for="category in categories" :key="category.value"
        class="orders-tab" :class="{ 'is-active': state.category === category.value }"
        :aria-label="category.label" :aria-pressed="state.category === category.value"
        hover-class="orders-button-pressed" @tap="selectCategory(category.value)"
      >{{ category.label }}</button>
    </view>

    <view v-if="state.guest" class="orders-empty">
      <text class="orders-empty-title sn-serif">登录后查看订单</text>
      <text class="orders-empty-copy">你的温泉旅程，都在这里</text>
      <button class="orders-primary" @tap="goLogin">登录 / 注册</button>
    </view>
    <view v-else-if="state.loading" class="orders-empty">
      <view class="orders-loading" />
      <text class="orders-empty-copy">正在读取订单…</text>
    </view>
    <view v-else-if="state.error" class="orders-empty">
      <text class="orders-empty-title sn-serif">订单暂时未能加载</text>
      <text class="orders-empty-copy">{{ state.error }}</text>
      <button class="orders-primary" @tap="model.load">重新加载</button>
    </view>
    <view v-else-if="cards.length === 0" class="orders-empty">
      <text class="orders-empty-title sn-serif">{{ state.orders.length ? '暂无此类订单' : '还没有订单' }}</text>
      <text class="orders-empty-copy">挑选一池好汤，开启松弛时光</text>
      <button class="orders-primary" @tap="goHome">去挑选一池好汤</button>
    </view>

    <view v-for="item in cards" :key="item.order_no" class="order-card">
      <view class="order-summary">
        <image v-if="item.image" class="order-image" :src="item.image" mode="aspectFill" />
        <view class="order-copy">
          <view class="order-header">
            <text class="order-title sn-serif">{{ item.title }}</text>
            <text class="order-status" :class="'status-' + item.status">{{ item.statusLabel }}</text>
          </view>
          <view class="order-meta">
            <text v-if="item.order_type !== 'PRIVATE'" class="order-description">{{ item.summary }}</text>
            <text v-if="item.date" class="order-date">{{ item.date }}</text>
            <text v-if="item.order_type === 'PRIVATE'" class="order-description">{{ item.summary }}</text>
            <text v-if="item.detail?.loading" class="order-detail-hint">正在读取{{ item.order_type === 'TICKET' ? '票券' : '预约' }}信息…</text>
            <text class="order-no">订单号 {{ item.order_no }}</text>
          </view>
          <view class="order-footer">
            <view class="order-amount">
              <text class="order-amount-label">{{ item.amountLabel }}</text>
              <text class="order-price">{{ item.amount === '—' ? '金额待确认' : '¥' + item.amount }}</text>
            </view>
            <button class="order-detail-button" hover-class="orders-button-pressed" @tap="model.toggle(item)">
              {{ state.expanded === item.order_no ? '收起详情' : '查看详情' }}
            </button>
          </view>
        </view>
      </view>

      <view v-if="item.detail?.error" class="order-error">
        <text>详情读取失败：{{ item.detail.error }}</text>
        <button class="order-retry" @tap="model.ensureDetail(item)">重试</button>
      </view>
      <view v-if="state.expanded === item.order_no" class="order-detail">
        <template v-if="item.order_type === 'TICKET' && item.detail?.data">
          <text class="order-detail-title">票券信息</text>
          <text>入园日期 {{ item.detail.data.visit_date }}</text>
          <view v-for="ticket in item.detail.data.tickets" :key="ticket.ticket_no" class="ticket-line">
            <text>{{ ticket.category === 'ADULT' ? '成人票' : ticket.category === 'CHILD' ? '儿童票' : ticket.category }} · {{ ticketStatus(ticket.status) }}</text>
            <text class="ticket-number">{{ ticket.ticket_no }}</text>
          </view>
          <text v-if="!item.detail.data.tickets?.length">支付完成后逐人生成票券</text>
        </template>
        <template v-else-if="item.order_type === 'PRIVATE' && item.detail?.data">
          <text class="order-detail-title">预约信息</text>
          <text>预约日期 {{ item.detail.data.visit_date }}</text>
          <text>预约场次 {{ slotTime(item.detail.data.start_at) }} — {{ slotTime(item.detail.data.end_at) }}</text>
          <text>{{ item.summary }}</text>
        </template>
        <text v-else-if="item.order_type === 'RECHARGE'">储值结果以服务端账本和支付状态为准</text>
        <text v-else-if="item.detail?.error">请重试读取详情</text>
        <text v-else-if="item.detail?.loading">正在读取详情…</text>
        <text v-else>暂无更多详情</text>
      </view>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
