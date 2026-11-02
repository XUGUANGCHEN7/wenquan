const { request, showError } = require("../../utils/api")
const { formatMoney } = require("../../utils/money")

const statusNames = { NOT_READY: "待支付", QUEUED: "等待商家接单", ACCEPTED: "商家已接单", PREPARING: "制作中", DELIVERED: "已送达", EXCEPTION: "前台人工处理中" }

Page({
  data: { loading: true, orders: [] },
  onShow() { this.loadOrders() },

  async loadOrders() {
    this.setData({ loading: true })
    try {
      let orderNos = wx.getStorageSync("dining_order_nos") || []
      if (wx.getStorageSync("dining_member_token")) {
        const memberOrders = await request("/orders")
        orderNos = [...new Set([...orderNos, ...memberOrders.filter((item) => item.order_type === "FOOD").map((item) => item.order_no)])]
      }
      const orders = await Promise.all(orderNos.map(async (orderNo) => {
        try { return await request(`/dining/orders/${orderNo}`) } catch (error) { return null }
      }))
      this.setData({ loading: false, orders: orders.filter(Boolean).map((order) => ({
        ...order, amount: formatMoney(order.amount_cents), statusName: statusNames[order.fulfillment_status] || order.fulfillment_status,
        items: order.items.map((line) => ({ ...line, price: formatMoney(line.unit_price_cents) })),
        roomNumber: order.room_number || order.room_id.replace("room-", "")
      })) })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  }
})
