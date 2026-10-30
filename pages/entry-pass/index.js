const qrcode = require("../../utils/qrcode")

Page({
  data: {
    orderNo: "",
    title: "",
    rows: [],
    payload: "",
    seconds: 60,
    failed: false,
    useViewFallback: false,
    viewMatrix: []
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
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
  },

  refresh() {
    const seed = this.data.orderNo + "." + Date.now() + "." + Math.random()
    const payload = "v2.ENTRY." + seed + "." + this.pseudoHmac(seed)
    // 预生成 view 网格矩阵：canvas 三次重试都失败时自动兜底渲染
    const { modules } = qrcode.makeMatrix(payload)
    const viewMatrix = modules.map((row) => row.map((cell) => !!cell))
    this.setData(
      { payload, viewMatrix, seconds: 60, failed: false, useViewFallback: false },
      () => this.drawQr()
    )
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

  drawQr(attempt) {
    const tryCount = attempt || 0
    const query = wx.createSelectorQuery().in(this)
    query
      .select("#pass-qr")
      .fields({ node: true, size: true })
      .exec((res) => {
        const item = res && res[0]
        if (!item || !item.node) {
          console.error("[entry-pass] 第" + (tryCount + 1) + "次取 canvas 节点失败")
          this.retryOrFail(tryCount)
          return
        }
        const width = item.width || 0
        if (width < 100) {
          console.error("[entry-pass] 第" + (tryCount + 1) + "次 canvas 尺寸异常：", width)
          this.retryOrFail(tryCount)
          return
        }
        try {
          qrcode.draw(item.node, this.data.payload, width)
          this.setData({ failed: false })
        } catch (e) {
          console.error("[entry-pass] 绘制异常：", e)
          this.retryOrFail(tryCount)
        }
      })
  },

  retryOrFail(tryCount) {
    if (tryCount < 2) {
      this.retryTimer = setTimeout(() => this.drawQr(tryCount + 1), 200)
      return
    }
    // canvas 三次尝试均失败 → 切换 view 网格兜底，二维码保证可见
    console.error("[entry-pass] canvas 渲染失败，切换 view 网格兜底")
    this.setData({ failed: true, useViewFallback: true })
  }
})
