<script setup>
import { computed, ref } from "vue"
import { onLoad, onShow } from "@dcloudio/uni-app"
import { request, payOrder, showError } from "../../utils/api"
import { parseRoomCode } from "../../utils/room-code"
import { updateCart, cartTotal } from "../../utils/cart"
import { formatMoney } from "../../utils/money"

const roomCode = ref("ROOM-01")
const roomOptions = ref([])
const roomIndex = ref(0)
const roomLabel = ref("正在读取房间")
const roomNumber = ref("--")
const canOrder = ref(false)
const message = ref("")
const loading = ref(true)
const merchants = ref([])
const selectedMerchantId = ref("")
const merchantName = ref("")
const products = ref([])
const menuLoading = ref(true)
const counts = ref([])
const paymentMethod = ref("WECHAT")
const memberLoggedIn = ref(false)
const submitting = ref(false)
const loadError = ref("")
const menuError = ref("")
let menuRequestId = 0

const quantity = computed(() => counts.value.reduce((sum, count) => sum + count, 0))
const total = computed(() => formatMoney(cartTotal(products.value, counts.value)))

onLoad((options) => {
  const code = parseRoomCode(options)
  roomCode.value = code
  uni.setStorageSync("dining_room_code", code)
  loadAll()
})

onShow(() => {
  memberLoggedIn.value = Boolean(uni.getStorageSync("dining_member_token"))
  if (!loading.value) {
    if (!merchants.value.length) loadAll()
    else loadRoomContext(roomCode.value)
  }
})

async function loadAll() {
  loading.value = true
  loadError.value = ""
  menuError.value = ""
  const errors = []
  let rooms = []
  let merchantData = []
  let context = null
  try {
    rooms = await request("/dining/rooms", { auth: false })
  } catch (error) {
    errors.push(`房间列表：${error.message || "请求失败"}`)
  }
  try {
    merchantData = await request("/dining/merchants", { auth: false })
  } catch (error) {
    errors.push(`商家列表：${error.message || "请求失败"}`)
  }
  try {
    context = await request(`/dining/room-context/${roomCode.value}`, { auth: false })
  } catch (error) {
    errors.push(`房间状态：${error.message || "请求失败"}`)
  }

  roomOptions.value = rooms.map((room) => ({
    ...room,
    label: `${room.room_number} 号房 · ${room.can_order ? "可下单" : "暂不可下单"}`,
  }))
  let index = roomOptions.value.findIndex((room) => room.room_code === roomCode.value)
  if (index < 0) index = 0
  if (!roomOptions.value.length && context) {
    roomOptions.value.push({
      room_code: context.room_code,
      room_number: context.room_number,
      can_order: context.can_order,
      label: `${context.room_number} 号房 · ${context.can_order ? "可下单" : "暂不可下单"}`,
    })
    index = 0
  }
  const nextMerchantId = merchantData.some((merchant) => merchant.id === selectedMerchantId.value)
    ? selectedMerchantId.value
    : (merchantData[0] ? merchantData[0].id : "")
  const nextMerchant = merchantData.find((merchant) => merchant.id === nextMerchantId)
  const selectedRoom = roomOptions.value[index]
  roomIndex.value = index
  roomLabel.value = selectedRoom ? selectedRoom.label : (context ? `${context.room_number} 号房` : "请选择房间")
  roomNumber.value = context ? context.room_number : (selectedRoom ? selectedRoom.room_number : "--")
  canOrder.value = context ? context.can_order : false
  message.value = context ? (context.message || "") : ""
  merchants.value = merchantData
  selectedMerchantId.value = nextMerchantId
  merchantName.value = nextMerchant ? nextMerchant.name : ""
  loadError.value = errors.length
    ? `${errors.join("；")}。请确认后端已启动、手机与电脑同一网络，并检查开发版合法域名设置。`
    : ""
  if (nextMerchantId) await loadMenu(nextMerchantId)
  else menuLoading.value = false
  if (errors.length) showError(new Error(errors[0]))
  loading.value = false
}

