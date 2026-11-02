import { describe, expect, it } from "vitest"
import { canAccess, type Role } from "./access"

describe("role route access", () => {
  it("keeps merchant accounts out of finance and hardware operations", () => {
    expect(canAccess(["finance", "admin"], "merchant")).toBe(false)
    expect(canAccess(["frontdesk", "admin"], "merchant")).toBe(false)
  })

  it("allows admin and explicitly assigned operational roles", () => {
    expect(canAccess(["finance", "admin"], "finance")).toBe(true)
    expect(canAccess(["merchant", "frontdesk", "admin"], "merchant")).toBe(true)
    expect(canAccess(undefined, "frontdesk")).toBe(true)
  })

  it("rejects anonymous access to protected routes", () => {
    const role: Role | null = null
    expect(canAccess(["admin"], role)).toBe(false)
  })
})
