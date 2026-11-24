import { it, expect } from "vitest"
import { createPrivateVerification } from "./privateVerification"
import type { TicketOrderLookup } from "./ticketVerification"

it("private scans only query; explicit selection is required to verify the same order", async () => {
  let calls = 0
  const order: TicketOrderLookup = { order_no: "PRIVATE1", order_type: "PRIVATE", status: "PAID", amount_cents: 12000,
    payment_method: "WECHAT", created_at: "", paid_at: "", member: null,
    private_booking: { booking_id: "b1", ticket_no: "PV-b1", voucher_status: "UNUSED", booking_status: "CONFIRMED", visit_date: "2026-11-15", start_at: "", end_at: "" } }
  const model = createPrivateVerification({ lookup: async () => structuredClone(order), verify: async () => { calls++; return { room_number: "1" } } })
  model.state.code = "PRIVATE1"
  await model.lookup()
  await model.confirm()
  expect(calls).toBe(0)
  model.state.selected = true
  expect(model.canConfirm.value).toBe(true)
  model.state.code = "PRIVATE2"
  expect(model.canConfirm.value).toBe(false)
  await model.lookup()
  model.state.selected = true
  await model.confirm()
  expect(calls).toBe(1)
  model.dispose()
})

it("used, unpaid and refund-pending private orders cannot be selected for verification", async () => {
  for (const fields of [{ status: "PENDING" }, { refund_application: { status: "PENDING" } }, { private_booking: { voucher_status: "USED", booking_status: "IN_USE" } }]) {
    const order = { order_no: "P1", order_type: "PRIVATE", status: "PAID", private_booking: { voucher_status: "UNUSED", booking_status: "CONFIRMED" }, ...fields } as TicketOrderLookup
    const model = createPrivateVerification({ lookup: async () => order, verify: async () => { throw Error("must not call") } })
    model.state.code = "P1"; await model.lookup(); model.state.selected = true
    expect(model.canConfirm.value).toBe(false)
    model.dispose()
  }
})
