<script setup>
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { request, payOrder, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"

const products = ref([])
const dayType = ref("WEEKDAY")
const priceError = ref("")
const product = computed(() => products.value.find(item => item.day_type === dayType.value))
const adult = ref(1)
const child = ref(0)
const adultPrice = computed(() => product.value?.adult_cents || 0)
const childPrice = computed(() => product.value?.child_cents || 0)
const adultDisplay = computed(() => formatMoney(adultPrice.value))
const childDisplay = computed(() => formatMoney(childPrice.value))
const paymentMethod = ref("WECHAT")
const submitting = ref(false)
const loading = ref(true)

const total = computed(() => formatMoney(adultPrice.value * adult.value + childPrice.value * child.value))

onLoad(loadPrices)

async function loadPrices() {
  loading.value = true
  priceError.value = ""
  try {
    const prices = await request("/catalog/ticket-products", { auth: false })
    if (!Array.isArray(prices) || !["WEEKDAY", "HOLIDAY"].every(kind => prices.some(item => item.day_type === kind && Number.isInteger(item.adult_cents) && item.adult_cents >= 0 && Number.isInteger(item.child_cents) && item.child_cents >= 0))) throw new Error("票价暂不可用，请重试")
    products.value = prices
  } catch (error) {
    products.value = []
    priceError.value = error.message || "票价读取失败"
    showError(error)
  } finally { loading.value = false }
}

function changeCount(type, delta) {
  if (type === "adult") adult.value = Math.max(0, Math.min(20 - child.value, adult.value + delta))
  else child.value = Math.max(0, Math.min(20 - adult.value, child.value + delta))
}

function selectPayment(method) {
  paymentMethod.value = method
}

async function submit() {
  if (submitting.value || loading.value || priceError.value || !product.value) return
  if (!adult.value && !child.value) {
    uni.showToast({ title: "请选择购票人数", icon: "none" })
    return
  }
  submitting.value = true
  try {
    const order = await request("/tickets/orders", {
      method: "POST",
      data: {
        day_type: dayType.value,
        adult_count: adult.value,
        child_count: child.value,
      },
    })
    const paid = await payOrder(order.order_no, paymentMethod.value)
    const mockNote = paymentMethod.value === "WECHAT" ? "（开发 Mock，非真实扣款）" : ""
    uni.showModal({
      title: paid.status === "PAID" ? "购票成功" : "订单已提交",
      content: `服务端确认金额 ¥${formatMoney(order.amount_cents)}${mockNote}`,
      showCancel: false,
      success: () => uni.switchTab({ url: "/pages/orders/index" }),
    })
  } catch (error) {
    showError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="page tickets-page">
    <view class="ticket-intro">
      <view>
        <text class="title">公共浴池入园票</text>
        <text class="desc">每位入园游客均需一张门票</text>
      </view>
      <image mode="aspectFill" src="/static/orders/ticket.jpg" />
    </view>
    <view class="tips">付款后30天内有效。工作日票适用于非节假日的周一至周五，节假日票适用于法定节假日。</view>

    <view class="form-section">
      <view class="step-head">
        <text>01</text>
        <view>
          <text>选择票种</text>
          <text>按实际入园当天的日期类型核销</text>
        </view>
      </view>
      <view class="ticket-types">
        <button v-for="item in products" :key="item.day_type" :class="{ active: dayType === item.day_type }" @tap="dayType = item.day_type">{{ item.name }}</button>
      </view>
      <text v-if="loading" class="ticket-price-state">正在读取票价…</text>
      <view v-if="priceError" class="ticket-price-state"><text>{{ priceError }}</text><button @tap="loadPrices">重新加载票价</button></view>
    </view>

    <view class="form-section">
      <view class="step-head">
        <text>02</text>
        <view>
          <text>选择购票人数</text>
          <text>支付后生成票券</text>
        </view>
      </view>
      <view class="guest">
        <view>
          <text>成人票 · ¥{{ adultDisplay }}</text>
          <text>付款后30天内使用</text>
        </view>
        <view class="counter">
          <button @tap="changeCount('adult', -1)">−</button>
          <text>{{ adult }}</text>
          <button @tap="changeCount('adult', 1)">＋</button>
        </view>
      </view>
      <view class="guest">
        <view>
          <text>儿童票 · ¥{{ childDisplay }}</text>
          <text>适用规则以商家为准</text>
        </view>
        <view class="counter">
          <button @tap="changeCount('child', -1)">−</button>
          <text>{{ child }}</text>
          <button @tap="changeCount('child', 1)">＋</button>
        </view>
      </view>
    </view>

    <view class="form-section">
      <view class="step-head">
        <text>03</text>
        <view>
          <text>支付方式</text>
        </view>
      </view>
      <view class="payment-methods" role="radiogroup" aria-label="支付方式">
        <button class="ticket-payment-card" :class="{ 'is-selected': paymentMethod === 'WECHAT' }" role="radio" :aria-checked="paymentMethod === 'WECHAT'" hover-class="ticket-payment-pressed" @tap="selectPayment('WECHAT')">
          <view class="ticket-payment-icon wechat-payment-icon" aria-hidden="true"><view class="wechat-bubble bubble-back" /><view class="wechat-bubble bubble-front" /></view>
          <text class="ticket-payment-label">微信支付</text>
          <view class="ticket-payment-check" aria-hidden="true" />
        </button>
        <button class="ticket-payment-card" :class="{ 'is-selected': paymentMethod === 'BALANCE' }" role="radio" :aria-checked="paymentMethod === 'BALANCE'" hover-class="ticket-payment-pressed" @tap="selectPayment('BALANCE')">
          <view class="ticket-payment-icon wallet-payment-icon" aria-hidden="true"><view class="wallet-outline"><view class="wallet-clasp" /></view></view>
          <text class="ticket-payment-label">会员余额</text>
          <view class="ticket-payment-check" aria-hidden="true" />
        </button>
      </view>
    </view>

    <view class="bottom-bar">
      <view><text>合计</text><text class="total"><text>¥</text>{{ total }}</text></view>
      <button :loading="submitting" :disabled="loading || submitting || !!priceError || !product" @tap="submit">{{ submitting ? "正在确认" : "确认购票" }}</button>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
