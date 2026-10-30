Page({
  data: {
    dates: [
      { label: "今天", date: "12/20" },
      { label: "明天", date: "12/21" },
      { label: "周日", date: "12/22" },
      { label: "周一", date: "12/23" }
    ],
    slots: [
      { name: "晨间票", time: "09:00—12:00", left: 32, price: 98 },
      { name: "午后票", time: "12:00—17:00", left: 18, price: 128 },
      { name: "星夜票", time: "17:00—21:30", left: 6, price: 158 }
    ],
    dateIndex: 0,
    slotIndex: 1,
    adult: 2,
    child: 0,
    total: 256
  },

  selectDate(event) {
    this.setData({ dateIndex: Number(event.currentTarget.dataset.index) })
  },

  selectSlot(event) {
    this.setData({ slotIndex: Number(event.currentTarget.dataset.index) }, this.calculate)
  },

  changeCount(event) {
    const type = event.currentTarget.dataset.type
    const delta = Number(event.currentTarget.dataset.delta)
    this.setData({ [type]: Math.max(0, this.data[type] + delta) }, this.calculate)
  },

  calculate() {
    const price = this.data.slots[this.data.slotIndex].price
    this.setData({ total: price * this.data.adult + Math.round(price * 0.6) * this.data.child })
  },

  submit() {
    if (!this.data.adult && !this.data.child) {
      wx.showToast({ title: "请选择购票人数", icon: "none" })
      return
    }
    const date = this.data.dates[this.data.dateIndex]
    const slot = this.data.slots[this.data.slotIndex]
    const { adult, child, total } = this.data
    wx.showModal({
      title: "确认支付",
      content: `共 ${adult + child} 张门票，合计 ¥${total}。当前为虚拟支付演示。`,
      confirmText: "虚拟支付",
      cancelText: "再想想",
      success: (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: "支付中…", mask: true })
        setTimeout(() => {
          wx.hideLoading()
          const app = getApp()
          const no = app.nextEntryOrderNo()
          // 存入温泉订单列表，"我的-门票订单"可随时重开凭证
          app.globalData.entryOrders.unshift({
            no,
            type: "ticket",
            title: "公共浴池入园凭证",
            date: date.label + " " + date.date,
            slot: slot.name + " " + slot.time,
            adult,
            child,
            amount: total,
            ts: Date.now()
          })
          wx.navigateTo({
            url: `/pages/entry-pass/index?no=${no}&type=ticket&date=${encodeURIComponent(date.label + " " + date.date)}&slot=${encodeURIComponent(slot.name + " " + slot.time)}&adult=${adult}&child=${child}&amount=${total}`
          })
        }, 900)
      }
    })
  }
})
