Page({
  data: {
    categories: ["全部商家", "正餐", "面食", "茶饮甜品"],
    categoryIndex: 0,
    merchants: [
      {
        id: "spring",
        name: "山泉食坊",
        desc: "暖汤面食 · 中式简餐",
        meta: "水吧旁 · 约15分钟出餐",
        tag: "可送私汤房",
        image: "https://images.unsplash.com/photo-1651449815995-9419a04685aa?auto=format&fit=crop&w=900&q=85"
      },
      {
        id: "tea",
        name: "竹里茶饮",
        desc: "现泡茶饮 · 甜品小食",
        meta: "休息大厅 · 约8分钟出餐",
        tag: "人气商家",
        image: "https://images.unsplash.com/photo-1755183829407-3b3d2705b7bf?auto=format&fit=crop&w=900&q=85"
      },
      {
        id: "shu",
        name: "蜀味小馆",
        desc: "川味小炒 · 家庭套餐",
        meta: "餐饮区2楼 · 约20分钟出餐",
        tag: "满60减8",
        image: "https://images.unsplash.com/photo-1726983534078-eb7f2013c8f7?auto=format&fit=crop&w=900&q=85"
      }
    ]
  },

  selectCategory(event) {
    this.setData({ categoryIndex: Number(event.currentTarget.dataset.index) })
  },

  openMerchant(event) {
    const index = Number(event.currentTarget.dataset.index)
    const merchant = this.data.merchants[index]
    wx.navigateTo({
      url: `/pages/menu/index?id=${merchant.id}&name=${encodeURIComponent(merchant.name)}`
    })
  }
})
