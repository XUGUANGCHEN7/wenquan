Page({
  data: {
    rooms: [
      {
        name: "松风",
        tag: "景观私汤",
        price: 398,
        image: "https://images.unsplash.com/photo-1712232907812-4bd219a99a49?auto=format&fit=crop&w=1200&q=85"
      },
      {
        name: "竹影",
        tag: "家庭私汤",
        price: 468,
        image: "https://images.unsplash.com/photo-1632790929202-a79cd10d9076?auto=format&fit=crop&w=1200&q=85"
      }
    ],
    roomIndex: 0,
    environment: [
      "https://images.unsplash.com/photo-1632790929202-a79cd10d9076?auto=format&fit=crop&w=700&q=85",
      "https://images.unsplash.com/photo-1610333684078-c89bd57f2e46?auto=format&fit=crop&w=700&q=85"
    ],
    dates: [
      { label: "今天", date: "12/20" },
      { label: "明天", date: "12/21" },
      { label: "周日", date: "12/22" },
      { label: "周一", date: "12/23" }
    ],
    slots: ["10:00—12:00", "14:00—16:00", "18:00—20:00"],
    dateIndex: 0,
    slotIndex: 1
  },

  selectRoom(event) {
    this.setData({ roomIndex: Number(event.currentTarget.dataset.index) })
  },

  selectDate(event) {
    this.setData({ dateIndex: Number(event.currentTarget.dataset.index) })
  },

  selectSlot(event) {
    this.setData({ slotIndex: Number(event.currentTarget.dataset.index) })
  },

  submit() {
    const room = this.data.rooms[this.data.roomIndex]
    const date = this.data.dates[this.data.dateIndex]
    wx.showModal({
      title: `预约${room.name}私汤房`,
      content: `${date.label} ${date.date} ${this.data.slots[this.data.slotIndex]}，2小时房费 ¥${room.price}。演示版本暂未接入支付。`,
      confirmText: "我知道了",
      showCancel: false
    })
  }
})
