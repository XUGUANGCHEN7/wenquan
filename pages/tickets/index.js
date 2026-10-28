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
    wx.showModal({
      title: "确认购买公共浴池门票",
      content: `共 ${this.data.adult + this.data.child} 张，合计 ¥${this.data.total}。演示版本暂未接入微信支付。`,
      confirmText: "我知道了",
      showCancel: false
    })
  }
})
