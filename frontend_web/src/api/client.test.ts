import { describe, expect, it } from "vitest"
import { ApiError, request } from "./client"

describe("typed API client", () => {
  it("adds the current role token and decodes the stable error envelope", async () => {
    let authorization = ""
    const fetcher: typeof fetch = async (_url, init) => {
      authorization = String((init?.headers as Record<string, string>).Authorization)
      return new Response(JSON.stringify({ code: "RESOURCE_FORBIDDEN", message: "Denied", request_id: "req-web-1" }), {
        status: 403, headers: { "Content-Type": "application/json" },
      })
    }
    const call = request("/operations/wallet/member-demo", { token: "dev-finance", fetcher })
    await expect(call).rejects.toEqual(new ApiError("RESOURCE_FORBIDDEN", "Denied", "req-web-1", 403))
    expect(authorization).toBe("Bearer dev-finance")
  })

  it("returns parsed JSON for successful requests", async () => {
    const fetcher: typeof fetch = async () => new Response(JSON.stringify({ status: "ok" }), {
      status: 200, headers: { "Content-Type": "application/json" },
    })
    await expect(request<{ status: string }>("/health", { fetcher })).resolves.toEqual({ status: "ok" })
  })
})
