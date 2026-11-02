import { describe, expect, it } from "vitest"
import { formatDateTime, formatMoney, parseYuanToCents, statusText } from "./format"

describe("operations formatting", () => {
  it("formats integer cents without floating point", () => {
    expect(formatMoney(2900)).toBe("29.00")
    expect(formatMoney(5)).toBe("0.05")
    expect(formatMoney(-105)).toBe("-1.05")
  })

  it("parses yuan strings to integer cents without floating-point drift", () => {
    expect(parseYuanToCents("29")).toBe(2900)
    expect(parseYuanToCents("29.5")).toBe(2950)
    expect(parseYuanToCents("0.05")).toBe(5)
    expect(parseYuanToCents("0.1")).toBe(10)
    expect(parseYuanToCents("29.999")).toBeNull()
    expect(parseYuanToCents("-1.00")).toBeNull()
  })

  it("uses readable status and safe empty dates", () => {
    expect(statusText("UNKNOWN")).toBe("结果未知")
    expect(statusText("CUSTOM_STATE")).toBe("CUSTOM_STATE")
    expect(formatDateTime(null)).toBe("—")
  })
})
