const config = require("../../config")
const { request, showError } = require("../../utils/api")
const { formatMoney } = require("../../utils/money")

Page({
  data: { balance: "0.00", plans: [], entries: [], selected: 0, loading: true, submitting: false },

  onShow() { this.loadWallet() },

  async loadWallet() {
    this.setData({ loading: true })
    try {
      const [balance, plans, entries] = await Promise.all([
        request("/wallet/balance"), request("/catalog/recharge-activities", { auth: false }), request("/wallet/entries")
      ])
      this.setData({
        loading: false, balance: formatMoney(balance.available_cents),
        plans: plans.map((plan) => ({ ...plan, amount: formatMoney(plan.principal_cents), gift: formatMoney(plan.gift_cents) })),
        entries: entries.map((entry) => ({ ...entry, delta: formatMoney(entry.delta_cents), after: formatMoney(entry.balance_after_cents) }))
      })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  selectPlan(event) { this.setData({ selected: Number(event.currentTarget.dataset.index) }) },

  async recharge() {
    const plan = this.data.plans[this.data.selected]
    if (!plan || this.data.submitting) return
    if (!config.development) {
      wx.showToast({ title: "正式微信支付适配器尚未配置", icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      const recharge = await request("/wallet/recharges", { method: "POST", data: { activity_id: plan.id } })
      await request(`/payments/${recharge.payment_no}/mock-confirm`, { method: "POST" })
      await this.loadWallet()
      wx.showModal({ title: "开发 Mock 储值完成", content: `服务端账本已确认储值 ¥${plan.amount}，赠送 ¥${plan.gift}；未发生真实微信扣款。`, showCancel: false })
    } catch (error) { showError(error) } finally {
      this.setData({ submitting: false })
    }
  }
})
