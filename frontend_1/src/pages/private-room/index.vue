<script setup>
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { request, payOrder, showError } from "../../utils/api"
import { formatMoney } from "../../utils/money"
import { orderDetailUrl } from "../orders/navigation"

const banners = ["/static/images/private-room/banner-01.png", "/static/images/private-room/banner-02.png"]
const dates = ref([])
const dateIndex = ref(-1)
const slots = ref([])
const selected = ref([])
const unitPrice = ref(0)
const expectedArrival = ref("10:00")
const paymentMethod = ref("WECHAT")
const loading = ref(true)
const datesLoading = ref(true)
const loadError = ref("")
const submitting = ref(false)
const quoting = ref(false)
const quote = ref(null)
const pendingBooking = ref(null)
const creationUncertain = ref(false)
let slotRequest = 0
let quoteRequest = 0
const unitPriceDisplay = computed(() => formatMoney(unitPrice.value))
const total = computed(() => formatMoney(pendingBooking.value?.amount_cents ?? quote.value?.amount_cents ?? selected.value.length * unitPrice.value))
const selectedDate = computed(() => dates.value[dateIndex.value]?.value || "")
const selectionSummary = computed(() => {
  if (!selectedDate.value) return "请选择到店日期"
  const picked = selected.value.map(index => slots.value[index])
  return `${selectedDate.value.slice(5).replace("-", "/")} ${picked.length ? picked[0].start + "—" + picked[picked.length - 1].end + " · " + picked.length + "场" : "请选择场次"}`
})
const canSubmit = computed(() => !creationUncertain.value && !!selectedDate.value && selected.value.length > 0 && !loading.value && !quoting.value && !submitting.value && quote.value?.available > 0)

onLoad(loadDates)
async function loadDates() {
  datesLoading.value = true
  loading.value = true
  loadError.value = ""
  try {
    const result = await request("/rooms/dates", { auth: false })
    dates.value = result.dates
    dateIndex.value = dates.value.findIndex(item => item.available)
    if (dateIndex.value >= 0) await loadSlots()
    else { slots.value = []; loading.value = false }
  } catch (error) {
    loadError.value = error.message || "预约信息加载失败"
    loading.value = false
    showError(error)
  } finally { datesLoading.value = false }
}
async function loadSlots() {
  const version = ++slotRequest
  ++quoteRequest
  loading.value = true
  selected.value = []
  slots.value = []
  quote.value = null
  quoting.value = false
  unitPrice.value = 0
  loadError.value = ""
  const visitDate = selectedDate.value
  if (!visitDate) { loading.value = false; return }
  try {
    const result = await request(`/rooms/slots?visit_date=${visitDate}`, { auth: false })
    if (version !== slotRequest) return
    slots.value = result.slots
    unitPrice.value = result.unit_price_cents
  } catch (error) {
    if (version !== slotRequest) return
    loadError.value = error.message || "场次加载失败"
    showError(error)
  } finally { if (version === slotRequest) loading.value = false }
}
function selectDate(index) {
  if (submitting.value || pendingBooking.value || !dates.value[index]?.available || index === dateIndex.value) return
  dateIndex.value = index
  return loadSlots()
}
async function selectSlot(index) {
  if (loading.value || submitting.value || pendingBooking.value) return
  const slot = slots.value[index]
  if (!slot || slot.available <= 0) return
  let next
  if (selected.value.includes(index) || selected.value.length > 1) next = [index]
  else if (!selected.value.length) next = [index]
  else {
    const from = Math.min(selected.value[0], index)
    const to = Math.max(selected.value[0], index)
    next = Array.from({ length: to - from + 1 }, (_, offset) => from + offset)
    if (next.some(item => slots.value[item].available <= 0)) {
      uni.showToast({ title: "连续区间中存在不可售场次", icon: "none" })
      return
    }
  }
  selected.value = next
  quote.value = null
  quoting.value = true
  const version = ++quoteRequest
  try {
    const indices = next.map(item => slots.value[item].slot_index)
    const result = await request(`/rooms/availability?visit_date=${selectedDate.value}&slots=${indices.join(",")}`, { auth: false })
    if (version !== quoteRequest) return
    quote.value = result
    if (result.available <= 0) uni.showToast({ title: "暂无房间可覆盖所选连续场次", icon: "none" })
  } catch (error) { if (version === quoteRequest) showError(error) }
  finally { if (version === quoteRequest) quoting.value = false }
}
function selectArrival(event) {
  if (!submitting.value && !pendingBooking.value) expectedArrival.value = event.detail.value
}
function selectPayment(method) { if (!submitting.value) paymentMethod.value = method }
function showNotice() {
  uni.showModal({ title: "预约须知", content: "预约时不选择具体房号，到店后由前台分房。先后点选起止场次可选择连续区间，连续预约仅末场清洁；库存以服务端对同一房间完整使用及清洁区间的校验为准。待支付预占保留15分钟，实际使用从前台分房起算。晚到冲突由前台处理，取消与退款按现有业务规则执行。", showCancel: false })
}
function openBooking() {
  if (pendingBooking.value) uni.navigateTo({ url: orderDetailUrl(pendingBooking.value) })
}
function openOrders() { uni.switchTab({ url: "/pages/orders/index" }) }
async function submit() {
  if (submitting.value || (!pendingBooking.value && !canSubmit.value)) return
  submitting.value = true
  try {
    if (!pendingBooking.value) {
      try { pendingBooking.value = await request("/rooms/bookings", {
        method: "POST",
        data: { visit_date: selectedDate.value, slot_indices: selected.value.map(index => slots.value[index].slot_index),
          expected_arrival_at: `${selectedDate.value}T${expectedArrival.value}:00` },
      }) } catch (error) {
        if (!error.code || error.code === "HTTP_ERROR") creationUncertain.value = true
        throw error
      }
    }
    const paid = await payOrder(pendingBooking.value.order_no, paymentMethod.value)
    uni.showModal({ title: paid.status === "PAID" ? "预约已确认" : "预约等待人工处理",
      content: `服务端金额 ¥${formatMoney(pendingBooking.value.amount_cents)}。到店后由前台分房。${paymentMethod.value === "WECHAT" ? "（开发 Mock 支付）" : ""}`,
      showCancel: false, success: openBooking })
  } catch (error) { showError(error) }
  finally { submitting.value = false }
}
</script>

