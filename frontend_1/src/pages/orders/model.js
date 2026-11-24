import { computed, reactive } from "vue"
import { formatMoney } from "../../utils/money.js"

export const categories = [
  { value: "ALL", label: "全部" }, { value: "TICKET", label: "门票" },
  { value: "PRIVATE", label: "私汤" }, { value: "RECHARGE", label: "储值" },
]
const types = {
  TICKET: { title: "公共浴池门票", image: "/static/orders/ticket.jpg" },
  PRIVATE: { title: "私汤预约", image: "/static/orders/private-room.jpg" },
  RECHARGE: { title: "会员储值", image: "/static/orders/wallet.jpg" },
}
const statuses = { PENDING: "待付款", PAID: "已支付", UNUSED: "待使用", COMPLETED: "已完成", CANCELLED: "已取消", CANCELED: "已取消", EXCEPTION: "人工处理中", REFUNDED: "已退款", REFUND_REVIEW: "退款审核中", REFUND_PROCESSING: "退款处理中" }

export function presentOrder(order, detail) {
  const type = types[order.order_type] || { title: order.order_type, image: "" }
  let summary = "订单信息以实际记录为准", date = ""
  if (order.order_type === "TICKET") {
    const tickets = detail?.tickets || []
    const adults = Number.isInteger(detail?.adult_count) ? detail.adult_count : tickets.filter(ticket => ticket.category === "ADULT").length
    const children = Number.isInteger(detail?.child_count) ? detail.child_count : tickets.filter(ticket => ticket.category === "CHILD").length
    summary = [adults && `成人票 × ${adults}`, children && `儿童票 × ${children}`].filter(Boolean).join(" · ") || "支付完成后逐人生成票券"
    if (!detail) summary = "查看入园日期与票券信息"
    if (detail?.visit_date) date = `入园日期 ${detail.visit_date.replaceAll("-", ".")}`
  } else if (order.order_type === "PRIVATE") {
    summary = detail ? (detail.room_number ? `已分房 ${detail.room_number} 号` : "到店后由前台分房") : "查看预约与分房信息"
    if (detail?.visit_date) date = `预约日期 ${detail.visit_date.replaceAll("-", ".")}`
  } else if (order.order_type === "RECHARGE") {
    summary = "储值结果以账户记录为准"
  }
  let statusKey = order.status, unused = false
  if (order.status === "PAID") {
    if (order.order_type === "RECHARGE") statusKey = "COMPLETED"
    if (order.order_type === "TICKET" && detail?.tickets?.length) {
      if (detail.tickets.every(ticket => ticket.status === "USED")) statusKey = "COMPLETED"
      else if (detail.tickets.some(ticket => ticket.status === "UNUSED")) statusKey = "UNUSED"
      unused = detail.tickets.every(ticket => ticket.status === "UNUSED")
    }
    if (order.order_type === "PRIVATE" && detail) {
      if (detail.voucher_status === "USED" || ["IN_USE", "COMPLETED"].includes(detail.booking_status)) statusKey = "COMPLETED"
      else if (detail.booking_status === "CONFIRMED" && detail.voucher_status === "UNUSED") { statusKey = "UNUSED"; unused = true }
    }
  }
  const application = order.refund_application
  if (application?.status === "PENDING" && order.status === "PAID") statusKey = "REFUND_REVIEW"
  if (application?.status === "APPROVED" && order.status !== "REFUNDED") {
    statusKey = application.refund_status === "SUCCESS" ? "REFUNDED" : application.refund_status === "FAILED" ? "EXCEPTION" : "REFUND_PROCESSING"
  }
  const voucherNumbers = order.status === "PENDING" ? [] : order.order_type === "TICKET"
    ? (detail?.tickets || []).map(ticket => ticket.ticket_no).filter(Boolean)
    : order.order_type === "PRIVATE" && detail?.ticket_no ? [detail.ticket_no] : []
  const slots = detail?.slot_count || detail?.slot_indices?.length
  const specification = order.order_type === "PRIVATE" ? (slots ? `私汤预约 × 1 · 连续 ${slots} 场` : "预约规格待确认")
    : order.order_type === "RECHARGE" ? "会员储值 × 1" : summary
  const dayType = detail?.day_type || order.day_type
  if (dayType) {
    const raw = detail?.valid_until
    const expiry = raw ? new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(raw) ? raw : `${raw}Z`) : null
    date = expiry && !Number.isNaN(expiry.getTime()) ? `有效期至 ${new Date(expiry.getTime() + 8 * 3600000).toISOString().slice(0, 10)}` : "付款后30天内有效"
  }
  if (detail?.admission_error?.code === "TICKET_EXPIRED" && statusKey === "UNUSED") statusKey = "EXPIRED"
  return { ...order, ...type, summary, specification: dayType ? `${dayType === "HOLIDAY" ? "节假日票" : "工作日票"} · ${specification}` : specification, date, statusKey, voucherNumbers,
    canRefund: order.status === "PAID" && unused && !["PENDING", "APPROVED"].includes(application?.status),
    statusLabel: statusKey === "EXPIRED" ? "已过期" : statuses[statusKey] || statusKey,
    amount: Number.isInteger(order.amount_cents) ? formatMoney(order.amount_cents) : "—",
    amountLabel: order.status === "PENDING" ? "应付" : order.status === "PAID" ? "实付" : "订单金额",
  }
}

