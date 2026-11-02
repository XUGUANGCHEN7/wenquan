const { request, payOrder, showError } = require("../../utils/api")
const { formatMoney, dateInput, dateLabel } = require("../../utils/money")

Page({
  data: {
    dates: [], dateIndex: 0, adult: 1, child: 0,
    adultPrice: 0, childPrice: 0, total: "0.00", adultDisplay: "0.00", childDisplay: "0.00",
    paymentMethod: "WECHAT", submitting: false, loading: true
  },

  onLoad() {
    const dates = Array.from({ length: 7 }, (_, index) => {
      const value = dateInput(index)
      return { value, label: dateLabel(value), display: value.slice(5).replace("-", "/") }
    })
    this.setData({ dates }, () => this.loadPrices())
  },

  async loadPrices() {
    this.setData({ loading: true })
    const visitDate = this.data.dates[this.data.dateIndex].value
    try {
      const prices = await request(`/catalog/ticket-prices?visit_date=${visitDate}`, { auth: false })
      this.setData({
        loading: false, adultPrice: prices.adult_cents, childPrice: prices.child_cents,
        adultDisplay: formatMoney(prices.adult_cents), childDisplay: formatMoney(prices.child_cents)
      }, () => this.calculate())
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  selectDate(event) {
    this.setData({ dateIndex: Number(event.currentTarget.dataset.index) }, () => this.loadPrices())
  },

  changeCount(event) {
    const type = event.currentTarget.dataset.type
    const delta = Number(event.currentTarget.dataset.delta)
    this.setData({ [type]: Math.max(0, this.data[type] + delta) }, () => this.calculate())
  },

  calculate() {
    const cents = this.data.adultPrice * this.data.adult + this.data.childPrice * this.data.child
    this.setData({ total: formatMoney(cents) })
  },

  selectPayment(event) { this.setData({ paymentMethod: event.currentTarget.dataset.method }) },

  async submit() {
    if (this.data.submitting) return
    if (!this.data.adult && !this.data.child) {
      wx.showToast({ title: "请选择购票人数", icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      const order = await request("/tickets/orders", {
        method: "POST",
        data: {
          visit_date: this.data.dates[this.data.dateIndex].value,
          adult_count: this.data.adult, child_count: this.data.child
        }
      })
      const paid = await payOrder(order.order_no, this.data.paymentMethod)
      this.setData({ total: formatMoney(order.amount_cents) })
      const mockNote = this.data.paymentMethod === "WECHAT" ? "（开发 Mock，非真实扣款）" : ""
      wx.showModal({
        title: paid.status === "PAID" ? "购票成功" : "订单已提交",
        content: `服务端确认金额 ¥${formatMoney(order.amount_cents)}${mockNote}`,
        showCancel: false,
        success: () => wx.switchTab({ url: "/pages/orders/index" })
      })
    } catch (error) { showError(error) } finally {
      this.setData({ submitting: false })
    }
  }
})
