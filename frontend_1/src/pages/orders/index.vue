<script setup>
import { computed, ref } from "vue"
import { onHide, onShow, onUnload } from "@dcloudio/uni-app"
import { request } from "../../utils/api.js"
import { getToken, redirectToLogin } from "../../utils/session.js"
import { categories, createOrdersModel, presentOrder } from "./model.js"
import { getOrderExamples } from "./examples.js"
import { orderDetailUrl } from "./navigation.js"

const model = createOrdersModel({ request, getToken })
const { state } = model
const refundTarget = ref("")
const refundReason = ref("")
const refundBusy = ref(false)
const refundError = ref("")
const memberFilter = ref("")
const voucherLoading = computed(() => memberFilter.value === "VOUCHERS" && Object.values(state.details).some(detail => detail.loading))
const cards = computed(() => model.visibleOrders.value.map(order => ({
  ...presentOrder(order, state.details[order.order_no]?.data),
  detail: state.details[order.order_no],
})).filter(order => memberFilter.value === "REFUND" ? !!order.refund_application || order.status === "REFUNDED" : memberFilter.value === "VOUCHERS" ? order.statusKey === "UNUSED" : true))
onShow(() => {
  const filter = uni.getStorageSync("member_order_filter")
  if (["ALL", "TICKET", "PRIVATE", "RECHARGE", "REFUND", "VOUCHERS"].includes(filter)) {
    uni.removeStorageSync("member_order_filter")
    memberFilter.value = ["REFUND", "VOUCHERS"].includes(filter) ? filter : ""
    state.category = ["TICKET", "PRIVATE", "RECHARGE"].includes(filter) ? filter : "ALL"
  }
  return state.exampleMode ? loadExamples() : model.load()
})
onHide(model.invalidate)
onUnload(model.invalidate)

function selectCategory(value) {
  memberFilter.value = ""
  state.category = value
  state.expanded = ""
}
function loadExamples() {
  model.invalidate()
  state.exampleMode = true
  state.guest = false
  state.error = ""
  state.orders = getOrderExamples()
  for (const order of state.orders) state.details[order.order_no] = { loading: false, data: order.example_detail, error: "" }
}
function openRefund(orderNo) {
  refundTarget.value = orderNo
  refundReason.value = ""
  refundError.value = ""
}
async function submitRefund() {
  if (refundBusy.value) return
  refundBusy.value = true
  refundError.value = ""
  try {
    const application = await model.submitRefund(refundTarget.value, refundReason.value)
    if (application) { refundTarget.value = ""; uni.showToast({ title: state.exampleMode ? "示例申请已演示" : "申请已提交，等待审核", icon: "none" }) }
  } catch (error) { refundError.value = error.message || "申请失败，请重试" }
  finally { refundBusy.value = false }
}
function goHome() { uni.switchTab({ url: "/pages/home/index" }) }
function goLogin() { redirectToLogin("/pages/orders/index") }
function goDetails(order) {
  uni.navigateTo({ url: orderDetailUrl(order, state.exampleMode) })
}
</script>

<template>
  <view class="page orders-page">
    <view v-if="memberFilter" class="orders-member-filter"><text>{{ memberFilter === 'REFUND' ? '退款记录' : '我的卡券 · 待使用' }}</text><button @tap="selectCategory('ALL')">查看全部订单</button></view>
    <view v-if="state.exampleMode" class="orders-example-note">示例预览 · 非真实购买记录，示例票券号不能用于前台核销。真实票券需付款后由服务端签发。</view>

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
    <view v-else-if="state.loading || voucherLoading" class="orders-empty">
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
            <text class="order-status" :class="'status-' + item.statusKey">{{ item.statusLabel }}</text>
          </view>
          <view class="order-meta">
            <text class="order-description">{{ item.specification }}</text>
            <text v-if="item.date" class="order-date">{{ item.date }}</text>
            <text v-if="item.detail?.loading" class="order-detail-hint">正在读取{{ item.order_type === 'TICKET' ? '票券' : '预约' }}信息…</text>
            <text v-if="item.refund_application?.status === 'REJECTED'" class="order-detail-hint">退款申请未通过：{{ item.refund_application.review_reason }}</text>
          </view>
          <view class="order-footer">
            <view class="order-amount">
              <text class="order-amount-label">{{ item.amountLabel }}</text>
              <text class="order-price">{{ item.amount === '—' ? '金额待确认' : '¥' + item.amount }}</text>
            </view>
            <button class="order-detail-button" hover-class="orders-button-pressed" @tap="goDetails(item)">
              查看详情
            </button>
          </view>
          <button v-if="item.canRefund" class="order-refund-button" @tap="openRefund(item.order_no)">申请退款</button>
        </view>
      </view>
      <view v-if="refundTarget === item.order_no && item.canRefund" class="order-refund-form">
        <text>申请整单退款</text>
        <text class="order-detail-hint">提交后等待审核，审核期间暂停核销。</text>
        <textarea v-model="refundReason" class="order-refund-reason" maxlength="500" placeholder="请填写退款原因" />
        <text v-if="refundError" class="order-refund-error">{{ refundError }}</text>
        <view class="order-refund-actions">
          <button class="order-detail-button" :disabled="refundBusy" @tap="refundTarget = ''">取消</button>
          <button class="order-detail-button" :disabled="refundBusy" @tap="submitRefund">{{ refundBusy ? '正在提交…' : '提交申请' }}</button>
        </view>
      </view>

      <view v-if="item.detail?.error" class="order-error">
        <text>详情读取失败：{{ item.detail.error }}</text>
        <button class="order-retry" @tap="model.ensureDetail(item)">重试</button>
      </view>

    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
