const test = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const { formatMoney } = require("../utils/money")

const root = path.resolve(__dirname, "..")

test("dining page lets guests choose a room and browse merchants on the left", () => {
  const wxml = fs.readFileSync(path.join(root, "pages", "room", "index.wxml"), "utf8")
  const script = fs.readFileSync(path.join(root, "pages", "room", "index.js"), "utf8")
  assert.match(wxml, /<picker/)
  assert.match(wxml, /merchant-rail/)
  assert.match(wxml, /bindtap="selectMerchant"/)
  assert.match(script, /\/dining\/rooms/)
  assert.match(script, /\/dining\/merchants/)
  assert.match(script, /\/dining\/menu\?merchant_id=/)
  assert.match(wxml, /load-error/)
  assert.match(wxml, /bindtap="loadAll"/)
})

test("dining mini program is independent and room-code based", () => {
  const app = JSON.parse(fs.readFileSync(path.join(root, "app.json"), "utf8"))
  assert.deepEqual(app.pages, ["pages/room/index", "pages/orders/index", "pages/mine/index"])
  for (const page of app.pages) {
    for (const extension of ["js", "json", "wxml", "wxss"]) {
      assert.ok(fs.existsSync(path.join(root, `${page}.${extension}`)), `${page}.${extension}`)
    }
  }
  const config = JSON.parse(fs.readFileSync(path.join(root, "project.config.json"), "utf8"))
  const memberConfig = JSON.parse(fs.readFileSync(path.join(root, "..", "frontend_1", "project.config.json"), "utf8"))
  assert.match(config.appid, /^wx[0-9a-f]{16}$/)
  assert.notEqual(config.appid, "touristappid")
  assert.notEqual(config.appid, memberConfig.appid)
  assert.equal(formatMoney(3800), "38.00")
})
