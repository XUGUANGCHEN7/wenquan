const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const vm = require("node:vm")
const root = path.resolve(process.argv[2] || "dist/dev/mp-weixin")
const code = fs.readFileSync(path.join(root, "components/OrderQrImage.js"), "utf8")
const vendor = fs.readFileSync(path.join(root, "common/vendor.js"), "utf8")
// Source-level tests cannot catch a component paired with a stale shared chunk.
const alias = code.match(/(?:const|var|let)\s+(\w+)\s*=\s*require\(["']\.\.\/common\/vendor\.js["']\)/)?.[1]
assert.ok(alias, "QR component must load its compiled vendor module")
// Production minification can reuse the vendor alias for inner callback locals.
assert.ok(!code.includes(`${alias}.getCurrentInstance`), "QR must not depend on stale composable exports")
assert.ok(code.includes("order-qr-encoder.js"), "QR encoder must be an independent local module")
const required = ["_export_sfc", "e", "t"]
for (const name of required) {
  assert.ok(new RegExp(`exports\\.${name}\\s*=`).test(vendor), `QR runtime dependency missing: ${name}`)
}
console.log(`PASS compiled QR dependencies (${required.length}): ${root}`)

async function verifyWithOldVendor() {
  let component, exported, fills = 0
  const cache = new Map()
  const canvas = { getContext: () => ({ fillRect() { fills++ } }) }
  // Match the failing runtime: no getCurrentInstance or QR factory export.
  const platform = {
    upx2px: value => value / 2, getWindowInfo: () => ({ pixelRatio: 3 }),
    createSelectorQuery() {
      const query = { in: () => query, select: () => query, node: fn => { query.callback = fn; return query }, exec: () => query.callback({ node: canvas }) }
      return query
    },
    canvasToTempFilePath(options) { exported = options; options.success({ tempFilePath: "wxfile://verified-order.png" }) },
  }
  const oldVendor = { index: platform, _export_sfc: component => component }
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports
    const module = { exports: {} }
    cache.set(filename, module)
    const run = vm.runInThisContext(`(function(require,module,exports,wx){${fs.readFileSync(filename, "utf8")}\n})`, { filename })
    run(specifier => {
      const target = path.resolve(path.dirname(filename), specifier)
      return target === path.join(root, "common/vendor.js") ? oldVendor : load(target)
    }, module, module.exports, { createComponent: options => { component = options } })
    return module.exports
  }
  load(path.join(root, "components/OrderQrImage.js"))
  const instance = { ...component.data(), text: "TK20261115144716B9FF2B9A176F", $nextTick: () => Promise.resolve(), $emit: () => {}, ...component.methods }
  await instance.renderCode()
  assert.equal(instance.imagePath, "wxfile://verified-order.png")
  assert.equal(exported.width, 480)
  assert.ok(fills > 100, "compiled local QR encoder must draw a complete QR")
  console.log("PASS compiled QR generation with stale vendor exports")
}
verifyWithOldVendor().catch(error => { console.error(error); process.exitCode = 1 })
