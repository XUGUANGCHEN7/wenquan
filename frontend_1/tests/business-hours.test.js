import test from "node:test"
import assert from "node:assert/strict"

test("home displays authoritative venue states and configured hours", async () => {
  const { businessPresentation } = await import("../src/utils/business-hours.js")
  for (const [status, label] of [["OPEN", "今日营业中"], ["NOT_OPEN", "今日未营业"], ["CLOSED", "今日已打烊"], ["REST", "今日休息"]]) {
    const result = businessPresentation({ status, opens_at: "10:30", closes_at: "21:15" })
    assert.equal(result.label, label)
    assert.equal(result.isOpen, status === "OPEN")
    assert.equal(result.hours, "营业时间 10:30—21:15")
  }
})

test("missing or unknown server state never claims the venue is open", async () => {
  const { businessPresentation } = await import("../src/utils/business-hours.js")
  for (const data of [null, {}, { status: "UNKNOWN" }]) {
    assert.equal(businessPresentation(data).label, "营业状态待确认")
    assert.equal(businessPresentation(data).isOpen, false)
    assert.equal(businessPresentation(data).hours, "营业时间待确认")
  }
})