async function loadRoomContext(code) {
  try {
    const context = await request(`/dining/room-context/${code}`, { auth: false })
    roomOptions.value = roomOptions.value.map((room) => room.room_code === code
      ? { ...room, can_order: context.can_order, label: `${room.room_number} 号房 · ${context.can_order ? "可下单" : "暂不可下单"}` }
      : room)
    const index = roomOptions.value.findIndex((room) => room.room_code === code)
    if (index >= 0) roomIndex.value = index
    roomLabel.value = index >= 0 ? roomOptions.value[index].label : `${context.room_number} 号房`
    roomNumber.value = context.room_number
    canOrder.value = context.can_order
    message.value = context.message || ""
  } catch (error) {
    canOrder.value = false
    loadError.value = `房间状态读取失败：${error.message || "请求失败"}`
    showError(error)
  }
}

async function selectRoom(event) {
  const index = Number(event.detail.value)
  const room = roomOptions.value[index]
  if (!room || room.room_code === roomCode.value) return
  roomCode.value = room.room_code
  roomIndex.value = index
  roomLabel.value = room.label
  roomNumber.value = room.room_number
  canOrder.value = room.can_order
  message.value = ""
  loadError.value = ""
  counts.value = []
  uni.setStorageSync("dining_room_code", room.room_code)
  await loadRoomContext(room.room_code)
}

async function selectMerchant(merchantId) {
  if (merchantId === selectedMerchantId.value) return
  await loadMenu(merchantId)
}

async function loadMenu(merchantId) {
  if (!merchantId) {
    selectedMerchantId.value = ""
    merchantName.value = ""
    products.value = []
    counts.value = []
    menuLoading.value = false
    return
  }
  const requestId = ++menuRequestId
  const merchant = merchants.value.find((item) => item.id === merchantId)
  selectedMerchantId.value = merchantId
  merchantName.value = merchant ? merchant.name : ""
  menuLoading.value = true
  products.value = []
  counts.value = []
  menuError.value = ""
  try {
    const menu = await request(`/dining/menu?merchant_id=${encodeURIComponent(merchantId)}`, { auth: false })
    if (requestId !== menuRequestId) return
    products.value = menu.map((item) => ({
      ...item,
      price: formatMoney(item.price_cents),
      mark: (item.name || "餐").slice(0, 1),
    }))
    counts.value = products.value.map(() => 0)
  } catch (error) {
    if (requestId === menuRequestId) {
      menuError.value = `菜单读取失败：${error.message || "请求失败"}`
      showError(error)
    }
  } finally {
    if (requestId === menuRequestId) menuLoading.value = false
  }
}

function changeCount(index, delta) {
  counts.value = updateCart(counts.value, index, delta)
}

function selectPayment(method) {
  if (method === "BALANCE" && !memberLoggedIn.value) {
    uni.showToast({ title: "请先在“会员”页明确登录", icon: "none" })
    return
  }
  paymentMethod.value = method
}

