import { describe, it, expect } from "vitest"
import { createTicketVerification, type TicketOrderLookup } from "./ticketVerification"

const order: TicketOrderLookup = { order_no: "ORDER1", order_type: "TICKET", status: "PAID", amount_cents: 8700,
  payment_method: "WECHAT", created_at: "2026-11-15", paid_at: "2026-11-15", member: null,
  tickets: [
    { ticket_no: "TC1", category: "ADULT", price_cents: 2900, status: "UNUSED", can_admit: true },
    { ticket_no: "TC2", category: "ADULT", price_cents: 2900, status: "UNUSED", can_admit: true },
    { ticket_no: "TC3", category: "ADULT", price_cents: 2900, status: "USED", can_admit: false },
  ] }

describe("ticket selection and batch admission", () => {
  it("starts with no selection and selects only eligible tickets", async () => {
    const model = createTicketVerification({ lookup: async () => order, admit: async () => { throw new Error("unused") } })
    model.state.code = "TC1"
    await model.lookup()
    expect(model.state.order?.order_no).toBe("ORDER1")
    expect(model.canSubmit.value).toBe(false)
    model.selectAll(true)
    expect(model.state.selected).toEqual(["TC1", "TC2"])
    expect(model.canSubmit.value).toBe(true)
    model.state.code = "other-code"
    expect(model.canSubmit.value).toBe(false)
    expect(model.state.selected).toEqual([])
  })

  it("discards a lookup response if the input changed", async () => {
    let resolve!: (value: TicketOrderLookup) => void
    const model = createTicketVerification({ lookup: () => new Promise(r => { resolve = r }), admit: async () => { throw new Error("unused") } })
    model.state.code = "TC1"
    const lookup = model.lookup()
    model.state.code = "TC2"
    resolve(order)
    await lookup
    expect(model.state.order).toBeNull()
    expect(model.canSubmit.value).toBe(false)
  })

  it("reuses an idempotency key after a network error and refreshes after success", async () => {
    const submissions: string[] = []
    let attempts = 0
    const model = createTicketVerification({ lookup: async () => order, admit: async payload => {
      submissions.push(payload.request_id)
      if (attempts++ === 0) throw new Error("网络超时")
      return { order_no: "ORDER1", admitted_count: 2, remaining_tickets: 0, admitted_at: "2026-11-15T10:00:00", admissions: [] }
    } }, () => "stable-batch-id")
    model.state.code = "TC1"
    await model.lookup()
    model.selectAll(true)
    await model.admit()
    expect(model.state.error).toContain("网络超时")
    expect(model.state.selected.length).toBe(2)
    await model.admit()
    expect(submissions).toEqual(["stable-batch-id", "stable-batch-id"])
    expect(model.state.selected).toEqual([])
    expect(model.state.results.length).toBe(1)
    expect(model.state.notice).toContain("2 张")
  })

  it("cannot submit a used ticket even if its checkbox was forged", async () => {
    let posts = 0
    const model = createTicketVerification({ lookup: async () => order, admit: async () => { posts++; throw new Error("unused") } })
    model.state.code = "TC1"
    await model.lookup()
    model.state.selected = ["TC3"]
    await model.admit()
    expect(posts).toBe(0)
    expect(model.canSubmit.value).toBe(false)
  })

  it("refreshes and clears selection on a server state conflict", async () => {
    let lookupCount = 0
    const model = createTicketVerification({
      lookup: async () => lookupCount++ === 0 ? order : { ...order, tickets: order.tickets!.map(ticket => ({ ...ticket, status: "USED", can_admit: false })) },
      admit: async () => { throw Object.assign(new Error("部分票券已核销"), { status: 409 }) },
    })
    model.state.code = "TC1"
    await model.lookup()
    model.selectAll(true)
    await model.admit()
    expect(model.state.error).toContain("部分票券已核销")
    expect(model.state.selected).toEqual([])
    expect(model.eligibleTickets.value).toEqual([])
    expect(model.canSubmit.value).toBe(false)
  })
})
