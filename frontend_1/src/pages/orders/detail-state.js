import { computed, reactive } from "vue"
import { createOrdersModel, presentOrder } from "./model.js"
import { getOrderExamples } from "./examples.js"
import { formatMoney } from "../../utils/money.js"

const money = value => Number.isInteger(value) ? formatMoney(value) : "待确认"
export function detailPresentation(order) {
  if (!order) return null
  const presented = presentOrder(order, order)
  const tickets = (order.tickets || []).map((ticket, index) => ({ ...ticket, index: index + 1,
    statusLabel: ({ UNUSED: "待使用", USED: "已核销", VOID: "已失效", INVALID: "已失效", REFUNDED: "已退款" })[ticket.status] || ticket.status,
    categoryLabel: ({ ADULT: "成人票", CHILD: "儿童票" })[ticket.category] || ticket.category,
  }))
  return { ...presented, tickets, hasVouchers: tickets.length > 0 || (order.order_type === "PRIVATE" && !!(order.ticket_no || order.booking_id)),
    statusCaption: ({ PENDING: "请尽快完成支付", UNUSED: "请在有效期内核销入园", COMPLETED: "订单已完成，感谢您的光临", REFUNDED: "退款已完成，请留意到账" })[presented.statusKey] || "",
    qrCodeText: ["TICKET", "PRIVATE"].includes(order.order_type) && presented.statusKey === "UNUSED" ? order.order_no || "" : "",
    quantityLabel: Number.isInteger(order.quantity) ? String(order.quantity) : "待确认",
    paidAmount: money(order.paid_amount_cents), principalAmount: money(order.principal_cents),
    giftAmount: money(order.gift_cents), creditedAmount: money(order.credited_cents),
    paymentLabel: ({ WECHAT: "微信支付", BALANCE: "会员余额" })[order.payment_method] || "待确认",
  }
}

export function copyOrderCode(value, platform = uni) {
  if (!value) return Promise.resolve(false)
  return new Promise(resolve => platform.setClipboardData({ data: String(value),
    success() { platform.showToast({ title: "已复制", icon: "success" }); resolve(true) },
    fail() { platform.showToast({ title: "复制失败，请重试", icon: "none" }); resolve(false) },
  }))
}

export function createOrderDetailModel({ request, getToken, allowExamples = false }) {
  const base = createOrdersModel({ request, getToken })
  const state = reactive({ loading: false, guest: false, error: "", order: null, exampleMode: false })
  const presentation = computed(() => detailPresentation(state.order))
  let generation = 0

  function invalidate() {
    generation++
    base.invalidate()
    state.order = null
    state.loading = false
  }

  async function load(id, { example = false } = {}) {
    invalidate()
    const current = generation, token = getToken()
    state.error = ""; state.guest = false; state.exampleMode = example && allowExamples
    if (!id || typeof id !== "string" || id.length > 160) { state.error = "缺少有效的订单标识"; return }
    if (example && !allowExamples) { state.error = "示例订单不可用"; return }
    if (!state.exampleMode && !token) { state.guest = true; return }
    state.loading = true
    try {
      const sample = state.exampleMode ? getOrderExamples().find(order => order.id === id || order.order_no === id) : null
      const order = state.exampleMode ? (sample ? Object.assign(sample, sample.example_detail) : null)
        : await request(`/orders/${encodeURIComponent(id)}`)
      if (current !== generation) return
      if (!state.exampleMode && token !== getToken()) {
        state.guest = !getToken()
        if (!state.guest) state.error = "登录状态已变更，请重新加载订单"
        return
      }
      if (!order?.order_no) throw new Error("订单不存在或已无法访问")
      state.order = order
      base.state.exampleMode = state.exampleMode
      base.state.orders = [order]
      base.state.details[order.order_no] = { data: order, loading: false, error: "" }
    } catch (error) {
      if (current !== generation) return
      if (!state.exampleMode && !getToken()) state.guest = true
      else state.error = error.message || "订单详情读取失败，请重试"
    } finally { if (current === generation) state.loading = false }
  }

  async function submitRefund(reason) {
    if (!state.order) throw new Error("请先加载订单")
    return base.submitRefund(state.order.order_no, reason)
  }
  return { state, presentation, load, invalidate, submitRefund }
}
