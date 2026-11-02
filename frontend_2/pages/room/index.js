const { request, payOrder, showError } = require("../../utils/api")
const { parseRoomCode } = require("../../utils/room-code")
const { updateCart, cartTotal } = require("../../utils/cart")
const { formatMoney } = require("../../utils/money")

Page({
  data: {
    roomCode: "ROOM-01", roomOptions: [], roomIndex: 0, roomLabel: "正在读取房间",
    roomNumber: "--", canOrder: false, message: "", loading: true,
    merchants: [], selectedMerchantId: "", merchantName: "", products: [], menuLoading: true,
    counts: [], quantity: 0, total: "0.00",
    paymentMethod: "WECHAT", memberLoggedIn: false, submitting: false
  },

  onLoad(options) {
    const roomCode = parseRoomCode(options)
    getApp().globalData.roomCode = roomCode
    wx.setStorageSync("dining_room_code", roomCode)
    this.setData({ roomCode }, () => this.loadAll())
  },

  onShow() {
    this.setData({ memberLoggedIn: Boolean(wx.getStorageSync("dining_member_token")) })
    if (this.data.merchants.length) this.loadRoomContext(this.data.roomCode)
  },

  async loadAll() {
    this.setData({ loading: true })
    try {
      const [rooms, merchants, context] = await Promise.all([
        request("/dining/rooms", { auth: false }),
        request("/dining/merchants", { auth: false }),
        request(`/dining/room-context/${this.data.roomCode}`, { auth: false })
      ])
      const roomOptions = rooms.map((room) => ({
        ...room, label: `${room.room_number} 号房 · ${room.can_order ? "可下单" : "暂不可下单"}`
      }))
      let roomIndex = roomOptions.findIndex((room) => room.room_code === this.data.roomCode)
      if (roomIndex < 0) roomIndex = 0
      const selectedMerchantId = merchants.some((merchant) => merchant.id === this.data.selectedMerchantId)
        ? this.data.selectedMerchantId : (merchants[0] ? merchants[0].id : "")
      this.setData({
        roomOptions, roomIndex,
        roomLabel: roomOptions[roomIndex] ? roomOptions[roomIndex].label : `${context.room_number} 号房`,
        roomNumber: context.room_number, canOrder: context.can_order, message: context.message || "",
        merchants, selectedMerchantId,
        merchantName: merchants.find((merchant) => merchant.id === selectedMerchantId)?.name || ""
      })
      await this.loadMenu(selectedMerchantId)
    } catch (error) {
      this.setData({ canOrder: false, menuLoading: false })
      showError(error)
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadRoomContext(roomCode) {
    try {
      const context = await request(`/dining/room-context/${roomCode}`, { auth: false })
      const roomOptions = this.data.roomOptions.map((room) => room.room_code === roomCode
        ? { ...room, can_order: context.can_order, label: `${room.room_number} 号房 · ${context.can_order ? "可下单" : "暂不可下单"}` }
        : room)
      const roomIndex = roomOptions.findIndex((room) => room.room_code === roomCode)
      this.setData({
        roomOptions, roomIndex: roomIndex < 0 ? this.data.roomIndex : roomIndex,
        roomLabel: roomOptions[roomIndex] ? roomOptions[roomIndex].label : `${context.room_number} 号房`,
        roomNumber: context.room_number, canOrder: context.can_order, message: context.message || "",
      })
    } catch (error) {
      this.setData({ canOrder: false })
      showError(error)
    }
  },

  async selectRoom(event) {
    const roomIndex = Number(event.detail.value)
    const room = this.data.roomOptions[roomIndex]
    if (!room || room.room_code === this.data.roomCode) return
    getApp().globalData.roomCode = room.room_code
    wx.setStorageSync("dining_room_code", room.room_code)
    this.setData({
      roomCode: room.room_code, roomIndex, roomLabel: room.label, roomNumber: room.room_number,
      canOrder: room.can_order, message: "", counts: [], quantity: 0, total: "0.00"
    })
    await this.loadRoomContext(room.room_code)
  },

  async selectMerchant(event) {
    const merchantId = event.currentTarget.dataset.id
    if (merchantId === this.data.selectedMerchantId) return
    await this.loadMenu(merchantId)
  },

  async loadMenu(merchantId) {
    if (!merchantId) {
      this.setData({ selectedMerchantId: "", merchantName: "", products: [], counts: [], quantity: 0, total: "0.00", menuLoading: false })
      return
    }
    const requestId = (this._menuRequestId || 0) + 1
    this._menuRequestId = requestId
    const merchant = this.data.merchants.find((item) => item.id === merchantId)
    this.setData({
      selectedMerchantId: merchantId, merchantName: merchant ? merchant.name : "",
      menuLoading: true, products: [], counts: [], quantity: 0, total: "0.00"
    })
    try {
      const menu = await request(`/dining/menu?merchant_id=${encodeURIComponent(merchantId)}`, { auth: false })
      if (requestId !== this._menuRequestId) return
      const products = menu.map((item) => ({
        ...item, price: formatMoney(item.price_cents), mark: (item.name || "餐").slice(0, 1)
      }))
      this.setData({ products, counts: products.map(() => 0), quantity: 0, total: "0.00", menuLoading: false })
    } catch (error) {
      if (requestId === this._menuRequestId) {
        this.setData({ menuLoading: false })
        showError(error)
      }
    }
  },

  changeCount(event) {
    const index = Number(event.currentTarget.dataset.index)
    const counts = updateCart(this.data.counts, index, Number(event.currentTarget.dataset.delta))
    const quantity = counts.reduce((sum, count) => sum + count, 0)
    this.setData({ counts, quantity, total: formatMoney(cartTotal(this.data.products, counts)) })
  },

  selectPayment(event) {
    const method = event.currentTarget.dataset.method
    if (method === "BALANCE" && !this.data.memberLoggedIn) {
      wx.showToast({ title: "请先在“会员”页明确登录", icon: "none" })
      return
    }
    this.setData({ paymentMethod: method })
  },

  async submit() {
    if (!this.data.quantity || this.data.submitting) {
      if (!this.data.quantity) wx.showToast({ title: "请先选择商品", icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      const items = this.data.counts.map((quantity, index) => ({ menu_item_id: this.data.products[index].id, quantity }))
        .filter((line) => line.quantity > 0)
      const order = await request("/dining/orders", { method: "POST", data: { room_code: this.data.roomCode, items } })
      const paid = await payOrder(order.order_no, this.data.paymentMethod)
      const stored = wx.getStorageSync("dining_order_nos") || []
      wx.setStorageSync("dining_order_nos", [...new Set([order.order_no, ...stored])].slice(0, 50))
      const exception = paid.fulfillment_status === "EXCEPTION"
      wx.showModal({
        title: exception ? "支付已确认，等待前台处理" : "点餐成功",
        content: exception ? "当前房间无法送达，订单已进入人工异常队列，未自动退款。" : `送至 ${this.data.roomNumber} 号私汤房。${this.data.paymentMethod === "WECHAT" ? "（开发 Mock 支付）" : ""}`,
        showCancel: false,
        success: () => wx.switchTab({ url: "/pages/orders/index" })
      })
    } catch (error) { showError(error) } finally {
      this.setData({ submitting: false })
    }
  }
})
