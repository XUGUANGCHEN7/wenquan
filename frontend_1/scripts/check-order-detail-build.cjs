const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const vm = require("node:vm")
const vue = require("vue")
require("./check-order-qr-build.cjs")

// Exercise the generated page and its shared chunks, not just the Vue source.
const root = path.resolve(process.argv[2] || "dist/dev/mp-weixin")
const app = JSON.parse(fs.readFileSync(path.join(root, "app.json"), "utf8"))
assert.ok(app.pages.includes("pages/orders/detail"), "detail route must be registered")
const wxml = fs.readFileSync(path.join(root, "pages/orders/detail.wxml"), "utf8")
assert.ok(wxml.includes("order-detail-page"), "detail template must be compiled")
assert.ok(!wxml.includes("<text>pages/orders/detail.wxml</text>"), "native placeholder must be absent")

async function check(type) {
  const cache = new Map(), hooks = {}, requests = []
  // Reproduce a development runtime that retained the old list-only chunk.
  // The detail page must initialize without consuming that stale module.
  cache.set(path.join(root, "pages/orders/detail-model.js"), {
    exports: { orderDetailUrl: order => `/pages/orders/detail?id=${order.id}` },
  })
  let page
  const record = { id: `real-${type}`, order_no: `ORDER-${type}`, order_type: type,
    status: "PAID", amount_cents: 5800, paid_amount_cents: 5800, quantity: 2,
    tickets: type === "TICKET" ? [{ ticket_no: "TICKET-1", category: "ADULT", status: "UNUSED" }, { ticket_no: "TICKET-2", category: "ADULT", status: "UNUSED" }] : [],
    booking_id: type === "PRIVATE" ? "booking-1" : undefined,
    ticket_no: type === "PRIVATE" ? "PV-booking-1" : undefined,
    booking_status: "CONFIRMED", voucher_status: "UNUSED", credited_cents: 5800 }
  const vendor = { ...vue, index: { upx2px: value => value / 2 },
    onLoad: fn => { hooks.load = fn }, onShow: fn => { hooks.show = fn },
    onHide() {}, onUnload() {},
    e: (...parts) => Object.assign({}, ...parts), t: value => String(value ?? ""),
    o: fn => fn, p: props => props, f: (items, fn) => items.map(fn),
  }
  function load(filename) {
    filename = path.resolve(filename)
    if (cache.has(filename)) return cache.get(filename).exports
    const module = { exports: {} }
    cache.set(filename, module)
    const localRequire = specifier => {
      const target = path.resolve(path.dirname(filename), specifier)
      if (target === path.join(root, "common/vendor.js")) return vendor
      if (target === path.join(root, "config.js")) return { config: { development: true } }
      if (target === path.join(root, "utils/session.js")) return { getToken: () => "isolated-test-session" }
      if (target === path.join(root, "utils/api.js")) return { request: async url => { requests.push(url); return record } }
      return load(target)
    }
    const run = vm.runInThisContext(`(function(require,module,exports,wx){${fs.readFileSync(filename, "utf8")}\n})`, { filename })
    run(localRequire, module, module.exports, { createPage: options => { page = options } })
    return module.exports
  }
  load(path.join(root, "pages/orders/detail.js"))
  const render = page.setup({})
  hooks.load({ id: record.id })
  await hooks.show()
  const data = render({}, [])
  assert.deepEqual(requests, [`/orders/${record.id}`])
  assert.equal(data.b, false, "loading should finish")
  assert.equal(data.e, "", "page must not have a request error")
  assert.ok(data.h, "detail content branch must be visible")
  assert.ok(JSON.stringify(data).includes(record.order_no), "rendered data must include this order's number")
  console.log(`PASS ${type}: compiled setup, request and render`)
}

;(async () => {
  for (const type of ["TICKET", "PRIVATE", "RECHARGE"]) await check(type)
  console.log(`PASS order detail build: ${root}`)
})().catch(error => { console.error(error); process.exitCode = 1 })
