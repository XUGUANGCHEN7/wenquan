const merchantMenus = [
  {
    id: "spring",
    name: "山泉食坊",
    desc: "暖汤面食",
    meta: "水吧旁 · 约15分钟出餐",
    window: "窗口1",
    products: [
      { name: "暖汤荞麦面", desc: "山泉高汤 · 时蔬 · 溏心蛋", price: 38, sold: 68, image: "https://images.unsplash.com/photo-1646200172184-62009769fd7f?auto=format&fit=crop&w=600&q=85" },
      { name: "秘制豚骨拉面", desc: "慢炖豚骨 · 叉烧 · 海苔", price: 42, sold: 57, image: "https://images.unsplash.com/photo-1706839640651-738dd3f6f710?auto=format&fit=crop&w=600&q=85" },
      { name: "温泉蛋牛肉饭", desc: "谷饲牛肉 · 温泉蛋 · 米饭", price: 46, sold: 46, image: "https://images.unsplash.com/photo-1726983534078-eb7f2013c8f7?auto=format&fit=crop&w=600&q=85" }
    ]
  },
  {
    id: "tea",
    name: "竹里茶饮",
    desc: "茶饮甜品",
    meta: "休息大厅 · 约8分钟出餐",
    window: "窗口2",
    products: [
      { name: "桂花乌龙", desc: "现泡乌龙 · 桂花蜜", price: 16, sold: 89, image: "https://images.unsplash.com/photo-1591224803255-6cfbba886c2c?auto=format&fit=crop&w=600&q=85" },
      { name: "红豆汤圆", desc: "手作汤圆 · 慢熬红豆", price: 22, sold: 54, image: "https://images.unsplash.com/photo-1519984388953-d2406bc725e1?auto=format&fit=crop&w=600&q=85" }
    ]
  },
  {
    id: "shu",
    name: "蜀味小馆",
    desc: "川味小炒",
    meta: "餐饮区2楼 · 约20分钟出餐",
    window: "窗口3",
    products: [
      { name: "温泉蛋牛肉饭", desc: "谷饲牛肉 · 温泉蛋 · 米饭", price: 46, sold: 71, image: "https://images.unsplash.com/photo-1726983534078-eb7f2013c8f7?auto=format&fit=crop&w=600&q=85" },
      { name: "家庭双人套餐", desc: "两荤两素 · 米饭 · 例汤", price: 98, sold: 32, image: "https://images.unsplash.com/photo-1646200172184-62009769fd7f?auto=format&fit=crop&w=600&q=85" }
    ]
  }
]

Page({
  data: {
    merchants: [],
    merchantIndex: 0,
    products: [],
    counts: [],
    quantity: 0,
    total: 0,
    involvedCount: 0,
    cartName: "",
    fulfillment: "pickup",
    privateRoom: null
  },

  carts: {},

  onLoad() {
    const merchants = merchantMenus.map((m) => ({ id: m.id, name: m.name, desc: m.desc, meta: m.meta }))
    this.setData({ merchants, ...this.applyMerchant(0) })
  },

  onShow() {
    // 私汤房预约成功后解锁配送权限
    const app = getApp()
    this.setData({ privateRoom: app.globalData.user.privateRoom || null })
  },

  setFulfillment(event) {
    const mode = event.currentTarget.dataset.mode
    if (mode === "delivery" && !this.data.privateRoom) {
      wx.showToast({ title: "配送仅限私汤房客人，请先预约私汤房", icon: "none" })
      return
    }
    this.setData({ fulfillment: mode })
  },

  // 购物车总累计：跨商家合计金额、件数与涉及商家数
  cartTotals() {
    let quantity = 0
    let total = 0
    let involvedCount = 0
    merchantMenus.forEach((m) => {
      const counts = this.carts[m.id] || []
      let merchantQty = 0
      counts.forEach((count, i) => {
        quantity += count
        total += count * m.products[i].price
        merchantQty += count
      })
      if (merchantQty > 0) involvedCount++
    })
    return { quantity, total, involvedCount }
  },

  applyMerchant(index) {
    const merchant = merchantMenus[index]
    const counts = this.carts[merchant.id] || merchant.products.map(() => 0)
    return {
      merchantIndex: index,
      products: merchant.products,
      counts,
      cartName: merchant.name,
      ...this.cartTotals()
    }
  },

  selectMerchant(event) {
    this.setData(this.applyMerchant(Number(event.currentTarget.dataset.index)))
  },

  changeCount(event) {
    const index = Number(event.currentTarget.dataset.index)
    const delta = Number(event.currentTarget.dataset.delta)
    const merchant = merchantMenus[this.data.merchantIndex]
    const counts = [...this.data.counts]
    counts[index] = Math.max(0, counts[index] + delta)
    this.carts[merchant.id] = counts
    this.setData({ counts, ...this.cartTotals() })
  },

  goOrders() {
    wx.navigateTo({ url: "/pages/dining-orders/index" })
  },

  checkout() {
    if (!this.data.quantity) {
      wx.showToast({ title: "请先选择商品", icon: "none" })
      return
    }
    const { quantity, total, involvedCount, fulfillment, privateRoom } = this.data
    const delivery = fulfillment === "delivery"
    // 汇总每个有餐的商家及其菜品明细
    const involved = []
    merchantMenus.forEach((m) => {
      const counts = this.carts[m.id] || []
      const items = []
      counts.forEach((count, i) => {
        if (count > 0) {
          items.push({ name: m.products[i].name, qty: count, subtotal: count * m.products[i].price })
        }
      })
      if (items.length) involved.push({ merchant: m, items })
    })
    wx.showModal({
      title: "确认支付",
      content: `${involvedCount > 1 ? involvedCount + " 家商家" : involved[0].merchant.name}共 ${quantity} 件商品，总累计 ¥${total}，${delivery ? "由服务员送至私汤房" : "请分别到各窗口取餐"}。当前为虚拟支付演示。`,
      confirmText: "虚拟支付",
      cancelText: "再想想",
      success: (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: "支付中…", mask: true })
        setTimeout(() => {
          wx.hideLoading()
          const app = getApp()
          // 一次支付，按商家拆单：每个商家一张取餐单（各自窗口号/取餐号）
          involved.forEach(({ merchant, items }) => {
            app.globalData.pickupOrders.push({
              id: "P" + Date.now() + "_" + merchant.id,
              no: app.nextPickupNo(),
              window: merchant.window,
              merchantName: merchant.name,
              items,
              qty: items.reduce((s, it) => s + it.qty, 0),
              total: items.reduce((s, it) => s + it.subtotal, 0),
              fulfillment,
              room: privateRoom ? privateRoom.room : "",
              state: "making",
              createdTs: Date.now()
            })
          })
          this.carts = {}
          this.setData(this.applyMerchant(this.data.merchantIndex))
          wx.navigateTo({ url: "/pages/dining-orders/index" })
        }, 900)
      }
    })
  }
})