<template>
  <view class="page private-page">
    <swiper class="room-banner" autoplay circular :interval="4000" :duration="500" indicator-dots indicator-color="rgba(255,255,255,.5)" indicator-active-color="#246B61">
      <swiper-item v-for="src in banners" :key="src"><image :src="src" mode="aspectFit" /></swiper-item>
    </swiper>
    <view class="facilities">
      <view><view class="facility-icon"><image src="/static/images/private-room/pool.png" mode="aspectFit" /></view><text>独立汤池</text></view>
      <view><view class="facility-icon"><image src="/static/images/private-room/lounge.png" mode="aspectFit" /></view><text>休息空间</text></view>
      <view><view class="facility-icon"><image src="/static/images/private-room/sauna.png" mode="aspectFit" /></view><text>包含桑拿</text></view>
      <view><view class="facility-icon"><image src="/static/images/private-room/door.png" mode="aspectFit" /></view><text>到店分房</text></view>
    </view>
    <view class="reservation-panel">
      <view class="room-heading"><view><text class="title">选择到店日期</text><text class="en">VISIT DATE</text></view><button class="notice-link" @tap="showNotice">查看预约须知 ›</button></view>
      <view v-if="datesLoading" class="room-state">正在加载预约日期…</view>
      <view v-else-if="!dates.length" class="room-state"><text>{{ loadError || "暂无可预约日期" }}</text><button @tap="loadDates">重新加载</button></view>
      <scroll-view v-else class="private-dates" scroll-x :show-scrollbar="false">
        <button v-for="(item, index) in dates" :key="item.value" :class="{ active: dateIndex === index }" :disabled="!item.available || submitting || !!pendingBooking" @tap="selectDate(index)">
          <text>{{ item.label }}</text><text>{{ item.value.slice(5).replace('-', '/') }}</text><text v-if="!item.available" class="date-unavailable">不可预约</text>
        </button>
      </scroll-view>
    </view>
    <view class="reservation-panel">
      <view class="room-heading"><view><text class="title">选择连续场次</text><text class="en">CONSECUTIVE SLOTS</text></view><text class="slot-price">¥{{ unitPriceDisplay }} / 场</text></view>
      <view v-if="loading" class="room-state">正在查询场次及库存…</view>
      <view v-else-if="loadError" class="room-state"><text>{{ loadError }}</text><button @tap="loadSlots">重新加载</button></view>
      <view v-else-if="!slots.length" class="room-state">暂无可预约场次</view>
      <view v-else class="slot-options">
        <button v-for="(item, index) in slots" :key="item.slot_index" :class="{ active: selected.includes(index), 'is-sold-out': item.available <= 0 }" :disabled="item.available <= 0 || submitting || !!pendingBooking" @tap="selectSlot(index)">
          <text class="slot-time">{{ item.start }} – {{ item.end }}</text>
          <view class="slot-meta"><text>{{ item.available > 0 ? '可订 ' + item.available + ' 间' : '已售罄' }}</text><view class="slot-check" /></view>
        </button>
      </view>
      <text v-if="quoting" class="availability-note">正在核对连续场次库存…</text>
      <text v-else-if="selected.length && !quote" class="availability-note">库存查询失败，请重新选择场次</text>
      <text v-else-if="quote && quote.available <= 0" class="availability-note">所选连续场次暂无同一房间可预约，请调整选择</text>
      <text v-else class="availability-note">先后点选起止场次，连续预约仅末场清洁</text>
    </view>
    <view class="booking-card arrival-card">
      <picker mode="time" :value="expectedArrival" :disabled="submitting || !!pendingBooking" @change="selectArrival"><view><text class="label">预计到店时间</text><text>{{ expectedArrival }}</text><text>›</text></view></picker>
    </view>
    <view class="form-section private-payment">
      <view class="step-head">
        <text>03</text>
        <view><text>支付方式</text></view>
      </view>
      <view class="payment-methods" role="radiogroup" aria-label="支付方式">
        <button class="room-payment-card" :class="{ 'is-selected': paymentMethod === 'WECHAT' }" role="radio" :aria-checked="paymentMethod === 'WECHAT'" hover-class="room-payment-pressed" @tap="selectPayment('WECHAT')">
          <view class="room-payment-icon wechat-payment-icon" aria-hidden="true"><view class="wechat-bubble bubble-back" /><view class="wechat-bubble bubble-front" /></view>
          <text class="room-payment-label">微信支付</text>
          <view class="room-payment-check" aria-hidden="true" />
        </button>
        <button class="room-payment-card" :class="{ 'is-selected': paymentMethod === 'BALANCE' }" role="radio" :aria-checked="paymentMethod === 'BALANCE'" hover-class="room-payment-pressed" @tap="selectPayment('BALANCE')">
          <view class="room-payment-icon wallet-payment-icon" aria-hidden="true"><view class="wallet-outline"><view class="wallet-clasp" /></view></view>
          <text class="room-payment-label">会员余额</text>
          <view class="room-payment-check" aria-hidden="true" />
        </button>
      </view>
    </view>
    <view v-if="creationUncertain" class="booking-reminder"><text>暂未确认创建结果，请先到订单页核对，避免重复预约。</text><button @tap="openOrders">前往订单页</button></view>
    <view v-if="pendingBooking" class="booking-reminder"><text>订单已创建，重试支付会沿用此订单。若订单已过期，请在订单页确认后重新预约。</text><button @tap="openBooking">查看订单</button></view>
    <view class="private-bottom">
      <view class="settlement-copy"><text class="settlement-amount"><text>¥</text>{{ total }}<text class="estimate-label">{{ pendingBooking ? '订单金额' : '预估合计' }}</text></text><text class="settlement-summary">已选：{{ selectionSummary }}</text></view>
      <button :loading="submitting" :disabled="submitting || (!pendingBooking && !canSubmit)" @tap="submit">{{ submitting ? '正在处理' : pendingBooking ? '继续支付' : '立即预约 →' }}</button>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
