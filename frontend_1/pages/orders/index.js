const { request, showError } = require("../../utils/api")
const { formatMoney } = require("../../utils/money")

const typeNames = { TICKET: "公共浴池门票", PRIVATE: "私汤预约", RECHARGE: "会员储值" }
const statusNames = { PENDING: "待支付", PAID: "已支付", EXCEPTION: "人工处理中", REFUNDED: "已退款" }

Page({
  data: { loading: true, orders: [], expanded: "", detail: null },

  onShow() { this.loadOrders() },

  async loadOrders() {
    this.setData({ loading: true })
    try {
      const orders = await request("/orders")
      this.setData({
        loading: false,
        orders: orders.map((order) => ({
          ...order, typeName: typeNames[order.order_type] || order.order_type,
          statusName: statusNames[order.status] || order.status,
          amount: formatMoney(order.amount_cents)
        }))
      })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  async toggle(event) {
    const order = event.currentTarget.dataset.order
    if (this.data.expanded === order.order_no) {
      this.setData({ expanded: "", detail: null })
      return
    }
    this.setData({ expanded: order.order_no, detail: null })
    try {
      let detail = null
      if (order.order_type === "TICKET") detail = await request(`/tickets/orders/${order.order_no}`)
      if (order.order_type === "PRIVATE") detail = await request(`/rooms/bookings/${order.business_id}`)
      this.setData({ detail })
    } catch (error) { showError(error) }
  },

  goHome() { wx.switchTab({ url: "/pages/home/index" }) }
})
