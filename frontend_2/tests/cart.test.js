import test from "node:test"
import assert from "node:assert/strict"
import { updateCart, cartTotal } from "../src/utils/cart.js"

test("cart never goes below zero and totals integer cents", () => {
  const items = [{ price_cents: 3800 }, { price_cents: 1600 }]
  let counts = updateCart([0, 0], 0, 1)
  counts = updateCart(counts, 0, 1)
  counts = updateCart(counts, 1, 1)
  assert.deepEqual(counts, [2, 1])
  assert.equal(cartTotal(items, counts), 9200)
  assert.deepEqual(updateCart(counts, 1, -1), [2, 0])
  assert.deepEqual(updateCart([0, 0], 1, -1), [0, 0])
})
