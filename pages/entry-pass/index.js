const qrcode = require("../../utils/qrcode")

Page({
  data: {
    orderNo: "",
    title: "",
    rows: [],
    qrModules: [],
    seconds: 60
  },

  onLoad(options) {
    const app = getApp()
    let title
    let rows
    if (options.type === "room") {
      title = "私汤房预约凭证"
      rows = [
        ["房型", decodeURIComponent(options.room || "") + "私汤房"],
        ["到店日期", decodeURIComponent(options.date || "")],
        ["使用时段", decodeURIComponent(options.slot || "")],
        ["房费", "¥" + (options.amount || "")]
      ]
    } else {
      title = "公共浴池入园凭证"
      rows = [
        ["入园日期", decodeURIComponent(options.date || "")],
        ["入园时段", decodeURIComponent(options.slot || "")],
        ["成人票", (options.adult || "0") + " 张"],
        ["儿童票", (options.child || "0") + " 张"],
        ["票款", "¥" + (options.amount || "")]
      ]
    }
    // 从订单历史进入时复用原订单号；新支付时生成新订单号
    this.setData({ orderNo: options.no || app.nextEntryOrderNo(), title, rows })
  },

  onReady() {
    this.refresh()
  },

  onShow() {
    // 从后台回来立即换新码；首次显示由 onReady 触发
    if (this.data.qrModules.length) this.refresh()
  },

  onHide() {
    this.clearTimers()
  },

  onUnload() {
    this.clearTimers()
  },

  clearTimers() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  },

  refresh() {
    const seed = this.data.orderNo + "." + Date.now() + "." + Math.random()
    const payload = "v2.ENTRY." + seed + "." + this.pseudoHmac(seed)
    // 纯 view 网格渲染：输出模块矩阵，不依赖 canvas，任何机型必显示
    const { modules } = qrcode.makeMatrix(payload)
    this.setData({
      payload,
      qrModules: modules.map((row) => row.map((cell) => !!cell)),
      seconds: 60
    })
    if (!this.timer) {
      this.timer = setInterval(() => {
        if (this.data.seconds <= 1) {
          this.refresh()
        } else {
          this.setData({ seconds: this.data.seconds - 1 })
        }
      }, 1000)
    }
  },

  pseudoHmac(seed) {
    let h = 0x811c9dc5
    for (let i = 0; i < seed.length; i++) {
      h ^= seed.charCodeAt(i)
      h = Math.imul(h, 0x01000193) >>> 0
    }
    return h.toString(16).padStart(8, "0")
  }
})
