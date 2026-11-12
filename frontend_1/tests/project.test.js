import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const src = path.join(root, "src")

test("member uni-app contains only member, ticket and private-room pages", () => {
  const pages = JSON.parse(fs.readFileSync(path.join(src, "pages.json"), "utf8"))
  assert.deepEqual(pages.pages.map((page) => page.path), [
    "pages/home/index", "pages/tickets/index", "pages/private-room/index",
    "pages/orders/index", "pages/mine/index", "pages/wallet/index",
  ])
  for (const page of pages.pages) {
    assert.ok(fs.existsSync(path.join(src, `${page.path}.vue`)), `${page.path}.vue`)
  }
  assert.ok(!pages.pages.some((page) => page.path.includes("menu") || page.path.includes("merchants")))
  assert.equal(pages.tabBar.list.length, 3)
})

test("member uni-app does not contain credentials or stale business prices", () => {
  const files = []
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (["node_modules", "tests"].includes(entry.name)) continue
      const target = path.join(directory, entry.name)
      if (entry.isDirectory()) walk(target)
      else if (/\.(js|json|vue|css)$/.test(entry.name)) files.push(target)
    }
  }
  walk(src)
  const source = files.map((file) => fs.readFileSync(file, "utf8")).join("\n")
  assert.ok(!source.includes("mcp.amap.com"))
  assert.ok(!source.includes("12/20"))
  assert.ok(!source.includes("¥398"))
  const manifest = JSON.parse(fs.readFileSync(path.join(src, "manifest.json"), "utf8"))
  const appid = manifest["mp-weixin"].appid
  assert.notEqual(appid, "touristappid")
  assert.match(appid, /^wx[0-9a-f]{16}$/)
  const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"))
  assert.equal(packageJson.scripts["build:mp-weixin"], "uni build -p mp-weixin")
})
