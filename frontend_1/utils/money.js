function formatMoney(cents) {
  const value = Number.isInteger(cents) ? cents : 0
  const sign = value < 0 ? "-" : ""
  const absolute = Math.abs(value)
  return `${sign}${Math.trunc(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`
}

function dateInput(offset = 0, base = new Date()) {
  const date = new Date(base.getFullYear(), base.getMonth(), base.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${date.getFullYear()}-${month}-${day}`
}

function dateLabel(value, base = new Date()) {
  if (value === dateInput(0, base)) return "今天"
  if (value === dateInput(1, base)) return "明天"
  return `${value.slice(5, 7)}/${value.slice(8, 10)}`
}

module.exports = { formatMoney, dateInput, dateLabel }
