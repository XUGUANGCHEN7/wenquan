import test from "node:test"
import assert from "node:assert/strict"

const ticket = { order_no: "T1", order_type: "TICKET", status: "PAID", amount_cents: 5800, business_id: "b1", created_at: "2026-11-13T01:00:00" }
const room = { order_no: "P1", order_type: "PRIVATE", status: "PENDING", amount_cents: 24000, business_id: "b2" }
const recharge = { order_no: "R1", order_type: "RECHARGE", status: "REFUNDED", amount_cents: 20000 }
const api = async () => import("../src/pages/orders/model.js")

test("order presentation keeps payment and admission semantics distinct", async () => {
  const { presentOrder } = await api()
  const paid = presentOrder(ticket, { visit_date: "2026-11-13", tickets: [{ category: "ADULT", status: "USED" }, { category: "CHILD", status: "UNUSED" }] })
  assert.equal(paid.title, "公共浴池门票")
  assert.equal(paid.statusLabel, "待使用")
  assert.equal(paid.amount, "58.00")
  assert.equal(paid.amountLabel, "实付")
  assert.equal(paid.date, "入园日期 2026.11.13")
  assert.equal(paid.summary, "成人票 × 1 · 儿童票 × 1")
  assert.equal(presentOrder(room, { visit_date: "2026-11-14", room_number: null }).summary, "到店后由前台分房")
  assert.equal(presentOrder(room, { room_number: "008" }).summary, "已分房 008 号")
  assert.equal(presentOrder(room).amountLabel, "应付")
  assert.equal(presentOrder(recharge).amountLabel, "订单金额")
  assert.equal(presentOrder({ ...ticket, amount_cents: null }).amount, "—")
})

test("usage status, voucher numbers and refund eligibility follow the latest rules", async () => {
  const { presentOrder } = await api()
  const unused = { tickets: [{ ticket_no: "TC1", status: "UNUSED", category: "ADULT" }] }
  assert.equal(presentOrder(ticket, unused).canRefund, true)
  assert.deepEqual(presentOrder(ticket, unused).voucherNumbers, ["TC1"])
  const used = presentOrder(ticket, { tickets: [{ ticket_no: "TC1", status: "USED" }] })
  assert.equal(used.statusLabel, "已完成")
  assert.equal(used.canRefund, false)
  assert.deepEqual(used.voucherNumbers, ["TC1"])
  assert.equal(presentOrder(room).statusLabel, "待付款")
  const privateOrder = { ...room, status: "PAID" }
  assert.equal(presentOrder(privateOrder, { ticket_no: "PV-booking-1", voucher_status: "UNUSED", booking_status: "CONFIRMED" }).canRefund, true)
  assert.equal(presentOrder(privateOrder, { ticket_no: "PV-booking-1", voucher_status: "USED", booking_status: "IN_USE" }).statusLabel, "已完成")
  const reviewed = presentOrder({ ...ticket, refund_application: { status: "PENDING" } }, unused)
  assert.equal(reviewed.statusLabel, "退款审核中")
  assert.equal(reviewed.canRefund, false)
  assert.equal(presentOrder({ ...recharge, status: "PAID" }).statusLabel, "已完成")
  assert.equal(presentOrder({ ...recharge, status: "PAID" }).canRefund, false)
})

test("eight isolated examples cover exactly the requested states", async () => {
  const { createOrderExamples } = await import("../src/pages/orders/examples.js")
  const { presentOrder } = await api()
  const examples = createOrderExamples()
  assert.equal(examples.length, 8)
  assert.equal(new Set(examples.map(order => order.order_no)).size, 8)
  for (const type of ["TICKET", "PRIVATE", "RECHARGE"]) {
    const labels = examples.filter(order => order.order_type === type).map(order => presentOrder(order, order.example_detail).statusLabel)
    assert.deepEqual(labels, type === "RECHARGE" ? ["待付款", "已完成"] : ["待付款", "待使用", "已完成"])
  }
})

