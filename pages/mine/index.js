Page({
  data: {
    nickname: "温泉旅人",
    balance: "368.00"
  },

  onShow() {
    const app = getApp()
    this.setData({ balance: Number(app.globalData.user.balance).toFixed(2) })
  },

  goWallet() {
    wx.navigateTo({ url: "/pages/wallet/index" })
  },

  goTicketOrders() {
    wx.navigateTo({ url: "/pages/orders/index" })
  },

  goRoomOrders() {
    wx.navigateTo({ url: "/pages/orders/index" })
  },

  goDiningOrders() {
    wx.navigateTo({ url: "/pages/dining-orders/index" })
  },

  showDeveloping() {
    wx.showToast({ title: "该功能正在建设中", icon: "none" })
  }
})
