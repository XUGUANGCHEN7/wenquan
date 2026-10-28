Page({
  data: {
    balance: "368.00",
    plans: [
      { amount: 200, gift: 20, label: "轻享礼" },
      { amount: 500, gift: 80, label: "最受欢迎" },
      { amount: 1000, gift: 200, label: "尊享礼" }
    ],
    selected: 1
  },

  onShow() {
    const app = getApp()
    this.setData({ balance: Number(app.globalData.user.balance).toFixed(2) })
  },

  selectPlan(event) {
    this.setData({ selected: Number(event.currentTarget.dataset.index) })
  },

  recharge() {
    const plan = this.data.plans[this.data.selected]
    wx.showModal({
      title: `储值 ¥${plan.amount}`,
      content: `本档赠送 ¥${plan.gift}。演示版本暂未接入微信支付，正式接入后支付成功将实时更新余额。`,
      confirmText: "我知道了",
      showCancel: false
    })
  }
})
