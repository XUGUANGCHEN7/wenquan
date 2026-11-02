const { request, payOrder, showError } = require("../../utils/api")
const { formatMoney, dateInput, dateLabel } = require("../../utils/money")

Page({
  data: {
    hero: "https://images.unsplash.com/photo-1712232907812-4bd219a99a49?auto=format&fit=crop&w=1200&q=85",
    dates: [], dateIndex: 0, slots: [], selected: [], unitPrice: 0,
    total: "0.00", unitPriceDisplay: "0.00", expectedArrival: "10:00", paymentMethod: "WECHAT",
    loading: true, submitting: false
  },

  onLoad() {
    const dates = Array.from({ length: 7 }, (_, index) => {
      const value = dateInput(index)
      return { value, label: `${dateLabel(value)} ${value.slice(5).replace("-", "/")}` }
    })
    this.setData({ dates }, () => this.loadSlots())
  },

  async loadSlots() {
    this.setData({ loading: true, selected: [], total: "0.00" })
    try {
      const result = await request(`/rooms/slots?visit_date=${this.data.dates[this.data.dateIndex].value}`, { auth: false })
      this.setData({ loading: false, slots: result.slots, unitPrice: result.unit_price_cents,
        unitPriceDisplay: formatMoney(result.unit_price_cents) })
    } catch (error) {
      this.setData({ loading: false })
      showError(error)
    }
  },

  selectDate(event) {
    this.setData({ dateIndex: Number(event.currentTarget.dataset.index) }, () => this.loadSlots())
  },

  selectSlot(event) {
    const index = Number(event.currentTarget.dataset.index)
    const slot = this.data.slots[index]
    if (!slot.available) {
      wx.showToast({ title: "该场次暂不可预约", icon: "none" })
      return
    }
    let selected = this.data.selected
    if (selected.includes(index) || selected.length > 1) selected = [index]
    else if (!selected.length) selected = [index]
    else {
      const from = Math.min(selected[0], index)
      const to = Math.max(selected[0], index)
      selected = Array.from({ length: to - from + 1 }, (_, offset) => from + offset)
      if (selected.some((item) => !this.data.slots[item].available)) {
        wx.showToast({ title: "连续区间中存在不可售场次", icon: "none" })
        return
      }
    }
    const slots = this.data.slots.map((slot) => ({ ...slot, active: selected.includes(slot.slot_index) }))
    this.setData({ selected, slots, total: formatMoney(selected.length * this.data.unitPrice) })
  },

  selectArrival(event) { this.setData({ expectedArrival: event.detail.value }) },
  selectPayment(event) { this.setData({ paymentMethod: event.currentTarget.dataset.method }) },

  async submit() {
    if (!this.data.selected.length || this.data.submitting) {
      if (!this.data.selected.length) wx.showToast({ title: "请选择连续场次", icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      const booking = await request("/rooms/bookings", {
        method: "POST",
        data: {
          visit_date: this.data.dates[this.data.dateIndex].value,
          slot_indices: this.data.selected,
          expected_arrival_at: `${this.data.dates[this.data.dateIndex].value}T${this.data.expectedArrival}:00`
        }
      })
      const paid = await payOrder(booking.order_no, this.data.paymentMethod)
      wx.showModal({
        title: paid.status === "PAID" ? "预约已确认" : "预约等待人工处理",
        content: `服务端金额 ¥${formatMoney(booking.amount_cents)}。到店后由前台分房，本订单未指定房号。${this.data.paymentMethod === "WECHAT" ? "（开发 Mock 支付）" : ""}`,
        showCancel: false,
        success: () => wx.switchTab({ url: "/pages/orders/index" })
      })
    } catch (error) { showError(error) } finally {
      this.setData({ submitting: false })
    }
  }
})
