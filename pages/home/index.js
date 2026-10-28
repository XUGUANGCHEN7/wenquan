Page({
  data: {
    hero: "https://images.unsplash.com/photo-1734244362947-749db3efc7b7?auto=format&fit=crop&w=1200&q=85",
    room: "https://images.unsplash.com/photo-1712232907812-4bd219a99a49?auto=format&fit=crop&w=800&q=85"
  },

  goTickets() {
    wx.navigateTo({ url: "/pages/tickets/index" })
  },

  goPrivateRoom() {
    wx.navigateTo({ url: "/pages/private-room/index" })
  },

  goMerchants() {
    wx.switchTab({ url: "/pages/merchants/index" })
  },

  goWallet() {
    wx.navigateTo({ url: "/pages/wallet/index" })
  },

  goMine() {
    wx.switchTab({ url: "/pages/mine/index" })
  }
})
