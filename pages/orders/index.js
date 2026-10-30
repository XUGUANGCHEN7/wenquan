Page({
  data: {
    entries: []
  },

  onShow() {
    const app = getApp()
    this.setData({ entries: app.globalData.entryOrders || [] })
  },

  viewPass(event) {
    const index = Number(event.currentTarget.dataset.index)
    const entry = this.data.entries[index]
    let url =
      `/pages/entry-pass/index?no=${entry.no}&type=${entry.type}` +
      `&date=${encodeURIComponent(entry.date)}&slot=${encodeURIComponent(entry.slot)}` +
      `&amount=${entry.amount}`
    if (entry.type === "room") {
      url += `&room=${encodeURIComponent(entry.room)}`
    } else {
      url += `&adult=${entry.adult}&child=${entry.child}`
    }
    wx.navigateTo({ url })
  },

  goHome() {
    wx.switchTab({ url: "/pages/home/index" })
  }
})
