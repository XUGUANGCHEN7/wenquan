App({
  globalData: {
    user: {
      nickname: "温泉旅人",
      balance: 368,
      privateRoom: null
    },
    cart: {},
    // 取餐订单列表：不同商家的订单逐单展示在取餐页
    pickupOrders: [],
    // 温泉凭证订单列表（门票/私汤房），供"我的-订单入口"随时重开凭证
    entryOrders: []
  },

  // 演示用：取餐号从 A037 起递增
  nextPickupNo() {
    this.globalData.pickupSeq = (this.globalData.pickupSeq || 36) + 1
    return "A" + String(this.globalData.pickupSeq).padStart(3, "0")
  },

  // 演示用：入园凭证订单号递增
  nextEntryOrderNo() {
    this.globalData.entrySeq = (this.globalData.entrySeq || 0) + 1
    return "HOT2026" + String(1000 + this.globalData.entrySeq)
  }
})
