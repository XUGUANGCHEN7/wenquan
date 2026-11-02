function updateCart(counts, index, delta) {
  const next = counts.slice()
  next[index] = Math.max(0, (next[index] || 0) + delta)
  return next
}

function cartTotal(items, counts) {
  return items.reduce((total, item, index) => total + item.price_cents * (counts[index] || 0), 0)
}
module.exports = { updateCart, cartTotal }
