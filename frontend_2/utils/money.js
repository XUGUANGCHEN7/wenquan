function formatMoney(cents) {
  const value = Number.isInteger(cents) ? cents : 0
  const sign = value < 0 ? "-" : ""
  const absolute = Math.abs(value)
  return `${sign}${Math.trunc(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`
}
module.exports = { formatMoney }
