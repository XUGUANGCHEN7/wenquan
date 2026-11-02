import { request } from "./client"

function token(): string {
  return localStorage.getItem("wenquan_token") ?? ""
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path, { token: token() })
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: "POST", body, token: token() })
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: "PATCH", body, token: token() })
  },
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE", token: token() })
  },
}
