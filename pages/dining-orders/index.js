Page({
  data: {
    active: null,
    others: []
  },

  onShow() {
    this.syncOrders()
    this.startTick()
  },

  onHide() {
    this.stopTick()
  },

  onUnload() {
    this.stopTick()
  },

  stopTick() {
    if (this.tick) {
      clearInterval(this.tick)
      this.tick = null
    }
  },

  // 从全局订单同步：最新一单作为醒目取餐卡，其余收在下面
  syncOrders() {
    const app = getApp()
    const sorted = (app.globalData.pickupOrders || [])
      .map((o) => ({
        ...o,
        stateText: o.state === "ready" ? "请取餐" : o.state === "done" ? "已取餐" : "制作中",
        fulfillText: o.fulfillment === "delivery" ? "送至 " + o.room + " 私汤房" : o.window,
        itemText: o.items.map((it) => it.name + " × " + it.qty).join(" · ")
      }))
      .sort((a, b) => b.createdTs - a.createdTs)

    // 尚未取餐的最新一单优先展示，取完后自动轮到下一单
    const activeIndex = sorted.findIndex((o) => o.state !== "done")
    const active = activeIndex >= 0 ? sorted[activeIndex] : null
    const others = sorted.filter((o, i) => i !== activeIndex)
    this.setData({ active, others })
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
