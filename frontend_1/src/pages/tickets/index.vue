<script setup>
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { request, payOrder, showError } from "../../utils/api"
import { formatMoney, dateInput, dateLabel } from "../../utils/money"

const dates = ref([])
const dateIndex = ref(0)
const adult = ref(1)
const child = ref(0)
const adultPrice = ref(0)
const childPrice = ref(0)
const adultDisplay = ref("0.00")
const childDisplay = ref("0.00")
const paymentMethod = ref("WECHAT")
const submitting = ref(false)
const loading = ref(true)

const total = computed(() => formatMoney(adultPrice.value * adult.value + childPrice.value * child.value))

onLoad(() => {
  dates.value = Array.from({ length: 7 }, (_, index) => {
    const value = dateInput(index)
    return { value, label: dateLabel(value), display: value.slice(5).replace("-", "/") }
  })
  loadPrices()
})

async function loadPrices() {
  loading.value = true
  const visitDate = dates.value[dateIndex.value]?.value
  if (!visitDate) return
  try {
    const prices = await request(`/catalog/ticket-prices?visit_date=${visitDate}`, { auth: false })
    adultPrice.value = prices.adult_cents
    childPrice.value = prices.child_cents
    adultDisplay.value = formatMoney(prices.adult_cents)
    childDisplay.value = formatMoney(prices.child_cents)
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

function selectDate(index) {
  dateIndex.value = index
  loadPrices()
}

function changeCount(type, delta) {
  if (type === "adult") adult.value = Math.max(0, adult.value + delta)
  else child.value = Math.max(0, child.value + delta)
}

function selectPayment(method) {
  paymentMethod.value = method
}

async function submit() {
  if (submitting.value) return
  if (!adult.value && !child.value) {
    uni.showToast({ title: "请选择购票人数", icon: "none" })
    return
  }
  submitting.value = true
  try {
    const order = await request("/tickets/orders", {
      method: "POST",
      data: {
        visit_date: dates.value[dateIndex.value].value,
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
        <text class="en">PUBLIC BATH</text>
        <text class="title">公共浴池入园票</text>
        <text class="desc">每位实际入园游客均需一张独立门票</text>
      </view>
      <image mode="aspectFill" src="https://images.unsplash.com/photo-1706189767508-8df45439f92c?auto=format&fit=crop&w=700&q=85" />
    </view>
    <view class="tips">平日 29 元，周末及后台配置节假日 49 元；每票仅支持一次人工核验入园，儿童规则与价格以服务端配置为准。</view>

    <view class="form-section">
      <view class="step-head">
        <text>01</text>
        <view>
          <text>选择入园日期</text>
          <text>价格由服务端按日期返回</text>
        </view>
      </view>
      <scroll-view class="dates" scroll-x>
        <button
          v-for="(item, index) in dates"
          :key="item.value"
          :class="{ active: dateIndex === index }"
          @tap="selectDate(index)"
        >
          <text>{{ item.label }}</text>
          <text>{{ item.display }}</text>
        </button>
      </scroll-view>
    </view>

    <view class="form-section">
      <view class="step-head">
        <text>02</text>
        <view>
          <text>选择购票人数</text>
          <text>支付后逐人生成独立票券</text>
        </view>
      </view>
      <view class="guest">
        <view>
          <text>成人票 · ¥{{ adultDisplay }}</text>
          <text>成交时保存价格快照</text>
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
          <text>适用规则以现场及后台配置为准</text>
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
          <text>支付结果以服务端查询为准</text>
        </view>
      </view>
      <view class="payment-methods">
        <button :class="{ active: paymentMethod === 'WECHAT' }" @tap="selectPayment('WECHAT')">微信支付</button>
        <button :class="{ active: paymentMethod === 'BALANCE' }" @tap="selectPayment('BALANCE')">会员余额</button>
      </view>
    </view>

    <view class="bottom-bar">
      <view><text>服务端价格预估</text><text class="total"><text>¥</text>{{ total }}</text></view>
      <button :loading="submitting" :disabled="loading || submitting" @tap="submit">{{ submitting ? "正在确认" : "确认购票" }}</button>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
