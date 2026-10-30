const qrcode = require("../../utils/qrcode")

Page({
  data: {
    orderNo: "",
    title: "",
    rows: [],
    payload: "",
    seconds: 60,
    failed: false
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
    this.setData({ orderNo: app.nextEntryOrderNo(), title, rows })
  },

  onReady() {
    this.refresh()
  },

  onShow() {
    // 从后台回来立即换新码；首次显示由 onReady 触发
    if (this.data.payload) this.refresh()
  },

  onHide() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  },

  onUnload() {
    if (this.timer) clearInterval(this.timer)
  },

  refresh() {
    const seed = this.data.orderNo + "." + Date.now() + "." + Math.random()
    const payload = "v2.ENTRY." + seed + "." + this.pseudoHmac(seed)
    this.setData({ payload, seconds: 60, failed: false }, () => this.drawQr())
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
  },

  drawQr() {
    const query = wx.createSelectorQuery()
    query
      .select("#pass-qr")
      .fields({ node: true, size: true })
      .exec((res) => {
        const item = res && res[0]
        if (!item || !item.node) {
          this.setData({ failed: true })
          return
        }
        try {
          qrcode.draw(item.node, this.data.payload, item.width)
        } catch (e) {
          this.setData({ failed: true })
        }
      })
  }
})
