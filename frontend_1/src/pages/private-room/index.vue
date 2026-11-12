<script setup>
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { request, payOrder, showError } from "../../utils/api"
import { formatMoney, dateInput, dateLabel } from "../../utils/money"

const hero = "https://images.unsplash.com/photo-1712232907812-4bd219a99a49?auto=format&fit=crop&w=1200&q=85"
const dates = ref([])
const dateIndex = ref(0)
const slots = ref([])
const selected = ref([])
const unitPrice = ref(0)
const expectedArrival = ref("10:00")
const paymentMethod = ref("WECHAT")
const loading = ref(true)
const submitting = ref(false)
const unitPriceDisplay = computed(() => formatMoney(unitPrice.value))
const total = computed(() => formatMoney(selected.value.length * unitPrice.value))

onLoad(() => {
  dates.value = Array.from({ length: 7 }, (_, index) => {
    const value = dateInput(index)
    return { value, label: `${dateLabel(value)} ${value.slice(5).replace("-", "/")}` }
  })
  loadSlots()
})

async function loadSlots() {
  loading.value = true
  selected.value = []
  const visitDate = dates.value[dateIndex.value]?.value
  if (!visitDate) return
  try {
    const result = await request(`/rooms/slots?visit_date=${visitDate}`, { auth: false })
    slots.value = result.slots
    unitPrice.value = result.unit_price_cents
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

function selectDate(index) {
  dateIndex.value = index
  loadSlots()
}

function selectSlot(index) {
  const slot = slots.value[index]
  if (!slot.available) {
    uni.showToast({ title: "该场次暂不可预约", icon: "none" })
    return
  }
  let next = selected.value
  if (next.includes(index) || next.length > 1) next = [index]
  else if (!next.length) next = [index]
  else {
    const from = Math.min(next[0], index)
    const to = Math.max(next[0], index)
    next = Array.from({ length: to - from + 1 }, (_, offset) => from + offset)
    if (next.some((item) => !slots.value[item].available)) {
      uni.showToast({ title: "连续区间中存在不可售场次", icon: "none" })
      return
    }
  }
  selected.value = next
}

function selectArrival(event) {
  expectedArrival.value = event.detail.value
}

function selectPayment(method) {
  paymentMethod.value = method
}

async function submit() {
  if (!selected.value.length || submitting.value) {
    if (!selected.value.length) uni.showToast({ title: "请选择连续场次", icon: "none" })
    return
  }
  submitting.value = true
  try {
    const visitDate = dates.value[dateIndex.value].value
    const booking = await request("/rooms/bookings", {
      method: "POST",
      data: {
        visit_date: visitDate,
        slot_indices: selected.value,
        expected_arrival_at: `${visitDate}T${expectedArrival.value}:00`,
      },
    })
    const paid = await payOrder(booking.order_no, paymentMethod.value)
    uni.showModal({
      title: paid.status === "PAID" ? "预约已确认" : "预约等待人工处理",
      content: `服务端金额 ¥${formatMoney(booking.amount_cents)}。到店后由前台分房，本订单未指定房号。${paymentMethod.value === "WECHAT" ? "（开发 Mock 支付）" : ""}`,
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
  <view class="page private-page">
    <view class="room-hero">
      <image mode="aspectFill" :src="hero" />
      <view class="shade" />
      <view class="hero-copy"><text>PRIVATE ONSEN</text><text>私汤场次预约</text><text>120 分钟 / 场 · 含桑拿 · 连续场次仅最后清洁一次</text></view>
    </view>
    <view class="facilities">
      <view><text>汤</text><text>独立汤池</text></view><view><text>憩</text><text>休息空间</text></view>
      <view><text>桑</text><text>包含桑拿</text></view><view><text>房</text><text>到店分房</text></view>
    </view>

    <view class="section-head room-head"><view><text class="en">VISIT DATE</text><text class="title">选择到店日期</text></view></view>
    <scroll-view class="dates private-dates" scroll-x>
      <button v-for="(item, index) in dates" :key="item.value" :class="{ active: dateIndex === index }" @tap="selectDate(index)">{{ item.label }}</button>
    </scroll-view>

    <view class="section-head room-head"><view><text class="en">CONSECUTIVE SLOTS</text><text class="title">选择连续场次</text></view><text class="more">¥{{ unitPriceDisplay }} / 场</text></view>
    <view class="slot-options">
      <button v-for="(item, index) in slots" :key="item.slot_index" :class="{ active: selected.includes(index) }" :disabled="item.available === 0" @tap="selectSlot(index)">
        <text>{{ item.start }}—{{ item.end }}</text><text>{{ item.available > 0 ? "可售 " + item.available + " 间" : "暂不可售" }}</text>
      </button>
    </view>
    <view class="availability-note">先后点选起止场次可选择连续区间；最终可售由服务端按同一房间的完整使用及清洁区间确认。</view>

    <view class="booking-card arrival-card">
      <picker mode="time" :value="expectedArrival" @change="selectArrival">
        <view><text class="label">预计到店时间</text><text>{{ expectedArrival }}</text><text>›</text></view>
      </picker>
    </view>
    <view class="form-section private-payment">
      <view class="payment-methods">
        <button :class="{ active: paymentMethod === 'WECHAT' }" @tap="selectPayment('WECHAT')">微信支付</button>
        <button :class="{ active: paymentMethod === 'BALANCE' }" @tap="selectPayment('BALANCE')">会员余额</button>
      </view>
    </view>
    <view class="notice"><text>预约与分房说明</text><text>预约时不选择具体房号；待支付预占保留 15 分钟。实际使用从前台分房起算，若晚到造成冲突，将交由前台处理，不会覆盖下一笔预约。取消与退款政策以业务方确认规则为准。</text></view>

    <view class="private-bottom">
      <view><text>{{ selected.length }} 场 · 服务端价格预估</text><text><text>¥</text>{{ total }}</text></view>
      <button :loading="submitting" :disabled="!selected.length || submitting" @tap="submit">提交预约</button>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