test("refund submission uses the member endpoint and excludes used/recharge orders", async () => {
  const { createOrdersModel, presentOrder } = await api()
  const posts = []
  const model = createOrdersModel({ getToken: () => "token", request: async (path, options) => {
    if (options?.method === "POST") { posts.push({ path, options }); return { status: "PENDING", reason: options.data.reason } }
    if (path === "/orders") return [ticket, { ...recharge, status: "PAID" }]
    return { tickets: [{ ticket_no: "TC1", status: "UNUSED" }] }
  } })
  await model.load()
  await assert.rejects(model.submitRefund("R1", "退回"))
  await model.submitRefund("T1", "行程变化")
  assert.equal(posts.length, 1)
  assert.equal(posts[0].path, "/orders/T1/refund-application")
  assert.equal(presentOrder(model.state.orders[0], model.state.details.T1.data).statusLabel, "退款审核中")
  await assert.rejects(model.submitRefund("T1", "重复申请"))
})

test("category filters use order_type and preserve source order", async () => {
  const { createOrdersModel } = await api()
  const model = createOrdersModel({ getToken: () => "token", request: async path => path === "/orders" ? [ticket, room, recharge] : {} })
  await model.load()
  assert.deepEqual(model.visibleOrders.value.map(x => x.order_no), ["T1", "P1", "R1"])
  model.state.category = "PRIVATE"
  assert.deepEqual(model.visibleOrders.value.map(x => x.order_no), ["P1"])
  model.state.category = "RECHARGE"
  assert.deepEqual(model.visibleOrders.value.map(x => x.order_no), ["R1"])
})

test("guests make no protected calls and list failure can be retried", async () => {
  const { createOrdersModel } = await api()
  let token = "", calls = 0, fail = true
  const model = createOrdersModel({ getToken: () => token, request: async () => { calls++; if (fail) throw new Error("网络连接失败"); return [] } })
  await model.load()
  assert.equal(model.state.guest, true)
  assert.equal(calls, 0)
  token = "token"
  await model.load()
  assert.equal(model.state.error, "网络连接失败")
  assert.equal(model.state.loading, false)
  assert.deepEqual(model.state.orders, [])
  fail = false
  await model.load()
  assert.equal(model.state.error, "")
  assert.equal(model.state.guest, false)
  assert.deepEqual(model.state.orders, [])
})

test("details use existing endpoints, isolate errors and support retry", async () => {
  const { createOrdersModel } = await api()
  let fail = true
  const paths = []
  const model = createOrdersModel({ getToken: () => "token", request: async path => {
    paths.push(path)
    if (path === "/orders") return [ticket, room, recharge]
    if (path === "/tickets/orders/T1") { if (fail) throw new Error("详情暂不可用"); return { visit_date: "2026-11-13", tickets: [] } }
    if (path === "/rooms/bookings/b2") return { visit_date: "2026-11-14" }
    throw new Error("Unexpected endpoint")
  } })
  await model.load()
  assert.equal(model.state.details.T1.error, "详情暂不可用")
  assert.equal(model.state.details.P1.data.visit_date, "2026-11-14")
  assert.equal(paths.length, 3)
  fail = false
  await model.toggle(ticket)
  assert.equal(model.state.expanded, "T1")
  assert.equal(model.state.details.T1.data.visit_date, "2026-11-13")
  await model.toggle(ticket)
  assert.equal(model.state.expanded, "")
})

test("detail prefetch is bounded and stale responses cannot repopulate a hidden page", async () => {
  const { createOrdersModel } = await api()
  let active = 0, peak = 0
  const model = createOrdersModel({ getToken: () => "token", request: async path => {
    if (path === "/orders") return Array.from({ length: 9 }, (_, i) => ({ ...ticket, order_no: `T${i}` }))
    active++; peak = Math.max(peak, active)
    await new Promise(resolve => setTimeout(resolve, 2))
    active--; return { tickets: [] }
  } })
  await model.load()
  assert.ok(peak <= 3)
  assert.equal(Object.keys(model.state.details).length, 9)
  let release
  const stale = createOrdersModel({ getToken: () => "token", request: () => new Promise(resolve => { release = resolve }) })
  const loading = stale.load()
  stale.invalidate()
  release([ticket])
  await loading
  assert.deepEqual(stale.state.orders, [])
})

test("a late detail response is discarded after page invalidation", async () => {
  const { createOrdersModel } = await api()
  let release
  const model = createOrdersModel({ getToken: () => "token", request: async path => {
    if (path === "/orders") return [ticket]
    return new Promise(resolve => { release = resolve })
  } })
  const pending = model.load()
  await new Promise(resolve => setTimeout(resolve, 0))
  model.invalidate()
  release({ visit_date: "2026-11-13", tickets: [] })
  await pending
  assert.deepEqual(model.state.details, {})
  assert.deepEqual(model.state.orders, [])
})
