import test from "node:test"
import assert from "node:assert/strict"

test("detail status captions follow payment and admission states", async () => {
  const { detailPresentation } = await import("../src/pages/orders/detail-state.js")
  const record = { order_type: "TICKET", status: "PAID", tickets: [{ status: "UNUSED" }] }
  assert.equal(detailPresentation({ ...record, status: "PENDING" }).statusCaption, "请尽快完成支付")
  assert.equal(detailPresentation(record).statusCaption, "请在有效期内核销入园")
  assert.equal(detailPresentation({ ...record, tickets: [{ status: "USED" }] }).statusCaption, "订单已完成，感谢您的光临")
  assert.equal(detailPresentation({ ...record, status: "REFUNDED" }).statusCaption, "退款已完成，请留意到账")
  assert.equal(detailPresentation({ ...record, refund_application: { status: "PENDING" } }).statusCaption, "")
})

test("admission QR contains the real order number only for unused public/private orders", async () => {
  const { detailPresentation } = await import("../src/pages/orders/detail-state.js")
  const ticket = { order_no: "ORDER-QR-TICKET", order_type: "TICKET", status: "PAID", tickets: [{ ticket_no: "T1", status: "UNUSED" }] }
  const privateOrder = { order_no: "ORDER-QR-PRIVATE", order_type: "PRIVATE", status: "PAID", booking_status: "CONFIRMED", voucher_status: "UNUSED" }
  assert.equal(detailPresentation(ticket).qrCodeText, ticket.order_no)
  assert.equal(detailPresentation(privateOrder).qrCodeText, privateOrder.order_no)
  for (const order of [ { ...ticket, status: "PENDING" }, { ...ticket, tickets: [{ ticket_no: "T1", status: "USED" }] },
    { ...ticket, refund_application: { status: "PENDING" } }, { ...privateOrder, voucher_status: "USED" },
    { ...ticket, order_type: "RECHARGE" }, { ...ticket, status: "REFUNDED" } ]) {
    assert.equal(detailPresentation(order).qrCodeText, "")
  }
})

test("detail navigation uses the real id and preserves example isolation", async () => {
  const { orderDetailUrl } = await import("../src/pages/orders/navigation.js")
  assert.equal(orderDetailUrl({ id: "ord-real-2", order_no: "SN2" }), "/pages/orders/detail?id=ord-real-2")
  assert.equal(orderDetailUrl({ order_no: "SN/2" }), "/pages/orders/detail?id=SN%2F2")
  assert.match(orderDetailUrl({ id: "example-2" }, true), /id=example-2&example=1$/)
})

test("detail loads distinct complete records by identity without list state", async () => {
  const { createOrderDetailModel } = await import("../src/pages/orders/detail-state.js")
  const paths = []
  const model = createOrderDetailModel({ getToken: () => "token", request: async path => {
    paths.push(path)
    const id = path.split("/").at(-1)
    return { id, order_no: `NUMBER-${id}`, order_type: "TICKET", status: "PAID", amount_cents: 5800,
      quantity: 2, paid_amount_cents: 5800, tickets: [{ ticket_no: `${id}-T1`, status: "UNUSED" }, { ticket_no: `${id}-T2`, status: "USED" }] }
  } })
  await model.load("id1")
  assert.equal(model.state.order.order_no, "NUMBER-id1")
  assert.equal(model.presentation.value.tickets.length, 2)
  assert.equal(model.presentation.value.tickets[1].ticket_no, "id1-T2")
  await model.load("id2")
  assert.equal(model.state.order.order_no, "NUMBER-id2")
  assert.deepEqual(paths, ["/orders/id1", "/orders/id2"])
})

test("clipboard copies each exact complete identifier and reports failures", async () => {
  const { copyOrderCode } = await import("../src/pages/orders/detail-state.js")
  const copied = [], messages = []
  const platform = { setClipboardData: options => { copied.push(options.data); options.success() }, showToast: options => messages.push(options.title) }
  await copyOrderCode("ORDER-LONG-123456789", platform)
  await copyOrderCode("TICKET-SECOND-987654321", platform)
  assert.deepEqual(copied, ["ORDER-LONG-123456789", "TICKET-SECOND-987654321"])
  assert.deepEqual(messages, ["已复制", "已复制"])
  platform.setClipboardData = options => options.fail()
  await copyOrderCode("code", platform)
  assert.equal(messages.at(-1), "复制失败，请重试")
})

test("recharge and unpaid orders have no empty voucher area", async () => {
  const { detailPresentation } = await import("../src/pages/orders/detail-state.js")
  const recharge = detailPresentation({ order_type: "RECHARGE", status: "PAID", amount_cents: 20000, paid_amount_cents: 20000, credited_cents: 22000 })
  assert.equal(recharge.hasVouchers, false)
  assert.equal(recharge.creditedAmount, "220.00")
  assert.equal(recharge.canRefund, false)
  assert.equal(detailPresentation({ order_type: "TICKET", status: "PENDING", tickets: [] }).hasVouchers, false)
})

test("detail refund reuses the existing endpoint and updates the visible status", async () => {
  const { createOrderDetailModel } = await import("../src/pages/orders/detail-state.js")
  const calls = []
  const model = createOrderDetailModel({ getToken: () => "token", request: async (path, options) => {
    calls.push({ path, options })
    if (options?.method === "POST") return { status: "PENDING", reason: options.data.reason }
    return { id: "private-id", order_no: "PRIVATE-NUMBER", order_type: "PRIVATE", status: "PAID", amount_cents: 12000,
      booking_id: "booking-1", ticket_no: "PV-booking-1", voucher_status: "UNUSED", booking_status: "CONFIRMED" }
  } })
  await model.load("private-id")
  assert.equal(model.presentation.value.canRefund, true)
  await model.submitRefund("行程变化")
  assert.equal(calls[1].path, "/orders/PRIVATE-NUMBER/refund-application")
  assert.equal(model.presentation.value.statusLabel, "退款审核中")
  assert.equal(model.presentation.value.canRefund, false)
})

test("expired authentication during detail loading cannot leave a blank or stale record", async () => {
  const { createOrderDetailModel } = await import("../src/pages/orders/detail-state.js")
  let token = "old-token", release
  const model = createOrderDetailModel({ getToken: () => token, request: () => new Promise(resolve => { release = resolve }) })
  const loading = model.load("order-id")
  token = ""
  release({ id: "order-id", order_no: "private-number", order_type: "TICKET", status: "PAID" })
  await loading
  assert.equal(model.state.guest, true)
  assert.equal(model.state.order, null)
})
