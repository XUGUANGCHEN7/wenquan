Page({
  data: {
    orders: []
  },

  onShow() {
    this.syncOrders()
    this.startTick()
  },

  onHide() {
    if (this.tick) {
      clearInterval(this.tick)
      this.tick = null
    }
  },

  onUnload() {
    if (this.tick) clearInterval(this.tick)
  },

  // 从全局订单列表同步：按状态生成展示字段
  syncOrders() {
    const app = getApp()
    const orders = (app.globalData.pickupOrders || []).map((o) => ({
      ...o,
      stateText: o.state === "ready" ? "请取餐" : o.state === "done" ? "已取餐" : "制作中"
    }))
    this.setData({ orders })
  },

  // 模拟后厨链路：下单 30 秒后自动出餐（"请取餐"）
  startTick() {
    if (this.tick) return
    this.tick = setInterval(() => {
      const app = getApp()
      const orders = app.globalData.pickupOrders || []
      let changed = false
      orders.forEach((o) => {
        if (o.state === "making" && Date.now() - o.createdTs >= 30000) {
          o.state = "ready"
          changed = true
        }
      })
      if (changed) this.syncOrders()
    }, 1000)
  },

  markDone(event) {
    const id = event.currentTarget.dataset.id
    const app = getApp()
    ;(app.globalData.pickupOrders || []).forEach((o) => {
      if (o.id === id) o.state = "done"
    })
    this.syncOrders()
  },

  goHome() {
    wx.switchTab({ url: "/pages/home/index" })
  }
})
