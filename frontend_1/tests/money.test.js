const test = require("node:test")
const assert = require("node:assert/strict")
const { formatMoney, dateInput, dateLabel } = require("../utils/money")

test("formats integer cents without floating point", () => {
  assert.equal(formatMoney(2900), "29.00")
  assert.equal(formatMoney(5), "0.05")
  assert.equal(formatMoney(12000), "120.00")
  assert.equal(formatMoney(-105), "-1.05")
  assert.equal(formatMoney(0), "0.00")
})

test("creates local ISO dates and concise labels", () => {
  const base = new Date(2026, 10, 1, 12)
  assert.equal(dateInput(7, base), "2026-11-08")
  assert.equal(dateLabel("2026-11-01", base), "今天")
  assert.equal(dateLabel("2026-11-02", base), "明天")
  assert.match(dateLabel("2026-11-08", base), /11\/08/)
})
