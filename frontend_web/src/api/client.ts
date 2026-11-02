export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public requestId: string,
    public status: number,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
  body?: unknown
  token?: string
  fetcher?: typeof fetch
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "")

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const fetcher = options.fetcher ?? fetch
  const response = await fetcher(`${baseUrl}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  const body = await response.json().catch(() => ({})) as Record<string, unknown>
  if (!response.ok) {
    throw new ApiError(
      String(body.code ?? "HTTP_ERROR"), String(body.message ?? `请求失败（${response.status}）`),
      String(body.request_id ?? response.headers.get("X-Request-ID") ?? "unknown"), response.status,
    )
  }
  return body as T
}
