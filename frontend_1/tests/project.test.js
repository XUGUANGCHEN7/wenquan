const test = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")

const root = path.resolve(__dirname, "..")

test("member mini program contains only member/ticket/private pages", () => {
  const app = JSON.parse(fs.readFileSync(path.join(root, "app.json"), "utf8"))
  assert.deepEqual(app.pages, [
    "pages/home/index", "pages/tickets/index", "pages/private-room/index",
    "pages/orders/index", "pages/mine/index", "pages/wallet/index"
  ])
  for (const page of app.pages) {
    for (const extension of ["js", "json", "wxml", "wxss"]) {
      assert.ok(fs.existsSync(path.join(root, `${page}.${extension}`)), `${page}.${extension}`)
    }
  }
  assert.ok(!app.pages.some((page) => page.includes("menu") || page.includes("merchants")))
  assert.equal(app.tabBar.list.length, 3)
})

test("project does not contain credentials or stale business prices", () => {
  const files = []
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (["node_modules", "tests"].includes(entry.name)) continue
      const target = path.join(directory, entry.name)
      if (entry.isDirectory()) walk(target)
      else if (/\.(js|json|wxml)$/.test(entry.name)) files.push(target)
    }
  }
  walk(root)
  const source = files.map((file) => fs.readFileSync(file, "utf8")).join("\n")
  assert.ok(!source.includes("mcp.amap.com"))
  assert.ok(!source.includes("12/20"))
  assert.ok(!source.includes("¥398"))
  const config = JSON.parse(fs.readFileSync(path.join(root, "project.config.json"), "utf8"))
  assert.notEqual(config.appid, "touristappid")
  assert.match(config.appid, /^wx[0-9a-f]{16}$/)
})
