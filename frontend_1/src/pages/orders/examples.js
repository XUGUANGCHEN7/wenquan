// UI-only fixtures. These codes are deliberately not valid backend credentials.
export function createOrderExamples() {
  const visitDate = new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10)
  const records = []
  for (const type of ["TICKET", "PRIVATE", "RECHARGE"]) {
    const stages = type === "RECHARGE" ? ["PENDING", "COMPLETED"] : ["PENDING", "UNUSED", "COMPLETED"]
    for (const stage of stages) {
      const paid = stage !== "PENDING"
      const order = { id: `example-order-${type}-${stage}`, order_no: `EXAMPLE-${type}-${stage}`, order_type: type,
        business_id: `example-${type}-${stage}`, status: paid ? "PAID" : "PENDING",
        amount_cents: type === "TICKET" ? 5800 : type === "PRIVATE" ? 12000 : 20000,
        refund_application: null, example_detail: null }
      order.quantity = type === "TICKET" ? 2 : 1
      order.created_at = `${visitDate}T01:00:00Z`
      order.paid_at = paid ? `${visitDate}T01:01:00Z` : null
      order.paid_amount_cents = paid ? order.amount_cents : 0
      if (type === "RECHARGE") Object.assign(order, { principal_cents: 20000, gift_cents: 2000, credited_cents: paid ? 22000 : 0 })
      if (type === "TICKET") order.example_detail = { visit_date: visitDate, adult_count: 2, child_count: 0, quantity: 2,
        tickets: paid ? [1, 2].map(index => ({ ticket_no: `DEMO-TC-${stage}-${index}`,
          category: "ADULT", status: stage === "UNUSED" ? "UNUSED" : "USED" })) : [] }
      if (type === "PRIVATE") order.example_detail = { visit_date: visitDate,
        booking_id: `example-${type}-${stage}`, slot_count: 1, slot_indices: [0],
        start_at: `${visitDate}T10:00:00`, end_at: `${visitDate}T12:00:00`,
        booking_status: !paid ? "HELD" : stage === "UNUSED" ? "CONFIRMED" : "COMPLETED",
        ticket_no: paid ? `DEMO-PV-${stage}` : null,
        voucher_status: !paid ? null : stage === "UNUSED" ? "UNUSED" : "USED",
        room_number: stage === "COMPLETED" ? "示例01" : null }
      records.push(order)
    }
  }
  return records
}

let exampleOrders
export function getOrderExamples() {
  if (!exampleOrders) exampleOrders = createOrderExamples()
  return exampleOrders
}