async function submit() {
  if (!quantity.value || submitting.value) {
    if (!quantity.value) uni.showToast({ title: "请先选择商品", icon: "none" })
    return
  }
  submitting.value = true
  try {
    const items = counts.value
      .map((count, index) => ({ menu_item_id: products.value[index].id, quantity: count }))
      .filter((line) => line.quantity > 0)
    const order = await request("/dining/orders", {
      method: "POST",
      data: { room_code: roomCode.value, items },
    })
    const paid = await payOrder(order.order_no, paymentMethod.value)
    const stored = uni.getStorageSync("dining_order_nos") || []
    uni.setStorageSync("dining_order_nos", [...new Set([order.order_no, ...stored])].slice(0, 50))
    const exception = paid.fulfillment_status === "EXCEPTION"
    uni.showModal({
      title: exception ? "支付已确认，等待前台处理" : "点餐成功",
      content: exception
        ? "当前房间无法送达，订单已进入人工异常队列，未自动退款。"
        : `送至 ${roomNumber.value} 号私汤房。${paymentMethod.value === "WECHAT" ? "（开发 Mock 支付）" : ""}`,
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
  <view class="page room-page">
    <view class="room-top">
      <view><text class="eyebrow">私汤房点餐</text><text class="room-current">{{ roomNumber }} 号房</text></view>
      <picker :range="roomOptions" range-key="label" :value="roomIndex" @change="selectRoom">
        <view class="room-picker"><text>{{ roomLabel }}</text><text class="chevron">⌄</text></view>
      </picker>
    </view>
    <view class="delivery" :class="{ unavailable: !canOrder }">选择送餐房间 · 房间号仅用于定位，不证明访客身份或会员余额权限</view>
    <view v-if="loadError" class="load-error"><text>{{ loadError }}</text><button @tap="loadAll">重新加载</button></view>
    <view v-if="!canOrder && !loading && !loadError" class="room-warning">{{ message || "当前房间暂不可下单，请选择其他房间或联系前台" }}</view>

    <view v-if="loading" class="empty">正在读取房间、商家与菜单…</view>
    <view v-else class="dining-layout">
      <scroll-view class="merchant-rail" scroll-y>
        <view class="rail-title">商家</view>
        <view v-for="merchant in merchants" :key="merchant.id" class="merchant-tab" :class="{ active: selectedMerchantId === merchant.id }" @tap="selectMerchant(merchant.id)">
          <text class="merchant-tab-name">{{ merchant.name }}</text><text class="merchant-tab-count">{{ merchant.item_count }} 件</text>
        </view>
        <view v-if="merchants.length === 0" class="rail-empty">暂无营业商家</view>
      </scroll-view>

      <scroll-view class="product-panel" scroll-y>
        <view v-if="merchantName" class="shop-head"><text class="shop-name">{{ merchantName }}</text><text class="shop-note">价格与库存由服务端确认</text></view>
        <view v-if="menuError" class="empty menu-error">{{ menuError }}</view>
        <view v-else-if="menuLoading" class="empty">正在读取商品…</view>
        <view v-else-if="!selectedMerchantId" class="empty">请选择左侧商家</view>
        <view v-else-if="products.length === 0" class="empty">该商家暂未上架商品</view>
        <view v-else class="products">
          <view v-for="(item, index) in products" :key="item.id" class="product-card" :class="{ 'sold-out': !item.available || item.stock === 0 }">
            <view class="product-image">
              <image v-if="item.image_url" :src="item.image_url" mode="aspectFill" />
              <text v-else>{{ item.mark }}</text>
            </view>
            <view class="product-info">
              <text class="product-name">{{ item.name }}</text>
              <text class="product-desc">{{ item.description || "现点现做" }}</text>
              <text class="product-category">{{ item.category }} · {{ item.stock === null ? "库存以后台为准" : "可售 " + item.stock }}</text>
              <text class="product-price">¥{{ item.price }}</text>
            </view>
            <view class="counter">
              <button :disabled="counts[index] === 0" @tap="changeCount(index, -1)">−</button>
              <text>{{ counts[index] }}</text>
              <button :disabled="!item.available || item.stock === 0" @tap="changeCount(index, 1)">＋</button>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="checkout-panel">
      <view class="payment-methods">
        <button :class="{ active: paymentMethod === 'WECHAT' }" @tap="selectPayment('WECHAT')">本人微信支付</button>
        <button :class="{ active: paymentMethod === 'BALANCE' }" @tap="selectPayment('BALANCE')">会员余额{{ memberLoggedIn ? "" : "（先登录）" }}</button>
      </view>
      <view class="checkout-bar">
        <view><text>{{ merchantName || "请选择商家" }} · 已选 {{ quantity }} 件</text><text>¥{{ total }}</text></view>
        <button :loading="submitting" :disabled="!canOrder || !selectedMerchantId || !quantity || submitting" @tap="submit">提交点餐</button>
      </view>
    </view>
  </view>
</template>

<style>
@import "./style.css";
</style>
