import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { formatMoney } from "../src/utils/money.js"

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const src = path.join(root, "src")

test("dining page lets guests choose a room and browse merchants on the left", () => {
  const roomPage = fs.readFileSync(path.join(src, "pages", "room", "index.vue"), "utf8")
  assert.match(roomPage, /<picker/)
  assert.match(roomPage, /merchant-rail/)
  assert.match(roomPage, /selectMerchant\(merchant\.id\)/)
  assert.match(roomPage, /\/dining\/rooms/)
  assert.match(roomPage, /\/dining\/merchants/)
  assert.match(roomPage, /\/dining\/menu\?merchant_id=/)
  assert.match(roomPage, /load-error/)
  assert.match(roomPage, /@tap="loadAll"/)
})

test("dining uni-app is independent and room-code based", () => {
  const pages = JSON.parse(fs.readFileSync(path.join(src, "pages.json"), "utf8"))
  assert.deepEqual(pages.pages.map((page) => page.path), ["pages/room/index", "pages/orders/index", "pages/mine/index"])
  for (const page of pages.pages) {
    assert.ok(fs.existsSync(path.join(src, `${page.path}.vue`)), `${page.path}.vue`)
  }
  const manifest = JSON.parse(fs.readFileSync(path.join(src, "manifest.json"), "utf8"))
  const memberManifest = JSON.parse(fs.readFileSync(path.join(root, "..", "frontend_1", "src", "manifest.json"), "utf8"))
  const appid = manifest["mp-weixin"].appid
  assert.match(appid, /^wx[0-9a-f]{16}$/)
  assert.notEqual(appid, "touristappid")
  assert.notEqual(appid, memberManifest["mp-weixin"].appid)
  assert.equal(formatMoney(3800), "38.00")
})
