Page({
  data: {
    orders: []
  },

  onShow() {
    const app = getApp()
    const orders = (app.globalData.pickupOrders || []).map((o) => ({
      ...o,
      stateText: o.state === "ready" ? "请取餐" : o.state === "done" ? "已取餐" : "制作中",
      fulfillText: o.fulfillment === "delivery" ? "送至 " + o.room + " 私汤房" : o.window
    }))
    this.setData({ orders })
  },

  goPickup() {
    wx.navigateTo({ url: "/pages/pickup/index" })
  }
})
