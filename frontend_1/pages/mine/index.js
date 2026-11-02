const config = require("../../config")
const { request, showError } = require("../../utils/api")
const { formatMoney } = require("../../utils/money")

Page({
  data: { nickname: "温泉旅人", balance: "0.00", loading: true },
  onShow() { this.loadProfile() },

  async loadProfile() {
    try {
      const [profile, wallet] = await Promise.all([
        request(`/members/${config.memberId}/profile`), request("/wallet/balance")
      ])
      this.setData({ nickname: profile.nickname, balance: formatMoney(wallet.available_cents), loading: false })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  goWallet() { wx.navigateTo({ url: "/pages/wallet/index" }) },
  goOrders() { wx.switchTab({ url: "/pages/orders/index" }) },
  contact() { wx.showToast({ title: "请前往前台或拨打园区公示电话", icon: "none" }) }
})
