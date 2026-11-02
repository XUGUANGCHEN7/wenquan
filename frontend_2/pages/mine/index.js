const { request, loginMember, showError } = require("../../utils/api")
const { formatMoney } = require("../../utils/money")

Page({
  data: { loggedIn: false, balance: "0.00", loading: false },
  onShow() {
    this.setData({ loggedIn: Boolean(wx.getStorageSync("dining_member_token")) })
    if (this.data.loggedIn) this.loadBalance()
  },

  async loadBalance() {
    this.setData({ loading: true })
    try {
      const balance = await request("/wallet/balance")
      this.setData({ balance: formatMoney(balance.available_cents), loading: false })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  async login() {
    this.setData({ loading: true })
    try {
      await loginMember()
      this.setData({ loggedIn: true })
      await this.loadBalance()
      wx.showToast({ title: "开发会员已明确绑定", icon: "none" })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  logout() {
    wx.removeStorageSync("dining_member_token")
    this.setData({ loggedIn: false, balance: "0.00" })
  }
})
