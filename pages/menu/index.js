const merchantMenus = {
  spring: [
    { name: "暖汤荞麦面", desc: "山泉高汤 · 时蔬 · 溏心蛋", price: 38, sold: 68, image: "https://images.unsplash.com/photo-1646200172184-62009769fd7f?auto=format&fit=crop&w=600&q=85" },
    { name: "秘制豚骨拉面", desc: "慢炖豚骨 · 叉烧 · 海苔", price: 42, sold: 57, image: "https://images.unsplash.com/photo-1706839640651-738dd3f6f710?auto=format&fit=crop&w=600&q=85" },
    { name: "温泉蛋牛肉饭", desc: "谷饲牛肉 · 温泉蛋 · 米饭", price: 46, sold: 46, image: "https://images.unsplash.com/photo-1726983534078-eb7f2013c8f7?auto=format&fit=crop&w=600&q=85" }
  ],
  tea: [
    { name: "桂花乌龙", desc: "现泡乌龙 · 桂花蜜", price: 16, sold: 89, image: "https://images.unsplash.com/photo-1591224803255-6cfbba886c2c?auto=format&fit=crop&w=600&q=85" },
    { name: "红豆汤圆", desc: "手作汤圆 · 慢熬红豆", price: 22, sold: 54, image: "https://images.unsplash.com/photo-1519984388953-d2406bc725e1?auto=format&fit=crop&w=600&q=85" }
  ],
  shu: [
    { name: "温泉蛋牛肉饭", desc: "谷饲牛肉 · 温泉蛋 · 米饭", price: 46, sold: 71, image: "https://images.unsplash.com/photo-1726983534078-eb7f2013c8f7?auto=format&fit=crop&w=600&q=85" },
    { name: "家庭双人套餐", desc: "两荤两素 · 米饭 · 例汤", price: 98, sold: 32, image: "https://images.unsplash.com/photo-1646200172184-62009769fd7f?auto=format&fit=crop&w=600&q=85" }
  ]
}

Page({
  data: {
    id: "spring",
    name: "山泉食坊",
    products: [],
    counts: [],
    quantity: 0,
    total: 0,
    categories: ["热销推荐", "主食套餐", "小食", "饮品"],
    categoryIndex: 0
  },

  onLoad(options) {
    const id = options.id || "spring"
    const products = merchantMenus[id] || merchantMenus.spring
    this.setData({
      id,
      name: decodeURIComponent(options.name || "山泉食坊"),
      products,
      counts: products.map(() => 0)
    })
  },

  selectCategory(event) {
    this.setData({ categoryIndex: Number(event.currentTarget.dataset.index) })
  },

  changeCount(event) {
    const index = Number(event.currentTarget.dataset.index)
    const delta = Number(event.currentTarget.dataset.delta)
    const counts = [...this.data.counts]
    counts[index] = Math.max(0, counts[index] + delta)
    const quantity = counts.reduce((sum, count) => sum + count, 0)
    const total = counts.reduce((sum, count, itemIndex) => sum + count * this.data.products[itemIndex].price, 0)
    this.setData({ counts, quantity, total })
  },

  checkout() {
    if (!this.data.quantity) {
      wx.showToast({ title: "请先选择商品", icon: "none" })
      return
    }
    wx.showModal({
      title: "确认点餐",
      content: `已选择 ${this.data.quantity} 件商品，合计 ¥${this.data.total}。演示版本暂未接入支付。`,
      confirmText: "我知道了",
      showCancel: false
    })
  }
})
