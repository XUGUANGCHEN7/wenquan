import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import { createRequire } from "node:module"
import { parse, compileScript } from "@vue/compiler-sfc"
import { transformSync } from "esbuild"

const require = createRequire(import.meta.url)
function evaluate(source, loader, imports = require) {
  const module = { exports: {} }
  new Function("require", "module", "exports", transformSync(source, { loader, format: "cjs" }).code)(imports, module, module.exports)
  return module.exports
}
const generator = evaluate(fs.readFileSync(new URL("../src/utils/order-qr-encoder.js", import.meta.url), "utf8"), "js")
const { descriptor } = parse(fs.readFileSync(new URL("../src/components/OrderQrImage.vue", import.meta.url), "utf8"))

test("order QR exports a square image with quiet edges and never displays a native canvas in the card", async () => {
  let exported
  const draws = [], errors = []
  const ctx = { fillStyle: "", fillRect: (...rect) => draws.push({ color: ctx.fillStyle, rect }) }
  const canvas = { getContext: () => ctx }
  globalThis.uni = {
    upx2px: value => value / 2, getWindowInfo: () => ({ pixelRatio: 3 }),
    createSelectorQuery: () => {
      const query = { in: () => query, select: () => query, node: fn => { query.callback = fn; return query }, exec: () => query.callback({ node: canvas }) }
      return query
    },
    canvasToTempFilePath: options => { exported = options; options.success({ tempFilePath: "wxfile://order-qr.png" }) },
  }
  const component = evaluate(compileScript(descriptor, { id: "order-qr-test" }).content, "js", name => {
    assert.notEqual(name, "vue", "QR must work without new vendor composable exports")
    return generator
  }).default
  const state = { ...component.data(), text: "TK20261115143914FB8DEF01F388", $nextTick: () => Promise.resolve(), $emit: (...args) => errors.push(args), ...component.methods }
  await state.renderCode()
  assert.equal(state.imagePath, "wxfile://order-qr.png")
  assert.equal(exported.width, 480)
  assert.equal(exported.height, 480)
  assert.equal(exported.canvas, canvas)
  assert.ok(draws.length > 100)
  for (const { rect: [x, y, width, height] } of draws.slice(1)) {
    assert.ok(x > 0 && y > 0 && x + width < 480 && y + height < 480, "quiet edges must stay white")
  }
  assert.deepEqual(errors, [])
  assert.match(descriptor.template.content, /<image[^>]+class="order-qr-image"/)
  component.beforeUnmount.call(state)
  exported.success({ tempFilePath: "wxfile://stale.png" })
  assert.equal(state.imagePath, "wxfile://order-qr.png")
})
