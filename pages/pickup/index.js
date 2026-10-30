Page({
  data: {
    no: "A037",
    window: "",
    qty: 0,
    total: 0,
    state: "making"
  },

  onLoad(options) {
    this.setData({
      no: options.no || "A037",
      window: decodeURIComponent(options.window || ""),
      qty: Number(options.qty || 0),
      total: Number(options.total || 0)
    })
    // 模拟后厨链路：支付成功 → 云打印/云喇叭通知后厨 → 30 秒后出餐
    this.timer = setTimeout(() => {
      this.setData({ state: "ready" })
    }, 30000)
  },

  onUnload() {
    if (this.timer) clearTimeout(this.timer)
  },

  goHome() {
    wx.switchTab({ url: "/pages/home/index" })
  }
})
