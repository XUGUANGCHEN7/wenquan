import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import { parse, compileScript } from "@vue/compiler-sfc"
import { transformSync } from "esbuild"
import * as vue from "vue"
import * as money from "../src/utils/money.js"

test("public purchase loads all server prices and submits the selected day type without a visit date", async () => {
  let load
  const sent = [], paid = []
  globalThis.uni = { showModal() {}, showToast() {} }
  const api = { request: async (path, options) => {
    if (path === "/catalog/ticket-products") return [
      { day_type: "WEEKDAY", adult_cents: 3100, child_cents: 1700 },
      { day_type: "HOLIDAY", adult_cents: 5300, child_cents: 2300 },
    ]
    sent.push(options.data)
    return { order_no: "NEW-ORDER", amount_cents: 7600 }
  }, payOrder: async (...args) => { paid.push(args); return { status: "PAID" } }, showError: error => { throw error } }
  const { descriptor } = parse(fs.readFileSync(new URL("../src/pages/tickets/index.vue", import.meta.url), "utf8"))
  const module = { exports: {} }
  const code = transformSync(compileScript(descriptor, { id: "purchase" }).content, { loader: "js", format: "cjs" }).code
  new Function("require", "module", "exports", code)(name => name === "vue" ? vue : name === "@dcloudio/uni-app" ? { onLoad: fn => { load = fn } } : name.endsWith("/api") ? api : money, module, module.exports)
  const state = module.exports.default.setup({}, { expose() {} })
  await load()
  assert.equal(state.total.value, "31.00")
  state.dayType.value = "HOLIDAY"
  state.changeCount("child", 1)
  assert.equal(state.total.value, "76.00")
  await state.submit()
  assert.deepEqual(sent, [{ day_type: "HOLIDAY", adult_count: 1, child_count: 1 }])
  assert.deepEqual(paid, [["NEW-ORDER", "WECHAT"]])
  state.selectPayment("BALANCE")
  assert.equal(state.paymentMethod.value, "BALANCE")
  await state.submit()
  assert.deepEqual(paid[1], ["NEW-ORDER", "BALANCE"])
  state.selectPayment("WECHAT")
  assert.equal(state.paymentMethod.value, "WECHAT")
  state.changeCount("adult", 99)
  assert.equal(state.adult.value + state.child.value, 20)
})

test("dateless order cards show the day type and Beijing expiry date, and expired QR is hidden", async () => {
  const { detailPresentation } = await import("../src/pages/orders/detail-state.js")
  const record = { order_type: "TICKET", order_no: "REAL", status: "PAID", day_type: "WEEKDAY", valid_until: "2026-12-01T18:00:00", tickets: [{ status: "UNUSED", ticket_no: "T1" }] }
  const current = detailPresentation(record)
  assert.match(current.specification, /工作日票/)
  assert.equal(current.date, "有效期至 2026-12-02")
  assert.equal(current.qrCodeText, "REAL")
  const expired = detailPresentation({ ...record, admission_error: { code: "TICKET_EXPIRED" } })
  assert.equal(expired.statusLabel, "已过期")
  assert.equal(expired.qrCodeText, "")
})