export function createOrdersModel({ request, getToken }) {
  const state = reactive({ loading: true, guest: false, error: "", orders: [], details: {}, category: "ALL", expanded: "", exampleMode: false })
  const visibleOrders = computed(() => state.orders.filter(order => state.category === "ALL" || order.order_type === state.category))
  let version = 0
  const pending = new Map()
  const current = (generation, token) => generation === version && token === getToken()

  function invalidate() {
    version++
    pending.clear()
    state.orders = []
    state.details = {}
    state.expanded = ""
    state.loading = false
  }

  function ensureDetail(order) {
    if (!["TICKET", "PRIVATE"].includes(order.order_type)) return Promise.resolve(null)
    const key = order.order_no
    if (state.details[key]?.data) return Promise.resolve(state.details[key].data)
    if (pending.has(key)) return pending.get(key)
    const generation = version, token = getToken()
    if (!token) return Promise.resolve(null)
    state.details[key] = { loading: true, data: null, error: "" }
    const path = order.order_type === "TICKET"
      ? `/tickets/orders/${encodeURIComponent(key)}` : `/rooms/bookings/${encodeURIComponent(order.business_id)}`
    const task = (async () => {
      try {
        const data = await request(path)
        if (!current(generation, token)) return null
        state.details[key] = { loading: false, data, error: "" }
        return data
      } catch (error) {
        if (generation !== version) return null
        if (!getToken()) { invalidate(); state.guest = true; return null }
        if (!current(generation, token)) return null
        state.details[key] = { loading: false, data: null, error: error.message || "详情读取失败，请重试" }
        return null
      } finally {
        if (generation === version) pending.delete(key)
      }
    })()
    pending.set(key, task)
    return task
  }

  async function load() {
    invalidate()
    state.exampleMode = false
    const generation = version, token = getToken()
    state.error = ""
    state.guest = !token
    if (!token) return
    state.loading = true
    try {
      const records = await request("/orders")
      if (!current(generation, token)) return
      if (!Array.isArray(records)) throw new Error("订单数据异常，请重试")
      state.orders = records
      state.loading = false
      let index = 0
      // Hydrate card metadata with at most three concurrent existing detail calls.
      await Promise.all(Array.from({ length: Math.min(3, records.length) }, async () => {
        while (current(generation, token) && index < records.length) await ensureDetail(records[index++])
      }))
    } catch (error) {
      if (generation !== version) return
      if (!getToken()) state.guest = true
      else if (current(generation, token)) state.error = error.message || "订单读取失败，请重试"
    } finally {
      if (generation === version) state.loading = false
    }
  }

  async function toggle(order) {
    if (state.expanded === order.order_no) { state.expanded = ""; return }
    state.expanded = order.order_no
    await ensureDetail(order)
  }

  async function submitRefund(orderNo, reason) {
    const order = state.orders.find(item => item.order_no === orderNo)
    if (!order || !presentOrder(order, state.details[orderNo]?.data).canRefund) throw new Error("此订单当前不可申请退款")
    if (!reason.trim()) throw new Error("请填写退款原因")
    const generation = version, token = getToken()
    const application = state.exampleMode ? { status: "PENDING", reason: reason.trim() }
      : await request(`/orders/${encodeURIComponent(orderNo)}/refund-application`, { method: "POST", data: { reason: reason.trim() } })
    if (generation !== version || (!state.exampleMode && token !== getToken())) return null
    order.refund_application = application
    return application
  }

  return { state, visibleOrders, load, toggle, ensureDetail, invalidate, submitRefund }
}
